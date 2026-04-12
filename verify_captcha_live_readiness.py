from __future__ import annotations

import argparse
import json
from pathlib import Path

import verify_gospider_captcha_live
import verify_javaspider_captcha_live
import verify_pyspider_captcha_live
import verify_rust_captcha_live


def collect_captcha_live_readiness_report(root: Path) -> dict:
    java = verify_javaspider_captcha_live.run_javaspider_captcha_live(root)
    python = verify_pyspider_captcha_live.run_pyspider_captcha_live(root)
    rust = verify_rust_captcha_live.run_rust_captcha_live(root)
    go = verify_gospider_captcha_live.run_gospider_captcha_live(root)
    frameworks = {
        "javaspider": java,
        "pyspider": python,
        "rustspider": rust,
        "gospider": go,
    }

    summaries = [frameworks[name]["summary"] for name in frameworks]
    if any(summary == "failed" for summary in summaries):
        summary = "failed"
    elif any(summary == "passed" for summary in summaries):
        summary = "passed"
    else:
        summary = "skipped"

    return {
        "command": "verify-captcha-live-readiness",
        "summary": summary,
        "summary_text": ", ".join(
            f"{name}={frameworks[name]['summary']}" for name in ("javaspider", "pyspider", "rustspider", "gospider")
        ),
        "exit_code": 1 if summary == "failed" else 0,
        "frameworks": frameworks,
    }


def render_markdown(report: dict) -> str:
    lines = [
        "# Captcha Live Readiness",
        "",
        f"Summary: {report['summary_text']}",
        "",
        "| Framework | Runtime | Summary | Details |",
        "| --- | --- | --- | --- |",
    ]
    for name, payload in report["frameworks"].items():
        lines.append(
            f"| {name} | {payload['runtime']} | {payload['summary']} | {payload['summary_text']} |"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Aggregate optional live captcha smoke readiness across runtimes")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent), help="repository root path")
    parser.add_argument("--json", action="store_true", help="print JSON report")
    parser.add_argument("--markdown-out", default="", help="optional markdown output path")
    args = parser.parse_args(argv)

    report = collect_captcha_live_readiness_report(Path(args.root).resolve())
    if args.markdown_out:
        Path(args.markdown_out).write_text(render_markdown(report), encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("verify-captcha-live-readiness:", report["summary"])
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
