from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import verify_runtime_stability


ROOT = Path(__file__).resolve().parents[1]


def test_collect_runtime_stability_report_aggregates_existing_evidence(monkeypatch):
    monkeypatch.setattr(
        verify_runtime_stability,
        "_readiness_by_framework",
        lambda root: {
            "javaspider": {"metrics": {"recovery_signal_rate": 1.0, "control_plane_rate": 1.0}},
            "pyspider": {"metrics": {"recovery_signal_rate": 1.0, "control_plane_rate": 1.0}},
            "gospider": {"metrics": {"recovery_signal_rate": 1.0, "control_plane_rate": 1.0}},
            "rustspider": {"metrics": {"recovery_signal_rate": 1.0, "control_plane_rate": 1.0}},
        },
    )
    monkeypatch.setattr(
        verify_runtime_stability,
        "_distributed_by_framework",
        lambda root: {
            "pyspider": {
                "summary": "passed",
                "summary_text": "3 passed, 0 failed",
                "metrics": {"pass_rate": 1.0},
                "checks": [{"name": "bounded-concurrency", "status": "passed", "details": "ok"}],
            },
            "gospider": {
                "summary": "passed",
                "summary_text": "4 passed, 0 failed",
                "metrics": {"pass_rate": 1.0},
                "checks": [{"name": "synthetic-soak", "status": "passed", "details": "ok"}],
            },
            "rustspider": {
                "summary": "passed",
                "summary_text": "2 passed, 0 failed",
                "metrics": {"pass_rate": 1.0},
                "checks": [{"name": "distributed-behavior", "status": "passed", "details": "ok"}],
            },
        },
    )
    monkeypatch.setattr(
        verify_runtime_stability,
        "_run",
        lambda command, cwd, timeout=600: {
            "command": command,
            "exit_code": 0,
            "status": "passed",
            "details": "ok",
        },
    )

    report = verify_runtime_stability.collect_runtime_stability_report(ROOT)

    assert report["command"] == "verify-runtime-stability"
    assert report["summary"] == "passed"
    assert report["exit_code"] == 0
    assert len(report["frameworks"]) == 4


def test_main_prints_json_report(monkeypatch, capsys):
    monkeypatch.setattr(
        verify_runtime_stability,
        "collect_runtime_stability_report",
        lambda root: {
            "command": "verify-runtime-stability",
            "summary": "passed",
            "summary_text": "4 frameworks passed, 0 frameworks failed",
            "exit_code": 0,
            "frameworks": [],
        },
    )

    exit_code = verify_runtime_stability.main(["--root", str(ROOT), "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["summary"] == "passed"


def test_runtime_stability_contract_schema_exists():
    schema = json.loads((ROOT / "schemas" / "spider-runtime-stability.schema.json").read_text(encoding="utf-8"))

    assert schema["properties"]["command"]["const"] == "verify-runtime-stability"
    assert "frontier_stress_rate" in schema["properties"]["frameworks"]["items"]["properties"]["metrics"]["properties"]
    assert "distributed_longevity_rate" in schema["properties"]["frameworks"]["items"]["properties"]["metrics"]["properties"]
