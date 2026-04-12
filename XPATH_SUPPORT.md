# XPath Support Contract

Current contract:

- `pyspider`: full XPath via `lxml`
- `javaspider`: full XPath via W3C XPath over Jsoup -> W3C DOM
- `gospider`: full XPath via `htmlquery`
- `rustspider`: full XPath via repository helper `tools/xpath_extract.py`

Failure behavior:

- syntactically invalid XPath should fail explicitly
- valid XPath with no matches returns empty / null

Note for Rust:

- XPath evaluation depends on the helper script under `tools/`
- mirror/publish directories must keep `tools/` in sync
