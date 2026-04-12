from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import verify_ultimate_events


ROOT = Path(__file__).resolve().parents[1]


def test_collect_ultimate_events_report_builds_active_and_resolved_events(tmp_path):
    trend = {
        "summary": "warning",
        "alerts": [
            {
                "event_id": "abc123",
                "framework": "gospider",
                "source": "ultimate",
                "key": "average_duration_ms",
                "severity": "warning",
                "details": "average_duration_ms regressed",
            }
        ],
    }
    history_dir = tmp_path / "history"
    history_dir.mkdir()
    previous = {
        "events": [
            {
                "event_id": "resolved-1",
                "framework": "pyspider",
                "source": "ultimate",
                "key": "proxy_capture_rate",
                "severity": "warning",
                "details": "proxy capture regressed",
                "state": "new",
                "occurrences": 1,
                "first_seen_at": "2026-01-01T00:00:00+00:00",
                "last_seen_at": "2026-01-01T00:00:00+00:00",
            }
        ]
    }
    (history_dir / "snapshot.json").write_text(json.dumps(previous), encoding="utf-8")

    report = verify_ultimate_events.collect_ultimate_events_report(ROOT, history_dir, trend)
    assert report["command"] == "verify-ultimate-events"
    assert report["summary"] == "warning"
    assert len(report["events"]) == 1
    assert len(report["resolved_events"]) == 1


def test_main_prints_json_report(monkeypatch, capsys):
    monkeypatch.setattr(
        verify_ultimate_events,
        "collect_ultimate_events_report",
        lambda root, history_dir=None, trend=None: {
            "command": "verify-ultimate-events",
            "summary": "passed",
            "summary_text": "0 active events, 0 resolved events",
            "exit_code": 0,
            "trend_summary": "passed",
            "events": [],
            "resolved_events": [],
            "history": {"count": 0, "generated_at": "2026-01-01T00:00:00+00:00"},
        },
    )

    exit_code = verify_ultimate_events.main(["--root", str(ROOT), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["command"] == "verify-ultimate-events"
