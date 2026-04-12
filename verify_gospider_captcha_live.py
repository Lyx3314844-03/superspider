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
    value = os.getenv("GOSPIDER_LIVE_CAPTCHA_SMOKE", "")
    return value in {"1", "true", "TRUE", "True"}


def _provider_keys() -> dict[str, bool]:
    return {
        "2captcha": bool((os.getenv("TWO_CAPTCHA_API_KEY") or os.getenv("CAPTCHA_API_KEY") or "").strip()),
        "anticaptcha": bool((os.getenv("ANTI_CAPTCHA_API_KEY") or "").strip()),
    }


def _challenge_targets() -> dict[str, bool]:
    return {
        "recaptcha": bool(
            (os.getenv("GOSPIDER_LIVE_RECAPTCHA_SITE_KEY") or "").strip()
            and (os.getenv("GOSPIDER_LIVE_RECAPTCHA_PAGE_URL") or "").strip()
        ),
        "hcaptcha": bool(
            (os.getenv("GOSPIDER_LIVE_HCAPTCHA_SITE_KEY") or "").strip()
            and (os.getenv("GOSPIDER_LIVE_HCAPTCHA_PAGE_URL") or "").strip()
        ),
    }


def run_gospider_captcha_live(root: Path) -> dict:
    go_root = root / "gospider"
    enabled = _enabled()
    keys = _provider_keys()
    targets = _challenge_targets()

    if not enabled or not any(keys.values()) or not any(targets.values()):
        reasons = []
        if not enabled:
            reasons.append("GOSPIDER_LIVE_CAPTCHA_SMOKE is not enabled")
        if not any(keys.values()):
            reasons.append("no captcha provider API key is configured")
        if not any(targets.values()):
            reasons.append("no live captcha challenge target is configured")
        return {
            "command": "verify-gospider-captcha-live",
            "summary": "skipped",
            "summary_text": "; ".join(reasons),
            "exit_code": 0,
            "runtime": "go",
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

    checks = []
    if keys["2captcha"] and targets["recaptcha"]:
        recaptcha = _run(
            ["go", "test", "./captcha", "-run", "TestLiveSolveReCaptchaWith2CaptchaIfConfigured$"],
            go_root,
        )
        checks.append(
            {
                "name": "2captcha-recaptcha-live-smoke",
                "status": recaptcha["status"],
                "details": recaptcha["stderr"] or recaptcha["stdout"] or "2captcha reCAPTCHA live smoke completed",
            }
        )

    if keys["anticaptcha"] and targets["hcaptcha"]:
        hcaptcha = _run(
            ["go", "test", "./captcha", "-run", "TestLiveSolveHCaptchaWithAntiCaptchaIfConfigured$"],
            go_root,
        )
        checks.append(
            {
                "name": "anticaptcha-hcaptcha-live-smoke",
                "status": hcaptcha["status"],
                "details": hcaptcha["stderr"] or hcaptcha["stdout"] or "anti-captcha hCaptcha live smoke completed",
            }
        )

    passed = sum(1 for check in checks if check["status"] == "passed")
    failed = len(checks) - passed
    return {
        "command": "verify-gospider-captcha-live",
        "summary": "failed" if failed else "passed",
        "summary_text": f"{passed} passed, {failed} failed",
        "exit_code": 1 if failed else 0,
        "runtime": "go",
        "checks": checks,
        "metrics": {
            "enabled": enabled,
            "provider_keys": keys,
            "challenge_targets": targets,
            "checks_passed": passed,
            "checks_failed": failed,
            "checks_total": len(checks),
            "live_ready": failed == 0 and len(checks) > 0,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run optional live captcha smoke verification for GoSpider")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent), help="repository root path")
    parser.add_argument("--json", action="store_true", help="print summary as JSON")
    args = parser.parse_args(argv)

    report = run_gospider_captcha_live(Path(args.root).resolve())
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("verify-gospider-captcha-live:", report["summary"])
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
