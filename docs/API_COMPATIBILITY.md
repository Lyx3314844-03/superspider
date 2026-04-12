# API Compatibility

The four runtimes now share one canonical kernel contract surface:

- `request`
- `fingerprint`
- `frontier`
- `scheduler`
- `middleware`
- `artifact_store`
- `session_pool`
- `proxy_policy`
- `observability`
- `cache`

Compatibility rules:

- additive changes are preferred over breaking renames
- runtime capability output must keep `kernel_contracts` stable
- shared config changes must remain backward-compatible within the same major line
- breaking contract changes require migration notes and release callouts

Verification:

- `python verify_runtime_core_capabilities.py --json`
- `python verify_runtime_readiness.py --json`
