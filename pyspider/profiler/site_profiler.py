import re
from dataclasses import dataclass, field
from typing import Dict, List
from urllib.parse import parse_qs, urlparse


@dataclass
class SiteProfile:
    url: str
    page_type: str
    site_family: str = "generic"
    signals: Dict[str, bool] = field(default_factory=dict)
    candidate_fields: List[str] = field(default_factory=list)
    risk_level: str = "low"
    crawler_type: str = "generic_http"
    runner_order: List[str] = field(default_factory=list)
    strategy_hints: List[str] = field(default_factory=list)
    job_templates: List[str] = field(default_factory=list)


class SiteProfiler:
    def profile(self, url: str, content: str) -> SiteProfile:
        lower = content.lower()
        compact = re.sub(r"\s+", "", lower)
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        url_lower = url.lower()
        site_family = self._site_family(parsed.netloc.lower())

        has_search_query = any(
            key in query for key in ("q", "query", "keyword", "search", "wd")
        ) or any(token in url_lower for token in ("/search", "search?", "keyword="))
        signals = {
            "has_form": "<form" in lower,
            "has_pagination": (
                "next" in lower
                or "page=" in lower
                or "pagination" in lower
                or "pager" in lower
                or "下一页" in content
            ),
            "has_list": (
                "<li" in lower
                or "<ul" in lower
                or "<ol" in lower
                or "product-list" in lower
                or "productlist" in lower
                or "goods-list" in lower
                or "sku-item" in lower
            ),
            "has_detail": "<article" in lower or "<h1" in lower,
            "has_captcha": (
                "captcha" in lower
                or "verify" in lower
                or "human verification" in lower
                or "滑块" in content
                or "验证码" in content
            ),
            "has_price": (
                "price" in lower
                or '"price"' in lower
                or "￥" in content
                or "¥" in content
                or "价格" in content
            ),
            "has_search": (
                has_search_query
                or 'type="search"' in lower
                or "搜索" in content
                or "search-input" in lower
            ),
            "has_login": (
                'type="password"' in lower
                or "sign in" in lower
                or "signin" in lower
                or "登录" in content
            ),
            "has_hydration": any(
                token in lower
                for token in (
                    "__next_data__",
                    "__next_f",
                    "__nuxt__",
                    "__apollo_state__",
                    "__initial_state__",
                    "__preloaded_state__",
                    "window.__initial_data__",
                )
            ),
            "has_api_bootstrap": any(
                token in lower
                for token in (
                    "__initial_state__",
                    "__preloaded_state__",
                    "__next_data__",
                    "__apollo_state__",
                    "application/json",
                    "window.__initial_data__",
                )
            ),
            "has_infinite_scroll": any(
                token in lower
                for token in (
                    "load more",
                    "infinite",
                    "intersectionobserver",
                    "onscroll",
                    "scrolltolower",
                    "virtual-list",
                )
            )
            or "加载更多" in content,
            "has_graphql": "graphql" in lower,
            "has_reviews": "review" in lower or "评价" in content or "comments" in lower,
            "has_product_schema": '"@type":"product"' in compact
            or '"@type":"offer"' in compact,
            "has_cart": (
                "add to cart" in lower
                or "购物车" in content
                or "buy-now" in lower
                or "立即购买" in content
            ),
            "has_sku": (
                "sku" in lower
                or "商品编号" in content
                or "item.jd.com" in url_lower
                or "/item.htm" in url_lower
            ),
            "has_image": "<img" in lower or "og:image" in lower,
        }

        crawler_type = self._crawler_type(signals, parsed.path.lower())

        if crawler_type in {
            "static_listing",
            "search_results",
            "ecommerce_search",
            "infinite_scroll_listing",
        }:
            page_type = "list"
        elif crawler_type in {"static_detail", "ecommerce_detail"} or signals[
            "has_detail"
        ]:
            page_type = "detail"
        else:
            page_type = "generic"

        candidate_fields: List[str] = []
        if "<title" in lower:
            candidate_fields.append("title")
        if signals["has_price"]:
            candidate_fields.append("price")
        if "author" in lower or "作者" in content:
            candidate_fields.append("author")
        if signals["has_sku"]:
            candidate_fields.append("sku")
        if signals["has_reviews"]:
            candidate_fields.append("rating")
        if signals["has_search"]:
            candidate_fields.append("keyword")
        if signals["has_image"]:
            candidate_fields.append("image")
        if "shop" in lower or "seller" in lower or "店铺" in content:
            candidate_fields.append("shop")
        if "description" in lower or "详情" in content:
            candidate_fields.append("description")

        risk_level = (
            "high"
            if signals["has_captcha"]
            else (
                "medium"
                if parsed.scheme == "https"
                and (
                    signals["has_form"]
                    or signals["has_login"]
                    or signals["has_hydration"]
                    or signals["has_graphql"]
                )
                else "low"
            )
        )
        runner_order = self._runner_order(crawler_type, signals)
        return SiteProfile(
            url=url,
            page_type=page_type,
            site_family=site_family,
            signals=signals,
            candidate_fields=self._dedupe(candidate_fields),
            risk_level=risk_level,
            crawler_type=crawler_type,
            runner_order=runner_order,
            strategy_hints=self._strategy_hints(crawler_type, signals),
            job_templates=self._job_templates(crawler_type, site_family),
        )

    def _site_family(self, host: str) -> str:
        mapping = {
            "jd.com": "jd",
            "3.cn": "jd",
            "taobao.com": "taobao",
            "tmall.com": "tmall",
            "pinduoduo.com": "pinduoduo",
            "yangkeduo.com": "pinduoduo",
            "xiaohongshu.com": "xiaohongshu",
            "xhslink.com": "xiaohongshu",
            "douyin.com": "douyin-shop",
            "jinritemai.com": "douyin-shop",
        }
        for suffix, family in mapping.items():
            if host == suffix or host.endswith("." + suffix):
                return family
        return "generic"

    def _crawler_type(self, signals: Dict[str, bool], path: str) -> str:
        if signals["has_login"] and not signals["has_detail"]:
            return "login_session"
        if signals["has_infinite_scroll"] and (
            signals["has_list"] or signals["has_search"]
        ):
            return "infinite_scroll_listing"
        if signals["has_price"] and (
            signals["has_cart"] or signals["has_sku"] or signals["has_product_schema"]
        ):
            if signals["has_search"] or (signals["has_list"] and "search" in path):
                return "ecommerce_search"
            if signals["has_list"] and not signals["has_detail"]:
                return "ecommerce_search"
            return "ecommerce_detail"
        if signals["has_hydration"] and (
            signals["has_list"] or signals["has_detail"] or signals["has_search"]
        ):
            return "hydrated_spa"
        if signals["has_api_bootstrap"] or signals["has_graphql"]:
            return "api_bootstrap"
        if signals["has_search"] and (signals["has_list"] or signals["has_pagination"]):
            return "search_results"
        if signals["has_list"] and not signals["has_detail"]:
            return "static_listing"
        if signals["has_detail"]:
            return "static_detail"
        return "generic_http"

    def _runner_order(self, crawler_type: str, signals: Dict[str, bool]) -> List[str]:
        browser_first_types = {
            "hydrated_spa",
            "infinite_scroll_listing",
            "login_session",
            "ecommerce_search",
        }
        if crawler_type in browser_first_types:
            return ["browser", "http"]
        if crawler_type == "ecommerce_detail":
            return (
                ["browser", "http"]
                if signals["has_hydration"]
                else ["http", "browser"]
            )
        if crawler_type in {"api_bootstrap", "static_listing", "static_detail"}:
            return ["http", "browser"]
        return ["http", "browser"]

    def _strategy_hints(
        self, crawler_type: str, signals: Dict[str, bool]
    ) -> List[str]:
        hints: Dict[str, List[str]] = {
            "generic_http": [
                "start with plain HTTP fetch and fall back to browser only if selectors are empty",
                "prefer stable title/meta/schema extraction before custom DOM selectors",
            ],
            "static_listing": [
                "use HTTP mode first and follow pagination links conservatively",
                "dedupe URLs before entering detail pages to avoid list-page churn",
            ],
            "static_detail": [
                "extract title, meta, and structured data before custom selectors",
                "persist raw HTML for selector iteration and regression tests",
            ],
            "search_results": [
                "seed from the search URL and normalize keyword/query parameters",
                "treat listing and detail extraction as separate stages with separate schemas",
            ],
            "ecommerce_search": [
                "start with browser rendering, capture HTML and network payloads, then promote stable fields into HTTP follow-up jobs",
                "split listing fields from detail fields so sku/price/image can be validated independently",
            ],
            "ecommerce_detail": [
                "extract embedded product JSON and schema.org blocks before relying on brittle CSS selectors",
                "keep screenshot and HTML artifacts together for price/title regression checks",
            ],
            "hydrated_spa": [
                "render the page in browser mode and inspect embedded hydration data before DOM scraping",
                "capture network responses and promote repeatable JSON endpoints into secondary HTTP jobs",
            ],
            "api_bootstrap": [
                "inspect script tags and bootstrap JSON before adding browser interactions",
                "extract stable JSON blobs into dedicated parsing rules so DOM churn matters less",
            ],
            "infinite_scroll_listing": [
                "drive a bounded scroll loop and stop when repeated snapshots stop changing",
                "persist network and DOM artifacts so load-more behavior can be replayed without guessing",
            ],
            "login_session": [
                "bootstrap an authenticated session once, then reuse cookies/storage state for follow-up jobs",
                "validate the post-login page shape before starting extraction to avoid scraping the login wall",
            ],
        }
        resolved = list(hints.get(crawler_type, hints["generic_http"]))
        if signals["has_captcha"]:
            resolved.append(
                "treat challenge pages as blockers and capture evidence instead of scraping through them"
            )
        return resolved

    def _job_templates(self, crawler_type: str, site_family: str) -> List[str]:
        shared = ["examples/crawler-types/api-bootstrap-http.json"]
        mapping = {
            "generic_http": ["examples/crawler-types/api-bootstrap-http.json"],
            "static_listing": ["examples/crawler-types/api-bootstrap-http.json"],
            "static_detail": ["examples/crawler-types/api-bootstrap-http.json"],
            "search_results": ["examples/crawler-types/api-bootstrap-http.json"],
            "ecommerce_search": ["examples/crawler-types/ecommerce-search-browser.json"],
            "ecommerce_detail": [
                "examples/crawler-types/ecommerce-search-browser.json",
                "examples/crawler-types/api-bootstrap-http.json",
            ],
            "hydrated_spa": ["examples/crawler-types/hydrated-spa-browser.json"],
            "api_bootstrap": ["examples/crawler-types/api-bootstrap-http.json"],
            "infinite_scroll_listing": [
                "examples/crawler-types/infinite-scroll-browser.json"
            ],
            "login_session": ["examples/crawler-types/login-session-browser.json"],
        }
        templates = list(mapping.get(crawler_type, shared))
        templates.extend(self._site_family_templates(site_family, crawler_type))
        return self._dedupe(templates)

    def _site_family_templates(
        self, site_family: str, crawler_type: str
    ) -> List[str]:
        mapping = {
            ("jd", "ecommerce_detail"): [
                "examples/site-presets/jd-detail-browser.json"
            ],
            ("taobao", "ecommerce_detail"): [
                "examples/site-presets/taobao-detail-browser.json"
            ],
            ("jd", "*"): ["examples/site-presets/jd-search-browser.json"],
            ("taobao", "*"): ["examples/site-presets/taobao-search-browser.json"],
            ("tmall", "*"): ["examples/site-presets/tmall-search-browser.json"],
            ("pinduoduo", "*"): ["examples/site-presets/pinduoduo-search-browser.json"],
            ("xiaohongshu", "*"): ["examples/site-presets/xiaohongshu-feed-browser.json"],
            ("douyin-shop", "*"): ["examples/site-presets/douyin-shop-browser.json"],
        }
        return mapping.get((site_family, crawler_type), mapping.get((site_family, "*"), []))

    def _dedupe(self, values: List[str]) -> List[str]:
        result: List[str] = []
        for value in values:
            if value not in result:
                result.append(value)
        return result
