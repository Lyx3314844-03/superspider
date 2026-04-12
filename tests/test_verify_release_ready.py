from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import verify_release_ready


ROOT = Path(__file__).resolve().parents[1]


def test_collect_report_includes_public_install_chain(monkeypatch):
    passed = {
        "summary": "passed",
        "summary_text": "ok",
        "exit_code": 0,
    }

    monkeypatch.setattr(verify_release_ready.generate_framework_completion_report, "collect_report", lambda root: passed)
    monkeypatch.setattr(verify_release_ready.verify_local_integrations, "collect_report", lambda root: passed)
    monkeypatch.setattr(verify_release_ready.verify_media_blackbox, "collect_report", lambda root: passed)
    monkeypatch.setattr(verify_release_ready.verify_runtime_stability, "collect_runtime_stability_report", lambda root: passed)
    monkeypatch.setattr(verify_release_ready.verify_runtime_stability_trends, "collect_runtime_stability_trend_report", lambda root: passed)
    monkeypatch.setattr(verify_release_ready.verify_result_contracts, "collect_result_contracts_report", lambda root: passed)
    monkeypatch.setattr(verify_release_ready.verify_runtime_core_capabilities, "collect_runtime_core_capabilities_report", lambda root: passed)
    monkeypatch.setattr(verify_release_ready.verify_superspider_control_plane_benchmark, "collect_report", lambda root: passed)
    monkeypatch.setattr(verify_release_ready.verify_superspider_control_plane, "collect_superspider_control_plane_report", lambda root: passed)
    monkeypatch.setattr(verify_release_ready.verify_superspider_control_plane_install_smoke, "collect_report", lambda root: passed)
    monkeypatch.setattr(verify_release_ready.verify_superspider_control_plane_package, "collect_report", lambda root: passed)
    monkeypatch.setattr(verify_release_ready.verify_superspider_control_plane_postgres_backend, "collect_report", lambda root: passed)
    monkeypatch.setattr(verify_release_ready.verify_superspider_control_plane_release, "collect_report", lambda root: passed)
    monkeypatch.setattr(verify_release_ready.verify_operator_products, "collect_operator_products_report", lambda root: passed)
    monkeypatch.setattr(verify_release_ready.verify_operating_system_support, "collect_operating_system_support_report", lambda root: passed)
    monkeypatch.setattr(verify_release_ready.verify_kernel_homogeneity, "collect_kernel_homogeneity_report", lambda root: passed)
    monkeypatch.setattr(verify_release_ready.verify_observability_evidence, "collect_observability_evidence_report", lambda root: passed)
    monkeypatch.setattr(verify_release_ready.verify_cache_incremental_evidence, "collect_cache_incremental_evidence_report", lambda root: passed)
    monkeypatch.setattr(verify_release_ready.verify_ecosystem_marketplace, "collect_ecosystem_marketplace_report", lambda root: passed)
    monkeypatch.setattr(verify_release_ready.verify_industry_proof_surface, "collect_industry_proof_surface_report", lambda root: passed)
    monkeypatch.setattr(verify_release_ready.verify_maturity_governance, "collect_maturity_governance_report", lambda root: passed)
    monkeypatch.setattr(verify_release_ready.verify_legacy_surfaces, "collect_legacy_surfaces_report", lambda root: passed)
    monkeypatch.setattr(verify_release_ready.verify_ecosystem_readiness, "collect_ecosystem_readiness_report", lambda root: passed)
    monkeypatch.setattr(verify_release_ready.verify_public_install_chain, "collect_report", lambda root: passed)
    monkeypatch.setattr(verify_release_ready.verify_javaspider_ai_live, "run_javaspider_ai_live", lambda root: passed)
    monkeypatch.setattr(verify_release_ready.verify_captcha_live_readiness, "collect_captcha_live_readiness_report", lambda root: passed)
    monkeypatch.setattr(verify_release_ready.verify_rust_captcha_live, "run_rust_captcha_live", lambda root: passed)

    report = verify_release_ready.collect_report(ROOT)

    required_names = [check["name"] for check in report["required_checks"]]
    assert "runtime-stability" in required_names
    assert "runtime-stability-trends" in required_names
    assert "result-contracts" in required_names
    assert "runtime-core-capabilities" in required_names
    assert "superspider-control-plane-benchmark" in required_names
    assert "superspider-control-plane" in required_names
    assert "superspider-control-plane-install-smoke" in required_names
    assert "superspider-control-plane-package" in required_names
    assert "superspider-control-plane-postgres-backend" in required_names
    assert "superspider-control-plane-release" in required_names
    assert "operator-products" in required_names
    assert "operating-system-support" in required_names
    assert "kernel-homogeneity" in required_names
    assert "observability-evidence" in required_names
    assert "cache-incremental-evidence" in required_names
    assert "ecosystem-marketplace" in required_names
    assert "industry-proof-surface" in required_names
    assert "maturity-governance" in required_names
    assert "legacy-surfaces" in required_names
    assert "ecosystem-readiness" in required_names
    assert "public-install-chain" in required_names
    assert report["sections"]["runtime_stability"]["summary"] == "passed"
    assert report["sections"]["runtime_stability_trends"]["summary"] == "passed"
    assert report["sections"]["result_contracts"]["summary"] == "passed"
    assert report["sections"]["runtime_core_capabilities"]["summary"] == "passed"
    assert report["sections"]["superspider_control_plane_benchmark"]["summary"] == "passed"
    assert report["sections"]["superspider_control_plane"]["summary"] == "passed"
    assert report["sections"]["superspider_control_plane_install_smoke"]["summary"] == "passed"
    assert report["sections"]["superspider_control_plane_package"]["summary"] == "passed"
    assert report["sections"]["superspider_control_plane_postgres_backend"]["summary"] == "passed"
    assert report["sections"]["superspider_control_plane_release"]["summary"] == "passed"
    assert report["sections"]["operator_products"]["summary"] == "passed"
    assert report["sections"]["operating_system_support"]["summary"] == "passed"
    assert report["sections"]["kernel_homogeneity"]["summary"] == "passed"
    assert report["sections"]["observability_evidence"]["summary"] == "passed"
    assert report["sections"]["cache_incremental_evidence"]["summary"] == "passed"
    assert report["sections"]["ecosystem_marketplace"]["summary"] == "passed"
    assert report["sections"]["industry_proof_surface"]["summary"] == "passed"
    assert report["sections"]["maturity_governance"]["summary"] == "passed"
    assert report["sections"]["legacy_surfaces"]["summary"] == "passed"
    assert report["sections"]["ecosystem_readiness"]["summary"] == "passed"
    assert report["sections"]["public_install_chain"]["summary"] == "passed"
    assert report["sections"]["captcha_live_readiness"]["summary"] == "passed"


def test_main_prints_json_report(monkeypatch, capsys):
    monkeypatch.setattr(
        verify_release_ready,
        "collect_report",
        lambda root: {
            "command": "verify-release-ready",
            "summary": "passed",
            "summary_text": "12 required passed, 0 required failed",
            "exit_code": 0,
            "required_checks": [],
            "optional_live_checks": [],
            "sections": {},
        },
    )

    exit_code = verify_release_ready.main(["--root", str(ROOT), "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["command"] == "verify-release-ready"
