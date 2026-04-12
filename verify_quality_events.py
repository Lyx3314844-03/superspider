from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import verify_replay_trends


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _priority_for_event(event: dict) -> str:
    if event.get("severity") == "failed":
        return "p1"
    if event.get("severity") == "warning":
        return "p2"
    return "p3"


def _load_snapshot(path: Path) -> dict | None:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "events" in data:
        return data
    return None


def _history_snapshots(history_dir: Path) -> list[dict]:
    if not history_dir.exists():
        return []
    snapshots = []
    for path in sorted(history_dir.glob("*.json")):
        snapshot = _load_snapshot(path)
        if snapshot is not None:
            snapshot["source"] = str(path)
            snapshots.append(snapshot)
    return snapshots


def _previous_snapshot(history_dir: Path) -> dict | None:
    snapshots = _history_snapshots(history_dir)
    if not snapshots:
        return None
    return snapshots[-1]


def collect_quality_events_report(root: Path, history_dir: Path | None = None, trend: dict | None = None) -> dict:
    trend = trend or verify_replay_trends.collect_replay_trend_report(root)
    resolved_history = history_dir or (root / "artifacts" / "quality-events-history")
    previous = _previous_snapshot(resolved_history)
    observed_at = _now_iso()
    previous_events = {
        event["event_id"]: event
        for event in (previous.get("events", []) if previous else [])
        if event.get("state") in {"new", "open"}
    }

    current_events = []
    current_ids = set()
    for alert in trend.get("alerts", []):
        event_id = alert["event_id"]
        current_ids.add(event_id)
        previous_event = previous_events.get(event_id)
        state = "open" if previous_event else "new"
        current_events.append({
            **alert,
            "state": state,
            "occurrences": int(previous_event.get("occurrences", 1)) + 1 if previous_event else 1,
            "first_seen_at": previous_event.get("first_seen_at", observed_at) if previous_event else observed_at,
            "last_seen_at": observed_at,
            "priority": _priority_for_event(alert),
            "is_new": state == "new",
            "is_regression": True,
            "is_resolved": False,
        })

    resolved_events = []
    for event_id, event in previous_events.items():
        if event_id not in current_ids:
            resolved_events.append({
                **event,
                "state": "resolved",
                "last_seen_at": observed_at,
                "priority": event.get("priority", _priority_for_event(event)),
                "is_new": False,
                "is_regression": False,
                "is_resolved": True,
            })

    warning_count = sum(1 for event in current_events if event["severity"] == "warning")
    failed_count = sum(1 for event in current_events if event["severity"] == "failed")
    if failed_count:
        summary = "failed"
        exit_code = 1
    elif warning_count:
        summary = "warning"
        exit_code = 0
    else:
        summary = "passed"
        exit_code = 0

    return {
        "command": "verify-quality-events",
        "summary": summary,
        "summary_text": f"{len(current_events)} active events, {len(resolved_events)} resolved events",
        "exit_code": exit_code,
        "trend_summary": trend["summary"],
        "events": current_events,
        "resolved_events": resolved_events,
        "history": {
            "count": len(_history_snapshots(resolved_history)),
            "latest_source": previous.get("source", "") if previous else "",
        },
    }


def write_snapshot(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "events": report["events"],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def build_compact_payload(report: dict) -> dict:
    severity_counts = {
        "failed": sum(1 for event in report["events"] if event["severity"] == "failed"),
        "warning": sum(1 for event in report["events"] if event["severity"] == "warning"),
    }
    visible_active = [event for event in report["events"] if event.get("state") == "new"]
    if not visible_active:
        visible_active = report["events"][:5]
    resolved_sample = report["resolved_events"][:5]
    suppressed_open_events = sum(1 for event in report["events"] if event.get("state") == "open")
    return {
        "command": "quality-events-compact",
        "summary": report["summary"],
        "summary_text": report["summary_text"],
        "exit_code": report["exit_code"],
        "trend_summary": report["trend_summary"],
        "severity_counts": severity_counts,
        "active_count": len(report["events"]),
        "resolved_count": len(report["resolved_events"]),
        "suppressed_open_events": suppressed_open_events,
        "sample_active_events": [
            {
                "event_id": event["event_id"],
                "framework": event["framework"],
                "source": event["source"],
                "key": event["key"],
                "severity": event["severity"],
                "state": event["state"],
                "priority": event["priority"],
                "details": event["details"],
            }
            for event in visible_active[:5]
        ],
        "sample_resolved_events": [
            {
                "event_id": event["event_id"],
                "framework": event["framework"],
                "source": event["source"],
                "key": event["key"],
                "severity": event["severity"],
                "state": event["state"],
                "priority": event["priority"],
                "details": event["details"],
            }
            for event in resolved_sample
        ],
    }


def write_ndjson(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for event in report["events"] + report["resolved_events"]:
        lines.append(json.dumps(event, ensure_ascii=False))
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build stable quality event output from trend alerts")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent), help="repository root path")
    parser.add_argument("--history-dir", default="", help="directory containing historical quality event snapshots")
    parser.add_argument("--snapshot-out", default="", help="optional path to write current active-event snapshot")
    parser.add_argument("--compact-out", default="", help="optional path to write compact notification JSON")
    parser.add_argument("--ndjson-out", default="", help="optional path to write NDJSON event stream")
    parser.add_argument("--json", action="store_true", help="print report as JSON")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    history_dir = Path(args.history_dir).resolve() if args.history_dir else (root / "artifacts" / "quality-events-history")
    report = collect_quality_events_report(root, history_dir)
    if args.snapshot_out:
        write_snapshot(Path(args.snapshot_out).resolve(), report)
    if args.compact_out:
        compact_path = Path(args.compact_out).resolve()
        compact_path.parent.mkdir(parents=True, exist_ok=True)
        compact_path.write_text(
            json.dumps(build_compact_payload(report), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    if args.ndjson_out:
        write_ndjson(Path(args.ndjson_out).resolve(), report)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("verify-quality-events:", report["summary"])
        print(report["summary_text"])
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
