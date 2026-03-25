from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from pathlib import Path


def build_framework_commands(system_name: str | None = None) -> dict[str, dict[str, list[str] | str]]:
    system_name = system_name or platform.system()
    if system_name == "Windows":
        javaspider_command = [
            "powershell",
            "-NoProfile",
            "-Command",
            "& mvn -q compile '-Dexec.mainClass=com.javaspider.cli.MediaDownloaderCLI' '-Dexec.args=doctor --json' 'org.codehaus.mojo:exec-maven-plugin:3.6.1:java'",
        ]
    else:
        javaspider_command = [
            "mvn",
            "-q",
            "compile",
            "-Dexec.mainClass=com.javaspider.cli.MediaDownloaderCLI",
            "-Dexec.args=doctor --json",
            "org.codehaus.mojo:exec-maven-plugin:3.6.1:java",
        ]

    return {
        "javaspider": {
            "cwd": "javaspider",
            "command": javaspider_command,
        },
        "pyspider": {
            "cwd": ".",
            "command": [sys.executable, "-m", "pyspider.cli.video_downloader", "doctor", "--json"],
        },
        "gospider": {
            "cwd": "gospider",
            "command": ["go", "run", "./cmd/gospider", "doctor", "--json", "--skip-network"],
        },
        "rustspider": {
            "cwd": "rustspider",
            "command": [
                "cargo",
                "run",
                "--quiet",
                "--bin",
                "preflight",
                "--",
                "--json",
                "--writable-path",
                "artifacts",
                "--require-ffmpeg",
                "--require-browser",
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
            report = json.loads(stdout)
        except json.JSONDecodeError:
            report = _failed_framework_report(
                framework,
                completed.returncode or 1,
                [],
                f"non-json stdout: {stdout}",
            )
    else:
        report = _failed_framework_report(framework, completed.returncode, [], stderr or "empty stdout")

    report.setdefault("command", "doctor" if framework != "rustspider" else "preflight")
    report.setdefault("runtime", framework_runtime(framework))
    report.setdefault("summary", "passed" if completed.returncode == 0 else "failed")
    report.setdefault("exit_code", completed.returncode)
    report.setdefault("checks", [])
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
    return {
        "command": "doctor" if framework != "rustspider" else "preflight",
        "runtime": framework_runtime(framework),
        "summary": "failed",
        "exit_code": exit_code if exit_code else 1,
        "checks": checks,
        "stderr": stderr,
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
