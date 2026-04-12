from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import verify_runtime_stability


def _load_snapshot(path: Path) -> dict | None:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "report" in data and isinstance(data["report"], dict):
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
    return snapshots[-1] if snapshots else None


def _framework_map(report: dict) -> dict[str, dict]:
    return {framework["name"]: framework for framework in report.get("frameworks", [])}


def _trend_map(current: dict, previous: dict | None) -> dict:
    previous_report = previous.get("report", {}).get("runtime_stability", {}) if previous else {}
    previous_frameworks = _framework_map(previous_report)
    trends = {}
    for framework in current.get("frameworks", []):
        previous_framework = previous_frameworks.get(framework["name"], {})
        current_metrics = framework.get("metrics", {})
        previous_metrics = previous_framework.get("metrics", {})
        trends[framework["name"]] = {
            "runtime": framework["runtime"],
            "current": {
                "summary": framework["summary"],
                "frontier_stress_rate": current_metrics.get("frontier_stress_rate"),
                "recovery_rate": current_metrics.get("recovery_rate"),
                "control_plane_rate": current_metrics.get("control_plane_rate"),
                "distributed_longevity_rate": current_metrics.get("distributed_longevity_rate"),
            },
            "previous": {
                "summary": previous_framework.get("summary"),
                "frontier_stress_rate": previous_metrics.get("frontier_stress_rate"),
                "recovery_rate": previous_metrics.get("recovery_rate"),
                "control_plane_rate": previous_metrics.get("control_plane_rate"),
                "distributed_longevity_rate": previous_metrics.get("distributed_longevity_rate"),
            },
            "delta": {
                "frontier_stress_rate": _delta(current_metrics.get("frontier_stress_rate"), previous_metrics.get("frontier_stress_rate")),
                "recovery_rate": _delta(current_metrics.get("recovery_rate"), previous_metrics.get("recovery_rate")),
                "control_plane_rate": _delta(current_metrics.get("control_plane_rate"), previous_metrics.get("control_plane_rate")),
                "distributed_longevity_rate": _delta(current_metrics.get("distributed_longevity_rate"), previous_metrics.get("distributed_longevity_rate")),
            },
            "summary_changed": (
                framework["summary"] != previous_framework.get("summary")
                if previous_framework
                else None
            ),
        }
    return trends


def _delta(current: object, previous: object) -> float | None:
    if isinstance(current, (int, float)) and isinstance(previous, (int, float)):
        return round(float(current) - float(previous), 4)
    return None


def _alerts(current: dict, previous: dict | None) -> list[dict]:
    previous_report = previous.get("report", {}).get("runtime_stability", {}) if previous else {}
    previous_frameworks = _framework_map(previous_report)
    alerts: list[dict] = []
    for framework in current.get("frameworks", []):
        prev = previous_frameworks.get(framework["name"])
        if not prev:
            continue
        current_metrics = framework.get("metrics", {})
        previous_metrics = prev.get("metrics", {})
        if framework["summary"] == "failed" and prev.get("summary") == "passed":
            alerts.append(
                {
                    "framework": framework["name"],
                    "source": "runtime-stability",
                    "severity": "failed",
                    "details": "runtime stability summary regressed from passed to failed",
                }
            )
        for key in (
            "frontier_stress_rate",
            "recovery_rate",
            "control_plane_rate",
            "distributed_longevity_rate",
        ):
            current_value = current_metrics.get(key)
            previous_value = previous_metrics.get(key)
            if isinstance(current_value, (int, float)) and isinstance(previous_value, (int, float)) and current_value < previous_value:
                alerts.append(
                    {
                        "framework": framework["name"],
                        "source": "runtime-stability",
                        "severity": "failed",
                        "details": f"{key} regressed from {previous_value:.4f} to {current_value:.4f}",
                    }
                )
    return alerts


def collect_runtime_stability_trend_report(
    root: Path,
    history_dir: Path | None = None,
    *,
    current_report: dict | None = None,
) -> dict:
    current_report = current_report or verify_runtime_stability.collect_runtime_stability_report(root)
    resolved_history = history_dir or (root / "artifacts" / "stability-history")
    previous = _previous_snapshot(resolved_history)
    alerts = _alerts(current_report, previous)
    failed_alerts = sum(1 for alert in alerts if alert["severity"] == "failed")
    return {
        "command": "verify-runtime-stability-trends",
        "summary": "passed" if failed_alerts == 0 else "failed",
        "summary_text": "no regressions detected" if failed_alerts == 0 else f"{failed_alerts} failed regressions",
        "exit_code": 0 if failed_alerts == 0 else 1,
        "history_depth": len(_history_snapshots(resolved_history)),
        "stability_trends": _trend_map(current_report, previous),
        "alerts": alerts,
    }


def snapshot_payload(report: dict) -> dict:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "report": {
            "runtime_stability": report,
        },
    }


def render_markdown(report: dict) -> str:
    lines = [
        "# Runtime Stability Trend Report",
        "",
        f"- summary: {report['summary']}",
        f"- history_depth: {report['history_depth']}",
        "",
        "| Framework | Runtime | Current | Previous | Stress Delta | Recovery Delta | Control Plane Delta | Distributed Delta | Summary Changed |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for name, item in report["stability_trends"].items():
        lines.append(
            f"| {name} | {item['runtime']} | {item['current']['summary']} | {item['previous']['summary']} | "
            f"{item['delta']['frontier_stress_rate']} | {item['delta']['recovery_rate']} | {item['delta']['control_plane_rate']} | "
            f"{item['delta']['distributed_longevity_rate']} | {item['summary_changed']} |"
        )
    if report["alerts"]:
        lines.extend(["", "## Alerts", ""])
        for alert in report["alerts"]:
            lines.append(f"- `{alert['severity']}` {alert['framework']}: {alert['details']}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build trend reports for runtime stability evidence")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent), help="repository root path")
    parser.add_argument("--history-dir", default="", help="optional history directory")
    parser.add_argument("--json", action="store_true", help="print JSON report")
    parser.add_argument("--markdown-out", default="", help="optional markdown output path")
    parser.add_argument("--snapshot-out", default="", help="optional snapshot output path")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    history_dir = Path(args.history_dir).resolve() if args.history_dir else None
    report = collect_runtime_stability_trend_report(root, history_dir=history_dir)
    if args.snapshot_out:
        Path(args.snapshot_out).write_text(
            json.dumps(snapshot_payload(verify_runtime_stability.collect_runtime_stability_report(root)), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    if args.markdown_out:
        Path(args.markdown_out).write_text(render_markdown(report), encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("verify-runtime-stability-trends:", report["summary"])
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
