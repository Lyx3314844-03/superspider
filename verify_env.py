from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from pathlib import Path

ALLOWED_DOCTOR_SUMMARIES = {"passed", "failed"}
ALLOWED_DOCTOR_CHECK_STATUSES = {"passed", "failed", "warning", "skipped"}


def build_pyspider_command(system_name: str | None = None) -> list[str]:
    system_name = system_name or platform.system()
    executable = Path(sys.executable)
    script_name = "pyspider.exe" if system_name == "Windows" else "pyspider"
    console_script = executable.with_name(script_name)
    if console_script.exists():
        return [str(console_script), "doctor", "--json"]
    return [sys.executable, "-m", "pyspider", "doctor", "--json"]


def build_framework_commands(system_name: str | None = None) -> dict[str, dict[str, list[str] | str]]:
    system_name = system_name or platform.system()
    if system_name == "Windows":
        javaspider_command = [
            "powershell",
            "-NoProfile",
            "-Command",
            "& mvn -q compile dependency:copy-dependencies; java -cp 'target/classes;target/dependency/*' com.javaspider.EnhancedSpider doctor --json",
        ]
    else:
        javaspider_command = [
            "bash",
            "-lc",
            "mvn -q compile dependency:copy-dependencies && java -cp 'target/classes:target/dependency/*' com.javaspider.EnhancedSpider doctor --json",
        ]

    return {
        "javaspider": {
            "cwd": "javaspider",
            "command": javaspider_command,
        },
        "pyspider": {
            "cwd": ".",
            "command": build_pyspider_command(system_name),
        },
        "gospider": {
            "cwd": "gospider",
            "command": ["go", "run", "./cmd/gospider", "doctor", "--json"],
        },
        "rustspider": {
            "cwd": "rustspider",
            "command": [
                "cargo",
                "run",
                "--quiet",
                "--",
                "doctor",
                "--json",
            ],
        },
    }


FRAMEWORK_COMMANDS = build_framework_commands()


def run_framework_doctor(root: Path, framework: str) -> dict:
    command_spec = FRAMEWORK_COMMANDS[framework]
    framework_root = root / command_spec["cwd"]
    try:
        completed = subprocess.run(
            command_spec["command"],
            cwd=framework_root,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        return _failed_framework_report(
            framework,
            1,
            [],
            f"command not found: {exc}",
        )

    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    if stdout:
        try:
            report = _normalize_doctor_report(
                framework,
                json.loads(_extract_json_payload(stdout)),
                completed.returncode,
                stderr,
            )
        except json.JSONDecodeError:
            report = _failed_framework_report(
                framework,
                completed.returncode or 1,
                [],
                f"non-json stdout: {stdout}",
            )
    else:
        report = _failed_framework_report(framework, completed.returncode, [], stderr or "empty stdout")

    if stderr:
        report["stderr"] = stderr
    return report


def aggregate_framework_reports(root: Path) -> dict:
    frameworks = []
    for framework in ("javaspider", "pyspider", "gospider", "rustspider"):
        frameworks.append({
            "name": framework,
            "report": run_framework_doctor(root, framework),
        })

    exit_code = 1 if any(item["report"].get("exit_code", 1) != 0 for item in frameworks) else 0
    return {
        "command": "verify-env",
        "summary": "failed" if exit_code else "passed",
        "exit_code": exit_code,
        "frameworks": frameworks,
    }


def framework_runtime(framework: str) -> str:
    return {
        "javaspider": "java",
        "pyspider": "python",
        "gospider": "go",
        "rustspider": "rust",
    }[framework]


def _failed_framework_report(framework: str, exit_code: int, checks: list[dict], stderr: str) -> dict:
    passed = sum(1 for check in checks if check.get("status") == "passed")
    failed = sum(1 for check in checks if check.get("status") == "failed")
    if failed == 0:
        failed = 1
    return {
        "command": "doctor",
        "runtime": framework_runtime(framework),
        "summary": "failed",
        "summary_text": f"{passed} passed, {failed} failed",
        "exit_code": exit_code if exit_code else 1,
        "checks": checks,
        "stderr": stderr,
    }


def _extract_json_payload(stdout: str) -> str:
    stripped = stdout.strip()
    if stripped.startswith("{"):
        return stripped
    first_brace = stripped.find("{")
    if first_brace >= 0:
        return stripped[first_brace:]
    return stripped


def _normalize_doctor_report(framework: str, report: dict, process_exit_code: int, stderr: str) -> dict:
    if not isinstance(report, dict):
        return _failed_framework_report(
            framework,
            process_exit_code,
            [],
            "doctor contract violation: report must be a JSON object",
        )

    checks = report.get("checks")
    if not isinstance(checks, list):
        return _failed_framework_report(
            framework,
            process_exit_code,
            [],
            "doctor contract violation: checks must be a list",
        )

    normalized_checks = []
    for index, check in enumerate(checks):
        normalized = _normalize_doctor_check(check)
        if normalized is None:
            return _failed_framework_report(
                framework,
                process_exit_code,
                [],
                f"doctor contract violation: invalid check at index {index}",
            )
        normalized_checks.append(normalized)

    expected_runtime = framework_runtime(framework)
    if report.get("command") != "doctor":
        return _failed_framework_report(
            framework,
            process_exit_code,
            normalized_checks,
            f"doctor contract violation: command must be 'doctor', got {report.get('command')!r}",
        )
    if report.get("runtime") != expected_runtime:
        return _failed_framework_report(
            framework,
            process_exit_code,
            normalized_checks,
            f"doctor contract violation: runtime must be {expected_runtime!r}, got {report.get('runtime')!r}",
        )

    summary = report.get("summary")
    if summary not in ALLOWED_DOCTOR_SUMMARIES:
        return _failed_framework_report(
            framework,
            process_exit_code,
            normalized_checks,
            f"doctor contract violation: summary must be one of {sorted(ALLOWED_DOCTOR_SUMMARIES)!r}",
        )

    summary_text = report.get("summary_text")
    if not isinstance(summary_text, str) or not summary_text.strip():
        return _failed_framework_report(
            framework,
            process_exit_code,
            normalized_checks,
            "doctor contract violation: summary_text must be a non-empty string",
        )

    exit_code = report.get("exit_code")
    if not isinstance(exit_code, int) or exit_code not in (0, 1):
        return _failed_framework_report(
            framework,
            process_exit_code,
            normalized_checks,
            f"doctor contract violation: exit_code must be 0 or 1, got {exit_code!r}",
        )

    if exit_code != process_exit_code:
        return _failed_framework_report(
            framework,
            process_exit_code,
            normalized_checks,
            f"doctor contract violation: payload exit_code {exit_code} does not match process exit code {process_exit_code}",
        )

    has_failed_check = any(check["status"] == "failed" for check in normalized_checks)
    if summary == "passed" and has_failed_check:
        return _failed_framework_report(
            framework,
            process_exit_code,
            normalized_checks,
            "doctor contract violation: passed summary cannot contain failed checks",
        )
    if summary == "failed" and not has_failed_check:
        return _failed_framework_report(
            framework,
            process_exit_code,
            normalized_checks,
            "doctor contract violation: failed summary must contain at least one failed check",
        )

    normalized_report = dict(report)
    normalized_report["checks"] = normalized_checks
    return normalized_report


def _normalize_doctor_check(check: object) -> dict | None:
    if not isinstance(check, dict):
        return None

    name = check.get("name")
    status = check.get("status")
    details = check.get("details")
    if not isinstance(name, str) or not name.strip():
        return None
    if not isinstance(status, str) or status not in ALLOWED_DOCTOR_CHECK_STATUSES:
        return None
    if not isinstance(details, str):
        return None

    return {
        "name": name,
        "status": status,
        "details": details,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Aggregate environment checks across all four spider frameworks")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent), help="repository root path")
    parser.add_argument("--json", action="store_true", help="print aggregate report as JSON")
    args = parser.parse_args(argv)

    report = aggregate_framework_reports(Path(args.root))
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("verify-env summary:", report["summary"])
        for framework in report["frameworks"]:
            print(f"- {framework['name']}: {framework['report']['summary']}")

    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
