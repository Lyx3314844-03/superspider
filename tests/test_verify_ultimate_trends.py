from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import verify_ultimate_trends


ROOT = Path(__file__).resolve().parents[1]


def test_collect_ultimate_trend_report_aggregates_regressions(tmp_path):
    current = {
        "frameworks": [
            {
                "name": "javaspider",
                "runtime": "java",
                "summary": "passed",
                "report": {
                    "results": [{"task_id": "1", "url": "https://example.com", "success": True, "error": "", "duration": "10ms", "anti_bot_level": "", "anti_bot_signals": []}]
                },
            },
            {
                "name": "gospider",
                "runtime": "go",
                "summary": "failed",
                "report": {
                    "results": [{"task_id": "2", "url": "https://example.com", "success": False, "error": "boom", "duration": "20ms", "anti_bot_level": "", "anti_bot_signals": []}]
                },
            },
        ]
    }
    previous = {
        "command": "verify-ultimate-trends",
        "framework_metrics": {
            "javaspider": {"runtime": "java", "contract_rate": 1.0, "success_rate": 1.0, "signal_capture_rate": 0.0, "proxy_capture_rate": 0.0, "average_duration_ms": 5.0},
            "gospider": {"runtime": "go", "contract_rate": 1.0, "success_rate": 1.0, "signal_capture_rate": 0.0, "proxy_capture_rate": 0.0, "average_duration_ms": 10.0},
        },
    }
    history_dir = tmp_path / "history"
    history_dir.mkdir()
    (history_dir / "snapshot.json").write_text(json.dumps(previous), encoding="utf-8")

    report = verify_ultimate_trends.collect_ultimate_trend_report(ROOT, history_dir, current_report=current)

    assert report["command"] == "verify-ultimate-trends"
    assert report["summary"] == "failed"
    assert any(alert["framework"] == "gospider" and alert["key"] == "contract_rate" for alert in report["alerts"])


def test_main_prints_json_report(monkeypatch, capsys):
    monkeypatch.setattr(
        verify_ultimate_trends,
        "collect_ultimate_trend_report",
        lambda root, history_dir=None: {
            "command": "verify-ultimate-trends",
            "summary": "passed",
            "summary_text": "4 frameworks tracked, 0 alerts",
            "exit_code": 0,
            "framework_metrics": {},
            "framework_trends": {},
            "alerts": [],
            "history": {"count": 0, "generated_at": "2026-01-01T00:00:00+00:00"},
        },
    )

    exit_code = verify_ultimate_trends.main(["--root", str(ROOT), "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["command"] == "verify-ultimate-trends"


def test_ultimate_trend_contract_is_documented_and_schema_exists():
    schema = json.loads((ROOT / "schemas" / "spider-ultimate-trend-report.schema.json").read_text(encoding="utf-8"))
    contract = (ROOT / "docs" / "framework-contract.md").read_text(encoding="utf-8")

    assert "Ultimate Trend Report" in contract
    assert schema["properties"]["command"]["const"] == "verify-ultimate-trends"
    assert schema["properties"]["summary"]["enum"] == ["passed", "warning", "failed"]
