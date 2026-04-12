# Adopters

This page is the public-facing place for adoption notes, user validation, and case-study links.

## Current State

The repository now has:

- public benchmark artifacts
- blackbox e2e artifacts
- starter kits
- external integration demos

The next layer is broader third-party adopter evidence.

The entries below are repository-owned validation stories.
They are intentionally not presented as external customer testimonials.

## What To Add Here

For each adopter or validation story, include:

- organization or project name
- runtime(s) used
- workload type
- approximate scale
- which operator surfaces were used
- which public artifacts support the claim

## Template

```md
### <Project / Team Name>

- Runtime: <java|go|python|rust|multi>
- Workload: <news crawl / e-commerce / workflow automation / research extraction / media crawl>
- Scale: <requests/day or tasks/day when shareable>
- Why this suite: <brief reason>
- Evidence: <links to benchmark, blackbox, screenshots, or release artifacts>
```

## Validation Sources

Acceptable public validation sources:

- reproducible benchmark links
- public issue threads
- public demo repos
- screenshots of control-plane or release artifacts
- explicit case-study markdown in this repository

## Repository Validation Stories

### Repository Validation: Nightly Scale Lane

- Runtime: multi
- Workload: synthetic frontier stress, distributed soak, benchmark publication
- Scale: scheduled multi-runtime verification with benchmark/stability history snapshots
- Why this suite: prove that the shared operator model remains stable across Java, Go, Python, and Rust
- Evidence: `.github/workflows/nightly-scale.yml`, `artifacts/runtime-stability.json`, `artifacts/runtime-stability-trends.json`, `artifacts/benchmark-history/current-benchmark.json`, `web-ui/public-benchmarks/index.html`

### Repository Validation: External Platform Demo

- Runtime: multi
- Workload: control-plane orchestration and public benchmark serving
- Scale: docker-compose multi-service demo surface, not a production deployment claim
- Why this suite: demonstrate the shared `/api/tasks` contract and external-facing platform shell
- Evidence: `examples/external/platform-demo/README.md`, `examples/external/control-plane-demo/README.md`, `examples/external/python-control-plane-client/README.md`, `examples/external/node-control-plane-client/README.md`
