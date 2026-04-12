# Nightly Scale

The nightly scale lane is the long-cycle evidence path for:

- synthetic soak stability
- benchmark and SLA history
- blackbox e2e continuity
- public benchmark page refresh

Workflow:

- `.github/workflows/nightly-scale.yml`

Current nightly artifacts:

- `artifacts/gospider-soak.log`
- `artifacts/runtime-stability.json`
- `artifacts/runtime-stability.md`
- `artifacts/runtime-stability-trends.json`
- `artifacts/runtime-stability-trends.md`
- `artifacts/benchmark-sla.json`
- `artifacts/benchmark-trends.json`
- `artifacts/benchmark-history/current-benchmark.json`
- `artifacts/benchmark-history/nightly-<run>.json`
- `artifacts/scale-history/gospider-soak-<run>.log`
- `artifacts/stability-history/current-runtime-stability.json`
- `artifacts/stability-history/runtime-stability-<run>.json`
- `web-ui/public-benchmarks/index.html`

This lane is intentionally conservative.
It starts with deterministic repository-owned evidence before claiming external internet-scale validation.
