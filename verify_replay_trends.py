from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import generate_framework_scorecard
import verify_replay_dashboard
import verify_quality_policy_governance
import verify_quality_thresholds


SCORE_KEYS = [
    "success_rate",
    "resilience_rate",
    "consistency_rate",
    "artifact_integrity_rate",
    "anti_bot_scenario_rate",
    "recovery_signal_rate",
    "workflow_replay_rate",
    "captcha_pass_rate",
    "concurrency_pass_rate",
    "browser_pass_rate",
    "distributed_pass_rate",
    "preflight_pass_rate",
]
HARD_REGRESSION_KEYS = {
    "success_rate",
    "resilience_rate",
    "consistency_rate",
    "artifact_integrity_rate",
    "anti_bot_scenario_rate",
    "recovery_signal_rate",
    "workflow_replay_rate",
    "captcha_pass_rate",
    "concurrency_pass_rate",
    "browser_pass_rate",
    "distributed_pass_rate",
    "preflight_pass_rate",
}


def _alert_event_id(source: str, framework: str, key: str) -> str:
    seed = f"{source}|{framework}|{key}".encode("utf-8")
    return hashlib.sha256(seed).hexdigest()[:16]


def _make_alert(framework: str, source: str, key: str, severity: str, details: str) -> dict:
    return {
        "event_id": _alert_event_id(source, framework, key),
        "framework": framework,
        "source": source,
        "key": key,
        "severity": severity,
        "details": details,
    }


def _load_snapshot(path: Path) -> dict | None:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "report" in data and isinstance(data["report"], dict):
        report = data["report"]
        if "dashboard" not in report and report.get("command") == "verify-replay-dashboard":
            data["report"] = {
                "dashboard": report,
                "scorecard": None,
                "quality_thresholds": None,
                "quality_policy_governance": None,
            }
        return data
    if isinstance(data, dict) and data.get("command") == "verify-replay-dashboard":
        return {
            "generated_at": "",
            "report": {
                "dashboard": data,
                "scorecard": None,
                "quality_thresholds": None,
                "quality_policy_governance": None,
            },
            "source": str(path),
        }
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


def _framework_trends(current: dict, previous: dict | None) -> dict:
    previous_dashboard = previous.get("report", {}).get("dashboard", {}) if previous else {}
    previous_scores = previous_dashboard.get("framework_scores", {})
    trends = {}
    for framework, scores in current.get("framework_scores", {}).items():
        entry = {
            "runtime": scores["runtime"],
            "current": {key: scores.get(key) for key in SCORE_KEYS},
            "delta": {},
        }
        previous_entry = previous_scores.get(framework, {})
        for key in SCORE_KEYS:
            current_value = scores.get(key)
            if current_value is not None and key in previous_entry and previous_entry.get(key) is not None:
                entry["delta"][key] = round(current_value - previous_entry[key], 4)
            else:
                entry["delta"][key] = None
        trends[framework] = entry
    return trends


def _scorecard_trends(current: dict, previous: dict | None) -> dict:
    current_frameworks = current.get("frameworks", {})
    previous_scorecard = previous.get("report", {}).get("scorecard", {}) if previous else {}
    previous_frameworks = previous_scorecard.get("frameworks", {}) if isinstance(previous_scorecard, dict) else {}
    trends = {}
    for framework, entry in current_frameworks.items():
        evidence = entry.get("evidence", {})
        prev_evidence = previous_frameworks.get(framework, {}).get("evidence", {})
        trends[framework] = {
            "runtime": entry.get("runtime"),
            "current": evidence,
            "delta": {
                "test_files": (
                    evidence.get("test_files", 0) - prev_evidence["test_files"]
                    if "test_files" in prev_evidence else None
                ),
                "readme_present": (
                    evidence.get("readme_present") != prev_evidence.get("readme_present")
                    if "readme_present" in prev_evidence else None
                ),
                "deploy_verified": (
                    evidence.get("deploy_verified") != prev_evidence.get("deploy_verified")
                    if "deploy_verified" in prev_evidence else None
                ),
            },
        }
    return trends


def _policy_trends(current: dict, previous: dict | None) -> dict:
    previous_quality = previous.get("report", {}).get("quality_thresholds", {}) if previous else {}
    previous_policy = previous_quality.get("policy", {}) if isinstance(previous_quality, dict) else {}
    current_policy = current.get("policy", {})
    return {
        "current": {
            "profile": current_policy.get("profile"),
            "digest": current_policy.get("digest"),
        },
        "previous": {
            "profile": previous_policy.get("profile"),
            "digest": previous_policy.get("digest"),
        },
        "changed": (
            bool(previous_policy)
            and (
                current_policy.get("profile") != previous_policy.get("profile")
                or current_policy.get("digest") != previous_policy.get("digest")
            )
        ),
    }


def _governance_trends(current: dict, previous: dict | None) -> dict:
    previous_governance = previous.get("report", {}).get("quality_policy_governance", {}) if previous else {}
    previous_meta = previous_governance.get("governance", {}) if isinstance(previous_governance, dict) else {}
    current_meta = current.get("governance", {})
    return {
        "current": {
            "version": current_meta.get("version"),
            "policy_digest": current_meta.get("policy_digest"),
            "default_profile": current_meta.get("default_profile"),
            "release_profile": current_meta.get("release_profile"),
        },
        "previous": {
            "version": previous_meta.get("version"),
            "policy_digest": previous_meta.get("policy_digest"),
            "default_profile": previous_meta.get("default_profile"),
            "release_profile": previous_meta.get("release_profile"),
        },
        "changed": (
            bool(previous_meta)
            and (
                current_meta.get("version") != previous_meta.get("version")
                or current_meta.get("policy_digest") != previous_meta.get("policy_digest")
                or current_meta.get("default_profile") != previous_meta.get("default_profile")
                or current_meta.get("release_profile") != previous_meta.get("release_profile")
            )
        ),
    }


def _collect_regression_alerts(
    current_dashboard: dict,
    current_scorecard: dict,
    current_quality: dict,
    current_governance: dict,
    previous: dict | None,
) -> list[dict]:
    alerts: list[dict] = []
    previous_dashboard = previous.get("report", {}).get("dashboard", {}) if previous else {}
    previous_scores = previous_dashboard.get("framework_scores", {})
    previous_scorecard = previous.get("report", {}).get("scorecard", {}) if previous else {}
    previous_frameworks = previous_scorecard.get("frameworks", {}) if isinstance(previous_scorecard, dict) else {}

    for framework, scores in current_dashboard.get("framework_scores", {}).items():
        prev_scores = previous_scores.get(framework, {})
        for key in SCORE_KEYS:
            current_value = scores.get(key)
            previous_value = prev_scores.get(key)
            if current_value is None or previous_value is None:
                continue
            if current_value < previous_value:
                severity = "failed" if key in HARD_REGRESSION_KEYS else "warning"
                alerts.append(_make_alert(
                    framework,
                    "dashboard",
                    key,
                    severity,
                    f"{key} regressed from {previous_value} to {current_value}",
                ))

    for framework, entry in current_scorecard.get("frameworks", {}).items():
        evidence = entry.get("evidence", {})
        prev_evidence = previous_frameworks.get(framework, {}).get("evidence", {})
        if not prev_evidence:
            continue

        current_tests = evidence.get("test_files")
        previous_tests = prev_evidence.get("test_files")
        if isinstance(current_tests, int) and isinstance(previous_tests, int) and current_tests < previous_tests:
            alerts.append(_make_alert(
                framework,
                "scorecard",
                "test_files",
                "warning",
                f"test_files regressed from {previous_tests} to {current_tests}",
            ))

        for key in ("readme_present", "deploy_verified", "monitor_verified", "browser_verified", "anti_bot_verified"):
            current_value = evidence.get(key)
            previous_value = prev_evidence.get(key)
            if previous_value is True and current_value is False:
                alerts.append(_make_alert(
                    framework,
                    "scorecard",
                    key,
                    "failed",
                    f"{key} regressed from true to false",
                ))

        if prev_evidence.get("distributed") == "verified" and evidence.get("distributed") != "verified":
            alerts.append(_make_alert(
                framework,
                "scorecard",
                "distributed",
                "warning",
                f"distributed status regressed from {prev_evidence.get('distributed')} to {evidence.get('distributed')}",
            ))

        if prev_evidence.get("test_status") in {"moderate", "strong"} and evidence.get("test_status") == "thin":
            alerts.append(_make_alert(
                framework,
                "scorecard",
                "test_status",
                "warning",
                f"test_status regressed from {prev_evidence.get('test_status')} to thin",
            ))

    previous_quality = previous.get("report", {}).get("quality_thresholds", {}) if previous else {}
    previous_policy = previous_quality.get("policy", {}) if isinstance(previous_quality, dict) else {}
    current_policy = current_quality.get("policy", {})
    if previous_policy:
        if current_policy.get("profile") != previous_policy.get("profile"):
            alerts.append(_make_alert(
                "global",
                "quality-policy",
                "profile",
                "failed",
                f"quality threshold profile changed from {previous_policy.get('profile')} to {current_policy.get('profile')}",
            ))
        elif current_policy.get("digest") != previous_policy.get("digest"):
            alerts.append(_make_alert(
                "global",
                "quality-policy",
                "digest",
                "warning",
                "quality threshold policy digest changed since the previous snapshot",
            ))

    previous_governance = previous.get("report", {}).get("quality_policy_governance", {}) if previous else {}
    previous_governance_meta = previous_governance.get("governance", {}) if isinstance(previous_governance, dict) else {}
    current_governance_meta = current_governance.get("governance", {})
    if previous_governance_meta:
        if current_governance_meta.get("version") != previous_governance_meta.get("version"):
            alerts.append(_make_alert(
                "global",
                "quality-governance",
                "version",
                "warning",
                f"quality governance version changed from {previous_governance_meta.get('version')} to {current_governance_meta.get('version')}",
            ))
        if current_governance_meta.get("policy_digest") != previous_governance_meta.get("policy_digest"):
            alerts.append(_make_alert(
                "global",
                "quality-governance",
                "policy_digest",
                "warning",
                "quality governance digest changed since the previous snapshot",
            ))

    return alerts


def collect_replay_trend_report(root: Path, history_dir: Path | None = None) -> dict:
    return collect_replay_trend_report_with_current(root, history_dir=history_dir)


def collect_replay_trend_report_with_current(
    root: Path,
    history_dir: Path | None = None,
    *,
    current_dashboard: dict | None = None,
    current_scorecard: dict | None = None,
    current_quality: dict | None = None,
    current_governance: dict | None = None,
) -> dict:
    current_dashboard = current_dashboard or verify_replay_dashboard.collect_replay_dashboard(root)
    current_scorecard = current_scorecard or generate_framework_scorecard.collect_framework_scorecard(root, dashboard=current_dashboard)
    current_quality = current_quality or verify_quality_thresholds.collect_quality_threshold_report(
        root,
        dashboard=current_dashboard,
        scorecard=current_scorecard,
    )
    current_governance = current_governance or verify_quality_policy_governance.collect_quality_policy_governance_report(root)
    resolved_history = history_dir or (root / "artifacts" / "replay-history")
    previous = _previous_snapshot(resolved_history)
    snapshots = _history_snapshots(resolved_history)
    alerts = _collect_regression_alerts(current_dashboard, current_scorecard, current_quality, current_governance, previous)
    failed_alerts = sum(1 for alert in alerts if alert["severity"] == "failed")
    warning_alerts = sum(1 for alert in alerts if alert["severity"] == "warning")

    if failed_alerts:
        summary = "failed"
        exit_code = 1
    elif warning_alerts:
        summary = "warning"
        exit_code = 0
    else:
        summary = current_dashboard["summary"]
        exit_code = current_dashboard["exit_code"]

    return {
        "command": "verify-replay-trends",
        "summary": summary,
        "summary_text": f"{len(snapshots)} historical snapshots, {warning_alerts} warnings, {failed_alerts} failed regressions",
        "exit_code": exit_code,
        "current": {
            "dashboard": current_dashboard,
            "scorecard": current_scorecard,
            "quality_thresholds": current_quality,
            "quality_policy_governance": current_governance,
        },
        "history": {
            "count": len(snapshots),
            "latest": previous.get("generated_at", "") if previous else "",
            "latest_source": previous.get("source", "") if previous else "",
        },
        "framework_trends": _framework_trends(current_dashboard, previous),
        "scorecard_trends": _scorecard_trends(current_scorecard, previous),
        "policy_trends": _policy_trends(current_quality, previous),
        "governance_trends": _governance_trends(current_governance, previous),
        "alerts": alerts,
    }


def write_snapshot(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "report": report["current"],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build replay trend report from current dashboard and historical snapshots")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent), help="repository root path")
    parser.add_argument("--history-dir", default="", help="directory containing historical replay dashboard snapshots")
    parser.add_argument("--snapshot-out", default="", help="optional path to write current dashboard snapshot")
    parser.add_argument("--json", action="store_true", help="print trend report as JSON")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    history_dir = Path(args.history_dir).resolve() if args.history_dir else (root / "artifacts" / "replay-history")
    report = collect_replay_trend_report(root, history_dir)
    if args.snapshot_out:
        write_snapshot(Path(args.snapshot_out).resolve(), report)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("verify-replay-trends summary:", report["summary"])
        print("history snapshots:", report["history"]["count"])
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
