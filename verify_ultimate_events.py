from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import verify_ultimate_trends


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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
            snapshots.append(snapshot)
    return snapshots


def _previous_snapshot(history_dir: Path) -> dict | None:
    snapshots = _history_snapshots(history_dir)
    return snapshots[-1] if snapshots else None


def collect_ultimate_events_report(root: Path, history_dir: Path | None = None, trend: dict | None = None) -> dict:
    trend = trend or verify_ultimate_trends.collect_ultimate_trend_report(root)
    resolved_history = history_dir or (root / "artifacts" / "ultimate-events-history")
    previous = _previous_snapshot(resolved_history)
    previous_events = {
        event["event_id"]: event
        for event in previous.get("events", [])
        if event.get("state") in {"new", "open"}
    } if previous else {}
    observed_at = _now_iso()

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
            "is_new": state == "new",
            "is_resolved": False,
        })

    resolved_events = []
    for event_id, event in previous_events.items():
        if event_id not in current_ids:
            resolved_events.append({
                **event,
                "state": "resolved",
                "last_seen_at": observed_at,
                "is_new": False,
                "is_resolved": True,
            })

    failed = sum(1 for event in current_events if event["severity"] == "failed")
    warnings = sum(1 for event in current_events if event["severity"] == "warning")
    if failed:
        summary = "failed"
        exit_code = 1
    elif warnings:
        summary = "warning"
        exit_code = 0
    else:
        summary = "passed"
        exit_code = 0

    return {
        "command": "verify-ultimate-events",
        "summary": summary,
        "summary_text": f"{len(current_events)} active events, {len(resolved_events)} resolved events",
        "exit_code": exit_code,
        "trend_summary": trend["summary"],
        "events": current_events,
        "resolved_events": resolved_events,
        "history": {
            "count": len(_history_snapshots(resolved_history)),
            "generated_at": observed_at,
        },
    }


def build_compact_payload(report: dict) -> dict:
    severity_counts = {
        "failed": sum(1 for event in report["events"] if event["severity"] == "failed"),
        "warning": sum(1 for event in report["events"] if event["severity"] == "warning"),
    }
    return {
        "command": "ultimate-events-compact",
        "summary": report["summary"],
        "summary_text": report["summary_text"],
        "exit_code": report["exit_code"],
        "trend_summary": report["trend_summary"],
        "severity_counts": severity_counts,
        "active_count": len(report["events"]),
        "resolved_count": len(report["resolved_events"]),
        "sample_active_events": report["events"][:5],
        "sample_resolved_events": report["resolved_events"][:5],
    }


def write_snapshot(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": _now_iso(),
        "events": report["events"],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_ndjson(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(event, ensure_ascii=False) for event in report["events"] + report["resolved_events"]]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build stable ultimate event output from ultimate trend alerts")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent), help="repository root path")
    parser.add_argument("--history-dir", default="", help="directory containing historical ultimate event snapshots")
    parser.add_argument("--snapshot-out", default="", help="optional path to write current active-event snapshot")
    parser.add_argument("--compact-out", default="", help="optional path to write compact notification JSON")
    parser.add_argument("--ndjson-out", default="", help="optional path to write NDJSON event stream")
    parser.add_argument("--json", action="store_true", help="print report as JSON")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    history_dir = Path(args.history_dir).resolve() if args.history_dir else (root / "artifacts" / "ultimate-events-history")
    report = collect_ultimate_events_report(root, history_dir)
    if args.snapshot_out:
        write_snapshot(Path(args.snapshot_out).resolve(), report)
    if args.compact_out:
        compact_path = Path(args.compact_out).resolve()
        compact_path.parent.mkdir(parents=True, exist_ok=True)
        compact_path.write_text(json.dumps(build_compact_payload(report), ensure_ascii=False, indent=2), encoding="utf-8")
    if args.ndjson_out:
        write_ndjson(Path(args.ndjson_out).resolve(), report)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"{report['command']}: {report['summary']}")
        print(report["summary_text"])
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
