from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import verify_quality_thresholds


ROOT = Path(__file__).resolve().parents[1]


def test_collect_quality_threshold_report_uses_dashboard_and_scorecard(monkeypatch):
    monkeypatch.setattr(
        verify_quality_thresholds.verify_replay_dashboard,
        "collect_replay_dashboard",
        lambda root: {"summary": "passed"},
    )
    monkeypatch.setattr(
        verify_quality_thresholds.generate_framework_scorecard,
        "collect_framework_scorecard",
        lambda root: {
            "summary": "passed",
            "frameworks": {
                "rustspider": {
                    "evidence": {
                        "readme_present": True,
                        "deploy_verified": True,
                        "monitor_verified": True,
                        "browser_verified": True,
                        "anti_bot_verified": True,
                        "distributed": "verified",
                        "test_status": "moderate",
                        "test_files": 10,
                    },
                    "scores": {
                        "success_rate": 1.0,
                        "resilience_rate": 1.0,
                        "consistency_rate": 1.0,
                        "artifact_integrity_rate": 1.0,
                        "anti_bot_scenario_rate": 1.0,
                        "recovery_signal_rate": 1.0,
                        "workflow_replay_rate": 1.0,
                        "control_plane_rate": 1.0,
                        "preflight_pass_rate": 1.0,
                        "browser_ready": True,
                        "ffmpeg_ready": True,
                    },
                }
            },
        },
    )

    report = verify_quality_thresholds.collect_quality_threshold_report(ROOT)

    assert report["command"] == "verify-quality-thresholds"
    assert report["summary"] == "passed"
    assert report["exit_code"] == 0
    assert not any(check["status"] == "failed" for check in report["checks"])
    assert report["policy"]["profile"] == "default"
    assert report["policy"]["digest"]


def test_load_threshold_policy_reads_overrides(tmp_path):
    path = tmp_path / "policy.json"
    path.write_text(json.dumps({
        "profiles": {
            "strict": {
                "hard_rate_keys": ["success_rate"],
                "hard_thresholds": {"default_rate": 0.9},
                "minimums": {"test_status": "moderate"},
                "warning_policies": {"thin_test_status": False},
            }
        }
    }), encoding="utf-8")

    policy = verify_quality_thresholds.load_threshold_policy(path, profile="strict")

    assert policy["hard_rate_keys"] == ["success_rate"]
    assert policy["hard_thresholds"]["default_rate"] == 0.9
    assert policy["minimums"]["test_status"] == "moderate"
    assert policy["warning_policies"]["thin_test_status"] is False


def test_collect_quality_threshold_report_honors_strict_minimums(monkeypatch):
    monkeypatch.setattr(
        verify_quality_thresholds.verify_replay_dashboard,
        "collect_replay_dashboard",
        lambda root: {"summary": "passed"},
    )
    monkeypatch.setattr(
        verify_quality_thresholds.generate_framework_scorecard,
        "collect_framework_scorecard",
        lambda root: {
            "summary": "passed",
            "frameworks": {
                "rustspider": {
                    "evidence": {
                        "readme_present": True,
                        "deploy_verified": True,
                        "monitor_verified": True,
                        "browser_verified": True,
                        "anti_bot_verified": True,
                        "distributed": "verified-local",
                        "test_status": "thin",
                        "test_files": 8,
                    },
                    "scores": {
                        "success_rate": 1.0,
                        "resilience_rate": 1.0,
                        "consistency_rate": 1.0,
                        "artifact_integrity_rate": 1.0,
                        "anti_bot_scenario_rate": 1.0,
                        "recovery_signal_rate": 1.0,
                        "workflow_replay_rate": 1.0,
                        "control_plane_rate": 1.0,
                        "preflight_pass_rate": 1.0,
                        "browser_ready": True,
                        "ffmpeg_ready": True,
                    },
                }
            },
        },
    )

    strict_policy = verify_quality_thresholds.load_threshold_policy(profile="strict")
    report = verify_quality_thresholds.collect_quality_threshold_report(ROOT, strict_policy)

    assert report["summary"] == "failed"
    assert any(check["name"] == "tests" and check["status"] == "failed" for check in report["checks"])
    assert any(check["name"] == "distributed" and check["status"] == "failed" for check in report["checks"])


def test_render_markdown_includes_table():
    markdown = verify_quality_thresholds.render_markdown({
        "summary": "passed",
        "summary_text": "1 passed, 0 warnings, 0 failed",
        "checks": [
            {"framework": "gospider", "name": "success_rate", "status": "passed", "details": "meets threshold 1.0"}
        ],
    })

    assert "| gospider | success_rate | passed | meets threshold 1.0 |" in markdown


def test_collect_quality_threshold_report_records_profile_and_digest(monkeypatch):
    monkeypatch.setattr(
        verify_quality_thresholds.verify_replay_dashboard,
        "collect_replay_dashboard",
        lambda root: {"summary": "passed"},
    )
    monkeypatch.setattr(
        verify_quality_thresholds.generate_framework_scorecard,
        "collect_framework_scorecard",
        lambda root: {
            "summary": "passed",
            "frameworks": {
                "gospider": {
                    "evidence": {
                        "readme_present": True,
                        "deploy_verified": True,
                        "monitor_verified": True,
                        "browser_verified": True,
                        "anti_bot_verified": True,
                        "distributed": "verified",
                        "test_status": "moderate",
                        "test_files": 21,
                    },
                    "scores": {
                        "success_rate": 1.0,
                        "resilience_rate": 1.0,
                        "consistency_rate": 1.0,
                        "artifact_integrity_rate": 1.0,
                        "anti_bot_scenario_rate": 1.0,
                        "recovery_signal_rate": 1.0,
                        "workflow_replay_rate": 1.0,
                        "control_plane_rate": 1.0,
                    },
                }
            },
        },
    )

    report = verify_quality_thresholds.collect_quality_threshold_report(
        ROOT,
        verify_quality_thresholds.load_threshold_policy(profile="strict"),
        profile="strict",
    )

    assert report["policy"]["profile"] == "strict"
    assert isinstance(report["policy"]["digest"], str)


def test_quality_thresholds_contract_is_documented_and_schema_exists():
    schema = json.loads((ROOT / "schemas" / "spider-quality-thresholds.schema.json").read_text(encoding="utf-8"))

    assert schema["properties"]["command"]["const"] == "verify-quality-thresholds"
    assert schema["properties"]["summary"]["enum"] == ["passed", "warning", "failed"]
