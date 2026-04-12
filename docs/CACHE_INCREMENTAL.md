# Cache And Incremental Crawl

The suite uses one cache/incremental contract vocabulary across all runtimes.

## Required Concepts

- HTTP cache backend
- conditional request support
- delta fetch
- dedup
- retention policy
- freshness policy

## Repository Surfaces

- `contracts/runtime-core.schema.json`
- `tools/http_cache_tool.py`
- `docs/framework-contract.md`
- `verify_operator_products.py`

## Notes

- cache storage is tracked through `store_path`
- freshness is tracked through `revalidate_seconds`
- incremental behavior is tracked through `delta_fetch`
- runtime-facing cache surfaces should remain aligned with the shared operator tooling

## Verification

Run:

```bash
python verify_cache_incremental_evidence.py --json --markdown-out artifacts/cache-incremental-evidence.md
```
