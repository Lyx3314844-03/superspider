from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path


def _run(command: list[str], cwd: Path) -> dict:
    executable = shutil.which(command[0]) or shutil.which(f"{command[0]}.cmd") or shutil.which(f"{command[0]}.exe")
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
    value = os.getenv("RUSTSPIDER_LIVE_CAPTCHA_SMOKE", "")
    return value in {"1", "true", "TRUE", "True"}


def _provider_keys() -> dict[str, bool]:
    return {
        "2captcha": bool((os.getenv("TWO_CAPTCHA_API_KEY") or os.getenv("CAPTCHA_API_KEY") or "").strip()),
        "anticaptcha": bool((os.getenv("ANTI_CAPTCHA_API_KEY") or "").strip()),
    }


def _challenge_targets() -> dict[str, bool]:
    return {
        "recaptcha": bool(
            (os.getenv("RUSTSPIDER_LIVE_RECAPTCHA_SITE_KEY") or "").strip()
            and (os.getenv("RUSTSPIDER_LIVE_RECAPTCHA_PAGE_URL") or "").strip()
        ),
        "hcaptcha": bool(
            (os.getenv("RUSTSPIDER_LIVE_HCAPTCHA_SITE_KEY") or "").strip()
            and (os.getenv("RUSTSPIDER_LIVE_HCAPTCHA_PAGE_URL") or "").strip()
        ),
        "turnstile": bool(
            (os.getenv("RUSTSPIDER_LIVE_TURNSTILE_SITE_KEY") or "").strip()
            and (os.getenv("RUSTSPIDER_LIVE_TURNSTILE_PAGE_URL") or "").strip()
        ),
    }


def run_rust_captcha_live(root: Path) -> dict:
    rust_root = root / "rustspider"
    enabled = _enabled()
    keys = _provider_keys()
    targets = _challenge_targets()

    if not enabled or not any(keys.values()) or not any(targets.values()):
        reasons = []
        if not enabled:
            reasons.append("RUSTSPIDER_LIVE_CAPTCHA_SMOKE is not enabled")
        if not any(keys.values()):
            reasons.append("no captcha provider API key is configured")
        if not any(targets.values()):
            reasons.append("no live captcha challenge target is configured")
        return {
            "command": "verify-rust-captcha-live",
            "summary": "skipped",
            "summary_text": "; ".join(reasons),
            "exit_code": 0,
            "runtime": "rust",
            "checks": [
                {
                    "name": "live-captcha-smoke",
                    "status": "skipped",
                    "details": "; ".join(reasons),
                }
            ],
            "metrics": {
                "enabled": enabled,
                "provider_keys": keys,
                "challenge_targets": targets,
                "live_ready": False,
            },
        }

    compile_check = _run(["cargo", "build", "--quiet"], rust_root)
    checks = [
        {
            "name": "compile-build",
            "status": compile_check["status"],
            "details": compile_check["stderr"] or compile_check["stdout"] or "cargo build completed",
        }
    ]

    if keys["2captcha"] and targets["recaptcha"]:
        two_check = _run(
            ["cargo", "test", "--quiet", "--lib", "live_solve_recaptcha_with_2captcha_if_configured", "--", "--exact", "--nocapture"],
            rust_root,
        )
        checks.append(
            {
                "name": "2captcha-recaptcha-live-smoke",
                "status": two_check["status"],
                "details": two_check["stderr"] or two_check["stdout"] or "2captcha reCAPTCHA live smoke completed",
            }
        )

    if keys["2captcha"] and targets["hcaptcha"]:
        hcaptcha_check = _run(
            ["cargo", "test", "--quiet", "--lib", "live_solve_hcaptcha_with_2captcha_if_configured", "--", "--exact", "--nocapture"],
            rust_root,
        )
        checks.append(
            {
                "name": "2captcha-hcaptcha-live-smoke",
                "status": hcaptcha_check["status"],
                "details": hcaptcha_check["stderr"] or hcaptcha_check["stdout"] or "2captcha hCaptcha live smoke completed",
            }
        )

    if keys["anticaptcha"] and targets["turnstile"]:
        anti_check = _run(
            ["cargo", "test", "--quiet", "--lib", "live_solve_turnstile_with_anticaptcha_if_configured", "--", "--exact", "--nocapture"],
            rust_root,
        )
        checks.append(
            {
                "name": "anticaptcha-turnstile-live-smoke",
                "status": anti_check["status"],
                "details": anti_check["stderr"] or anti_check["stdout"] or "anti-captcha Turnstile live smoke completed",
            }
        )

    passed = sum(1 for check in checks if check["status"] == "passed")
    failed = len(checks) - passed
    return {
        "command": "verify-rust-captcha-live",
        "summary": "failed" if failed else "passed",
        "summary_text": f"{passed} passed, {failed} failed",
        "exit_code": 1 if failed else 0,
        "runtime": "rust",
        "checks": checks,
        "metrics": {
            "enabled": enabled,
            "provider_keys": keys,
            "challenge_targets": targets,
            "checks_passed": passed,
            "checks_failed": failed,
            "checks_total": len(checks),
            "live_ready": failed == 0 and any(keys.values()),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run optional live captcha smoke verification for RustSpider")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent), help="repository root path")
    parser.add_argument("--json", action="store_true", help="print summary as JSON")
    args = parser.parse_args(argv)

    report = run_rust_captcha_live(Path(args.root).resolve())
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("verify-rust-captcha-live:", report["summary"])
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
