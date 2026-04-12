from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import generate_github_release_body


ROOT = Path(__file__).resolve().parents[1]


def test_render_markdown_includes_new_maturity_sections():
    report = {
        "summary_text": "8 required passed, 0 required failed",
        "optional_live_checks": [
            {"name": "javaspider-ai-live", "status": "skipped", "details": "missing key"},
            {"name": "captcha-live-readiness", "status": "skipped", "details": "all runtimes skipped or unsupported"},
        ],
        "sections": {
            "framework_completion": {"summary_text": "4 frameworks passed, 0 frameworks failed", "frameworks": {}},
            "local_integrations": {"summary_text": "7 passed, 0 failed"},
            "media_blackbox": {"summary_text": "2 passed, 0 failed"},
            "runtime_stability": {"summary_text": "4 frameworks passed, 0 frameworks failed"},
            "runtime_stability_trends": {"summary_text": "1 trend report passed"},
            "result_contracts": {"summary_text": "8 passed, 0 failed"},
            "runtime_core_capabilities": {"summary_text": "5 passed, 0 failed"},
            "superspider_control_plane_benchmark": {"summary_text": "4 passed, 0 failed"},
            "superspider_control_plane": {"summary_text": "11 passed, 0 failed"},
            "superspider_control_plane_install_smoke": {"summary_text": "8 passed, 0 failed"},
            "superspider_control_plane_package": {"summary_text": "4 passed, 0 failed"},
            "superspider_control_plane_postgres_backend": {"summary_text": "1 passed, 0 failed, 1 skipped"},
            "superspider_control_plane_release": {"summary_text": "10 passed, 0 failed"},
            "operator_products": {"summary_text": "9 passed, 0 failed"},
            "operating_system_support": {"summary_text": "15 passed, 0 failed"},
            "kernel_homogeneity": {"summary_text": "5 passed, 0 failed"},
            "observability_evidence": {"summary_text": "5 passed, 0 failed"},
            "cache_incremental_evidence": {"summary_text": "4 passed, 0 failed"},
            "ecosystem_marketplace": {"summary_text": "4 passed, 0 failed"},
            "ecosystem_readiness": {"summary_text": "4 passed, 0 failed"},
            "captcha_live_readiness": {"summary_text": "javaspider=skipped, pyspider=skipped, rustspider=skipped, gospider=unsupported"},
            "industry_proof_surface": {"summary_text": "5 passed, 0 failed"},
            "legacy_surfaces": {"summary_text": "17 passed, 0 failed"},
        },
    }

    markdown = generate_github_release_body.render_markdown(ROOT, report)

    assert "Runtime stability" in markdown
    assert "Result contracts" in markdown
    assert "Core capability surface" in markdown
    assert "SuperSpider control-plane benchmark" in markdown
    assert "SuperSpider control-plane compiler/router" in markdown
    assert "SuperSpider control-plane install smoke" in markdown
    assert "SuperSpider control-plane package" in markdown
    assert "SuperSpider control-plane Postgres backend" in markdown
    assert "SuperSpider control-plane release" in markdown
    assert "Operator products" in markdown
    assert "Operating system support" in markdown
    assert "Kernel homogeneity" in markdown
    assert "Observability evidence" in markdown
    assert "Cache and incremental evidence" in markdown
    assert "Ecosystem marketplace" in markdown
    assert "Ecosystem readiness" in markdown
    assert "Captcha live readiness" in markdown
    assert "Industry proof surface" in markdown
    assert "RUNTIME_CORE_CAPABILITIES_REPORT.md" in markdown
    assert "SUPERSPIDER_CONTROL_PLANE_REPORT.md" in markdown
    assert "SUPERSPIDER_CONTROL_PLANE_BENCHMARK_REPORT.md" in markdown
    assert "artifacts/superspider-control-plane-install-smoke.json" in markdown
    assert "artifacts/superspider-control-plane-package.json" in markdown
    assert "artifacts/superspider-control-plane-postgres-backend.json" in markdown
    assert "artifacts/superspider-control-plane-release.json" in markdown
    assert "OPERATOR_PRODUCTS_REPORT.md" in markdown
    assert "artifacts/operating-system-support.md" in markdown
    assert "KERNEL_HOMOGENEITY_REPORT.md" in markdown
    assert "OBSERVABILITY_EVIDENCE_REPORT.md" in markdown
    assert "CACHE_INCREMENTAL_EVIDENCE_REPORT.md" in markdown
    assert "ECOSYSTEM_MARKETPLACE_REPORT.md" in markdown
    assert "RESULT_CONTRACTS_REPORT.md" in markdown
    assert "ECOSYSTEM_READINESS_REPORT.md" in markdown
    assert "artifacts/captcha-live-readiness.md" in markdown
    assert "INDUSTRY_PROOF_SURFACE_REPORT.md" in markdown
    assert "SuperSpider Package Artifacts" in markdown
    assert "docs/ADOPTERS.md" in markdown
    assert "captcha-live-readiness" in markdown


def test_render_markdown_tolerates_missing_sections():
    report = {
        "summary_text": "0 required passed, 0 required failed",
        "optional_live_checks": [],
        "sections": {},
    }

    markdown = generate_github_release_body.render_markdown(ROOT, report)

    assert "Framework completion: `framework completion unavailable`" in markdown
    assert "Operating system support: `not available`" in markdown


def test_main_uses_existing_release_ready_without_refresh(monkeypatch, tmp_path, capsys):
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    (tmp_path / "VERSION").write_text("1.2.3", encoding="utf-8")
    (artifacts / "release-readiness.json").write_text(
        json.dumps(
            {
                "summary": "passed",
                "summary_text": "1 required passed, 0 required failed",
                "exit_code": 0,
                "optional_live_checks": [],
                "sections": {},
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        generate_github_release_body.verify_release_ready,
        "collect_report",
        lambda root: (_ for _ in ()).throw(AssertionError("should not refresh")),
    )

    exit_code = generate_github_release_body.main(["--root", str(tmp_path), "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["summary"] == "passed"
