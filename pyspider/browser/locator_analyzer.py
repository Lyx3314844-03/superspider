from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

try:
    from bs4 import BeautifulSoup  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    BeautifulSoup = None


@dataclass(frozen=True)
class LocatorTarget:
    tag: str = ""
    text: str = ""
    role: str = ""
    name: str = ""
    placeholder: str = ""
    attr: str = ""
    value: str = ""

    @classmethod
    def for_text(cls, text: str, tag: str = "") -> "LocatorTarget":
        return cls(tag=tag, text=text)

    @classmethod
    def for_field(cls, name: str) -> "LocatorTarget":
        return cls(name=name)


@dataclass(frozen=True)
class LocatorCandidate:
    kind: str
    expr: str
    score: int
    reason: str

    def playwright_selector(self) -> str:
        return f"xpath={self.expr}" if self.kind == "xpath" else self.expr


@dataclass(frozen=True)
class LocatorPlan:
    candidates: List[LocatorCandidate]

    def best(self) -> Optional[LocatorCandidate]:
        return self.candidates[0] if self.candidates else None


class LocatorAnalyzer:
    def analyze(self, html: str, target: LocatorTarget) -> LocatorPlan:
        if BeautifulSoup is None:
            return LocatorPlan([])
        soup = BeautifulSoup(html or "", "html.parser")
        candidates: Dict[tuple[str, str], LocatorCandidate] = {}
        for element in soup.find_all(True):
            score = _match_score(element, target)
            if score <= 0:
                continue
            for candidate in _element_candidates(soup, element, score):
                key = (candidate.kind, candidate.expr)
                current = candidates.get(key)
                if current is None or candidate.score > current.score:
                    candidates[key] = candidate
        ordered = sorted(candidates.values(), key=lambda item: (-item.score, item.kind, item.expr))
        return LocatorPlan(ordered)


def _match_score(element: Any, target: LocatorTarget) -> int:
    score = 0
    tag = (element.name or "").lower()
    if target.tag and target.tag.lower() != tag:
        return 0
    if target.tag:
        score += 2
    text = element.get_text(" ", strip=True)
    if target.text:
        if text == target.text:
            score += 6
        elif target.text.lower() in text.lower():
            score += 3
    for field, expected, weight in [
        ("role", target.role, 4),
        ("name", target.name, 4),
        ("placeholder", target.placeholder, 4),
    ]:
        if expected and expected.lower() in str(element.get(field, "")).lower():
            score += weight
    if target.name:
        for attr in ["id", "aria-label", "data-testid", "data-test"]:
            if target.name.lower() in str(element.get(attr, "")).lower():
                score += 3
    if target.attr and target.value and str(element.get(target.attr, "")) == target.value:
        score += 6
    return score


def _element_candidates(soup: Any, element: Any, score: int) -> List[LocatorCandidate]:
    tag = element.name or "*"
    candidates: List[LocatorCandidate] = []
    for attr in ["id", "data-testid", "data-test", "name", "aria-label", "placeholder", "role"]:
        value = str(element.get(attr, "")).strip()
        if not value:
            continue
        css = f"{tag}[{attr}='{_css_quote(value)}']" if attr != "id" else f"#{_css_ident(value)}"
        xpath = f"//{tag}[@{attr}={_xpath_literal(value)}]"
        bonus = 8 if _css_count(soup, css) == 1 else 3
        candidates.append(LocatorCandidate("css", css, score + bonus, f"{attr} attribute"))
        candidates.append(LocatorCandidate("xpath", xpath, score + bonus - 1, f"{attr} attribute"))
    text = element.get_text(" ", strip=True)
    if text:
        snippet = text[:80]
        candidates.append(
            LocatorCandidate("xpath", f"//{tag}[contains(normalize-space(.), {_xpath_literal(snippet)})]", score + 2, "visible text")
        )
    full_css = _full_css_path(element)
    full_xpath = _full_xpath(element)
    if full_css:
        candidates.append(LocatorCandidate("css", full_css, score + 1, "structural css path"))
    if full_xpath:
        candidates.append(LocatorCandidate("xpath", full_xpath, score + 1, "structural xpath path"))
    return candidates


def _css_count(soup: Any, selector: str) -> int:
    try:
        return len(soup.select(selector))
    except Exception:
        return 0


def _css_ident(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "_-" else f"\\{ord(ch):x} " for ch in value)


def _css_quote(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _xpath_literal(value: str) -> str:
    if "'" not in value:
        return f"'{value}'"
    if '"' not in value:
        return f'"{value}"'
    return "concat(" + ", \"'\", ".join(f"'{part}'" for part in value.split("'")) + ")"


def _full_css_path(element: Any) -> str:
    parts: List[str] = []
    current = element
    while getattr(current, "name", None) and current.name not in {"[document]"}:
        tag = current.name
        if current.get("id"):
            parts.append(f"{tag}#{_css_ident(str(current.get('id')))}")
            break
        siblings = [sib for sib in current.parent.find_all(tag, recursive=False)] if current.parent else []
        index = siblings.index(current) + 1 if current in siblings else 1
        parts.append(f"{tag}:nth-of-type({index})")
        current = current.parent
    return " > ".join(reversed(parts))


def _full_xpath(element: Any) -> str:
    parts: List[str] = []
    current = element
    while getattr(current, "name", None) and current.name not in {"[document]"}:
        tag = current.name
        if current.get("id"):
            parts.append(f"{tag}[@id={_xpath_literal(str(current.get('id')))}]")
            break
        siblings = [sib for sib in current.parent.find_all(tag, recursive=False)] if current.parent else []
        index = siblings.index(current) + 1 if current in siblings else 1
        parts.append(f"{tag}[{index}]")
        current = current.parent
    return "/" + "/".join(reversed(parts)) if parts else ""
