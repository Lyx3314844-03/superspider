from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path


def _extract_json_payload(stdout: str) -> str:
    stripped = stdout.strip()
    first_brace = stripped.find("{")
    return stripped[first_brace:] if first_brace >= 0 else stripped


def run_rust_preflight(root: Path) -> dict:
    with tempfile.TemporaryDirectory() as tmpdir:
        completed = subprocess.run(
            [
                "cargo",
                "run",
                "--quiet",
                "--bin",
                "preflight",
                "--",
                "--json",
                "--writable-path",
                tmpdir,
                "--require-browser",
                "--require-ffmpeg",
            ],
            cwd=root / "rustspider",
            capture_output=True,
            text=True,
            check=False,
        )

    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    payload = json.loads(_extract_json_payload(stdout))
    checks = payload.get("checks", [])
    passed = sum(1 for check in checks if check.get("status") == "passed")
    failed = sum(1 for check in checks if check.get("status") == "failed")
    total = passed + failed

    browser_ready = any(
        check.get("name") == "dependency:browser automation runtime" and check.get("status") == "passed"
        for check in checks
    )
    ffmpeg_ready = any(
        check.get("name") == "dependency:ffmpeg" and check.get("status") == "passed"
        for check in checks
    )
    filesystem_ready = any(
        str(check.get("name", "")).startswith("filesystem:") and check.get("status") == "passed"
        for check in checks
    )

    return {
        "command": "verify-rust-preflight-summary",
        "summary": payload.get("summary", "failed"),
        "summary_text": payload.get("summary_text", ""),
        "exit_code": payload.get("exit_code", completed.returncode or 1),
        "runtime": "rust",
        "checks": checks,
        "metrics": {
            "checks_passed": passed,
            "checks_failed": failed,
            "checks_total": total,
            "pass_rate": round(passed / total, 4) if total else 0.0,
            "browser_ready": browser_ready,
            "ffmpeg_ready": ffmpeg_ready,
            "filesystem_ready": filesystem_ready,
        },
        "stderr": stderr,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run and summarize the Rust preflight contract with production-like requirements")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent), help="repository root path")
    parser.add_argument("--json", action="store_true", help="print summary as JSON")
    args = parser.parse_args(argv)

    report = run_rust_preflight(Path(args.root).resolve())
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("verify-rust-preflight-summary:", report["summary"])
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
