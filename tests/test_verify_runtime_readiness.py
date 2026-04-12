from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import verify_runtime_readiness


ROOT = Path(__file__).resolve().parents[1]


def test_collect_runtime_readiness_report_aggregates_framework_summaries(monkeypatch):
    canned = {
        "javaspider": {
            "name": "javaspider",
            "runtime": "java",
            "summary": "passed",
            "exit_code": 0,
            "metrics": {"checks_passed": 4, "checks_failed": 0, "checks_total": 4, "success_rate": 1.0, "resilience_rate": 1.0, "consistency_rate": 1.0, "artifact_integrity_rate": 1.0, "anti_bot_scenario_rate": 1.0, "recovery_signal_rate": 1.0, "workflow_replay_rate": 1.0, "control_plane_rate": 1.0, "durations_ms": {"success_job": 12}},
            "checks": [{"name": "success-job", "status": "passed", "details": "ok"}],
        },
        "pyspider": {
            "name": "pyspider",
            "runtime": "python",
            "summary": "passed",
            "exit_code": 0,
            "metrics": {"checks_passed": 4, "checks_failed": 0, "checks_total": 4, "success_rate": 1.0, "resilience_rate": 1.0, "consistency_rate": 1.0, "artifact_integrity_rate": 1.0, "anti_bot_scenario_rate": 1.0, "recovery_signal_rate": 1.0, "workflow_replay_rate": 0.0, "control_plane_rate": 1.0, "durations_ms": {"success_job": 10}},
            "checks": [{"name": "success-job", "status": "passed", "details": "ok"}],
        },
        "gospider": {
            "name": "gospider",
            "runtime": "go",
            "summary": "failed",
            "exit_code": 1,
            "metrics": {"checks_passed": 3, "checks_failed": 1, "checks_total": 4, "success_rate": 0.75, "resilience_rate": 0.5, "consistency_rate": 1.0, "artifact_integrity_rate": 1.0, "anti_bot_scenario_rate": 0.5, "recovery_signal_rate": 0.5, "workflow_replay_rate": 1.0, "control_plane_rate": 0.0, "durations_ms": {"success_job": 8}},
            "checks": [{"name": "failure-injection", "status": "failed", "details": "missing"}],
        },
        "rustspider": {
            "name": "rustspider",
            "runtime": "rust",
            "summary": "passed",
            "exit_code": 0,
            "metrics": {"checks_passed": 4, "checks_failed": 0, "checks_total": 4, "success_rate": 1.0, "resilience_rate": 1.0, "consistency_rate": 1.0, "artifact_integrity_rate": 1.0, "anti_bot_scenario_rate": 1.0, "recovery_signal_rate": 1.0, "workflow_replay_rate": 0.0, "control_plane_rate": 1.0, "durations_ms": {"success_job": 9}},
            "checks": [{"name": "success-job", "status": "passed", "details": "ok"}],
        },
    }

    monkeypatch.setattr(
        verify_runtime_readiness,
        "run_framework_readiness",
        lambda root, framework: canned[framework],
    )

    report = verify_runtime_readiness.collect_runtime_readiness_report(ROOT)

    assert report["command"] == "verify-runtime-readiness"
    assert report["summary"] == "failed"
    assert report["summary_text"] == "3 frameworks passed, 1 frameworks failed"
    assert report["exit_code"] == 1


def test_success_result_checks_validate_output_and_marker(tmp_path):
    output_path = tmp_path / "result.json"
    output_path.write_text('{"title":"Marker Title","state":"succeeded"}', encoding="utf-8")

    checks = verify_runtime_readiness._success_result_checks(
        {
            "state": "succeeded",
            "anti_bot": {
                "challenge": "captcha",
                "fingerprint_profile": "synthetic-captcha",
                "session_mode": "sticky",
                "stealth": True,
            },
            "recovery": {
                "strategy": "captcha-solve",
                "recovered": True,
                "events": [
                    {"phase": "detect", "signal": "captcha", "status": "passed"},
                    {"phase": "mitigate", "action": "solve", "status": "passed"},
                    {"phase": "resume", "action": "continue", "status": "passed"},
                ],
            },
            "warnings": ["synthetic captcha recovery"],
        },
        output_path,
        "Marker Title",
        {
            "challenge": "captcha",
            "fingerprint_profile": "synthetic-captcha",
            "session_mode": "sticky",
            "stealth": True,
        },
        {
            "strategy": "captcha-solve",
            "recovered": True,
            "events": [
                {"phase": "detect", "signal": "captcha", "status": "passed"},
                {"phase": "mitigate", "action": "solve", "status": "passed"},
                {"phase": "resume", "action": "continue", "status": "passed"},
            ],
        },
        "synthetic captcha recovery",
    )

    assert [check["status"] for check in checks] == ["passed", "passed", "passed", "passed", "passed", "passed"]


def test_load_antibot_replay_scenarios_reads_replay_corpus():
    scenarios = verify_runtime_readiness.load_antibot_replay_scenarios()

    assert {"captcha", "proxy", "challenge"} <= set(scenarios)
    assert scenarios["captcha"]["anti_bot"]["challenge"] == "captcha"
    assert scenarios["proxy"]["anti_bot"]["proxy_id"] == "proxy-synthetic-1"
    assert Path(ROOT / scenarios["challenge"]["fixture_path"]).exists()
    assert "expected_tokens" in scenarios["captcha"]


def test_replay_fixture_helpers_read_fixture_content():
    scenarios = verify_runtime_readiness.load_antibot_replay_scenarios()
    challenge = scenarios["challenge"]

    content = verify_runtime_readiness.load_replay_fixture_text(challenge)
    title = verify_runtime_readiness.derive_fixture_title(challenge)

    assert "challenge-running" in content
    assert title == "Just a moment..."


def test_normalize_payload_for_comparison_ignores_runtime_noise():
    payload = {
        "state": "succeeded",
        "job_id": "job-1",
        "run_id": "run-1",
        "output": {"format": "json", "path": "artifacts/a.json"},
        "metrics": {"latency_ms": 42},
    }

    normalized = verify_runtime_readiness._normalize_payload_for_comparison(payload)

    assert "job_id" not in normalized
    assert "run_id" not in normalized
    assert "path" not in normalized["output"]
    assert normalized["metrics"]["latency_ms"] == 0


def test_main_prints_json_report(monkeypatch, capsys):
    monkeypatch.setattr(
        verify_runtime_readiness,
        "collect_runtime_readiness_report",
        lambda root: {
            "command": "verify-runtime-readiness",
            "summary": "passed",
            "summary_text": "4 frameworks passed, 0 frameworks failed",
            "exit_code": 0,
            "frameworks": [],
        },
    )

    exit_code = verify_runtime_readiness.main(["--root", str(ROOT), "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["summary"] == "passed"


def test_runtime_readiness_contract_is_documented_and_schema_exists():
    schema = json.loads((ROOT / "schemas" / "spider-runtime-readiness.schema.json").read_text(encoding="utf-8"))

    assert schema["properties"]["command"]["const"] == "verify-runtime-readiness"
    assert "resilience_rate" in schema["properties"]["frameworks"]["items"]["properties"]["metrics"]["properties"]
    assert "anti_bot_scenario_rate" in schema["properties"]["frameworks"]["items"]["properties"]["metrics"]["properties"]
    assert "recovery_signal_rate" in schema["properties"]["frameworks"]["items"]["properties"]["metrics"]["properties"]
    assert "workflow_replay_rate" in schema["properties"]["frameworks"]["items"]["properties"]["metrics"]["properties"]
    assert "control_plane_rate" in schema["properties"]["frameworks"]["items"]["properties"]["metrics"]["properties"]
    assert schema["properties"]["frameworks"]["items"]["properties"]["runtime"]["enum"] == [
        "java",
        "python",
        "go",
        "rust",
    ]
