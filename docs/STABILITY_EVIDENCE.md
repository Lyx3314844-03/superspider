# Stability Evidence

`verify_runtime_stability.py` is the aggregate long-running maturity report for the four runtimes.

It combines:

- frontier synthetic stress and recovery tests
- runtime readiness recovery/control-plane signals
- async/distributed soak evidence where supported
- per-runtime distributed longevity summaries

Run it with:

```bash
python verify_runtime_stability.py --json --markdown-out artifacts/runtime-stability.md
```

Artifacts:

- `artifacts/runtime-stability.json`
- `artifacts/runtime-stability.md`

Trend report:

```bash
python verify_runtime_stability_trends.py --json --markdown-out artifacts/runtime-stability-trends.md --snapshot-out artifacts/stability-history/current-runtime-stability.json
```

Trend artifacts:

- `artifacts/runtime-stability-trends.json`
- `artifacts/runtime-stability-trends.md`
- `artifacts/stability-history/current-runtime-stability.json`

Current maturity evidence buckets:

- `frontier-stress`
- `recovery-signals`
- `runtime-control-plane`
- `distributed-longevity`
- `soak-evidence`

Interpretation rules:

- `passed`: the runtime produced the expected evidence for that category
- `failed`: the runtime did not meet the expected signal or test requirement
- `skipped`: the category is not currently claimed for that runtime
