# Operations

This repository ships a shared operations lane for all four frameworks.

The operations lane is expected to keep `metrics`, `trace`, and failure-classification evidence visible at repository level, not only inside per-runtime logs.

## Benchmark And SLA

Generate a unified report:

```bash
python verify_benchmark_sla.py --json --markdown-out artifacts/benchmark-sla.md
```

The report combines:

- runtime readiness latency evidence
- per-framework benchmark asset discovery
- explicit success-job SLA thresholds

Artifacts:

- `artifacts/benchmark-sla.json`
- `artifacts/benchmark-sla.md`

## Blackbox E2E

Generate a unified cross-framework blackbox report:

```bash
python verify_blackbox_e2e.py --json --markdown-out artifacts/blackbox-e2e.md
```

The report combines:

- CLI version probes
- runtime success/resilience signals
- artifact integrity signals
- anti-bot and recovery envelope checks

Artifacts:

- `artifacts/blackbox-e2e.json`
- `artifacts/blackbox-e2e.md`

## Runtime Stability

Generate the aggregate long-running stability report:

```bash
python verify_runtime_stability.py --json --markdown-out artifacts/runtime-stability.md
```

The report combines:

- frontier synthetic stress
- soak and longevity evidence
- recovery signal checks
- control-plane continuity

Artifacts:

- `artifacts/runtime-stability.json`
- `artifacts/runtime-stability.md`
- `artifacts/runtime-stability-trends.json`
- `artifacts/runtime-stability-trends.md`
- `artifacts/stability-history/current-runtime-stability.json`

## Benchmark Trends

Generate a historical trend report and snapshot:

```bash
python verify_benchmark_trends.py --json --markdown-out artifacts/benchmark-trends.md --snapshot-out artifacts/benchmark-history/current-benchmark.json
```

Artifacts:

- `artifacts/benchmark-trends.json`
- `artifacts/benchmark-trends.md`
- `artifacts/benchmark-history/current-benchmark.json`

## Control Plane Artifacts

Task-oriented control surfaces should write operator evidence into `artifacts/control-plane`.

Current examples include:

- `results.jsonl`
- `events.jsonl`
- runtime-specific audit JSONL streams

## Release Lane

The aggregate verification workflows should publish:

- smoke output
- runtime readiness
- replay dashboard and trends
- framework scorecard
- benchmark/SLA report
- blackbox e2e report
- benchmark trend report
- release summary markdown
