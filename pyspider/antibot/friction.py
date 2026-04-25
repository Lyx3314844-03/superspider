"""Compliant access-friction profiling for difficult crawl targets.

The analyzer does not bypass challenges. It classifies responses and returns
operational next steps such as honoring Retry-After, reducing request rate,
switching to a rendered browser capture, or stopping for human authorization.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from email.utils import parsedate_to_datetime
from typing import Dict, Iterable, List, Mapping, Optional


@dataclass(frozen=True)
class AccessFrictionReport:
    level: str
    signals: List[str] = field(default_factory=list)
    recommended_actions: List[str] = field(default_factory=list)
    retry_after_seconds: Optional[int] = None
    should_upgrade_to_browser: bool = False
    requires_human_access: bool = False
    challenge_handoff: Dict[str, object] = field(default_factory=dict)
    capability_plan: Dict[str, object] = field(default_factory=dict)

    @property
    def blocked(self) -> bool:
        return self.level in {"medium", "high"}

    def to_dict(self) -> Dict[str, object]:
        return {
            "level": self.level,
            "signals": list(self.signals),
            "recommended_actions": list(self.recommended_actions),
            "retry_after_seconds": self.retry_after_seconds,
            "should_upgrade_to_browser": self.should_upgrade_to_browser,
            "requires_human_access": self.requires_human_access,
            "challenge_handoff": dict(self.challenge_handoff),
            "capability_plan": dict(self.capability_plan),
            "blocked": self.blocked,
        }


def analyze_access_friction(
    html: str = "",
    status_code: int = 200,
    headers: Optional[Mapping[str, str]] = None,
    url: str = "",
) -> AccessFrictionReport:
    normalized_headers = _normalize_headers(headers or {})
    haystack = "\n".join([url, html, "\n".join(f"{k}: {v}" for k, v in normalized_headers.items())]).lower()
    signals: List[str] = []

    if status_code in {401, 403}:
        signals.append("auth-or-forbidden")
    if status_code == 429:
        signals.append("rate-limited")
    if status_code in {503, 520, 521, 522}:
        signals.append("temporary-gateway-or-challenge")

    _collect_keyword_signals(
        signals,
        haystack,
        {
            "captcha": ("captcha", "recaptcha", "hcaptcha", "turnstile", "验证码", "滑块"),
            "slider-captcha": ("geetest", "gt_captcha", "nc_token", "aliyuncaptcha", "tencentcaptcha", "滑块验证", "拖动滑块"),
            "managed-browser-challenge": ("cf-chl", "checking your browser", "browser verification", "challenge-platform", "please enable javascript"),
            "request-blocked": ("access denied", "request blocked", "request rejected", "被拒绝", "封禁", "访问过于频繁"),
            "auth-required": ("login", "sign in", "扫码", "登录", "安全验证"),
            "waf-vendor": ("cloudflare", "akamai", "imperva", "datadome", "perimeterx", "aliyun", "tencent", "bytedance", "dun.163"),
            "risk-control": ("risk control", "风险", "异常访问", "suspicious activity", "环境异常", "账号存在风险"),
            "js-signature": ("x-bogus", "a_bogus", "msToken", "m_h5_tk", "h5st", "_signature", "cryptojs", "__webpack_require__", "webpackchunk"),
            "fingerprint-required": ("navigator.webdriver", "canvas fingerprint", "webgl", "deviceid", "fpcollect", "sec-ch-ua"),
        },
    )
    html_lower = (html or "").lower()
    if status_code == 200 and html and len(html.strip()) < 300 and (
        "<script" in html_lower or "enable javascript" in html_lower or "window.location" in html_lower
    ):
        signals.append("empty-or-script-shell")

    if "retry-after" in normalized_headers:
        signals.append("retry-after")
    if any(header in normalized_headers for header in ("cf-ray", "x-datadome", "x-akamai-transformed")):
        signals.append("waf-vendor")

    signals = _dedupe(signals)
    retry_after = _parse_retry_after(normalized_headers.get("retry-after"))
    level = _level_for(status_code, signals)
    actions = _recommended_actions(signals, retry_after)

    return AccessFrictionReport(
        level=level,
        signals=signals,
        recommended_actions=actions,
        retry_after_seconds=retry_after,
        should_upgrade_to_browser=any(
            signal in signals
            for signal in (
                "managed-browser-challenge",
                "captcha",
                "slider-captcha",
                "auth-required",
                "waf-vendor",
                "js-signature",
                "fingerprint-required",
                "empty-or-script-shell",
            )
        ),
        requires_human_access=any(signal in signals for signal in ("captcha", "slider-captcha", "auth-required")),
        challenge_handoff=_challenge_handoff(signals),
        capability_plan=_capability_plan(level, signals, retry_after),
    )


def _normalize_headers(headers: Mapping[str, str]) -> Dict[str, str]:
    return {str(key).lower(): str(value) for key, value in headers.items()}


def _collect_keyword_signals(signals: List[str], haystack: str, groups: Mapping[str, Iterable[str]]) -> None:
    for signal, patterns in groups.items():
        if any(pattern.lower() in haystack for pattern in patterns):
            signals.append(signal)


def _dedupe(items: Iterable[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _parse_retry_after(value: Optional[str]) -> Optional[int]:
    if not value:
        return None
    value = value.strip()
    if value.isdigit():
        return max(0, int(value))
    try:
        retry_at = parsedate_to_datetime(value)
        from datetime import datetime, timezone

        now = datetime.now(tz=retry_at.tzinfo or timezone.utc)
        return max(0, int((retry_at - now).total_seconds()))
    except Exception:
        return None


def _level_for(status_code: int, signals: List[str]) -> str:
    if any(signal in signals for signal in ("captcha", "slider-captcha", "auth-required", "request-blocked")):
        return "high"
    if status_code in {401, 403, 429}:
        return "high"
    if any(signal in signals for signal in ("managed-browser-challenge", "waf-vendor", "risk-control", "js-signature", "fingerprint-required", "empty-or-script-shell")):
        return "medium"
    if signals:
        return "low"
    return "none"


def _recommended_actions(signals: List[str], retry_after: Optional[int]) -> List[str]:
    actions: List[str] = []
    if retry_after is not None or "rate-limited" in signals:
        actions.extend(["honor-retry-after", "reduce-concurrency", "increase-crawl-delay"])
    if any(signal in signals for signal in ("managed-browser-challenge", "waf-vendor", "empty-or-script-shell")):
        actions.extend(["render-with-browser", "persist-session-state", "capture-html-screenshot-har"])
    if any(signal in signals for signal in ("js-signature", "fingerprint-required")):
        actions.extend(["capture-devtools-network", "run-nodejs-reverse-analysis", "replay-authorized-session-only"])
    if any(signal in signals for signal in ("captcha", "slider-captcha", "auth-required")):
        actions.extend(["pause-for-human-access", "document-authorization-requirement"])
    if "request-blocked" in signals:
        actions.append("stop-or-seek-site-permission")
    actions.append("respect-robots-and-terms")
    return _dedupe(actions)


def _challenge_handoff(signals: List[str]) -> Dict[str, object]:
    required = any(signal in signals for signal in ("captcha", "slider-captcha", "auth-required", "risk-control"))
    if not required:
        return {"required": False, "method": "none", "resume": "automatic"}
    return {
        "required": True,
        "method": "human-authorized-browser-session",
        "resume": "after-challenge-cleared-and-session-persisted",
        "artifacts": ["screenshot", "html", "cookies-or-storage-state", "network-summary"],
        "stop_conditions": ["explicit-access-denied", "robots-disallow", "missing-site-permission"],
    }


def _capability_plan(level: str, signals: List[str], retry_after: Optional[int]) -> Dict[str, object]:
    transport_order = ["http"]
    if any(signal in signals for signal in ("managed-browser-challenge", "waf-vendor", "captcha", "slider-captcha", "auth-required", "empty-or-script-shell")):
        transport_order.extend(["browser-render", "authorized-session-replay"])
    if any(signal in signals for signal in ("js-signature", "fingerprint-required")):
        transport_order.extend(["devtools-analysis", "node-reverse-analysis"])
    if "request-blocked" in signals:
        transport_order.append("stop-until-permission")

    crawl_delay_seconds = retry_after if retry_after is not None else 1
    if level == "medium":
        crawl_delay_seconds = max(crawl_delay_seconds, 5)
    if level == "high":
        crawl_delay_seconds = max(crawl_delay_seconds, 30)

    return {
        "mode": "maximum-compliant",
        "transport_order": _dedupe(transport_order),
        "throttle": {
            "concurrency": 1 if level in {"medium", "high"} else 2,
            "crawl_delay_seconds": crawl_delay_seconds,
            "jitter_ratio": 0.35,
            "honor_retry_after": True,
        },
        "session": {
            "persist_storage_state": True,
            "reuse_only_after_authorized_access": any(
                signal in signals for signal in ("captcha", "slider-captcha", "auth-required", "risk-control")
            ),
            "isolate_by_site": True,
        },
        "artifacts": ["html", "screenshot", "cookies-or-storage-state", "network-summary", "friction-report"],
        "retry_budget": 0 if "request-blocked" in signals else (1 if level == "high" else 2),
        "stop_conditions": ["robots-disallow", "explicit-access-denied", "missing-site-permission"],
    }
