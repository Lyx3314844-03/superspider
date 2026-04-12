from __future__ import annotations

import argparse
import json
from pathlib import Path

import smoke_test
import verify_runtime_readiness


def _readiness_check(framework: dict, metric: str, expected: float = 1.0) -> dict:
    value = float(framework["metrics"].get(metric, 0.0))
    return {
        "name": metric,
        "status": "passed" if value >= expected else "failed",
        "details": f"measured={value:.4f} expected>={expected:.4f}",
    }


def _framework_report(smoke_check: dict, readiness_framework: dict) -> dict:
    checks = [
        {
            "name": "version-probe",
            "status": smoke_check["summary"],
            "details": smoke_check["details"],
        },
        _readiness_check(readiness_framework, "success_rate"),
        _readiness_check(readiness_framework, "resilience_rate"),
        _readiness_check(readiness_framework, "artifact_integrity_rate"),
        _readiness_check(readiness_framework, "anti_bot_scenario_rate"),
        _readiness_check(readiness_framework, "recovery_signal_rate"),
        _readiness_check(readiness_framework, "control_plane_rate"),
    ]
    passed = all(check["status"] == "passed" for check in checks)
    return {
        "name": readiness_framework["name"],
        "runtime": readiness_framework["runtime"],
        "summary": "passed" if passed else "failed",
        "exit_code": 0 if passed else 1,
        "checks": checks,
    }


def collect_blackbox_e2e_report(
    root: Path,
    smoke_report: dict | None = None,
    readiness_report: dict | None = None,
) -> dict:
    smoke_report = smoke_report or smoke_test.run_smoke_suite(root)
    readiness_report = readiness_report or verify_runtime_readiness.collect_runtime_readiness_report(root)
    smoke_by_name = {check["name"]: check for check in smoke_report["checks"]}
    frameworks = [
        _framework_report(smoke_by_name[item["name"]], item)
        for item in readiness_report["frameworks"]
    ]
    passed = sum(1 for item in frameworks if item["summary"] == "passed")
    failed = len(frameworks) - passed
    return {
        "command": "verify-blackbox-e2e",
        "summary": "passed" if failed == 0 else "failed",
        "summary_text": f"{passed} frameworks passed blackbox e2e, {failed} frameworks failed",
        "exit_code": 0 if failed == 0 else 1,
        "frameworks": frameworks,
    }


def render_markdown(report: dict) -> str:
    lines = [
        "# Blackbox E2E Report",
        "",
        "| Framework | Runtime | Summary | Version | Success | Resilience | Artifacts | Anti-bot | Recovery | Control Plane |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in report["frameworks"]:
        checks = {check["name"]: check["status"] for check in item["checks"]}
        lines.append(
            f"| {item['name']} | {item['runtime']} | {item['summary']} | "
            f"{checks['version-probe']} | {checks['success_rate']} | {checks['resilience_rate']} | "
            f"{checks['artifact_integrity_rate']} | {checks['anti_bot_scenario_rate']} | {checks['recovery_signal_rate']} | {checks['control_plane_rate']} |"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a blackbox end-to-end verification report")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent), help="repository root path")
    parser.add_argument("--json", action="store_true", help="print JSON report")
    parser.add_argument("--markdown-out", default="", help="optional markdown output path")
    args = parser.parse_args(argv)

    report = collect_blackbox_e2e_report(Path(args.root).resolve())
    if args.markdown_out:
        Path(args.markdown_out).write_text(render_markdown(report), encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("verify-blackbox-e2e:", report["summary"])
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
