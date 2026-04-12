from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import verify_rust_preflight_summary


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


def run_rust_browser_summary(root: Path) -> dict:
    rust_root = root / "rustspider"
    config_check = _run(
        ["cargo", "test", "--features", "browser", "--test", "capability_scorecard", "--", "browser_config_defaults_cover_headless_and_webdriver"],
        rust_root,
    )
    example_check = _run(
        ["cargo", "test", "--features", "browser", "--test", "browser_examples_scorecard"],
        rust_root,
    )
    compile_check = _run(
        ["cargo", "check", "--features", "browser", "--example", "playwright_example"],
        rust_root,
    )
    preflight = verify_rust_preflight_summary.run_rust_preflight(root)
    preflight_ready = preflight["summary"] == "passed" and preflight["metrics"]["browser_ready"]

    checks = [
        {
            "name": "browser-config",
            "status": config_check["status"],
            "details": config_check["stderr"] or config_check["stdout"] or "browser config test completed",
        },
        {
            "name": "browser-example-assets",
            "status": example_check["status"],
            "details": example_check["stderr"] or example_check["stdout"] or "browser example assets test completed",
        },
        {
            "name": "browser-example-compile",
            "status": compile_check["status"],
            "details": compile_check["stderr"] or compile_check["stdout"] or "browser example compile completed",
        },
        {
            "name": "browser-preflight",
            "status": "passed" if preflight_ready else "failed",
            "details": preflight["summary_text"],
        },
    ]

    passed = sum(1 for check in checks if check["status"] == "passed")
    failed = len(checks) - passed
    return {
        "command": "verify-rust-browser-summary",
        "summary": "failed" if failed else "passed",
        "summary_text": f"{passed} passed, {failed} failed",
        "exit_code": 1 if failed else 0,
        "runtime": "rust",
        "checks": checks,
        "metrics": {
            "checks_passed": passed,
            "checks_failed": failed,
            "checks_total": len(checks),
            "pass_rate": round(passed / len(checks), 4) if checks else 0.0,
            "config_ready": config_check["status"] == "passed",
            "example_assets_ready": example_check["status"] == "passed",
            "example_compile_ready": compile_check["status"] == "passed",
            "browser_proof_ready": failed == 0,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Rust browser capability summary checks")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent), help="repository root path")
    parser.add_argument("--json", action="store_true", help="print summary as JSON")
    args = parser.parse_args(argv)

    report = run_rust_browser_summary(Path(args.root).resolve())
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("verify-rust-browser-summary:", report["summary"])
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
