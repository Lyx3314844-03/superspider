from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import verify_benchmark_trends
import verify_cache_incremental_evidence
import verify_ecosystem_readiness
import verify_ecosystem_marketplace
import verify_industry_proof_surface
import verify_kernel_homogeneity
import verify_observability_evidence
import verify_runtime_core_capabilities
import verify_runtime_stability


def _read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _load_or_collect(root: Path, artifact_name: str, collect) -> dict:
    artifact = root / "artifacts" / artifact_name
    payload = _read_json(artifact)
    return payload if payload is not None else collect(root)


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


def _third_party_adopter_entry_count(root: Path) -> int:
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
        if stripped.startswith("### ") and not stripped.startswith("### Repository Validation:"):
            count += 1
    return count


def _kernel_homogeneity_gap(core_report: dict) -> bool:
    frameworks = [check for check in core_report.get("checks", []) if check.get("name") in {"javaspider", "gospider", "pyspider", "rustspider"}]
    exports_by_runtime: list[dict] = []
    for check in frameworks:
        stdout = check.get("stdout", "")
        first_brace = stdout.find("{")
        if first_brace < 0:
            continue
        payload = json.loads(stdout[first_brace:])
        exports_by_runtime.append(payload.get("kernel_contracts", {}))
    if len(exports_by_runtime) < 2:
        return False
    baseline = exports_by_runtime[0]
    for current in exports_by_runtime[1:]:
        if current != baseline:
            return True
    return False


def collect_maturity_gap_report(root: Path) -> dict:
    runtime_stability = _load_or_collect(root, "runtime-stability.json", verify_runtime_stability.collect_runtime_stability_report)
    kernel_homogeneity = _load_or_collect(root, "kernel-homogeneity.json", verify_kernel_homogeneity.collect_kernel_homogeneity_report)
    observability = _load_or_collect(root, "observability-evidence.json", verify_observability_evidence.collect_observability_evidence_report)
    cache_incremental = _load_or_collect(root, "cache-incremental-evidence.json", verify_cache_incremental_evidence.collect_cache_incremental_evidence_report)
    ecosystem_marketplace = _load_or_collect(root, "ecosystem-marketplace.json", verify_ecosystem_marketplace.collect_ecosystem_marketplace_report)
    ecosystem = _load_or_collect(root, "ecosystem-readiness.json", verify_ecosystem_readiness.collect_ecosystem_readiness_report)
    industry_proof = _load_or_collect(root, "industry-proof-surface.json", verify_industry_proof_surface.collect_industry_proof_surface_report)
    benchmark_trends = _load_or_collect(root, "benchmark-trends.json", verify_benchmark_trends.collect_benchmark_trend_report)
    runtime_core = _read_json(root / "artifacts" / "runtime-core-capabilities.json")
    if runtime_core is None:
        runtime_core = {
            "summary": kernel_homogeneity["summary"],
            "summary_text": "derived from kernel homogeneity evidence",
            "checks": [],
        }
    release_like_summary = "passed" if all(
        report["summary"] == "passed"
        for report in (runtime_stability, runtime_core, kernel_homogeneity, observability, cache_incremental, ecosystem_marketplace, ecosystem, industry_proof)
    ) else "attention-needed"
    release_like_details = (
        "derived from runtime stability, core capability, and ecosystem evidence"
    )

    proven = [
        {
            "name": "maturity-gates",
            "status": release_like_summary,
            "details": release_like_details,
        },
        {
            "name": "runtime-stability",
            "status": runtime_stability["summary"],
            "details": runtime_stability["summary_text"],
        },
        {
            "name": "runtime-core-capabilities",
            "status": runtime_core["summary"],
            "details": runtime_core["summary_text"],
        },
        {
            "name": "kernel-homogeneity",
            "status": kernel_homogeneity["summary"],
            "details": kernel_homogeneity["summary_text"],
        },
        {
            "name": "observability-evidence",
            "status": observability["summary"],
            "details": observability["summary_text"],
        },
        {
            "name": "cache-incremental-evidence",
            "status": cache_incremental["summary"],
            "details": cache_incremental["summary_text"],
        },
        {
            "name": "ecosystem-marketplace",
            "status": ecosystem_marketplace["summary"],
            "details": ecosystem_marketplace["summary_text"],
        },
        {
            "name": "ecosystem-readiness",
            "status": ecosystem["summary"],
            "details": ecosystem["summary_text"],
        },
        {
            "name": "industry-proof-surface",
            "status": industry_proof["summary"],
            "details": industry_proof["summary_text"],
        },
    ]

    gaps: list[dict] = []
    history_depth = int(benchmark_trends.get("history_depth", 0))
    if history_depth < 7:
        gaps.append(
            {
                "name": "benchmark-history-depth",
                "severity": "medium",
                "details": f"public benchmark history depth is {history_depth}; keep accumulating nightly runs before making stronger external maturity claims",
            }
        )

    adopter_entries = _adopter_entry_count(root)
    third_party_entries = _third_party_adopter_entry_count(root)
    if adopter_entries == 0:
        gaps.append(
            {
                "name": "public-adopter-evidence",
                "severity": "high",
                "details": "docs/ADOPTERS.md contains the template surface but no public adopter entries yet",
            }
        )
    elif third_party_entries == 0:
        gaps.append(
            {
                "name": "third-party-adopter-evidence",
                "severity": "medium",
                "details": "repository-owned validation stories now exist, but public third-party adopter entries are still missing",
            }
        )

    missing_live_env = []
    if not (os.environ.get("OPENAI_API_KEY") or os.environ.get("AI_API_KEY")):
        missing_live_env.append("ai")
    if not any(
        os.environ.get(name)
        for name in ("CAPTCHA_API_KEY", "TWOCAPTCHA_API_KEY", "ANTICAPTCHA_API_KEY")
    ):
        missing_live_env.append("captcha")
    if missing_live_env:
        gaps.append(
            {
                "name": "live-external-validation",
                "severity": "medium",
                "details": f"optional live validation lanes remain skipped-by-default because provider credentials are absent for: {', '.join(missing_live_env)}",
            }
        )

    if _kernel_homogeneity_gap(runtime_core):
        gaps.append(
            {
                "name": "kernel-homogeneity",
                "severity": "medium",
                "details": "kernel contract keys are aligned across runtimes, but the concrete type/export surfaces still differ by language and are not yet one highly isomorphic kernel design",
            }
        )

    summary = "passed" if not gaps else "attention-needed"
    return {
        "command": "generate-maturity-gap-report",
        "summary": summary,
        "summary_text": f"{len(proven)} proven areas, {len(gaps)} remaining gap areas",
        "exit_code": 0,
        "proven": proven,
        "gaps": gaps,
    }


def render_markdown(report: dict) -> str:
    lines = [
        "# Maturity Gap Report",
        "",
        f"Summary: {report['summary_text']}",
        "",
        "## Proven",
        "",
    ]
    for item in report["proven"]:
        lines.append(f"- `{item['name']}`: `{item['status']}` | {item['details']}")
    lines.extend(["", "## Remaining Gaps", ""])
    if not report["gaps"]:
        lines.append("- No open maturity gaps were detected by the current report inputs.")
    else:
        for item in report["gaps"]:
            lines.append(f"- `{item['name']}` ({item['severity']}): {item['details']}")
    lines.extend(
        [
            "",
            "## Next Moves",
            "",
            "- Add public adopter/case-study entries with real workload scale in `docs/ADOPTERS.md`.",
            "- Keep extending nightly benchmark/stability history before making stronger external maturity claims.",
            "- Continue reducing runtime-internal divergence behind the shared kernel contracts.",
            "- Turn optional live validation lanes on in controlled environments when provider credentials are available.",
        ]
    )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a maturity gap report from release, stability, core, and ecosystem evidence")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent), help="repository root path")
    parser.add_argument("--json", action="store_true", help="print JSON report")
    parser.add_argument("--markdown-out", default="", help="optional markdown output path")
    args = parser.parse_args(argv)

    report = collect_maturity_gap_report(Path(args.root).resolve())
    if args.markdown_out:
        Path(args.markdown_out).write_text(render_markdown(report), encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("generate-maturity-gap-report:", report["summary"])
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
