from __future__ import annotations

import argparse
import json
from pathlib import Path


def collect_cache_incremental_evidence_report(root: Path) -> dict:
    schema = json.loads((root / "contracts" / "runtime-core.schema.json").read_text(encoding="utf-8"))
    manifest = json.loads((root / "contracts" / "ecosystem-manifest.json").read_text(encoding="utf-8"))
    docs = {
        "guide": root / "docs" / "CACHE_INCREMENTAL.md",
        "contract": root / "docs" / "framework-contract.md",
        "tool": root / "tools" / "http_cache_tool.py",
    }
    checks: list[dict] = []

    docs_present = all(path.exists() for path in docs.values())
    checks.append(
        {
            "name": "docs-and-tool-surface",
            "status": "passed" if docs_present else "failed",
            "details": "cache guide, framework contract, and shared HTTP cache tool are present"
            if docs_present
            else "missing cache guide, framework contract, or HTTP cache tool",
        }
    )

    cache = schema.get("properties", {}).get("cache", {})
    required_fields = set(cache.get("required") or [])
    expected_fields = {"enabled", "store_path", "delta_fetch", "revalidate_seconds"}
    schema_ok = required_fields == expected_fields
    checks.append(
        {
            "name": "schema-cache-envelope",
            "status": "passed" if schema_ok else "failed",
            "details": "runtime-core schema exposes enabled / store_path / delta_fetch / revalidate_seconds"
            if schema_ok
            else f"cache required fields={sorted(required_fields)!r}",
        }
    )

    shared_contracts_ok = all("cache" in set(runtime.get("kernel_contracts") or []) for runtime in manifest.get("runtimes", []))
    checks.append(
        {
            "name": "runtime-cache-contract",
            "status": "passed" if shared_contracts_ok else "failed",
            "details": "all runtimes advertise cache in kernel contracts"
            if shared_contracts_ok
            else "one or more runtimes are missing cache in kernel_contracts",
        }
    )

    wording = docs["guide"].read_text(encoding="utf-8").lower()
    wording_ok = all(term in wording for term in ("conditional", "delta fetch", "retention", "freshness"))
    checks.append(
        {
            "name": "guide-language",
            "status": "passed" if wording_ok else "failed",
            "details": "cache guide mentions conditional requests, delta fetch, retention, and freshness"
            if wording_ok
            else "cache guide is missing one or more required cost-optimization terms",
        }
    )

    passed = sum(1 for check in checks if check["status"] == "passed")
    failed = len(checks) - passed
    return {
        "command": "verify-cache-incremental-evidence",
        "summary": "passed" if failed == 0 else "failed",
        "summary_text": f"{passed} passed, {failed} failed",
        "exit_code": 0 if failed == 0 else 1,
        "checks": checks,
    }


def render_markdown(report: dict) -> str:
    lines = [
        "# Cache And Incremental Evidence",
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
    parser = argparse.ArgumentParser(description="Verify cache and incremental crawl evidence surfaces")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent), help="repository root path")
    parser.add_argument("--json", action="store_true", help="print JSON report")
    parser.add_argument("--markdown-out", default="", help="optional markdown output path")
    args = parser.parse_args(argv)

    report = collect_cache_incremental_evidence_report(Path(args.root).resolve())
    if args.markdown_out:
        Path(args.markdown_out).write_text(render_markdown(report), encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("verify-cache-incremental-evidence:", report["summary"])
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
