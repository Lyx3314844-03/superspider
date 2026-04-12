import json
import re
from typing import Any, Dict, List, Optional

from pyspider.parser.parser import HTMLParser, JSONParser

try:
    from jsonpath_ng.ext import parse as parse_jsonpath  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    parse_jsonpath = None

try:
    from lxml import html as lxml_html  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    lxml_html = None


class ExtractionStudio:
    def run(
        self,
        content: str,
        schema: Dict[str, Any],
        extract_specs: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        properties = schema.get("properties", {}) if schema else {}
        extracted: Dict[str, Any] = {}
        extract_specs = list(extract_specs or [])

        if extract_specs:
            html_parser = HTMLParser(content)
            json_parser = (
                JSONParser(content) if self._looks_like_json(content) else None
            )
            for spec in extract_specs:
                field = str(spec.get("field") or "").strip()
                if not field:
                    continue
                value = self._extract_with_spec(content, html_parser, json_parser, spec)
                required = bool(spec.get("required"))
                if value in (None, ""):
                    if required:
                        raise ValueError(
                            f'required extract field "{field}" could not be resolved'
                        )
                    continue
                self._validate_schema(
                    field, value, spec.get("schema") or properties.get(field) or {}
                )
                extracted[field] = value
            return extracted

        for field in properties:
            pattern = re.compile(
                rf"{re.escape(field)}\s*[:=]\s*([^\n<]+)", re.IGNORECASE
            )
            match = pattern.search(content)
            if match:
                extracted[field] = match.group(1).strip()
                continue

            if field.lower() == "title":
                title_match = re.search(
                    r"<title>(.*?)</title>", content, re.IGNORECASE | re.DOTALL
                )
                if title_match:
                    extracted[field] = title_match.group(1).strip()

        return extracted

    def _extract_with_spec(
        self,
        content: str,
        html_parser: HTMLParser,
        json_parser: Optional[JSONParser],
        spec: Dict[str, Any],
    ) -> Any:
        field = str(spec.get("field") or "").strip()
        extract_type = str(spec.get("type") or "").strip().lower()
        expr = str(spec.get("expr") or "").strip()
        attr = str(spec.get("attr") or "").strip()
        path = str(spec.get("path") or expr).strip()

        if extract_type == "css":
            selector = expr or ("title" if field == "title" else "")
            return html_parser.css_first(selector) if selector else None
        if extract_type == "css_attr":
            return html_parser.css_attr_first(expr, attr)
        if extract_type == "xpath":
            return self._xpath_first(content, expr)
        if extract_type == "json_path":
            return self._json_path_first(json_parser, path)
        if extract_type == "regex":
            return self._regex_first(content, expr)
        if extract_type == "ai":
            if field == "title":
                return html_parser.title()
            if field == "html":
                return content
        if field == "url":
            return None
        if field in {"html", "dom"}:
            return content
        return None

    def _xpath_first(self, content: str, expr: str) -> Optional[str]:
        if not expr or lxml_html is None:
            return None
        try:
            tree = lxml_html.fromstring(content)
            results = tree.xpath(expr)
        except Exception:
            return None
        if not results:
            return None
        first = results[0]
        if isinstance(first, str):
            return first.strip()
        if hasattr(first, "text_content"):
            return first.text_content().strip()
        return str(first).strip()

    def _json_path_first(self, json_parser: Optional[JSONParser], path: str) -> Any:
        if not path or json_parser is None:
            return None
        normalized = path[2:] if path.startswith("$.") else path
        if parse_jsonpath is not None:
            try:
                matches = parse_jsonpath(path).find(json_parser.data)
            except Exception:
                matches = []
            if matches:
                return matches[0].value
        return json_parser.get(normalized)

    def _regex_first(self, content: str, expr: str) -> Optional[str]:
        if not expr:
            return None
        match = re.search(expr, content, re.IGNORECASE | re.DOTALL)
        if not match:
            return None
        if match.groups():
            return match.group(1).strip()
        return match.group(0).strip()

    def _validate_schema(self, field: str, value: Any, schema: Dict[str, Any]) -> None:
        expected_type = str(schema.get("type") or "").strip()
        if not expected_type:
            return
        valid = (
            (expected_type == "string" and isinstance(value, str))
            or (expected_type == "number" and isinstance(value, (int, float)))
            or (
                expected_type == "integer"
                and isinstance(value, int)
                and not isinstance(value, bool)
            )
            or (expected_type == "boolean" and isinstance(value, bool))
            or (expected_type == "object" and isinstance(value, dict))
            or (expected_type == "array" and isinstance(value, list))
        )
        if not valid:
            raise ValueError(
                f'extract field "{field}" violates schema.type={expected_type}'
            )

    def _looks_like_json(self, content: str) -> bool:
        stripped = content.strip()
        if not stripped or stripped[0] not in "{[":
            return False
        try:
            json.loads(stripped)
        except Exception:
            return False
        return True
