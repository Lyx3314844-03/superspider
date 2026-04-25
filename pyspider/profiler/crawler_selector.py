from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from .site_profiler import SiteProfile, SiteProfiler


@dataclass
class CrawlerSelectionRequest:
    url: str
    content: str = ""
    scenario_hint: Optional[str] = None


@dataclass
class CrawlerSelection:
    scenario: str
    crawler_type: str
    recommended_runner: str
    runner_order: List[str] = field(default_factory=list)
    site_family: str = "generic"
    risk_level: str = "low"
    capabilities: List[str] = field(default_factory=list)
    strategy_hints: List[str] = field(default_factory=list)
    job_templates: List[str] = field(default_factory=list)
    fallback_plan: List[str] = field(default_factory=list)
    stop_conditions: List[str] = field(default_factory=list)
    confidence: float = 0.0
    reason_codes: List[str] = field(default_factory=list)
    profile: Optional[SiteProfile] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CrawlerSelector:
    def __init__(self, profiler: Optional[SiteProfiler] = None) -> None:
        self.profiler = profiler or SiteProfiler()

    def select(self, request: CrawlerSelectionRequest | str, content: str = "") -> CrawlerSelection:
        if isinstance(request, str):
            request = CrawlerSelectionRequest(url=request, content=content)
        html = request.content or content or f"<title>{request.url}</title>"
        profile = self.profiler.profile(request.url, html)
        scenario = request.scenario_hint or self._scenario(profile)
        runner_order = list(profile.runner_order or ["http", "browser"])
        return CrawlerSelection(
            scenario=scenario,
            crawler_type=profile.crawler_type,
            recommended_runner=runner_order[0],
            runner_order=runner_order,
            site_family=profile.site_family,
            risk_level=profile.risk_level,
            capabilities=self._capabilities(profile, runner_order),
            strategy_hints=list(profile.strategy_hints),
            job_templates=list(profile.job_templates),
            fallback_plan=self._fallback_plan(profile, runner_order),
            stop_conditions=self._stop_conditions(profile),
            confidence=self._confidence(profile),
            reason_codes=self._reason_codes(profile),
            profile=profile,
        )

    def _scenario(self, profile: SiteProfile) -> str:
        mapping = {
            "login_session": "authenticated_session",
            "infinite_scroll_listing": "infinite_scroll_listing",
            "ecommerce_search": "ecommerce_listing",
            "ecommerce_detail": "ecommerce_detail",
            "hydrated_spa": "javascript_hydrated_page",
            "api_bootstrap": "embedded_api_or_bootstrap_json",
            "search_results": "search_results",
            "static_listing": "static_listing",
            "static_detail": "static_detail",
        }
        return mapping.get(profile.crawler_type, "generic_page")

    def _capabilities(self, profile: SiteProfile, runner_order: List[str]) -> List[str]:
        signals = profile.signals
        capabilities: List[str] = []
        if "http" in runner_order:
            capabilities.append("http_fetch")
        if "browser" in runner_order:
            capabilities.append("browser_rendering")
        if signals.get("has_pagination"):
            capabilities.append("pagination")
        if signals.get("has_infinite_scroll"):
            capabilities.append("scroll_automation")
        if signals.get("has_login"):
            capabilities.append("session_cookies")
        if signals.get("has_api_bootstrap") or signals.get("has_graphql"):
            capabilities.append("network_or_bootstrap_json")
        if signals.get("has_price") or signals.get("has_product_schema"):
            capabilities.append("commerce_fields")
        if signals.get("has_captcha"):
            capabilities.append("anti_bot_evidence")
        if profile.page_type == "detail":
            capabilities.append("detail_extraction")
        if profile.page_type == "list":
            capabilities.append("listing_extraction")
        return self._dedupe(capabilities)

    def _fallback_plan(self, profile: SiteProfile, runner_order: List[str]) -> List[str]:
        if runner_order[0] == "browser":
            plan = [
                "render with browser and save DOM, screenshot, and network artifacts",
                "promote stable JSON/API responses into HTTP replay jobs",
                "fall back to DOM selectors only after bootstrap/network data is empty",
            ]
        else:
            plan = [
                "start with HTTP fetch and schema/meta/bootstrap extraction",
                "fall back to browser rendering when required fields are missing",
                "persist raw HTML and normalized fields for selector regression tests",
            ]
        if profile.signals.get("has_captcha"):
            plan.append("stop on captcha/challenge pages and return evidence instead of bypassing blindly")
        if profile.crawler_type == "login_session":
            plan.append("establish authenticated storage state before queueing follow-up URLs")
        return plan

    def _stop_conditions(self, profile: SiteProfile) -> List[str]:
        if profile.crawler_type == "infinite_scroll_listing":
            return [
                "stop after two unchanged DOM or item-count snapshots",
                "stop when network responses repeat without new item IDs",
                "respect configured max pages/items/time budget",
            ]
        if profile.page_type == "list":
            return [
                "stop when next-page URL repeats or disappears",
                "stop when item URLs no longer add new fingerprints",
                "respect configured max pages/items/time budget",
            ]
        if profile.crawler_type == "login_session":
            return [
                "stop if post-login page still contains password or captcha signals",
                "stop when authenticated session storage cannot be established",
            ]
        return [
            "stop after required fields are present and normalized",
            "stop when HTTP and browser surfaces both produce empty required fields",
        ]

    def _confidence(self, profile: SiteProfile) -> float:
        score = 0.55
        if profile.crawler_type != "generic_http":
            score += 0.15
        if profile.site_family != "generic":
            score += 0.1
        if profile.candidate_fields:
            score += 0.05
        if len(profile.runner_order) > 1:
            score += 0.05
        if profile.risk_level == "medium":
            score -= 0.05
        elif profile.risk_level == "high":
            score -= 0.15
        return round(max(0.2, min(0.95, score)), 2)

    def _reason_codes(self, profile: SiteProfile) -> List[str]:
        reasons = [
            f"crawler_type:{profile.crawler_type}",
            f"page_type:{profile.page_type}",
            f"site_family:{profile.site_family}",
            f"risk:{profile.risk_level}",
        ]
        reasons.extend(f"signal:{name}" for name, enabled in profile.signals.items() if enabled)
        return self._dedupe(reasons)

    def _dedupe(self, values: List[str]) -> List[str]:
        result: List[str] = []
        for value in values:
            if value not in result:
                result.append(value)
        return result
