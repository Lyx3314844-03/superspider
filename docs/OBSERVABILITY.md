# Observability

The suite treats observability as a first-class kernel contract, not an optional add-on.

## Required Surfaces

- structured logs
- metrics
- trace
- failure classification
- release artifacts that keep operations evidence visible

## Repository Surfaces

- `contracts/runtime-core.schema.json`
- `unified_monitor.py`
- `monitoring/`
- `docs/OPERATIONS.md`
- `docs/STABILITY_EVIDENCE.md`
- `docs/web-control-plane-contract.md`

## Expectations

- metrics should stay readable at suite level
- trace evidence should stay exportable through runtime envelopes or control-plane artifacts
- failure classification should remain explicit in reports and operator tooling
- tenant and worker health should remain inspectable in public verification surfaces

## Verification

Run:

```bash
python verify_observability_evidence.py --json --markdown-out artifacts/observability-evidence.md
```
