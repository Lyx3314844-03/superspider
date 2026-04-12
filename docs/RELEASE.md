# Release Flow

## Required Gates

- shared config contract files are present
- each runtime supports the unified CLI contract
- Java: `mvn test`
- Go: `go test ./...`
- Rust: `cargo test`
- Python: `pytest pyspider/tests`

## Recommended Release Sequence

1. Update shared schema and example config if the contract changes.
2. Run each runtime through `config init`.
3. Validate generated configs with `python validate_contract_configs.py --json`.
4. Run each runtime through `doctor`.
5. Run the aggregate readiness gates:
   - `python verify_release_ready.py --json --markdown-out RELEASE_READINESS_REPORT.md`
   - `python verify_superspider_control_plane.py --json --markdown-out SUPERSPIDER_CONTROL_PLANE_REPORT.md`
   - `python generate_framework_completion_report.py --json --markdown-out CURRENT_FRAMEWORK_COMPLETION_REPORT.md`
   - `python verify_local_integrations.py --json --markdown-out LOCAL_INTEGRATIONS_REPORT.md`
   - `python verify_runtime_stability.py --json --markdown-out artifacts/runtime-stability.md`
   - `python verify_result_contracts.py --json --markdown-out RESULT_CONTRACTS_REPORT.md`
   - `python verify_runtime_core_capabilities.py --json --markdown-out RUNTIME_CORE_CAPABILITIES_REPORT.md`
   - `python verify_operator_products.py --json --markdown-out OPERATOR_PRODUCTS_REPORT.md`
   - `python verify_ecosystem_readiness.py --json --markdown-out ECOSYSTEM_READINESS_REPORT.md`
   - `python verify_public_install_chain.py --json --markdown-out PUBLIC_INSTALL_CHAIN_REPORT.md`
6. Optionally run live external-service smoke checks when keys are available:
   - `python verify_javaspider_ai_live.py --json`
   - `python verify_rust_captcha_live.py --json`
7. Generate the GitHub release body from the current verification state:
   - `python generate_github_release_body.py --output GITHUB_RELEASE_BODY_v1.0.0.md`
8. Publish benchmark/SLA and blackbox reports:
   - `python verify_benchmark_sla.py --json --markdown-out artifacts/benchmark-sla.md`
   - `python verify_blackbox_e2e.py --json --markdown-out artifacts/blackbox-e2e.md`
   - `python verify_runtime_readiness.py --json`
   - `python verify_benchmark_trends.py --json --markdown-out artifacts/benchmark-trends.md --snapshot-out artifacts/benchmark-history/current-benchmark.json`
   - `python verify_media_blackbox.py --json --markdown-out MEDIA_BLACKBOX_REPORT.md`
9. Tag the repository with `v*`.
10. Let `.github/workflows/release.yml` publish the release summary and generated release body.

## Release Evidence Notes

- Treat `control_plane_rate` as a release-facing readiness signal, not just an internal metric.
- Treat `verify_superspider_control_plane.py` as the shared routing parity gate for compiler/dispatcher correctness.
- Public benchmark pages should show both the current runtime readiness table and readiness trend history so `/api/tasks` parity regressions are externally visible.
