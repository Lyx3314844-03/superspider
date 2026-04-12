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


def run_gospider_distributed_summary(root: Path) -> dict:
    go_root = root / "gospider"
    lease_check = _run(
        ["go", "test", "./distributed", "-run", "^TestDistributedServiceLeasesAndCompletesJob$"],
        go_root,
    )
    heartbeat_check = _run(
        ["go", "test", "./distributed", "-run", "^TestDistributedServiceHeartbeatRenewsLease$"],
        go_root,
    )
    dead_letter_check = _run(
        ["go", "test", "./distributed", "-run", "^TestDistributedServiceExpiredLeaseRequeuesUntilDeadLetter$"],
        go_root,
    )
    soak_check = _run(
        ["go", "test", "./distributed", "-run", "^TestRunSyntheticSoakProducesStableReport$"],
        go_root,
    )

    checks = [
        {
            "name": "lease-lifecycle",
            "status": lease_check["status"],
            "details": lease_check["stderr"] or lease_check["stdout"] or "lease lifecycle test completed",
        },
        {
            "name": "lease-heartbeat",
            "status": heartbeat_check["status"],
            "details": heartbeat_check["stderr"] or heartbeat_check["stdout"] or "lease heartbeat test completed",
        },
        {
            "name": "dead-letter-budget",
            "status": dead_letter_check["status"],
            "details": dead_letter_check["stderr"] or dead_letter_check["stdout"] or "dead-letter budget test completed",
        },
        {
            "name": "synthetic-soak",
            "status": soak_check["status"],
            "details": soak_check["stderr"] or soak_check["stdout"] or "synthetic soak test completed",
        },
    ]

    passed = sum(1 for check in checks if check["status"] == "passed")
    failed = len(checks) - passed
    exit_code = 1 if failed else 0
    return {
        "command": "verify-gospider-distributed-summary",
        "summary": "failed" if exit_code else "passed",
        "summary_text": f"{passed} passed, {failed} failed",
        "exit_code": exit_code,
        "runtime": "go",
        "checks": checks,
        "metrics": {
            "checks_passed": passed,
            "checks_failed": failed,
            "checks_total": len(checks),
            "pass_rate": round(passed / len(checks), 4) if checks else 0.0,
            "lease_ready": lease_check["status"] == "passed",
            "heartbeat_ready": heartbeat_check["status"] == "passed",
            "dead_letter_ready": dead_letter_check["status"] == "passed",
            "soak_ready": soak_check["status"] == "passed",
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run GoSpider distributed resilience summary checks")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent), help="repository root path")
    parser.add_argument("--json", action="store_true", help="print summary as JSON")
    args = parser.parse_args(argv)

    report = run_gospider_distributed_summary(Path(args.root).resolve())
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("verify-gospider-distributed-summary:", report["summary"])
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
