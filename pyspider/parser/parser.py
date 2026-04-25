"""
HTML 和 JSON 解析器
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from html import unescape
from html.parser import HTMLParser as StdHTMLParser
from typing import Any, Dict, List, Optional, Tuple

try:
    from bs4 import BeautifulSoup  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - exercised only on minimal envs
    BeautifulSoup = None

try:
    from lxml import html as lxml_html  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - exercised only on minimal envs
    lxml_html = None


@dataclass
class _MiniNode:
    tag: str
    attrs: Dict[str, str] = field(default_factory=dict)
    children: List["_MiniNode"] = field(default_factory=list)
    text_chunks: List[str] = field(default_factory=list)

    def text_content(self) -> str:
        parts = list(self.text_chunks)
        for child in self.children:
            parts.append(child.text_content())
        return unescape(" ".join(part for part in parts if part).strip())


class _MiniHTMLTreeBuilder(StdHTMLParser):
    _VOID_TAGS = {"meta", "img", "br", "hr", "input", "link"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = _MiniNode(tag="[document]")
        self._stack = [self.root]

    def handle_starttag(self, tag: str, attrs) -> None:
        node = _MiniNode(tag=tag.lower(), attrs={k: v or "" for k, v in attrs})
        self._stack[-1].children.append(node)
        if node.tag not in self._VOID_TAGS:
            self._stack.append(node)

    def handle_startendtag(self, tag: str, attrs) -> None:
        node = _MiniNode(tag=tag.lower(), attrs={k: v or "" for k, v in attrs})
        self._stack[-1].children.append(node)

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.lower()
        while len(self._stack) > 1:
            node = self._stack.pop()
            if node.tag == normalized:
                break

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self._stack[-1].text_chunks.append(text)


def _iter_nodes(node: _MiniNode):
    for child in node.children:
        yield child
        yield from _iter_nodes(child)


def _split_selectors(selector: str) -> List[str]:
    return [part.strip() for part in selector.split(",") if part.strip()]


def _parse_simple_selector(selector: str) -> dict:
    pattern = re.compile(
        r"^(?P<tag>[a-zA-Z][\w-]*)?"
        r"(?P<id>#[\w-]+)?"
        r"(?P<classes>(?:\.[\w-]+)*)"
        r"(?:\[(?P<attr>[\w:-]+)(?:=[\"']?(?P<value>[^\"'\]]+)[\"']?)?\])?$"
    )
    match = pattern.fullmatch(selector)
    if not match:
        return {"raw": selector}

    classes = [part for part in match.group("classes").split(".") if part]
    return {
        "tag": (match.group("tag") or "").lower(),
        "id": (match.group("id") or "")[1:],
        "classes": classes,
        "attr": match.group("attr") or "",
        "value": match.group("value") or "",
        "raw": selector,
    }


def _matches(node: _MiniNode, selector: str) -> bool:
    spec = _parse_simple_selector(selector)
    if spec.get("raw") == selector and not any(
        [spec.get("tag"), spec.get("id"), spec.get("classes"), spec.get("attr")]
    ):
        return False

    tag = spec.get("tag")
    if tag and node.tag != tag:
        return False

    node_id = node.attrs.get("id", "")
    if spec.get("id") and node_id != spec["id"]:
        return False

    classes = node.attrs.get("class", "").split()
    for name in spec.get("classes", []):
        if name not in classes:
            return False

    attr = spec.get("attr")
    if attr:
        if attr not in node.attrs:
            return False
        value = spec.get("value")
        if value and node.attrs.get(attr) != value:
            return False

    return True


class HTMLParser:
    """HTML 解析器"""

    def __init__(self, html: str):
        self.html = html
        self._soup = BeautifulSoup(html, "html.parser") if BeautifulSoup else None
        if self._soup is None:
            builder = _MiniHTMLTreeBuilder()
            builder.feed(html)
            builder.close()
            self._root = builder.root
        else:
            self._root = None

    def _fallback_nodes(self, selector: str) -> List[_MiniNode]:
        selectors = _split_selectors(selector)
        nodes: List[_MiniNode] = []
        seen = set()
        for simple_selector in selectors:
            for node in _iter_nodes(self._root):
                if _matches(node, simple_selector):
                    identity = id(node)
                    if identity not in seen:
                        seen.add(identity)
                        nodes.append(node)
        return nodes

    def css(self, selector: str) -> List[str]:
        """CSS 选择器提取"""
        selector, mode, attr = _normalize_css_selector(selector)
        if self._soup is not None:
            return [
                _beautiful_soup_value(elem, mode, attr)
                for elem in self._soup.select(selector)
                if _beautiful_soup_value(elem, mode, attr) != ""
            ]
        return [
            _mini_node_value(node, mode, attr)
            for node in self._fallback_nodes(selector)
            if _mini_node_value(node, mode, attr) != ""
        ]

    def css_first(self, selector: str) -> Optional[str]:
        """获取第一个匹配"""
        selector, mode, attr = _normalize_css_selector(selector)
        if self._soup is not None:
            elem = self._soup.select_one(selector)
            return _beautiful_soup_value(elem, mode, attr) if elem else None
        nodes = self._fallback_nodes(selector)
        return _mini_node_value(nodes[0], mode, attr) if nodes else None

    def css_attr(self, selector: str, attr: str) -> List[str]:
        """获取属性"""
        selector, _, pseudo_attr = _normalize_css_selector(selector)
        attr = pseudo_attr or attr
        if self._soup is not None:
            return [elem.get(attr, "") for elem in self._soup.select(selector)]
        return [node.attrs.get(attr, "") for node in self._fallback_nodes(selector)]

    def css_attr_first(self, selector: str, attr: str) -> Optional[str]:
        """获取第一个属性"""
        selector, _, pseudo_attr = _normalize_css_selector(selector)
        attr = pseudo_attr or attr
        if self._soup is not None:
            elem = self._soup.select_one(selector)
            return elem.get(attr) if elem else None
        nodes = self._fallback_nodes(selector)
        return nodes[0].attrs.get(attr) if nodes else None

    def xpath(self, expr: str) -> List[str]:
        """XPath 提取"""
        if not expr:
            return []

        if lxml_html is not None:
            try:
                tree = lxml_html.fromstring(self.html)
                results = tree.xpath(expr)
                values: List[str] = []
                for item in results:
                    if isinstance(item, str):
                        values.append(item.strip())
                    elif hasattr(item, "text_content"):
                        values.append(item.text_content().strip())
                    else:
                        values.append(str(item).strip())
                return [value for value in values if value]
            except Exception:
                pass

        translated = _translate_simple_xpath(expr)
        if translated is None:
            return []

        selector, attr = translated
        if attr:
            return [value for value in self.css_attr(selector, attr) if value]
        return [value for value in self.css(selector) if value]

    def xpath_first(self, expr: str) -> Optional[str]:
        """获取第一个 XPath 结果"""
        values = self.xpath(expr)
        return values[0] if values else None

    def links(self) -> List[str]:
        """获取所有链接"""
        return self.css_attr("a", "href")

    def images(self) -> List[str]:
        """获取所有图片"""
        return self.css_attr("img", "src")

    def title(self) -> Optional[str]:
        """获取标题"""
        if self._soup is not None:
            title_tag = self._soup.find("title")
            return title_tag.get_text(strip=True) if title_tag else None
        return self.css_first("title")

    def text(self) -> str:
        """获取文本"""
        if self._soup is not None:
            return self._soup.get_text(strip=True)
        return self._root.text_content()


def _translate_simple_xpath(expr: str) -> Optional[tuple[str, Optional[str]]]:
    normalized = expr.strip()
    if not normalized.startswith("//"):
        return None

    attr_match = re.fullmatch(
        r"//([a-zA-Z][\w-]*)(?:\[@([\w:-]+)='([^']+)'\])?/@([\w:-]+)", normalized
    )
    if attr_match:
        tag, filter_attr, filter_value, target_attr = attr_match.groups()
        selector = tag
        if filter_attr and filter_value:
            selector += f"[{filter_attr}='{filter_value}']"
        return selector, target_attr

    text_match = re.fullmatch(
        r"//([a-zA-Z][\w-]*)(?:\[@([\w:-]+)='([^']+)'\])?/text\(\)", normalized
    )
    if text_match:
        tag, filter_attr, filter_value = text_match.groups()
        selector = tag
        if filter_attr and filter_value:
            selector += f"[{filter_attr}='{filter_value}']"
        return selector, None

    class_match = re.fullmatch(r"//([a-zA-Z][\w-]*)\[@class='([^']+)'\]", normalized)
    if class_match:
        tag, class_name = class_match.groups()
        selector = f"{tag}.{class_name.replace(' ', '.')}"
        return selector, None

    attr_filter_match = re.fullmatch(
        r"//([a-zA-Z][\w-]*)\[@([\w:-]+)='([^']+)'\]", normalized
    )
    if attr_filter_match:
        tag, attr_name, value = attr_filter_match.groups()
        selector = f"{tag}[{attr_name}='{value}']"
        return selector, None

    tag_match = re.fullmatch(r"//([a-zA-Z][\w-]*)", normalized)
    if tag_match:
        return tag_match.group(1), None

    return None


def _normalize_css_selector(selector: str) -> Tuple[str, str, Optional[str]]:
    normalized = (selector or "").strip()
    attr_match = re.search(r"::attr\(([^)]+)\)\s*$", normalized, re.IGNORECASE)
    if attr_match:
        return normalized[: attr_match.start()].strip(), "attr", attr_match.group(1).strip()
    for suffix, mode in (("::text", "text"), ("::html", "html")):
        if normalized.lower().endswith(suffix):
            return normalized[: -len(suffix)].strip(), mode, None
    return normalized, "text", None


def _beautiful_soup_value(elem: Any, mode: str, attr: Optional[str]) -> str:
    if mode == "attr" and attr:
        return str(elem.get(attr, "")).strip()
    if mode == "html":
        return "".join(str(child) for child in elem.contents).strip()
    return elem.get_text(strip=True)


def _mini_node_value(node: _MiniNode, mode: str, attr: Optional[str]) -> str:
    if mode == "attr" and attr:
        return node.attrs.get(attr, "").strip()
    return node.text_content().strip()


class JSONParser:
    """JSON 解析器"""

    def __init__(self, json_str: str):
        self.data = json.loads(json_str)

    def get(self, path: str) -> Any:
        """获取 JSON 路径"""
        keys = path.split(".")
        result = self.data
        for key in keys:
            if isinstance(result, dict):
                result = result.get(key)
            elif isinstance(result, list) and key.isdigit():
                result = result[int(key)]
            else:
                return None
        return result

    def get_string(self, path: str) -> Optional[str]:
        """获取字符串"""
        val = self.get(path)
        return str(val) if val is not None else None

    def get_int(self, path: str) -> Optional[int]:
        """获取整数"""
        val = self.get(path)
        return int(val) if val is not None else None

    def get_float(self, path: str) -> Optional[float]:
        """获取浮点数"""
        val = self.get(path)
        return float(val) if val is not None else None

    def get_bool(self, path: str) -> Optional[bool]:
        """获取布尔值"""
        val = self.get(path)
        return bool(val) if val is not None else None

    def get_list(self, path: str) -> Optional[List]:
        """获取列表"""
        val = self.get(path)
        return val if isinstance(val, list) else None
