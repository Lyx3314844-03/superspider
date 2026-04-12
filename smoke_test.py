from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from pathlib import Path


def build_pyspider_command(system_name: str | None = None, subcommand: str = "version") -> list[str]:
    system_name = system_name or platform.system()
    executable = Path(sys.executable)
    script_name = "pyspider.exe" if system_name == "Windows" else "pyspider"
    console_script = executable.with_name(script_name)
    if console_script.exists():
        return [str(console_script), subcommand]
    return [sys.executable, "-m", "pyspider", subcommand]


def build_smoke_commands(system_name: str | None = None) -> dict[str, dict[str, str | list[str]]]:
    system_name = system_name or platform.system()
    if system_name == "Windows":
        javaspider_command = [
            "powershell",
            "-NoProfile",
            "-Command",
            "& mvn -q compile dependency:copy-dependencies; java -cp 'target/classes;target/dependency/*' com.javaspider.EnhancedSpider version",
        ]
    else:
        javaspider_command = [
            "bash",
            "-lc",
            "mvn -q compile dependency:copy-dependencies && java -cp 'target/classes:target/dependency/*' com.javaspider.EnhancedSpider version",
        ]

    return {
        "javaspider": {
            "cwd": "javaspider",
            "runtime": "java",
            "command": javaspider_command,
            "expect": "JavaSpider Framework CLI v",
        },
        "pyspider": {
            "cwd": ".",
            "runtime": "python",
            "command": build_pyspider_command(system_name, "version"),
            "expect": "pyspider 1.0.0",
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
            "command": ["cargo", "run", "--quiet", "--", "version"],
            "expect": "rustspider 1.0.0",
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
    passed = sum(1 for check in checks if check["summary"] == "passed")
    failed = len(checks) - passed
    exit_code = 1 if failed else 0
    return {
        "command": "smoke-test",
        "summary": "failed" if exit_code else "passed",
        "summary_text": f"{passed} passed, {failed} failed",
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
