from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def _run(command: list[str], cwd: Path) -> dict:
    completed = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "command": command,
        "exit_code": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
        "status": "passed" if completed.returncode == 0 else "failed",
    }


def run_rust_distributed_summary(root: Path) -> dict:
    rust_root = root / "rustspider"
    compile_check = _run(
        ["cargo", "test", "--features", "distributed", "--test", "distributed_scorecard"],
        rust_root,
    )
    behavior_check = _run(
        ["cargo", "test", "--test", "distributed_behavior_scorecard"],
        rust_root,
    )

    checks = [
        {
            "name": "distributed-feature-gate",
            "status": compile_check["status"],
            "details": compile_check["stderr"] or compile_check["stdout"] or "distributed feature gate completed",
        },
        {
            "name": "distributed-behavior-scorecard",
            "status": behavior_check["status"],
            "details": behavior_check["stderr"] or behavior_check["stdout"] or "distributed behavior scorecard completed",
        },
    ]

    passed = sum(1 for check in checks if check["status"] == "passed")
    failed = len(checks) - passed
    exit_code = 1 if failed else 0
    return {
        "command": "verify-rust-distributed-summary",
        "summary": "failed" if exit_code else "passed",
        "summary_text": f"{passed} passed, {failed} failed",
        "exit_code": exit_code,
        "runtime": "rust",
        "checks": checks,
        "metrics": {
            "checks_passed": passed,
            "checks_failed": failed,
            "checks_total": len(checks),
            "pass_rate": round(passed / len(checks), 4) if checks else 0.0,
            "feature_gate_ready": compile_check["status"] == "passed",
            "behavior_ready": behavior_check["status"] == "passed",
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Rust distributed capability summary checks")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent), help="repository root path")
    parser.add_argument("--json", action="store_true", help="print summary as JSON")
    args = parser.parse_args(argv)

    report = run_rust_distributed_summary(Path(args.root).resolve())
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("verify-rust-distributed-summary:", report["summary"])
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
