from __future__ import annotations

import argparse
import json
from pathlib import Path

import validate_antibot_replays
import validate_workflow_replays
import verify_gospider_distributed_summary
import verify_javaspider_captcha_summary
import verify_pyspider_concurrency_summary
import verify_rust_browser_summary
import verify_rust_distributed_summary
import verify_rust_preflight_summary
import verify_quality_policy_governance
import verify_runtime_readiness


def _load_report(fn, root: Path) -> dict:
    return fn(root)


def collect_replay_dashboard(root: Path) -> dict:
    antibot = _load_report(validate_antibot_replays.collect_antibot_replay_report, root)
    workflow = _load_report(validate_workflow_replays.collect_workflow_replay_report, root)
    readiness = _load_report(verify_runtime_readiness.collect_runtime_readiness_report, root)
    gospider_distributed = _load_report(verify_gospider_distributed_summary.run_gospider_distributed_summary, root)
    javaspider_captcha = _load_report(verify_javaspider_captcha_summary.run_javaspider_captcha_summary, root)
    pyspider_concurrency = _load_report(verify_pyspider_concurrency_summary.run_pyspider_concurrency_summary, root)
    rust_browser = _load_report(verify_rust_browser_summary.run_rust_browser_summary, root)
    rust_distributed = _load_report(verify_rust_distributed_summary.run_rust_distributed_summary, root)
    rust_preflight = _load_report(verify_rust_preflight_summary.run_rust_preflight, root)
    quality_governance = _load_report(verify_quality_policy_governance.collect_quality_policy_governance_report, root)

    sections = {
        "antibot_replays": antibot,
        "workflow_replays": workflow,
        "runtime_readiness": readiness,
        "gospider_distributed_summary": gospider_distributed,
        "javaspider_captcha_summary": javaspider_captcha,
        "pyspider_concurrency_summary": pyspider_concurrency,
        "rust_browser_summary": rust_browser,
        "rust_distributed_summary": rust_distributed,
        "rust_preflight_summary": rust_preflight,
        "quality_policy_governance": quality_governance,
    }

    passed_sections = sum(1 for report in sections.values() if report["summary"] == "passed")
    failed_sections = len(sections) - passed_sections
    exit_code = 1 if failed_sections else 0

    framework_scores = {}
    for framework in readiness.get("frameworks", []):
        framework_scores[framework["name"]] = {
            "runtime": framework["runtime"],
            "success_rate": framework["metrics"]["success_rate"],
            "resilience_rate": framework["metrics"]["resilience_rate"],
            "consistency_rate": framework["metrics"]["consistency_rate"],
            "artifact_integrity_rate": framework["metrics"]["artifact_integrity_rate"],
            "anti_bot_scenario_rate": framework["metrics"]["anti_bot_scenario_rate"],
            "recovery_signal_rate": framework["metrics"]["recovery_signal_rate"],
            "workflow_replay_rate": framework["metrics"]["workflow_replay_rate"],
            "control_plane_rate": framework["metrics"]["control_plane_rate"],
        }
    if "javaspider" in framework_scores:
        framework_scores["javaspider"]["captcha_pass_rate"] = javaspider_captcha["metrics"]["pass_rate"]
        framework_scores["javaspider"]["captcha_closed_loop_ready"] = javaspider_captcha["metrics"]["captcha_closed_loop_ready"]
        framework_scores["javaspider"]["audit_ready"] = javaspider_captcha["metrics"]["audit_ready"]
        framework_scores["javaspider"]["artifact_ready"] = javaspider_captcha["metrics"]["artifact_ready"]
    if "pyspider" in framework_scores:
        framework_scores["pyspider"]["concurrency_pass_rate"] = pyspider_concurrency["metrics"]["pass_rate"]
        framework_scores["pyspider"]["bounded_concurrency_ready"] = pyspider_concurrency["metrics"]["bounded_concurrency_ready"]
        framework_scores["pyspider"]["stream_ready"] = pyspider_concurrency["metrics"]["stream_ready"]
        framework_scores["pyspider"]["soak_ready"] = pyspider_concurrency["metrics"]["soak_ready"]
    if "gospider" in framework_scores:
        framework_scores["gospider"]["distributed_pass_rate"] = gospider_distributed["metrics"]["pass_rate"]
        framework_scores["gospider"]["lease_ready"] = gospider_distributed["metrics"]["lease_ready"]
        framework_scores["gospider"]["heartbeat_ready"] = gospider_distributed["metrics"]["heartbeat_ready"]
        framework_scores["gospider"]["dead_letter_ready"] = gospider_distributed["metrics"]["dead_letter_ready"]
        framework_scores["gospider"]["soak_ready"] = gospider_distributed["metrics"]["soak_ready"]
    if "rustspider" in framework_scores:
        framework_scores["rustspider"]["browser_pass_rate"] = rust_browser["metrics"]["pass_rate"]
        framework_scores["rustspider"]["browser_proof_ready"] = rust_browser["metrics"]["browser_proof_ready"]
        framework_scores["rustspider"]["distributed_pass_rate"] = rust_distributed["metrics"]["pass_rate"]
        framework_scores["rustspider"]["distributed_ready"] = rust_distributed["metrics"]["feature_gate_ready"] and rust_distributed["metrics"]["behavior_ready"]
        framework_scores["rustspider"]["preflight_pass_rate"] = rust_preflight["metrics"]["pass_rate"]
        framework_scores["rustspider"]["browser_ready"] = rust_preflight["metrics"]["browser_ready"]
        framework_scores["rustspider"]["ffmpeg_ready"] = rust_preflight["metrics"]["ffmpeg_ready"]

    return {
        "command": "verify-replay-dashboard",
        "summary": "failed" if exit_code else "passed",
        "summary_text": f"{passed_sections} sections passed, {failed_sections} sections failed",
        "exit_code": exit_code,
        "sections": sections,
        "framework_scores": framework_scores,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Aggregate replay/readiness gates into a single dashboard report")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent), help="repository root path")
    parser.add_argument("--json", action="store_true", help="print dashboard report as JSON")
    args = parser.parse_args(argv)

    report = collect_replay_dashboard(Path(args.root).resolve())
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("verify-replay-dashboard summary:", report["summary"])
        for name, section in report["sections"].items():
            print(f"- {name}: {section['summary']}")
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
