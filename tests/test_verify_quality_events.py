from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import verify_quality_events


ROOT = Path(__file__).resolve().parents[1]


def test_collect_quality_events_report_marks_new_and_resolved(monkeypatch, tmp_path):
    previous = {
        "generated_at": "2026-04-09T00:00:00+00:00",
        "events": [
            {
                "event_id": "evt-1",
                "framework": "global",
                "source": "quality-policy",
                "key": "digest",
                "severity": "warning",
                "details": "old",
                "state": "open",
            }
        ],
    }
    history_dir = tmp_path / "history"
    history_dir.mkdir()
    (history_dir / "snapshot.json").write_text(json.dumps(previous), encoding="utf-8")

    monkeypatch.setattr(
        verify_quality_events.verify_replay_trends,
        "collect_replay_trend_report",
        lambda root: {
            "summary": "warning",
            "alerts": [
                {
                    "event_id": "evt-2",
                    "framework": "gospider",
                    "source": "scorecard",
                    "key": "test_files",
                    "severity": "warning",
                    "details": "new warning",
                }
            ],
        },
    )

    report = verify_quality_events.collect_quality_events_report(ROOT, history_dir)

    assert report["summary"] == "warning"
    assert report["events"][0]["state"] == "new"
    assert report["events"][0]["is_new"] is True
    assert report["events"][0]["is_regression"] is True
    assert report["events"][0]["priority"] == "p2"
    assert report["resolved_events"][0]["state"] == "resolved"
    assert report["resolved_events"][0]["is_resolved"] is True


def test_compact_payload_and_ndjson_export(tmp_path):
    report = {
        "summary": "warning",
        "summary_text": "1 active events, 1 resolved events",
        "exit_code": 0,
        "trend_summary": "warning",
        "events": [
            {
                "event_id": "evt-1",
                "framework": "gospider",
                "source": "scorecard",
                "key": "test_files",
                "severity": "warning",
                "details": "regressed",
                "state": "new",
                "priority": "p2",
            }
        ],
        "resolved_events": [
            {
                "event_id": "evt-2",
                "framework": "global",
                "source": "quality-policy",
                "key": "digest",
                "severity": "warning",
                "details": "resolved",
                "state": "resolved",
                "priority": "p2",
            }
        ],
    }

    compact = verify_quality_events.build_compact_payload(report)
    assert compact["command"] == "quality-events-compact"
    assert compact["active_count"] == 1
    assert compact["resolved_count"] == 1
    assert compact["suppressed_open_events"] == 0
    assert compact["sample_active_events"][0]["priority"] == "p2"
    assert compact["sample_resolved_events"][0]["state"] == "resolved"

    ndjson_path = tmp_path / "events.ndjson"
    verify_quality_events.write_ndjson(ndjson_path, report)
    lines = ndjson_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["event_id"] == "evt-1"


def test_quality_events_contract_is_documented_and_schema_exists():
    schema = json.loads((ROOT / "schemas" / "spider-quality-events.schema.json").read_text(encoding="utf-8"))

    assert schema["properties"]["command"]["const"] == "verify-quality-events"
