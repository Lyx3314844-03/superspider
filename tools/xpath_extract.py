import json
import sys
import xml.etree.ElementTree as ET

try:
    from lxml import etree, html  # type: ignore
except Exception:  # pragma: no cover
    etree = None
    html = None


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"error": "usage: xpath_extract.py <xpath>"}))
        return 2

    xpath_expr = sys.argv[1]
    source = sys.stdin.read()
    if html is not None:
        try:
            tree = html.fromstring(source)
            results = tree.xpath(xpath_expr)
            values = []
            for item in results:
                if etree is not None and isinstance(item, etree._ElementUnicodeResult):
                    values.append(str(item).strip())
                elif etree is not None and isinstance(item, etree._Element):
                    values.append("".join(item.itertext()).strip())
                else:
                    values.append(str(item).strip())
            print(json.dumps({"values": values}, ensure_ascii=False))
            return 0
        except Exception:
            pass

    try:
        print(json.dumps({"values": _stdlib_xpath(source, xpath_expr)}, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({"error": str(exc)}))
        return 1


def _stdlib_xpath(source: str, xpath_expr: str):
    normalized = xpath_expr.strip()
    want_text = normalized.endswith("/text()")
    want_attr = "/@" in normalized
    attr_name = None
    if want_text:
        normalized = normalized[:-7]
    if want_attr:
        normalized, attr_name = normalized.rsplit("/@", 1)
    query = "." + normalized if normalized.startswith("//") else normalized
    root = ET.fromstring(source)
    nodes = root.findall(query)
    values = []
    for node in nodes:
        if attr_name is not None:
            value = node.attrib.get(attr_name)
        elif want_text:
            value = "".join(node.itertext())
        else:
            value = "".join(node.itertext())
        if value is not None:
            values.append(value.strip())
    return values


if __name__ == "__main__":
    raise SystemExit(main())
