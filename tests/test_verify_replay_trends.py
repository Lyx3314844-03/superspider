from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import verify_replay_trends


ROOT = Path(__file__).resolve().parents[1]


def test_collect_replay_trend_report_without_history(monkeypatch, tmp_path):
    monkeypatch.setattr(
        verify_replay_trends.verify_replay_dashboard,
        "collect_replay_dashboard",
        lambda root: {
            "command": "verify-replay-dashboard",
            "summary": "passed",
            "summary_text": "ok",
            "exit_code": 0,
            "framework_scores": {
                "gospider": {
                    "runtime": "go",
                    "success_rate": 1.0,
                    "resilience_rate": 1.0,
                    "consistency_rate": 1.0,
                    "artifact_integrity_rate": 1.0,
                    "anti_bot_scenario_rate": 1.0,
                    "recovery_signal_rate": 1.0,
                    "workflow_replay_rate": 1.0,
                    "distributed_pass_rate": 1.0,
                    "preflight_pass_rate": 1.0,
                }
            },
        },
    )
    monkeypatch.setattr(
        verify_replay_trends.generate_framework_scorecard,
        "collect_framework_scorecard",
        lambda root: {
            "command": "generate-framework-scorecard",
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
                    },
                }
            },
        },
    )
    monkeypatch.setattr(
        verify_replay_trends.verify_quality_thresholds,
        "collect_quality_threshold_report",
        lambda root: {
            "command": "verify-quality-thresholds",
            "summary": "passed",
            "summary_text": "ok",
            "exit_code": 0,
            "policy": {
                "profile": "default",
                "digest": "abc123",
            },
        },
    )
    monkeypatch.setattr(
        verify_replay_trends.verify_quality_policy_governance,
        "collect_quality_policy_governance_report",
        lambda root: {
            "command": "verify-quality-policy-governance",
            "summary": "passed",
            "summary_text": "ok",
            "exit_code": 0,
            "governance": {
                "version": "2026.04.09",
                "policy_digest": "abc123",
                "default_profile": "default",
                "release_profile": "strict",
            },
        },
    )

    report = verify_replay_trends.collect_replay_trend_report(ROOT, tmp_path)

    assert report["command"] == "verify-replay-trends"
    assert report["summary"] == "passed"
    assert report["history"]["count"] == 0
    assert report["framework_trends"]["gospider"]["delta"]["success_rate"] is None
    assert report["framework_trends"]["gospider"]["current"]["preflight_pass_rate"] == 1.0
    assert report["framework_trends"]["gospider"]["current"]["distributed_pass_rate"] == 1.0
    assert report["scorecard_trends"]["gospider"]["current"]["test_files"] == 21
    assert report["scorecard_trends"]["gospider"]["delta"]["test_files"] is None
    assert report["policy_trends"]["current"]["profile"] == "default"
    assert report["governance_trends"]["current"]["version"] == "2026.04.09"
    assert report["alerts"] == []


def test_write_snapshot_persists_dashboard(tmp_path):
    report = {
        "current": {
            "dashboard": {
                "command": "verify-replay-dashboard",
                "summary": "passed",
            },
            "scorecard": {
                "command": "generate-framework-scorecard",
                "summary": "passed",
            },
            "quality_thresholds": {
                "command": "verify-quality-thresholds",
                "summary": "passed",
            },
            "quality_policy_governance": {
                "command": "verify-quality-policy-governance",
                "summary": "passed",
            },
        }
    }
    path = tmp_path / "snapshot.json"

    verify_replay_trends.write_snapshot(path, report)

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["report"]["dashboard"]["command"] == "verify-replay-dashboard"
    assert payload["report"]["scorecard"]["command"] == "generate-framework-scorecard"
    assert payload["report"]["quality_thresholds"]["command"] == "verify-quality-thresholds"
    assert payload["report"]["quality_policy_governance"]["command"] == "verify-quality-policy-governance"
    assert payload["generated_at"]


def test_replay_trends_contract_is_documented_and_schema_exists():
    schema = json.loads((ROOT / "schemas" / "spider-replay-trends.schema.json").read_text(encoding="utf-8"))

    assert schema["properties"]["command"]["const"] == "verify-replay-trends"
    assert "scorecard_trends" in schema["properties"]
    assert "policy_trends" in schema["properties"]
    assert "governance_trends" in schema["properties"]
    assert schema["properties"]["summary"]["enum"] == ["passed", "warning", "failed"]
    assert "alerts" in schema["properties"]


def test_collect_replay_trend_report_emits_warning_on_test_count_regression(monkeypatch, tmp_path):
    previous = {
        "generated_at": "2026-04-09T00:00:00+00:00",
        "report": {
            "dashboard": {
                "command": "verify-replay-dashboard",
                "framework_scores": {
                    "gospider": {
                        "runtime": "go",
                        "success_rate": 1.0,
                        "resilience_rate": 1.0,
                        "consistency_rate": 1.0,
                        "artifact_integrity_rate": 1.0,
                        "anti_bot_scenario_rate": 1.0,
                        "recovery_signal_rate": 1.0,
                        "workflow_replay_rate": 1.0,
                        "distributed_pass_rate": 1.0,
                        "preflight_pass_rate": 1.0,
                    }
                },
            },
            "scorecard": {
                "frameworks": {
                    "gospider": {
                        "runtime": "go",
                        "evidence": {
                            "test_files": 30,
                            "test_status": "moderate",
                            "distributed": "verified",
                            "anti_bot_verified": True,
                            "browser_verified": True,
                            "monitor_verified": True,
                            "deploy_verified": True,
                            "readme_present": True,
                        },
                    }
                }
            },
        },
    }
    history_dir = tmp_path / "history"
    history_dir.mkdir()
    (history_dir / "snapshot.json").write_text(json.dumps(previous), encoding="utf-8")

    monkeypatch.setattr(
        verify_replay_trends.verify_replay_dashboard,
        "collect_replay_dashboard",
        lambda root: {
            "command": "verify-replay-dashboard",
            "summary": "passed",
            "summary_text": "ok",
            "exit_code": 0,
            "framework_scores": {
                "gospider": {
                    "runtime": "go",
                    "success_rate": 1.0,
                    "resilience_rate": 1.0,
                    "consistency_rate": 1.0,
                    "artifact_integrity_rate": 1.0,
                    "anti_bot_scenario_rate": 1.0,
                    "recovery_signal_rate": 1.0,
                    "workflow_replay_rate": 1.0,
                    "distributed_pass_rate": 1.0,
                    "preflight_pass_rate": 1.0,
                }
            },
        },
    )
    monkeypatch.setattr(
        verify_replay_trends.generate_framework_scorecard,
        "collect_framework_scorecard",
        lambda root: {
            "command": "generate-framework-scorecard",
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
                    },
                }
            },
        },
    )
    monkeypatch.setattr(
        verify_replay_trends.verify_quality_thresholds,
        "collect_quality_threshold_report",
        lambda root: {
            "command": "verify-quality-thresholds",
            "summary": "passed",
            "summary_text": "ok",
            "exit_code": 0,
            "policy": {
                "profile": "default",
                "digest": "same-digest",
            },
        },
    )
    monkeypatch.setattr(
        verify_replay_trends.verify_quality_policy_governance,
        "collect_quality_policy_governance_report",
        lambda root: {
            "command": "verify-quality-policy-governance",
            "summary": "passed",
            "summary_text": "ok",
            "exit_code": 0,
            "governance": {
                "version": "2026.04.09",
                "policy_digest": "same-digest",
                "default_profile": "default",
                "release_profile": "strict",
            },
        },
    )

    report = verify_replay_trends.collect_replay_trend_report(ROOT, history_dir)

    assert report["summary"] == "warning"
    assert any(alert["key"] == "test_files" and alert["severity"] == "warning" for alert in report["alerts"])


def test_collect_replay_trend_report_emits_failed_alert_on_policy_profile_change(monkeypatch, tmp_path):
    previous = {
        "generated_at": "2026-04-09T00:00:00+00:00",
        "report": {
            "dashboard": {"command": "verify-replay-dashboard", "framework_scores": {}},
            "scorecard": {"frameworks": {}},
            "quality_thresholds": {
                "command": "verify-quality-thresholds",
                "policy": {"profile": "default", "digest": "abc"},
            },
        },
    }
    history_dir = tmp_path / "history"
    history_dir.mkdir()
    (history_dir / "snapshot.json").write_text(json.dumps(previous), encoding="utf-8")

    monkeypatch.setattr(
        verify_replay_trends.verify_replay_dashboard,
        "collect_replay_dashboard",
        lambda root: {
            "command": "verify-replay-dashboard",
            "summary": "passed",
            "summary_text": "ok",
            "exit_code": 0,
            "framework_scores": {},
        },
    )
    monkeypatch.setattr(
        verify_replay_trends.generate_framework_scorecard,
        "collect_framework_scorecard",
        lambda root: {"command": "generate-framework-scorecard", "frameworks": {}},
    )
    monkeypatch.setattr(
        verify_replay_trends.verify_quality_thresholds,
        "collect_quality_threshold_report",
        lambda root: {
            "command": "verify-quality-thresholds",
            "summary": "passed",
            "summary_text": "ok",
            "exit_code": 0,
            "policy": {"profile": "strict", "digest": "def"},
        },
    )
    monkeypatch.setattr(
        verify_replay_trends.verify_quality_policy_governance,
        "collect_quality_policy_governance_report",
        lambda root: {
            "command": "verify-quality-policy-governance",
            "summary": "passed",
            "summary_text": "ok",
            "exit_code": 0,
            "governance": {
                "version": "2026.04.10",
                "policy_digest": "def",
                "default_profile": "default",
                "release_profile": "strict",
            },
        },
    )

    report = verify_replay_trends.collect_replay_trend_report(ROOT, history_dir)

    assert report["summary"] == "failed"
    assert any(alert["source"] == "quality-policy" and alert["severity"] == "failed" for alert in report["alerts"])
