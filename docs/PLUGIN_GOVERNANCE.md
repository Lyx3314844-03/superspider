# Plugin Governance

Plugin and integration manifests are shared surfaces, not ad-hoc local configuration.

Rules:

- manifests must stay JSON-serializable and schema-valid
- plugin IDs are stable public identifiers
- runtime-specific loaders may differ, but manifest meaning must stay aligned
- new plugin hooks must document request/response ordering and failure behavior
- incompatible plugin manifest changes require explicit migration notes

Verification surfaces:

- `plugins list`
- `plugins run`
- `scrapy-plugins.schema.json`
- `verify_runtime_core_capabilities.py`
