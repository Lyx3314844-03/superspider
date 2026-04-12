from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

import verify_gospider_distributed_summary
import verify_pyspider_concurrency_summary
import verify_rust_distributed_summary
import verify_runtime_readiness


FRAMEWORKS: tuple[tuple[str, str], ...] = (
    ("javaspider", "java"),
    ("pyspider", "python"),
    ("gospider", "go"),
    ("rustspider", "rust"),
)


def _resolve_command(command: list[str]) -> list[str]:
    if not command:
        return command
    executable = (
        shutil.which(command[0])
        or shutil.which(f"{command[0]}.cmd")
        or shutil.which(f"{command[0]}.exe")
    )
    if executable:
        return [executable, *command[1:]]
    return command


def _run(command: list[str], cwd: Path, timeout: int = 600) -> dict:
    resolved = _resolve_command(command)
    completed = subprocess.run(
        resolved,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )
    details = "\n".join(
        part for part in (completed.stdout.strip(), completed.stderr.strip()) if part
    ).strip()
    return {
        "command": resolved,
        "exit_code": completed.returncode,
        "status": "passed" if completed.returncode == 0 else "failed",
        "details": details or "command completed",
    }


def _stress_command(root: Path, framework: str) -> tuple[list[str], Path]:
    if framework == "javaspider":
        return (
            ["mvn", "-q", "-Dtest=SpiderRuntimeStabilityTest", "test"],
            root / "javaspider",
        )
    if framework == "pyspider":
        return (
            [
                sys.executable,
                "-m",
                "pytest",
                str(root / "pyspider" / "tests" / "test_runtime_contracts.py"),
                "-q",
                "--no-cov",
                "-k",
                "frontier_synthetic_soak_and_recovery_metrics",
            ],
            root,
        )
    if framework == "gospider":
        return (
            ["go", "test", "./core", "-run", "^TestAutoscaledFrontierSyntheticSoakAndRecovery$"],
            root / "gospider",
        )
    return (
        ["cargo", "test", "frontier_synthetic_soak_recovers_after_failures", "--lib"],
        root / "rustspider",
    )


def _readiness_by_framework(root: Path) -> dict[str, dict]:
    report = verify_runtime_readiness.collect_runtime_readiness_report(root)
    return {item["name"]: item for item in report.get("frameworks", [])}


def _distributed_by_framework(root: Path) -> dict[str, dict]:
    return {
        "gospider": verify_gospider_distributed_summary.run_gospider_distributed_summary(root),
        "pyspider": verify_pyspider_concurrency_summary.run_pyspider_concurrency_summary(root),
        "rustspider": verify_rust_distributed_summary.run_rust_distributed_summary(root),
    }


def collect_runtime_stability_report(root: Path) -> dict:
    readiness = _readiness_by_framework(root)
    distributed = _distributed_by_framework(root)
    frameworks: list[dict] = []

    for framework, runtime in FRAMEWORKS:
        checks: list[dict] = []

        stress_command, stress_cwd = _stress_command(root, framework)
        stress = _run(stress_command, stress_cwd, timeout=1800)
        checks.append(
            {
                "name": "frontier-stress",
                "status": stress["status"],
                "details": stress["details"],
                "command": stress["command"],
            }
        )

        readiness_payload = readiness.get(framework)
        if readiness_payload:
            recovery_rate = float(readiness_payload["metrics"].get("recovery_signal_rate", 0.0))
            control_plane_rate = float(readiness_payload["metrics"].get("control_plane_rate", 0.0))
            checks.append(
                {
                    "name": "recovery-signals",
                    "status": "passed" if recovery_rate >= 1.0 else "failed",
                    "details": f"recovery_signal_rate={recovery_rate:.4f}",
                }
            )
            checks.append(
                {
                    "name": "runtime-control-plane",
                    "status": "passed" if control_plane_rate >= 1.0 else "failed",
                    "details": f"control_plane_rate={control_plane_rate:.4f}",
                }
            )
        else:
            recovery_rate = 0.0
            control_plane_rate = 0.0
            checks.append(
                {
                    "name": "recovery-signals",
                    "status": "failed",
                    "details": "runtime readiness report missing for framework",
                }
            )
            checks.append(
                {
                    "name": "runtime-control-plane",
                    "status": "failed",
                    "details": "runtime readiness report missing for framework",
                }
            )

        distributed_payload = distributed.get(framework)
        if distributed_payload:
            distributed_pass_rate = float(distributed_payload["metrics"].get("pass_rate", 0.0))
            checks.append(
                {
                    "name": "distributed-longevity",
                    "status": distributed_payload["summary"],
                    "details": distributed_payload["summary_text"],
                }
            )
            soak_ready = distributed_payload.get("summary") == "passed" or any(
                check["name"] in {"synthetic-soak", "bounded-concurrency"}
                and check["status"] == "passed"
                for check in distributed_payload.get("checks", [])
            )
            checks.append(
                {
                    "name": "soak-evidence",
                    "status": "passed" if soak_ready else "failed",
                    "details": f"distributed/async summary pass_rate={distributed_pass_rate:.4f}",
                }
            )
        else:
            distributed_pass_rate = None
            checks.append(
                {
                    "name": "distributed-longevity",
                    "status": "skipped",
                    "details": "no distributed longevity surface defined for this runtime",
                }
            )
            checks.append(
                {
                    "name": "soak-evidence",
                    "status": "passed" if stress["status"] == "passed" else "failed",
                    "details": "frontier stress test is the current longevity evidence for this runtime",
                }
            )

        passed = sum(1 for check in checks if check["status"] == "passed")
        failed = sum(1 for check in checks if check["status"] == "failed")
        skipped = len(checks) - passed - failed
        total_effective = passed + failed
        frameworks.append(
            {
                "name": framework,
                "runtime": runtime,
                "summary": "failed" if failed else "passed",
                "exit_code": 1 if failed else 0,
                "metrics": {
                    "checks_passed": passed,
                    "checks_failed": failed,
                    "checks_skipped": skipped,
                    "checks_total": len(checks),
                    "pass_rate": round(passed / total_effective, 4) if total_effective else 1.0,
                    "frontier_stress_rate": 1.0 if stress["status"] == "passed" else 0.0,
                    "recovery_rate": recovery_rate,
                    "control_plane_rate": control_plane_rate,
                    "distributed_longevity_rate": distributed_pass_rate,
                    "soak_ready": any(
                        check["name"] == "soak-evidence" and check["status"] == "passed"
                        for check in checks
                    ),
                },
                "checks": checks,
            }
        )

    passed_frameworks = sum(1 for framework in frameworks if framework["summary"] == "passed")
    failed_frameworks = len(frameworks) - passed_frameworks
    return {
        "command": "verify-runtime-stability",
        "summary": "passed" if failed_frameworks == 0 else "failed",
        "summary_text": f"{passed_frameworks} frameworks passed, {failed_frameworks} frameworks failed",
        "exit_code": 0 if failed_frameworks == 0 else 1,
        "frameworks": frameworks,
    }


def render_markdown(report: dict) -> str:
    lines = [
        "# Runtime Stability",
        "",
        f"Summary: {report['summary_text']}",
        "",
        "| Framework | Status |",
        "| --- | --- |",
    ]
    for framework in report["frameworks"]:
        lines.append(f"| {framework['name']} | {framework['summary']} |")
    lines.append("")
    for framework in report["frameworks"]:
        lines.append(f"## {framework['name']}")
        lines.append("")
        lines.append(f"- Runtime: `{framework['runtime']}`")
        lines.append(f"- Summary: `{framework['summary']}`")
        metrics = framework["metrics"]
        lines.append(
            f"- Metrics: pass_rate={metrics['pass_rate']}, frontier_stress_rate={metrics['frontier_stress_rate']}, recovery_rate={metrics['recovery_rate']}, control_plane_rate={metrics['control_plane_rate']}, distributed_longevity_rate={metrics['distributed_longevity_rate']}"
        )
        for check in framework["checks"]:
            lines.append(f"- {check['name']}: {check['status']} | {check['details']}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify long-running stability evidence across the four runtimes")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent), help="repository root path")
    parser.add_argument("--json", action="store_true", help="print summary as JSON")
    parser.add_argument("--markdown-out", default="", help="optional markdown output path")
    args = parser.parse_args(argv)

    report = collect_runtime_stability_report(Path(args.root).resolve())
    if args.markdown_out:
        Path(args.markdown_out).write_text(render_markdown(report), encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("verify-runtime-stability:", report["summary"])
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
