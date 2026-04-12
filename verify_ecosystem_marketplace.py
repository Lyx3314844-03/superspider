from __future__ import annotations

import argparse
import json
from pathlib import Path


DOCS = (
    "docs/MARKETPLACE.md",
    "docs/SUPPORT.md",
    "docs/PLUGIN_GOVERNANCE.md",
    "docs/COOKBOOK.md",
    "MIGRATION.md",
)


def collect_ecosystem_marketplace_report(root: Path) -> dict:
    catalog = json.loads((root / "contracts" / "integration-catalog.json").read_text(encoding="utf-8"))
    checks: list[dict] = []

    docs_present = all((root / relative).exists() for relative in DOCS)
    checks.append(
        {
            "name": "docs-surface",
            "status": "passed" if docs_present else "failed",
            "details": "marketplace, support, governance, cookbook, and migration docs are present"
            if docs_present
            else "missing one or more ecosystem marketplace docs",
        }
    )

    entrypoints = {entrypoint["id"]: entrypoint for entrypoint in catalog.get("entrypoints", [])}
    entrypoints_ok = {"marketplace", "support"}.issubset(entrypoints)
    checks.append(
        {
            "name": "catalog-entrypoints",
            "status": "passed" if entrypoints_ok else "failed",
            "details": "integration catalog exposes marketplace and support entrypoints"
            if entrypoints_ok
            else "integration catalog is missing marketplace or support entrypoints",
        }
    )

    plugin_ids = {plugin["id"] for plugin in catalog.get("plugins", [])}
    required_plugins = {"http-cache", "incremental-crawl", "observability-monitor"}
    plugins_ok = required_plugins.issubset(plugin_ids)
    checks.append(
        {
            "name": "plugin-catalog",
            "status": "passed" if plugins_ok else "failed",
            "details": "plugin catalog exposes cache, incremental, and observability extension surfaces"
            if plugins_ok
            else f"missing plugin IDs: {sorted(required_plugins - plugin_ids)!r}",
        }
    )

    starters_root = root / "examples" / "starters"
    starters_ok = starters_root.exists() and any(starters_root.iterdir())
    checks.append(
        {
            "name": "starter-surface",
            "status": "passed" if starters_ok else "failed",
            "details": "starter templates exist for ecosystem onboarding"
            if starters_ok
            else "starter templates are missing",
        }
    )

    passed = sum(1 for check in checks if check["status"] == "passed")
    failed = len(checks) - passed
    return {
        "command": "verify-ecosystem-marketplace",
        "summary": "passed" if failed == 0 else "failed",
        "summary_text": f"{passed} passed, {failed} failed",
        "exit_code": 0 if failed == 0 else 1,
        "checks": checks,
    }


def render_markdown(report: dict) -> str:
    lines = [
        "# Ecosystem Marketplace",
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
    parser = argparse.ArgumentParser(description="Verify marketplace, support, plugin catalog, and starter surfaces")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent), help="repository root path")
    parser.add_argument("--json", action="store_true", help="print JSON report")
    parser.add_argument("--markdown-out", default="", help="optional markdown output path")
    args = parser.parse_args(argv)

    report = collect_ecosystem_marketplace_report(Path(args.root).resolve())
    if args.markdown_out:
        Path(args.markdown_out).write_text(render_markdown(report), encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("verify-ecosystem-marketplace:", report["summary"])
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
