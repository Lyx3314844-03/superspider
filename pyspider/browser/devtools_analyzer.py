from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlparse

try:
    from bs4 import BeautifulSoup  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    BeautifulSoup = None

from .locator_analyzer import _css_ident, _full_css_path, _full_xpath


@dataclass(frozen=True)
class ElementSnapshot:
    tag: str
    css: str
    xpath: str
    text: str = ""
    attrs: Dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ReverseRecommendation:
    kind: str
    priority: int
    reason: str
    evidence: List[str]


@dataclass(frozen=True)
class DevToolsReport:
    elements: List[ElementSnapshot]
    script_sources: List[str]
    inline_script_samples: List[str]
    network_candidates: List[Dict[str, Any]]
    console_events: List[Dict[str, Any]]
    reverse_recommendations: List[ReverseRecommendation]
    summary: Dict[str, Any]

    def best_reverse_route(self) -> Optional[ReverseRecommendation]:
        return self.reverse_recommendations[0] if self.reverse_recommendations else None


class DevToolsAnalyzer:
    """Analyze browser/F12 artifacts and choose Node.js reverse-analysis routes."""

    IMPORTANT_ATTRS = [
        "id",
        "class",
        "name",
        "type",
        "href",
        "src",
        "role",
        "aria-label",
        "data-testid",
        "data-test",
        "placeholder",
        "action",
        "method",
    ]

    def analyze(
        self,
        html: str,
        network_events: Optional[Iterable[Dict[str, Any]]] = None,
        console_events: Optional[Iterable[Dict[str, Any]]] = None,
    ) -> DevToolsReport:
        if BeautifulSoup is None:
            return DevToolsReport([], [], [], [], list(console_events or []), [], {"element_count": 0})

        soup = BeautifulSoup(html or "", "html.parser")
        elements = [_snapshot_element(element) for element in soup.find_all(True)]
        script_sources, inline_samples = _script_artifacts(soup)
        network = _network_candidates(network_events or [])
        recommendations = _recommend_reverse_routes(html or "", script_sources, inline_samples, network)
        summary = {
            "element_count": len(elements),
            "script_count": len(script_sources) + len(inline_samples),
            "network_candidate_count": len(network),
            "best_reverse_route": recommendations[0].kind if recommendations else "",
        }
        return DevToolsReport(elements, script_sources, inline_samples, network, list(console_events or []), recommendations, summary)


def _snapshot_element(element: Any) -> ElementSnapshot:
    attrs: Dict[str, str] = {}
    for name in DevToolsAnalyzer.IMPORTANT_ATTRS:
        value = element.get(name)
        if value is None:
            continue
        if isinstance(value, list):
            attrs[name] = " ".join(str(item) for item in value)
        else:
            attrs[name] = str(value)
    return ElementSnapshot(
        tag=element.name or "",
        css=_full_css_path(element),
        xpath=_full_xpath(element),
        text=element.get_text(" ", strip=True)[:120],
        attrs=attrs,
    )


def _script_artifacts(soup: Any) -> tuple[List[str], List[str]]:
    sources: List[str] = []
    inline_samples: List[str] = []
    for script in soup.find_all("script"):
        src = str(script.get("src", "")).strip()
        if src:
            sources.append(src)
            continue
        code = (script.string or script.get_text() or "").strip()
        if code:
            inline_samples.append(code[:2000])
    return sources, inline_samples


def _network_candidates(events: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for event in events:
        url = str(event.get("url", ""))
        if not url or url in seen:
            continue
        resource_type = str(event.get("resource_type", event.get("type", ""))).lower()
        signal = f"{url} {resource_type}".lower()
        if (
            resource_type in {"script", "xhr", "fetch", "websocket", "document"}
            or any(token in signal for token in ["api", "sign", "token", "encrypt", "decrypt", "jsonp", "webpack"])
        ):
            seen.add(url)
            result.append(
                {
                    "url": url,
                    "method": event.get("method", ""),
                    "status": event.get("status", ""),
                    "resource_type": resource_type,
                    "host": urlparse(url).netloc,
                }
            )
    return result


def _recommend_reverse_routes(
    html: str,
    script_sources: List[str],
    inline_samples: List[str],
    network: List[Dict[str, Any]],
) -> List[ReverseRecommendation]:
    corpus = "\n".join([html[:8000], *script_sources, *inline_samples, *(str(item.get("url", "")) for item in network)]).lower()
    recommendations: Dict[str, ReverseRecommendation] = {}

    def add(kind: str, priority: int, reason: str, markers: List[str]) -> None:
        evidence = [marker for marker in markers if marker.lower() in corpus]
        if evidence:
            recommendations[kind] = ReverseRecommendation(kind, priority, reason, evidence[:8])

    add("analyze_crypto", 100, "发现加密、签名或摘要相关标记，优先交给 Node.js crypto 逆向分析", ["cryptojs", "crypto.subtle", "aes", "rsa", "md5", "sha1", "sha256", "encrypt", "decrypt", "signature", "sign"])
    add("analyze_webpack", 90, "发现 webpack 模块运行时，适合进入模块表和导出函数逆向", ["__webpack_require__", "webpackjsonp", "webpackchunk", "webpack://"])
    add("simulate_browser", 80, "脚本依赖浏览器运行时对象，适合用 Node.js 浏览器环境模拟", ["localstorage", "sessionstorage", "navigator.", "document.", "window.", "canvas", "webdriver"])
    add("analyze_ast", 60, "存在外链或内联脚本，适合进行 AST 结构分析和函数定位", [".js", "function", "=>", "eval(", "new function"])

    return sorted(recommendations.values(), key=lambda item: (-item.priority, item.kind))
