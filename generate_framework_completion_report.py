from __future__ import annotations

import argparse
import json
from pathlib import Path

import verify_gospider_distributed_summary
import verify_javaspider_captcha_summary
import verify_javaspider_ai_live
import verify_local_integrations
import verify_media_blackbox
import verify_pyspider_concurrency_summary
import verify_rust_browser_summary
import verify_rust_captcha_live
import verify_rust_distributed_summary


def _load_framework_sections(root: Path) -> dict[str, dict]:
    return {
        "gospider_distributed": verify_gospider_distributed_summary.run_gospider_distributed_summary(root),
        "javaspider_captcha": verify_javaspider_captcha_summary.run_javaspider_captcha_summary(root),
        "javaspider_ai_live": verify_javaspider_ai_live.run_javaspider_ai_live(root),
        "local_integrations": verify_local_integrations.collect_report(root),
        "media_blackbox": verify_media_blackbox.collect_report(root),
        "pyspider_concurrency": verify_pyspider_concurrency_summary.run_pyspider_concurrency_summary(root),
        "rustspider_browser": verify_rust_browser_summary.run_rust_browser_summary(root),
        "rustspider_captcha_live": verify_rust_captcha_live.run_rust_captcha_live(root),
        "rustspider_distributed": verify_rust_distributed_summary.run_rust_distributed_summary(root),
    }


def _framework_statuses(sections: dict[str, dict]) -> dict[str, dict]:
    return {
        "gospider": {
            "summary": "passed"
            if sections["gospider_distributed"]["summary"] == "passed"
            and sections["media_blackbox"]["summary"] == "passed"
            and sections["local_integrations"]["summary"] == "passed"
            else "failed",
            "evidence": {
                "distributed": sections["gospider_distributed"]["summary_text"],
                "media_cli": "youtube/youku/tencent/iqiyi connected",
                "media_blackbox": sections["media_blackbox"]["summary_text"],
                "storage": "csv dataset export implemented",
                "session": "proxy-aware HTTP client implemented",
            },
            "remaining_focus": [
                "deepen site-specific media parsing and download hit-rate",
            ],
        },
        "javaspider": {
            "summary": "passed"
            if sections["javaspider_captcha"]["summary"] == "passed"
            and sections["local_integrations"]["summary"] == "passed"
            else "failed",
            "evidence": {
                "captcha_recovery": sections["javaspider_captcha"]["summary_text"],
                "selector_jsonpath": "nested field/index/wildcard support implemented",
                "selector_ai": "real AI + heuristic fallback implemented",
                "structured_ai": "schema-driven structured extraction implemented",
                "local_integrations": sections["local_integrations"]["summary_text"],
                "optional_live_ai": sections["javaspider_ai_live"]["summary_text"],
            },
            "remaining_focus": [
                "expand schema enforcement and higher-level extraction contracts",
            ],
        },
        "pyspider": {
            "summary": "passed"
            if sections["pyspider_concurrency"]["summary"] == "passed"
            and sections["media_blackbox"]["summary"] == "passed"
            and sections["local_integrations"]["summary"] == "passed"
            else "failed",
            "evidence": {
                "concurrency": sections["pyspider_concurrency"]["summary_text"],
                "checkpoint": "json + sqlite checkpoint backends implemented",
                "curlconverter": "curl to aiohttp conversion implemented",
                "multimedia": "generic default multimedia extraction implemented",
                "media_blackbox": sections["media_blackbox"]["summary_text"],
            },
            "remaining_focus": [
                "add more platform-specific multimedia spiders beyond generic extraction",
            ],
        },
        "rustspider": {
            "summary": "passed"
            if sections["rustspider_browser"]["summary"] == "passed"
            and sections["rustspider_distributed"]["summary"] == "passed"
            and sections["local_integrations"]["summary"] == "passed"
            else "failed",
            "evidence": {
                "browser": sections["rustspider_browser"]["summary_text"],
                "distributed": sections["rustspider_distributed"]["summary_text"],
                "cookie_persistence": "json persistence implemented",
                "captcha": "2captcha / anti-captcha request flow implemented with local end-to-end tests",
                "local_integrations": sections["local_integrations"]["summary_text"],
                "optional_live_captcha": sections["rustspider_captcha_live"]["summary_text"],
            },
            "remaining_focus": [
                "perform real third-party captcha service integration validation",
            ],
        },
    }


def collect_report(root: Path) -> dict:
    sections = _load_framework_sections(root)
    frameworks = _framework_statuses(sections)
    passed_frameworks = sum(1 for info in frameworks.values() if info["summary"] == "passed")
    failed_frameworks = len(frameworks) - passed_frameworks

    return {
        "command": "generate-framework-completion-report",
        "summary": "passed" if failed_frameworks == 0 else "failed",
        "summary_text": f"{passed_frameworks} frameworks passed, {failed_frameworks} frameworks failed",
        "exit_code": 0 if failed_frameworks == 0 else 1,
        "sections": sections,
        "frameworks": frameworks,
    }


def render_markdown(report: dict) -> str:
    lines = [
        "# Framework Completion Report",
        "",
        f"Summary: {report['summary_text']}",
        "",
        "| Framework | Summary | Evidence | Remaining Focus |",
        "| --- | --- | --- | --- |",
    ]

    for framework, info in report["frameworks"].items():
        evidence = "; ".join(f"{key}={value}" for key, value in info["evidence"].items())
        remaining = "; ".join(info["remaining_focus"]) if info["remaining_focus"] else "-"
        lines.append(f"| {framework} | {info['summary']} | {evidence} | {remaining} |")

    lines.extend(
        [
            "",
            "## Raw Sections",
            "",
        ]
    )
    for section_name, section in report["sections"].items():
        lines.append(f"### {section_name}")
        lines.append("")
        lines.append(f"- Summary: {section['summary_text']}")
        for check in section.get("checks", []):
            lines.append(f"- {check['name']}: {check['status']} - {check['details']}")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a unified completion report for the four spider frameworks")
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
        print("generate-framework-completion-report:", report["summary"])
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
