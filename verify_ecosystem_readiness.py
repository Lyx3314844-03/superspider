from __future__ import annotations

import argparse
import json
from pathlib import Path


DOCS = (
    "docs/COOKBOOK.md",
    "docs/API_COMPATIBILITY.md",
    "docs/ECOSYSTEM.md",
    "docs/MARKETPLACE.md",
    "docs/SUPPORT.md",
    "docs/STARTERS.md",
    "docs/PLUGIN_GOVERNANCE.md",
    "docs/COMPARE.md",
    "docs/INDUSTRY_PROOF.md",
    "MIGRATION.md",
)

STARTERS = ("pyspider", "gospider", "javaspider", "rustspider", "csharpspider")
EXTERNAL_EXAMPLES = (
    "examples/external/README.md",
    "examples/external/platform-demo/README.md",
    "examples/external/control-plane-demo/README.md",
    "examples/external/python-control-plane-client/README.md",
    "examples/external/node-control-plane-client/README.md",
)


def _adopter_entry_count(root: Path) -> int:
    content = (root / "docs" / "ADOPTERS.md").read_text(encoding="utf-8")
    count = 0
    in_code_block = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        if stripped.startswith("### "):
            count += 1
    return count


def collect_ecosystem_readiness_report(root: Path) -> dict:
    checks: list[dict] = []

    docs_present = all((root / relative).exists() for relative in DOCS)
    checks.append(
        {
            "name": "docs-surface",
            "status": "passed" if docs_present else "failed",
            "details": "ecosystem docs are present" if docs_present else "missing one or more ecosystem docs",
        }
    )

    starter_root = root / "examples" / "starters"
    starters_present = starter_root.exists() and all(
        (starter_root / f"{name}-starter" / "README.md").exists()
        for name in STARTERS
    )
    checks.append(
        {
            "name": "starter-surface",
            "status": "passed" if starters_present else "failed",
            "details": "starter readmes exist for all runtimes" if starters_present else "missing starter README or starter directory",
        }
    )

    external_examples_present = all((root / relative).exists() for relative in EXTERNAL_EXAMPLES)
    checks.append(
        {
            "name": "external-examples",
            "status": "passed" if external_examples_present else "failed",
            "details": "external example surfaces are present" if external_examples_present else "missing external example README or demo surface",
        }
    )

    adopter_entries = _adopter_entry_count(root)
    checks.append(
        {
            "name": "adopter-validation-surface",
            "status": "passed" if adopter_entries >= 1 else "failed",
            "details": f"documented validation stories: {adopter_entries}",
        }
    )

    integration_catalog = json.loads((root / "contracts" / "integration-catalog.json").read_text(encoding="utf-8"))
    plugin_ids = {plugin["id"] for plugin in integration_catalog.get("plugins", [])}
    entrypoints = {entrypoint["id"]: entrypoint for entrypoint in integration_catalog.get("entrypoints", [])}
    plugin_catalog_ok = {
        "profile-site",
        "sitemap-discover",
        "selector-studio",
        "anti-bot",
        "node-reverse",
        "http-cache",
        "incremental-crawl",
        "observability-monitor",
    }.issubset(plugin_ids)
    benchmark_reports_ok = "benchmark-reports" in entrypoints and {
        "runtime-readiness",
        "framework-scorecard",
        "benchmark-sla",
        "blackbox-e2e",
        "benchmark-trends",
    }.issubset(set(entrypoints["benchmark-reports"].get("artifacts", [])))
    marketplace_surface_ok = {"marketplace", "support"}.issubset(entrypoints)
    checks.append(
        {
            "name": "integration-catalog",
            "status": "passed" if plugin_catalog_ok and benchmark_reports_ok and marketplace_surface_ok else "failed",
            "details": "integration catalog exposes plugin, marketplace, support, and benchmark report surfaces"
            if plugin_catalog_ok and benchmark_reports_ok and marketplace_surface_ok
            else "integration catalog is missing plugin IDs, marketplace/support entrypoints, or benchmark report artifacts",
        }
    )

    passed = sum(1 for check in checks if check["status"] == "passed")
    failed = len(checks) - passed
    return {
        "command": "verify-ecosystem-readiness",
        "summary": "passed" if failed == 0 else "failed",
        "summary_text": f"{passed} passed, {failed} failed",
        "exit_code": 0 if failed == 0 else 1,
        "checks": checks,
    }


def render_markdown(report: dict) -> str:
    lines = [
        "# Ecosystem Readiness",
        "",
        f"Summary: {report['summary_text']}",
        "",
        "| Check | Status | Details |",
        "| --- | --- | --- |",
    ]
    for check in report["checks"]:
        lines.append(f"| {check['name']} | {check['status']} | {check['details']} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify ecosystem-facing docs, starters, examples, and integration catalog surfaces")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent), help="repository root path")
    parser.add_argument("--json", action="store_true", help="print JSON report")
    parser.add_argument("--markdown-out", default="", help="optional markdown output path")
    args = parser.parse_args(argv)

    report = collect_ecosystem_readiness_report(Path(args.root).resolve())
    if args.markdown_out:
        Path(args.markdown_out).write_text(render_markdown(report), encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("verify-ecosystem-readiness:", report["summary"])
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
