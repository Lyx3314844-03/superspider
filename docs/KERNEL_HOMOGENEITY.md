# Kernel Homogeneity

This document tracks the suite-level requirement that JavaSpider, GoSpider, PySpider, and RustSpider expose the same core kernel shape even when their internal implementations differ.

## Canonical Kernel Keys

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

## What Counts As Homogeneous

- every runtime exports the same kernel key set in `contracts/ecosystem-manifest.json`
- the canonical schema stays in `contracts/runtime-core.schema.json`
- runtime capability payloads continue to emit the same kernel key set
- control-plane routing assumes the same kernel vocabulary across all runtimes

## What Does Not Count

- matching CLI names without matching kernel contracts
- a shared README with divergent runtime capability payloads
- one runtime shipping pool/cache/observability surfaces that the others do not formally expose

## Verification

Run:

```bash
python verify_kernel_homogeneity.py --json --markdown-out artifacts/kernel-homogeneity.md
```
