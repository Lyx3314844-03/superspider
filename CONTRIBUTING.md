# Contributing

This repository is a four-runtime crawler suite:

- `javaspider`
- `gospider`
- `pyspider`
- `rustspider`

Changes should strengthen the shared contract, not only one runtime in isolation.

## Contribution Priorities

High-value contributions:

- cross-runtime contract alignment
- browser/runtime correctness
- public benchmark evidence
- replay and blackbox verification
- structured logs and control-plane artifacts
- deployment and release hardening
- third-party integrations and examples

## Before Opening A PR

Run the relevant local gates:

```bash
python smoke_test.py --json
python verify_runtime_readiness.py --json
python verify_benchmark_sla.py --json --markdown-out artifacts/benchmark-sla.md
python verify_blackbox_e2e.py --json --markdown-out artifacts/blackbox-e2e.md
```

Language-specific checks:

```bash
cd javaspider && mvn test
cd gospider && go test ./...
cd pyspider && python -m pytest --no-cov
cd rustspider && cargo test
```

## PR Expectations

Every PR should describe:

- what changed
- which runtime(s) changed
- whether the shared contract changed
- what evidence was collected
- remaining risks

If a PR changes operator surfaces, include at least one of:

- updated docs
- updated schema
- updated release artifact output
- updated blackbox verification

## Design Rule

Prefer one shared operator experience across all four runtimes.

Good examples:

- the same command name across runtimes
- the same JSON envelope shape across runtimes
- the same artifact directory layout across runtimes

Bad examples:

- a one-off feature that only exists in one runtime without a contract reason
- runtime-specific output shapes for equivalent operator endpoints
