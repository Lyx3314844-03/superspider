#!/usr/bin/env python
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from html import unescape
from html.parser import HTMLParser
from typing import Any


@dataclass
class Node:
    tag: str
    attrs: dict[str, str] = field(default_factory=dict)
    children: list["Node"] = field(default_factory=list)
    text_chunks: list[str] = field(default_factory=list)

    def text_content(self) -> str:
        parts = list(self.text_chunks)
        for child in self.children:
            child_text = child.text_content()
            if child_text:
                parts.append(child_text)
        return unescape(" ".join(part for part in parts if part).strip())


class TreeBuilder(HTMLParser):
    VOID_TAGS = {"meta", "img", "br", "hr", "input", "link", "source"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Node("[document]")
        self.stack = [self.root]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = Node(tag.lower(), {key: value or "" for key, value in attrs})
        self.stack[-1].children.append(node)
        if node.tag not in self.VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        node = Node(tag.lower(), {key: value or "" for key, value in attrs})
        self.stack[-1].children.append(node)

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.lower()
        while len(self.stack) > 1:
            node = self.stack.pop()
            if node.tag == normalized:
                break

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self.stack[-1].text_chunks.append(text)


def emit(payload: dict[str, Any], exit_code: int = 0) -> int:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))
    sys.stdout.flush()
    return exit_code


def iter_descendants(node: Node):
    for child in node.children:
        yield child
        yield from iter_descendants(child)


def parse_segment(segment: str) -> tuple[str, str | None]:
    match = re.fullmatch(r"([A-Za-z_][\w\-]*|\*)(?:\[(.+)\])?", segment.strip())
    if not match:
        raise ValueError(f"unsupported xpath segment: {segment}")
    return match.group(1), match.group(2)


def apply_predicate(nodes: list[Node], predicate: str | None) -> list[Node]:
    if predicate is None:
        return nodes

    predicate = predicate.strip()
    if predicate.isdigit():
        index = int(predicate) - 1
        if index < 0 or index >= len(nodes):
            return []
        return [nodes[index]]

    attr_match = re.fullmatch(r"@([\w:-]+)=['\"]([^'\"]+)['\"]", predicate)
    if attr_match:
        attr_name, attr_value = attr_match.groups()
        return [
            node for node in nodes if node.attrs.get(attr_name) == attr_value
        ]

    raise ValueError(f"unsupported xpath predicate: {predicate}")


def evaluate_xpath(html: str, xpath: str) -> list[str]:
    normalized = xpath.strip()
    if not normalized.startswith("//"):
        raise ValueError("only descendant-rooted xpath expressions are supported")

    attr_target = None
    text_target = False
    if normalized.endswith("/text()"):
        text_target = True
        normalized = normalized[:-7]
    else:
        attr_suffix = re.search(r"/@([\w:-]+)$", normalized)
        if attr_suffix:
            attr_target = attr_suffix.group(1)
            normalized = normalized[: -(len(attr_target) + 2)]

    segments = [segment for segment in normalized[2:].split("/") if segment.strip()]
    if not segments:
        return []

    builder = TreeBuilder()
    builder.feed(html)
    builder.close()

    current: list[Node] = [builder.root]
    for index, segment in enumerate(segments):
        tag_name, predicate = parse_segment(segment)
        next_nodes: list[Node] = []
        for node in current:
            if index == 0:
                matches = [
                    child
                    for child in iter_descendants(node)
                    if tag_name == "*" or child.tag == tag_name
                ]
            else:
                matches = [
                    child
                    for child in node.children
                    if tag_name == "*" or child.tag == tag_name
                ]
            next_nodes.extend(apply_predicate(matches, predicate))
        current = next_nodes

    if attr_target:
        return [value for value in (node.attrs.get(attr_target, "").strip() for node in current) if value]
    if text_target:
        return [value for value in (node.text_content() for node in current) if value]
    return [value for value in (node.text_content() for node in current) if value]


def main() -> int:
    if len(sys.argv) < 2:
        return emit({"error": "xpath expression is required", "values": []}, 1)

    xpath = sys.argv[1]
    html = sys.stdin.read()

    try:
        values = evaluate_xpath(html, xpath)
    except Exception as exc:
        return emit({"error": str(exc), "values": []}, 1)

    return emit({"error": None, "values": values})


if __name__ == "__main__":
    raise SystemExit(main())
