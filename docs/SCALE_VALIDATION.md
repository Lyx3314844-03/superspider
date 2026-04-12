# Scale Validation

Large-scale credibility should be built from staged evidence instead of vague claims.

## Validation Ladder

1. Local blackbox e2e
2. Runtime readiness
3. Distributed behavior checks
4. Soak and long-running task validation
5. Release artifact publication

## Existing Scale-Relevant Signals

- `gospider/distributed/soak.go`
- `gospider/distributed/soak_test.go`
- `rustspider/tests/distributed_behavior_scorecard.rs`
- `rustspider/tests/distributed_scorecard.rs`
- root runtime readiness and replay dashboards
- `verify_runtime_stability.py`

## Required Evidence Before Claiming Large-Scale Readiness

- all four runtimes pass blackbox e2e
- benchmark and SLA report is green
- distributed summaries are green where supported
- release workflow publishes artifacts for the run
- runtime stability report is green

## Recommended Public Statement

Use phrasing like:

- "validated through repository blackbox e2e, runtime readiness, replay evidence, and distributed scorecards"

Avoid phrasing like:

- "battle-tested at internet scale"

unless you have external production references you can publish.

## Next Scale Work

- add nightly soak workflow
- persist historical benchmark trend snapshots
- document recommended single-node and distributed deployment topologies
- capture control-plane result/event volumes over longer runs
