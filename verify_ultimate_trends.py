from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import verify_ultimate_contract


METRIC_KEYS = [
    "contract_rate",
    "success_rate",
    "signal_capture_rate",
    "proxy_capture_rate",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _alert_id(framework: str, key: str) -> str:
    seed = f"ultimate|{framework}|{key}".encode("utf-8")
    return hashlib.sha256(seed).hexdigest()[:16]


def _parse_duration_ms(value) -> float | None:
    if isinstance(value, (int, float)):
        return float(value) * 1000.0
    if not isinstance(value, str) or not value:
        return None
    if value.endswith("ms"):
        try:
            return float(value[:-2])
        except ValueError:
            return None
    if value.endswith("s"):
        try:
            return float(value[:-1]) * 1000.0
        except ValueError:
            return None
    return None


def _history_snapshots(history_dir: Path) -> list[dict]:
    if not history_dir.exists():
        return []
    snapshots = []
    for path in sorted(history_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("command") == "verify-ultimate-trends":
            snapshots.append(data)
    return snapshots


def _previous_snapshot(history_dir: Path) -> dict | None:
    snapshots = _history_snapshots(history_dir)
    return snapshots[-1] if snapshots else None


def _framework_metrics(report: dict) -> dict:
    metrics: dict[str, dict] = {}
    for framework in report.get("frameworks", []):
        payload = framework.get("report") or {}
        results = payload.get("results") or []
        total = len(results)
        successes = sum(1 for item in results if item.get("success") is True)
        signals = sum(1 for item in results if item.get("anti_bot_signals"))
        proxies = sum(1 for item in results if item.get("proxy_used"))
        durations = [
            parsed
            for item in results
            if (parsed := _parse_duration_ms(item.get("duration"))) is not None
        ]
        metrics[framework["name"]] = {
            "runtime": framework["runtime"],
            "contract_rate": 1.0 if framework.get("summary") == "passed" else 0.0,
            "success_rate": round(successes / total, 4) if total else 0.0,
            "signal_capture_rate": round(signals / total, 4) if total else 0.0,
            "proxy_capture_rate": round(proxies / total, 4) if total else 0.0,
            "average_duration_ms": round(sum(durations) / len(durations), 4) if durations else None,
        }
    return metrics


def _make_alert(framework: str, key: str, severity: str, details: str) -> dict:
    return {
        "event_id": _alert_id(framework, key),
        "framework": framework,
        "source": "ultimate",
        "key": key,
        "severity": severity,
        "details": details,
    }


def collect_ultimate_trend_report(root: Path, history_dir: Path | None = None, current_report: dict | None = None) -> dict:
    current_report = current_report or verify_ultimate_contract.collect_ultimate_contract_report(root)
    resolved_history = history_dir or (root / "artifacts" / "ultimate-history")
    previous = _previous_snapshot(resolved_history)
    current_metrics = _framework_metrics(current_report)
    previous_metrics = previous.get("framework_metrics", {}) if previous else {}

    alerts: list[dict] = []
    trends: dict[str, dict] = {}
    for framework, metrics in current_metrics.items():
        previous_entry = previous_metrics.get(framework, {})
        delta = {}
        for key in METRIC_KEYS:
            previous_value = previous_entry.get(key)
            current_value = metrics.get(key)
            delta[key] = round(current_value - previous_value, 4) if previous_value is not None else None
            if previous_value is not None and current_value is not None and current_value < previous_value:
                severity = "failed" if key in {"contract_rate", "success_rate"} else "warning"
                alerts.append(_make_alert(framework, key, severity, f"{key} regressed from {previous_value} to {current_value}"))
        previous_duration = previous_entry.get("average_duration_ms")
        current_duration = metrics.get("average_duration_ms")
        duration_delta = None
        if previous_duration is not None and current_duration is not None:
            duration_delta = round(current_duration - previous_duration, 4)
            if current_duration > previous_duration * 1.2:
                alerts.append(_make_alert(framework, "average_duration_ms", "warning", f"average_duration_ms regressed from {previous_duration} to {current_duration}"))
        trends[framework] = {
            "runtime": metrics["runtime"],
            "current": metrics,
            "delta": {
                **delta,
                "average_duration_ms": duration_delta,
            },
        }

    failed = sum(1 for alert in alerts if alert["severity"] == "failed")
    warnings = sum(1 for alert in alerts if alert["severity"] == "warning")
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
        "command": "verify-ultimate-trends",
        "summary": summary,
        "summary_text": f"{len(current_metrics)} frameworks tracked, {len(alerts)} alerts",
        "exit_code": exit_code,
        "framework_metrics": current_metrics,
        "framework_trends": trends,
        "alerts": alerts,
        "history": {
            "count": len(_history_snapshots(resolved_history)),
            "generated_at": _now_iso(),
        },
    }


def write_snapshot(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build ultimate trend report")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent), help="repository root path")
    parser.add_argument("--history-dir", default="", help="directory containing historical ultimate snapshots")
    parser.add_argument("--snapshot-out", default="", help="optional path to write current snapshot")
    parser.add_argument("--json", action="store_true", help="print JSON output")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    history_dir = Path(args.history_dir).resolve() if args.history_dir else (root / "artifacts" / "ultimate-history")
    report = collect_ultimate_trend_report(root, history_dir)
    if args.snapshot_out:
        write_snapshot(Path(args.snapshot_out).resolve(), report)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"{report['command']}: {report['summary']}")
        print(report["summary_text"])
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
