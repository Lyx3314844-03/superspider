from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import generate_framework_scorecard


ROOT = Path(__file__).resolve().parents[1]


def _dashboard():
    return {
        "framework_scores": {
            "javaspider": {"anti_bot_scenario_rate": 1.0, "recovery_signal_rate": 1.0, "workflow_replay_rate": 1.0},
            "pyspider": {"anti_bot_scenario_rate": 1.0, "recovery_signal_rate": 1.0, "workflow_replay_rate": 1.0},
            "gospider": {"anti_bot_scenario_rate": 1.0, "recovery_signal_rate": 1.0, "workflow_replay_rate": 1.0},
            "rustspider": {
                "anti_bot_scenario_rate": 1.0,
                "recovery_signal_rate": 1.0,
                "workflow_replay_rate": 1.0,
                "browser_proof_ready": True,
            },
        },
        "sections": {
            "runtime_readiness": {
                "summary": "passed",
                "frameworks": [
                    {"name": "javaspider", "summary": "passed"},
                    {"name": "pyspider", "summary": "passed"},
                    {"name": "gospider", "summary": "passed"},
                ],
            },
            "rust_preflight_summary": {"summary": "passed"},
            "rust_distributed_summary": {"summary": "passed"},
        },
    }


def test_collect_framework_scorecard_passes_for_repo(monkeypatch):
    monkeypatch.setattr(generate_framework_scorecard.verify_replay_dashboard, "collect_replay_dashboard", lambda root: _dashboard())
    monkeypatch.setattr(
        generate_framework_scorecard.verify_runtime_stability,
        "collect_runtime_stability_report",
        lambda root: {
            "frameworks": [
                {"name": "javaspider", "summary": "passed"},
                {"name": "pyspider", "summary": "passed"},
                {"name": "gospider", "summary": "passed"},
                {"name": "rustspider", "summary": "passed"},
            ]
        },
    )
    monkeypatch.setattr(
        generate_framework_scorecard.verify_runtime_stability_trends,
        "collect_runtime_stability_trend_report",
        lambda root, current_report=None: {"alerts": [], "stability_trends": {}},
    )
    monkeypatch.setattr(
        generate_framework_scorecard.verify_runtime_core_capabilities,
        "collect_runtime_core_capabilities_report",
        lambda root: {"checks": [{"name": name, "status": "passed"} for name in generate_framework_scorecard.FRAMEWORKS]},
    )
    monkeypatch.setattr(
        generate_framework_scorecard.verify_superspider_control_plane,
        "collect_superspider_control_plane_report",
        lambda root: {
            "frameworks": {name: {"summary": "passed"} for name in generate_framework_scorecard.FRAMEWORKS}
        },
    )
    monkeypatch.setattr(
        generate_framework_scorecard.verify_maturity_governance,
        "collect_maturity_governance_report",
        lambda root: {"summary": "passed"},
    )
    monkeypatch.setattr(
        generate_framework_scorecard.verify_legacy_surfaces,
        "collect_legacy_surfaces_report",
        lambda root: {"summary": "passed"},
    )
    monkeypatch.setattr(
        generate_framework_scorecard.verify_ecosystem_readiness,
        "collect_ecosystem_readiness_report",
        lambda root: {"summary": "passed"},
    )
    monkeypatch.setattr(
        generate_framework_scorecard.verify_captcha_live_readiness,
        "collect_captcha_live_readiness_report",
        lambda root: {
            "frameworks": {
                "javaspider": {"summary": "passed"},
                "pyspider": {"summary": "skipped"},
                "gospider": {"summary": "skipped"},
                "rustspider": {"summary": "passed"},
            }
        },
    )
    report = generate_framework_scorecard.collect_framework_scorecard(ROOT)

    assert report["command"] == "generate-framework-scorecard"
    assert report["summary"] == "passed"
    assert "rustspider" in report["frameworks"]
    assert report["frameworks"]["rustspider"]["evidence"]["readme_present"] is True
    assert report["frameworks"]["rustspider"]["evidence"]["distributed"] == "verified"
    assert report["frameworks"]["rustspider"]["evidence"]["stability_verified"] is True
    assert report["frameworks"]["rustspider"]["evidence"]["stability_trends_verified"] is True
    assert report["frameworks"]["rustspider"]["evidence"]["core_contracts_verified"] is True
    assert report["frameworks"]["rustspider"]["evidence"]["control_plane_verified"] is True
    assert report["frameworks"]["rustspider"]["evidence"]["maturity_governance_verified"] is True
    assert report["frameworks"]["rustspider"]["evidence"]["legacy_isolation_verified"] is True
    assert report["frameworks"]["rustspider"]["evidence"]["ecosystem_verified"] is True
    assert report["frameworks"]["rustspider"]["evidence"]["live_captcha_status"] == "passed"


def test_render_markdown_includes_frameworks():
    report = {
        "frameworks": {
            "gospider": {
                "runtime": "go",
                "evidence": {
                    "test_files": 21,
                    "test_status": "moderate",
                    "distributed": "verified",
                    "anti_bot_verified": True,
                    "browser_verified": True,
                    "monitor_verified": True,
                    "deploy_verified": True,
                    "readme_present": True,
                    "stability_verified": True,
                    "stability_trends_verified": True,
                    "core_contracts_verified": True,
                    "control_plane_verified": True,
                    "maturity_governance_verified": True,
                    "legacy_isolation_verified": True,
                    "ecosystem_verified": True,
                    "live_captcha_status": "skipped",
                },
            }
        }
    }
    markdown = generate_framework_scorecard.render_markdown(report)
    assert "| gospider | go | 21 (moderate) | verified | yes | yes | yes | yes | yes | yes | yes | yes | yes | yes | yes | yes | skipped |" in markdown


def test_framework_scorecard_contract_is_documented_and_schema_exists():
    schema = json.loads((ROOT / "schemas" / "spider-framework-scorecard.schema.json").read_text(encoding="utf-8"))

    assert schema["properties"]["command"]["const"] == "generate-framework-scorecard"


def test_monitor_verified_uses_framework_specific_readiness_for_non_rust():
    dashboard = {
        "sections": {
            "runtime_readiness": {
                "summary": "failed",
                "frameworks": [
                    {"name": "gospider", "summary": "passed"},
                    {"name": "pyspider", "summary": "failed"},
                ],
            },
            "rust_preflight_summary": {"summary": "passed"},
        }
    }

    assert generate_framework_scorecard._monitor_verified("gospider", dashboard) is True
    assert generate_framework_scorecard._monitor_verified("pyspider", dashboard) is False
