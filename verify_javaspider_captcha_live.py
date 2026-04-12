from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path


def _run(command: list[str], cwd: Path) -> dict:
    executable = (
        shutil.which(command[0])
        or shutil.which(f"{command[0]}.cmd")
        or shutil.which(f"{command[0]}.exe")
    )
    if executable:
        command = [executable, *command[1:]]
    completed = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        env=os.environ.copy(),
    )
    return {
        "command": command,
        "exit_code": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
        "status": "passed" if completed.returncode == 0 else "failed",
    }


def _enabled() -> bool:
    value = os.getenv("JAVASPIDER_LIVE_CAPTCHA_SMOKE", "")
    return value in {"1", "true", "TRUE", "True"}


def _command_available(command: str) -> bool:
    return any(
        shutil.which(candidate)
        for candidate in (command, f"{command}.cmd", f"{command}.exe")
    )


def _routes() -> dict[str, bool]:
    return {
        "tesseract": _command_available("tesseract"),
        "deathbycaptcha": bool(
            (os.getenv("DEATHBYCAPTCHA_USERNAME") or "").strip()
            and (os.getenv("DEATHBYCAPTCHA_PASSWORD") or "").strip()
        ),
        "custom": bool((os.getenv("JAVASPIDER_CUSTOM_CAPTCHA_URL") or "").strip()),
    }


def run_javaspider_captcha_live(root: Path) -> dict:
    java_root = root / "javaspider"
    enabled = _enabled()
    routes = _routes()

    if not enabled or not any(routes.values()):
        reasons = []
        if not enabled:
            reasons.append("JAVASPIDER_LIVE_CAPTCHA_SMOKE is not enabled")
        if not any(routes.values()):
            reasons.append("no live captcha route is configured")
        return {
            "command": "verify-javaspider-captcha-live",
            "summary": "skipped",
            "summary_text": "; ".join(reasons),
            "exit_code": 0,
            "runtime": "java",
            "checks": [
                {
                    "name": "live-captcha-smoke",
                    "status": "skipped",
                    "details": "; ".join(reasons),
                }
            ],
            "metrics": {
                "enabled": enabled,
                "routes": routes,
                "live_ready": False,
            },
        }

    compile_check = _run(["mvn", "-q", "-DskipTests", "test-compile"], java_root)
    live_check = _run(["mvn", "-q", "-Dtest=CaptchaSolverLiveSmokeTest", "test"], java_root)
    checks = [
        {
            "name": "test-compile",
            "status": compile_check["status"],
            "details": compile_check["stderr"] or compile_check["stdout"] or "test compile completed",
        },
        {
            "name": "live-captcha-smoke",
            "status": live_check["status"],
            "details": live_check["stderr"] or live_check["stdout"] or "live captcha smoke completed",
        },
    ]
    passed = sum(1 for check in checks if check["status"] == "passed")
    failed = len(checks) - passed
    return {
        "command": "verify-javaspider-captcha-live",
        "summary": "failed" if failed else "passed",
        "summary_text": f"{passed} passed, {failed} failed",
        "exit_code": 1 if failed else 0,
        "runtime": "java",
        "checks": checks,
        "metrics": {
            "enabled": enabled,
            "routes": routes,
            "checks_passed": passed,
            "checks_failed": failed,
            "checks_total": len(checks),
            "live_ready": failed == 0,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run optional live captcha smoke verification for JavaSpider")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent), help="repository root path")
    parser.add_argument("--json", action="store_true", help="print summary as JSON")
    args = parser.parse_args(argv)

    report = run_javaspider_captcha_live(Path(args.root).resolve())
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("verify-javaspider-captcha-live:", report["summary"])
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
