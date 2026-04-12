from __future__ import annotations

import argparse
import json
from pathlib import Path

import generate_framework_completion_report
import verify_captcha_live_readiness
import verify_javaspider_ai_live
import verify_cache_incremental_evidence
import verify_ecosystem_readiness
import verify_ecosystem_marketplace
import verify_industry_proof_surface
import verify_kernel_homogeneity
import verify_legacy_surfaces
import verify_local_integrations
import verify_maturity_governance
import verify_media_blackbox
import verify_observability_evidence
import verify_operating_system_support
import verify_operator_products
import verify_public_install_chain
import verify_result_contracts
import verify_runtime_core_capabilities
import verify_runtime_stability
import verify_runtime_stability_trends
import verify_superspider_control_plane_benchmark
import verify_superspider_control_plane
import verify_superspider_control_plane_install_smoke
import verify_superspider_control_plane_package
import verify_superspider_control_plane_postgres_backend
import verify_superspider_control_plane_release
import verify_rust_captcha_live


def _read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _load_or_collect(root: Path, artifact_name: str, collect) -> dict:
    artifact = root / "artifacts" / artifact_name
    payload = _read_json(artifact)
    return payload if payload is not None else collect(root)


def collect_report(root: Path) -> dict:
    completion = _load_or_collect(root, "framework-completion-report.json", generate_framework_completion_report.collect_report)
    local_integrations = _load_or_collect(root, "local-integrations.json", verify_local_integrations.collect_report)
    media_blackbox = _load_or_collect(root, "media-blackbox.json", verify_media_blackbox.collect_report)
    runtime_stability = _load_or_collect(root, "runtime-stability.json", verify_runtime_stability.collect_runtime_stability_report)
    runtime_stability_trends = _load_or_collect(root, "runtime-stability-trends.json", verify_runtime_stability_trends.collect_runtime_stability_trend_report)
    result_contracts = _load_or_collect(root, "result-contracts.json", verify_result_contracts.collect_result_contracts_report)
    runtime_core_capabilities = _load_or_collect(root, "runtime-core-capabilities.json", verify_runtime_core_capabilities.collect_runtime_core_capabilities_report)
    superspider_control_plane_benchmark = _load_or_collect(root, "superspider-control-plane-benchmark.json", verify_superspider_control_plane_benchmark.collect_report)
    superspider_control_plane = _load_or_collect(root, "superspider-control-plane.json", verify_superspider_control_plane.collect_superspider_control_plane_report)
    superspider_control_plane_install_smoke = _load_or_collect(root, "superspider-control-plane-install-smoke.json", verify_superspider_control_plane_install_smoke.collect_report)
    superspider_control_plane_package = _load_or_collect(root, "superspider-control-plane-package.json", verify_superspider_control_plane_package.collect_report)
    superspider_control_plane_postgres_backend = _load_or_collect(root, "superspider-control-plane-postgres-backend.json", verify_superspider_control_plane_postgres_backend.collect_report)
    superspider_control_plane_release = _load_or_collect(root, "superspider-control-plane-release.json", verify_superspider_control_plane_release.collect_report)
    operator_products = _load_or_collect(root, "operator-products.json", verify_operator_products.collect_operator_products_report)
    operating_system_support = _load_or_collect(root, "operating-system-support.json", verify_operating_system_support.collect_operating_system_support_report)
    kernel_homogeneity = _load_or_collect(root, "kernel-homogeneity.json", verify_kernel_homogeneity.collect_kernel_homogeneity_report)
    observability_evidence = _load_or_collect(root, "observability-evidence.json", verify_observability_evidence.collect_observability_evidence_report)
    cache_incremental_evidence = _load_or_collect(root, "cache-incremental-evidence.json", verify_cache_incremental_evidence.collect_cache_incremental_evidence_report)
    ecosystem_marketplace = _load_or_collect(root, "ecosystem-marketplace.json", verify_ecosystem_marketplace.collect_ecosystem_marketplace_report)
    industry_proof_surface = _load_or_collect(root, "industry-proof-surface.json", verify_industry_proof_surface.collect_industry_proof_surface_report)
    maturity_governance = _load_or_collect(root, "maturity-governance.json", verify_maturity_governance.collect_maturity_governance_report)
    ecosystem_readiness = _load_or_collect(root, "ecosystem-readiness.json", verify_ecosystem_readiness.collect_ecosystem_readiness_report)
    public_install_chain = _load_or_collect(root, "public-install-chain.json", verify_public_install_chain.collect_report)
    legacy_surfaces = _load_or_collect(root, "legacy-surfaces.json", verify_legacy_surfaces.collect_legacy_surfaces_report)
    java_live = verify_javaspider_ai_live.run_javaspider_ai_live(root)
    captcha_live = _load_or_collect(root, "captcha-live-readiness.json", verify_captcha_live_readiness.collect_captcha_live_readiness_report)
    rust_live = verify_rust_captcha_live.run_rust_captcha_live(root)

    required_checks = [
        {
            "name": "framework-completion",
            "status": completion["summary"],
            "details": completion["summary_text"],
        },
        {
            "name": "local-integrations",
            "status": local_integrations["summary"],
            "details": local_integrations["summary_text"],
        },
        {
            "name": "media-blackbox",
            "status": media_blackbox["summary"],
            "details": media_blackbox["summary_text"],
        },
        {
            "name": "runtime-stability",
            "status": runtime_stability["summary"],
            "details": runtime_stability["summary_text"],
        },
        {
            "name": "runtime-stability-trends",
            "status": runtime_stability_trends["summary"],
            "details": runtime_stability_trends["summary_text"],
        },
        {
            "name": "result-contracts",
            "status": result_contracts["summary"],
            "details": result_contracts["summary_text"],
        },
        {
            "name": "runtime-core-capabilities",
            "status": runtime_core_capabilities["summary"],
            "details": runtime_core_capabilities["summary_text"],
        },
        {
            "name": "superspider-control-plane-benchmark",
            "status": superspider_control_plane_benchmark["summary"],
            "details": superspider_control_plane_benchmark["summary_text"],
        },
        {
            "name": "superspider-control-plane",
            "status": superspider_control_plane["summary"],
            "details": superspider_control_plane["summary_text"],
        },
        {
            "name": "superspider-control-plane-install-smoke",
            "status": superspider_control_plane_install_smoke["summary"],
            "details": superspider_control_plane_install_smoke["summary_text"],
        },
        {
            "name": "superspider-control-plane-package",
            "status": superspider_control_plane_package["summary"],
            "details": superspider_control_plane_package["summary_text"],
        },
        {
            "name": "superspider-control-plane-postgres-backend",
            "status": superspider_control_plane_postgres_backend["summary"],
            "details": superspider_control_plane_postgres_backend["summary_text"],
        },
        {
            "name": "superspider-control-plane-release",
            "status": superspider_control_plane_release["summary"],
            "details": superspider_control_plane_release["summary_text"],
        },
        {
            "name": "operator-products",
            "status": operator_products["summary"],
            "details": operator_products["summary_text"],
        },
        {
            "name": "operating-system-support",
            "status": operating_system_support["summary"],
            "details": operating_system_support["summary_text"],
        },
        {
            "name": "kernel-homogeneity",
            "status": kernel_homogeneity["summary"],
            "details": kernel_homogeneity["summary_text"],
        },
        {
            "name": "observability-evidence",
            "status": observability_evidence["summary"],
            "details": observability_evidence["summary_text"],
        },
        {
            "name": "cache-incremental-evidence",
            "status": cache_incremental_evidence["summary"],
            "details": cache_incremental_evidence["summary_text"],
        },
        {
            "name": "ecosystem-marketplace",
            "status": ecosystem_marketplace["summary"],
            "details": ecosystem_marketplace["summary_text"],
        },
        {
            "name": "industry-proof-surface",
            "status": industry_proof_surface["summary"],
            "details": industry_proof_surface["summary_text"],
        },
        {
            "name": "maturity-governance",
            "status": maturity_governance["summary"],
            "details": maturity_governance["summary_text"],
        },
        {
            "name": "legacy-surfaces",
            "status": legacy_surfaces["summary"],
            "details": legacy_surfaces["summary_text"],
        },
        {
            "name": "ecosystem-readiness",
            "status": ecosystem_readiness["summary"],
            "details": ecosystem_readiness["summary_text"],
        },
        {
            "name": "public-install-chain",
            "status": public_install_chain["summary"],
            "details": public_install_chain["summary_text"],
        },
    ]

    optional_checks = [
        {
            "name": "javaspider-ai-live",
            "status": java_live["summary"],
            "details": java_live["summary_text"],
        },
        {
            "name": "rustspider-captcha-live",
            "status": rust_live["summary"],
            "details": rust_live["summary_text"],
        },
        {
            "name": "captcha-live-readiness",
            "status": captcha_live["summary"],
            "details": captcha_live["summary_text"],
        },
    ]

    required_failed = sum(1 for check in required_checks if check["status"] != "passed")
    required_passed = len(required_checks) - required_failed

    return {
        "command": "verify-release-ready",
        "summary": "passed" if required_failed == 0 else "failed",
        "summary_text": f"{required_passed} required passed, {required_failed} required failed",
        "exit_code": 0 if required_failed == 0 else 1,
        "required_checks": required_checks,
        "optional_live_checks": optional_checks,
        "sections": {
            "framework_completion": completion,
            "local_integrations": local_integrations,
            "media_blackbox": media_blackbox,
            "runtime_stability": runtime_stability,
            "runtime_stability_trends": runtime_stability_trends,
            "result_contracts": result_contracts,
            "runtime_core_capabilities": runtime_core_capabilities,
            "superspider_control_plane_benchmark": superspider_control_plane_benchmark,
            "superspider_control_plane": superspider_control_plane,
            "superspider_control_plane_install_smoke": superspider_control_plane_install_smoke,
            "superspider_control_plane_package": superspider_control_plane_package,
            "superspider_control_plane_postgres_backend": superspider_control_plane_postgres_backend,
            "superspider_control_plane_release": superspider_control_plane_release,
            "operator_products": operator_products,
            "operating_system_support": operating_system_support,
            "kernel_homogeneity": kernel_homogeneity,
            "observability_evidence": observability_evidence,
            "cache_incremental_evidence": cache_incremental_evidence,
            "ecosystem_marketplace": ecosystem_marketplace,
            "industry_proof_surface": industry_proof_surface,
            "maturity_governance": maturity_governance,
            "legacy_surfaces": legacy_surfaces,
            "ecosystem_readiness": ecosystem_readiness,
            "public_install_chain": public_install_chain,
            "javaspider_ai_live": java_live,
            "captcha_live_readiness": captcha_live,
            "rustspider_captcha_live": rust_live,
        },
    }


def render_markdown(report: dict) -> str:
    lines = [
        "# Release Readiness Report",
        "",
        f"Summary: {report['summary_text']}",
        "",
        "## Required Checks",
        "",
        "| Check | Status | Details |",
        "| --- | --- | --- |",
    ]
    for check in report["required_checks"]:
        lines.append(f"| {check['name']} | {check['status']} | {check['details']} |")

    lines.extend(
        [
            "",
            "## Optional Live Checks",
            "",
            "| Check | Status | Details |",
            "| --- | --- | --- |",
        ]
    )
    for check in report["optional_live_checks"]:
        lines.append(f"| {check['name']} | {check['status']} | {check['details']} |")

    lines.extend(
        [
            "",
            "## Section Summaries",
            "",
        ]
    )
    for name, section in report["sections"].items():
        lines.append(f"- {name}: {section['summary_text']}")

    return "\n".join(lines).strip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Aggregate release-readiness checks for the spider framework suite")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent), help="repository root path")
    parser.add_argument("--json", action="store_true", help="print JSON report")
    parser.add_argument("--markdown-out", default="", help="optional markdown output path")
    args = parser.parse_args(argv)

    report = collect_report(Path(args.root).resolve())
    if args.markdown_out:
        Path(args.markdown_out).write_text(render_markdown(report), encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("verify-release-ready:", report["summary"])
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
