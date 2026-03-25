from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from pathlib import Path


def build_smoke_commands(system_name: str | None = None) -> dict[str, dict[str, str | list[str]]]:
    system_name = system_name or platform.system()
    if system_name == "Windows":
        javaspider_command = [
            "powershell",
            "-NoProfile",
            "-Command",
            "& mvn -q compile '-Dexec.mainClass=com.javaspider.cli.MediaDownloaderCLI' '-Dexec.args=version' 'org.codehaus.mojo:exec-maven-plugin:3.6.1:java'",
        ]
    else:
        javaspider_command = [
            "mvn",
            "-q",
            "compile",
            "-Dexec.mainClass=com.javaspider.cli.MediaDownloaderCLI",
            "-Dexec.args=version",
            "org.codehaus.mojo:exec-maven-plugin:3.6.1:java",
        ]

    return {
        "javaspider": {
            "cwd": "javaspider",
            "runtime": "java",
            "command": javaspider_command,
            "expect": "MediaDownloader CLI v",
        },
        "pyspider": {
            "cwd": ".",
            "runtime": "python",
            "command": [sys.executable, "-m", "pyspider.cli.video_downloader", "--help"],
            "expect": "视频下载命令行工具",
        },
        "gospider": {
            "cwd": "gospider",
            "runtime": "go",
            "command": ["go", "run", "./cmd/gospider", "version"],
            "expect": "gospider version",
        },
        "rustspider": {
            "cwd": "rustspider",
            "runtime": "rust",
            "command": ["cargo", "run", "--quiet", "--bin", "preflight", "--", "--help"],
            "expect": "rustspider preflight",
        },
    }


SMOKE_COMMANDS = build_smoke_commands()


def run_smoke_check(root: Path, framework: str) -> dict:
    spec = SMOKE_COMMANDS[framework]
    framework_root = root / str(spec["cwd"])
    try:
        completed = subprocess.run(
            spec["command"],
            cwd=framework_root,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        return {
            "name": framework,
            "runtime": spec["runtime"],
            "summary": "failed",
            "exit_code": 1,
            "details": f"command not found: {exc}",
        }

    combined_output = "\n".join(
        part for part in (completed.stdout.strip(), completed.stderr.strip()) if part
    ).strip()
    expected = str(spec["expect"])
    success = completed.returncode == 0 and expected in combined_output

    details = f"matched expected output: {expected}"
    if not success:
        details = combined_output or f"expected output not found: {expected}"

    return {
        "name": framework,
        "runtime": spec["runtime"],
        "summary": "passed" if success else "failed",
        "exit_code": 0 if success else (completed.returncode or 1),
        "details": details,
    }


def run_smoke_suite(root: Path) -> dict:
    checks = [run_smoke_check(root, framework) for framework in ("javaspider", "pyspider", "gospider", "rustspider")]
    exit_code = 1 if any(check["exit_code"] != 0 for check in checks) else 0
    return {
        "command": "smoke-test",
        "summary": "failed" if exit_code else "passed",
        "exit_code": exit_code,
        "checks": checks,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run smoke tests for all four spider framework entrypoints")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent), help="repository root path")
    parser.add_argument("--json", action="store_true", help="print smoke test report as JSON")
    args = parser.parse_args(argv)

    report = run_smoke_suite(Path(args.root))
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("smoke-test summary:", report["summary"])
        for check in report["checks"]:
            print(f"- {check['name']}: {check['summary']}")

    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
