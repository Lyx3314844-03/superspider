from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import verify_benchmark_sla
import verify_blackbox_e2e
import verify_runtime_readiness


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


def _benchmark_trends(current: dict, previous: dict | None) -> dict:
    previous_report = previous.get("report", {}).get("benchmark_sla", {}) if previous else {}
    previous_frameworks = {
        item["name"]: item for item in previous_report.get("frameworks", [])
    }
    trends = {}
    for item in current.get("frameworks", []):
        previous_item = previous_frameworks.get(item["name"], {})
        current_sla = item["sla"]["success_job_ms"]["measured"]
        previous_sla = (
            previous_item.get("sla", {})
            .get("success_job_ms", {})
            .get("measured")
        )
        trends[item["name"]] = {
            "runtime": item["runtime"],
            "current": item["sla"]["success_job_ms"],
            "delta_ms": current_sla - previous_sla if isinstance(previous_sla, int) else None,
            "summary_changed": (
                item["summary"] != previous_item.get("summary")
                if previous_item else None
            ),
        }
    return trends


def _blackbox_trends(current: dict, previous: dict | None) -> dict:
    previous_report = previous.get("report", {}).get("blackbox_e2e", {}) if previous else {}
    previous_frameworks = {
        item["name"]: item for item in previous_report.get("frameworks", [])
    }
    trends = {}
    for item in current.get("frameworks", []):
        previous_item = previous_frameworks.get(item["name"], {})
        trends[item["name"]] = {
            "runtime": item["runtime"],
            "current": item["summary"],
            "previous": previous_item.get("summary"),
            "changed": (
                item["summary"] != previous_item.get("summary")
                if previous_item else None
            ),
        }
    return trends


def _readiness_trends(current: dict, previous: dict | None) -> dict:
    previous_report = previous.get("report", {}).get("runtime_readiness", {}) if previous else {}
    previous_frameworks = {
        item["name"]: item for item in previous_report.get("frameworks", [])
    }
    trends = {}
    for item in current.get("frameworks", []):
        previous_item = previous_frameworks.get(item["name"], {})
        current_control_plane = item.get("metrics", {}).get("control_plane_rate")
        previous_control_plane = previous_item.get("metrics", {}).get("control_plane_rate")
        trends[item["name"]] = {
            "runtime": item["runtime"],
            "current": {
                "summary": item["summary"],
                "control_plane_rate": current_control_plane,
            },
            "previous": {
                "summary": previous_item.get("summary"),
                "control_plane_rate": previous_control_plane,
            },
            "delta": {
                "control_plane_rate": (
                    round(current_control_plane - previous_control_plane, 4)
                    if isinstance(current_control_plane, (int, float))
                    and isinstance(previous_control_plane, (int, float))
                    else None
                )
            },
            "summary_changed": (
                item["summary"] != previous_item.get("summary")
                if previous_item else None
            ),
        }
    return trends


def _alerts(
    current_benchmark: dict,
    current_blackbox: dict,
    current_readiness: dict,
    previous: dict | None,
) -> list[dict]:
    alerts = []
    previous_benchmark = previous.get("report", {}).get("benchmark_sla", {}) if previous else {}
    previous_blackbox = previous.get("report", {}).get("blackbox_e2e", {}) if previous else {}
    previous_readiness = previous.get("report", {}).get("runtime_readiness", {}) if previous else {}
    previous_benchmark_frameworks = {
        item["name"]: item for item in previous_benchmark.get("frameworks", [])
    }
    previous_blackbox_frameworks = {
        item["name"]: item for item in previous_blackbox.get("frameworks", [])
    }
    previous_readiness_frameworks = {
        item["name"]: item for item in previous_readiness.get("frameworks", [])
    }

    for item in current_benchmark.get("frameworks", []):
        prev = previous_benchmark_frameworks.get(item["name"])
        if not prev:
            continue
        current_sla = item["sla"]["success_job_ms"]["measured"]
        prev_sla = prev["sla"]["success_job_ms"]["measured"]
        if current_sla > prev_sla:
            alerts.append({
                "framework": item["name"],
                "source": "benchmark-sla",
                "severity": "warning",
                "details": f"success_job_ms regressed from {prev_sla}ms to {current_sla}ms",
            })
        if item["summary"] == "failed" and prev.get("summary") == "passed":
            alerts.append({
                "framework": item["name"],
                "source": "benchmark-sla",
                "severity": "failed",
                "details": "benchmark/SLA summary regressed from passed to failed",
            })

    for item in current_blackbox.get("frameworks", []):
        prev = previous_blackbox_frameworks.get(item["name"])
        if prev and item["summary"] == "failed" and prev.get("summary") == "passed":
            alerts.append({
                "framework": item["name"],
                "source": "blackbox-e2e",
                "severity": "failed",
                "details": "blackbox e2e summary regressed from passed to failed",
            })

    for item in current_readiness.get("frameworks", []):
        prev = previous_readiness_frameworks.get(item["name"])
        if not prev:
            continue
        current_control_plane = item.get("metrics", {}).get("control_plane_rate")
        previous_control_plane = prev.get("metrics", {}).get("control_plane_rate")
        if (
            isinstance(current_control_plane, (int, float))
            and isinstance(previous_control_plane, (int, float))
            and current_control_plane < previous_control_plane
        ):
            alerts.append({
                "framework": item["name"],
                "source": "runtime-readiness",
                "severity": "failed",
                "details": (
                    "control_plane_rate regressed from "
                    f"{previous_control_plane:.4f} to {current_control_plane:.4f}"
                ),
            })
        if item.get("summary") == "failed" and prev.get("summary") == "passed":
            alerts.append({
                "framework": item["name"],
                "source": "runtime-readiness",
                "severity": "failed",
                "details": "runtime readiness summary regressed from passed to failed",
            })

    return alerts


def collect_benchmark_trend_report(
    root: Path,
    history_dir: Path | None = None,
    *,
    current_benchmark: dict | None = None,
    current_blackbox: dict | None = None,
    current_readiness: dict | None = None,
) -> dict:
    current_benchmark = current_benchmark or verify_benchmark_sla.collect_benchmark_sla_report(root)
    current_blackbox = current_blackbox or verify_blackbox_e2e.collect_blackbox_e2e_report(root)
    current_readiness = current_readiness or verify_runtime_readiness.collect_runtime_readiness_report(root)
    resolved_history = history_dir or (root / "artifacts" / "benchmark-history")
    previous = _previous_snapshot(resolved_history)
    alerts = _alerts(current_benchmark, current_blackbox, current_readiness, previous)
    failed_alerts = sum(1 for alert in alerts if alert["severity"] == "failed")
    warning_alerts = sum(1 for alert in alerts if alert["severity"] == "warning")

    if failed_alerts:
        summary = "failed"
        exit_code = 1
        summary_text = f"{failed_alerts} failed regressions, {warning_alerts} warnings"
    elif warning_alerts:
        summary = "passed"
        exit_code = 0
        summary_text = f"0 failed regressions, {warning_alerts} warnings"
    else:
        summary = "passed"
        exit_code = 0
        summary_text = "no regressions detected"

    return {
        "command": "verify-benchmark-trends",
        "summary": summary,
        "summary_text": summary_text,
        "exit_code": exit_code,
        "history_depth": len(_history_snapshots(resolved_history)),
        "benchmark_trends": _benchmark_trends(current_benchmark, previous),
        "blackbox_trends": _blackbox_trends(current_blackbox, previous),
        "readiness_trends": _readiness_trends(current_readiness, previous),
        "alerts": alerts,
    }


def snapshot_payload(benchmark_report: dict, blackbox_report: dict, runtime_readiness_report: dict) -> dict:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "report": {
            "benchmark_sla": benchmark_report,
            "blackbox_e2e": blackbox_report,
            "runtime_readiness": runtime_readiness_report,
        },
    }


def render_markdown(report: dict) -> str:
    lines = [
        "# Benchmark Trend Report",
        "",
        f"- summary: {report['summary']}",
        f"- history_depth: {report['history_depth']}",
        "",
        "## Benchmark Trends",
        "",
        "| Framework | Runtime | Current SLA | Delta (ms) | Summary Changed |",
        "| --- | --- | --- | --- | --- |",
    ]
    for name, item in report["benchmark_trends"].items():
        current = item["current"]
        lines.append(
            f"| {name} | {item['runtime']} | {current['measured']}ms / {current['threshold']}ms | "
            f"{item['delta_ms']} | {item['summary_changed']} |"
        )
    lines.extend([
        "",
        "## Blackbox Trends",
        "",
        "| Framework | Runtime | Current | Previous | Changed |",
        "| --- | --- | --- | --- | --- |",
    ])
    for name, item in report["blackbox_trends"].items():
        lines.append(
            f"| {name} | {item['runtime']} | {item['current']} | {item['previous']} | {item['changed']} |"
        )
    lines.extend([
        "",
        "## Runtime Readiness Trends",
        "",
        "| Framework | Runtime | Current Summary | Previous Summary | Control Plane | Delta | Summary Changed |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ])
    for name, item in report["readiness_trends"].items():
        current = item["current"]
        previous = item["previous"]
        lines.append(
            f"| {name} | {item['runtime']} | {current['summary']} | {previous['summary']} | "
            f"{current['control_plane_rate']} | {item['delta']['control_plane_rate']} | {item['summary_changed']} |"
        )
    if report["alerts"]:
        lines.extend(["", "## Alerts", ""])
        for alert in report["alerts"]:
            lines.append(f"- `{alert['severity']}` {alert['framework']}: {alert['details']}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build trend reports for benchmark/SLA and blackbox e2e")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent), help="repository root path")
    parser.add_argument("--history-dir", default="", help="optional history directory")
    parser.add_argument("--json", action="store_true", help="print JSON report")
    parser.add_argument("--markdown-out", default="", help="optional markdown output path")
    parser.add_argument("--snapshot-out", default="", help="optional snapshot output path")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    history_dir = Path(args.history_dir).resolve() if args.history_dir else None
    benchmark = verify_benchmark_sla.collect_benchmark_sla_report(root)
    blackbox = verify_blackbox_e2e.collect_blackbox_e2e_report(root)
    readiness = verify_runtime_readiness.collect_runtime_readiness_report(root)
    report = collect_benchmark_trend_report(
        root,
        history_dir=history_dir,
        current_benchmark=benchmark,
        current_blackbox=blackbox,
        current_readiness=readiness,
    )

    if args.snapshot_out:
        snapshot_path = Path(args.snapshot_out)
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot_path.write_text(
            json.dumps(snapshot_payload(benchmark, blackbox, readiness), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    if args.markdown_out:
        markdown_path = Path(args.markdown_out)
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(render_markdown(report), encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("verify-benchmark-trends:", report["summary"])
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
