from __future__ import annotations

import argparse
import json
from pathlib import Path


def _adopter_story_count(root: Path) -> int:
    content = (root / "docs" / "ADOPTERS.md").read_text(encoding="utf-8")
    return sum(1 for line in content.splitlines() if line.strip().startswith("### "))


def collect_industry_proof_surface_report(root: Path) -> dict:
    benchmark = json.loads((root / "artifacts" / "benchmark-trends.json").read_text(encoding="utf-8"))
    checks: list[dict] = []

    docs_present = all(
        (root / relative).exists()
        for relative in (
            "docs/INDUSTRY_PROOF.md",
            "docs/ADOPTERS.md",
            "docs/NIGHTLY_SCALE.md",
            "docs/SCALE_VALIDATION.md",
            "docs/PUBLIC_BENCHMARKS.md",
        )
    )
    checks.append(
        {
            "name": "docs-surface",
            "status": "passed" if docs_present else "failed",
            "details": "industry proof docs are present" if docs_present else "missing one or more proof-surface docs",
        }
    )

    benchmark_surface_ok = (root / "web-ui" / "public-benchmarks" / "index.html").exists() and (root / "artifacts" / "benchmark-history").exists()
    checks.append(
        {
            "name": "public-benchmark-surface",
            "status": "passed" if benchmark_surface_ok else "failed",
            "details": "public benchmark site and benchmark history directory exist"
            if benchmark_surface_ok
            else "missing public benchmark site or benchmark history directory",
        }
    )

    history_depth = int(benchmark.get("history_depth", 0) or 0)
    history_ok = history_depth >= 2
    checks.append(
        {
            "name": "benchmark-history-depth",
            "status": "passed" if history_ok else "failed",
            "details": f"benchmark history depth is {history_depth}",
        }
    )

    adopter_count = _adopter_story_count(root)
    checks.append(
        {
            "name": "validation-stories",
            "status": "passed" if adopter_count >= 2 else "failed",
            "details": f"public adopter/validation stories counted: {adopter_count}",
        }
    )

    current_summary_present = all(
        (root / "artifacts" / relative).exists()
        for relative in ("runtime-stability.json", "framework-scorecard.json", "ecosystem-readiness.json")
    )
    checks.append(
        {
            "name": "published-proof-artifacts",
            "status": "passed" if current_summary_present else "failed",
            "details": "core proof artifacts exist in artifacts/" if current_summary_present else "missing one or more published proof artifacts",
        }
    )

    passed = sum(1 for check in checks if check["status"] == "passed")
    failed = len(checks) - passed
    return {
        "command": "verify-industry-proof-surface",
        "summary": "passed" if failed == 0 else "failed",
        "summary_text": f"{passed} passed, {failed} failed",
        "exit_code": 0 if failed == 0 else 1,
        "checks": checks,
        "history_depth": history_depth,
        "validation_story_count": adopter_count,
    }


def render_markdown(report: dict) -> str:
    lines = [
        "# Industry Proof Surface",
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
    parser = argparse.ArgumentParser(description="Verify repository-owned public proof surfaces and benchmark history")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent), help="repository root path")
    parser.add_argument("--json", action="store_true", help="print JSON report")
    parser.add_argument("--markdown-out", default="", help="optional markdown output path")
    args = parser.parse_args(argv)

    report = collect_industry_proof_surface_report(Path(args.root).resolve())
    if args.markdown_out:
        Path(args.markdown_out).write_text(render_markdown(report), encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("verify-industry-proof-surface:", report["summary"])
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
