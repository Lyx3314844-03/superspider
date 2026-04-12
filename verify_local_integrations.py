from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def _resolve_command(command: list[str]) -> list[str]:
    if not command:
        return command
    executable = shutil.which(command[0]) or shutil.which(f"{command[0]}.cmd") or shutil.which(f"{command[0]}.exe")
    if executable:
        return [executable, *command[1:]]
    return command


def _run(command: list[str], cwd: Path, extra_env: dict[str, str] | None = None) -> dict:
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)

    resolved_command = _resolve_command(command)
    completed = subprocess.run(
        resolved_command,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    details = "\n".join(
        part for part in (completed.stdout.strip(), completed.stderr.strip()) if part
    ).strip()
    return {
        "command": resolved_command,
        "exit_code": completed.returncode,
        "status": "passed" if completed.returncode == 0 else "failed",
        "details": details or "command completed",
    }


def collect_report(root: Path) -> dict:
    python_env = {"PYTHONPATH": str(root)}
    checks = [
        {
            "name": "gospider-media-cli",
            **_run(["go", "test", "./cmd/gospider", "./extractors/iqiyi"], root / "gospider"),
        },
        {
            "name": "gospider-official-surfaces",
            **_run(
                ["go", "test", "./cmd/gospider", "-run", "TestCurlCommandConvertsToRestyTemplate|TestMediaDRMCommand"],
                root / "gospider",
            ),
        },
        {
            "name": "gospider-ai-structured-local",
            **_run(
                ["go", "test", "./runtime/http", "-run", "TestHTTPRuntimeAIExtractsStructuredFields"],
                root / "gospider",
            ),
        },
        {
            "name": "javaspider-ai-selector",
            **_run(
                ["mvn", "-q", "-Dtest=AIExtractorContractTest,HtmlSelectorContractTest", "test"],
                root / "javaspider",
            ),
        },
        {
            "name": "javaspider-official-surfaces",
            **_run(
                ["mvn", "-q", "-Dtest=SuperSpiderCLITest,GenericParserTest", "test"],
                root / "javaspider",
            ),
        },
        {
            "name": "rustspider-captcha-local-e2e",
            **_run(
                ["cargo", "test", "test_solve_image_with_2captcha_local_server", "--lib"],
                root / "rustspider",
            ),
        },
        {
            "name": "rustspider-captcha-local-e2e-recaptcha",
            **_run(
                ["cargo", "test", "test_solve_recaptcha_with_anticaptcha_local_server", "--lib"],
                root / "rustspider",
            ),
        },
        {
            "name": "pyspider-multimedia-defaults",
            **_run(
                ["pytest", "-q", "pyspider/tests/test_multimedia_downloader.py"],
                root,
                extra_env=python_env,
            ),
        },
        {
            "name": "pyspider-official-surfaces",
            **_run(
                [
                    "pytest",
                    "-q",
                    "pyspider/tests/test_cli.py",
                    "pyspider/tests/test_cli_runtime.py",
                    "pyspider/tests/test_video_downloader.py",
                ],
                root,
                extra_env=python_env,
            ),
        },
        {
            "name": "pyspider-checkpoint-and-converters",
            **_run(
                [
                    "pytest",
                    "-q",
                    "pyspider/tests/test_cli.py",
                    "pyspider/tests/test_checkpoint.py",
                    "pyspider/tests/test_curlconverter.py",
                    "pyspider/tests/test_dependencies.py",
                ],
                root,
                extra_env=python_env,
            ),
        },
        {
            "name": "media-blackbox-local",
            **_run(
                [sys.executable, "verify_media_blackbox.py", "--json"],
                root,
                extra_env=python_env,
            ),
        },
        {
            "name": "rustspider-media-parser-local",
            **_run(
                ["cargo", "test", "video_parser_supports_bilibili_and_douyin_html", "--lib"],
                root / "rustspider",
            ),
        },
        {
            "name": "rustspider-ai-structured-local",
            **_run(
                ["cargo", "test", "rust_cli_job_command_ai_extracts_structured_fields_from_html", "--test", "job_contract"],
                root / "rustspider",
            ),
        },
        {
            "name": "rustspider-cli-capabilities-surface",
            **_run(
                ["cargo", "run", "--quiet", "--", "capabilities"],
                root / "rustspider",
            ),
        },
    ]

    passed = sum(1 for check in checks if check["status"] == "passed")
    failed = len(checks) - passed
    return {
        "command": "verify-local-integrations",
        "summary": "passed" if failed == 0 else "failed",
        "summary_text": f"{passed} passed, {failed} failed",
        "exit_code": 0 if failed == 0 else 1,
        "checks": checks,
    }


def render_markdown(report: dict) -> str:
    lines = [
        "# Local Integrations Report",
        "",
        f"Summary: {report['summary_text']}",
        "",
        "| Check | Status |",
        "| --- | --- |",
    ]
    for check in report["checks"]:
        lines.append(f"| {check['name']} | {check['status']} |")
    lines.append("")
    for check in report["checks"]:
        lines.append(f"## {check['name']}")
        lines.append("")
        lines.append(f"- Status: {check['status']}")
        lines.append(f"- Command: `{' '.join(check['command'])}`")
        lines.append(f"- Details: {check['details']}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run local integration checks across the four spider frameworks")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent), help="repository root path")
    parser.add_argument("--json", action="store_true", help="print JSON report")
    parser.add_argument("--markdown-out", default="", help="optional markdown output path")
    args = parser.parse_args(argv)

    report = collect_report(Path(args.root).resolve())
    if args.markdown_out:
        Path(args.markdown_out).write_text(render_markdown(report), encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("verify-local-integrations:", report["summary"])
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
