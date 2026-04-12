from __future__ import annotations

import argparse
import json
from pathlib import Path

import verify_runtime_readiness


FRAMEWORKS = {
    "javaspider": {
        "runtime": "java",
        "benchmark_globs": ["src/test/java/**/*.java"],
        "thresholds_ms": {"success_job": 60000},
    },
    "pyspider": {
        "runtime": "python",
        "benchmark_globs": ["tests/test_benchmarks.py"],
        "thresholds_ms": {"success_job": 20000},
    },
    "gospider": {
        "runtime": "go",
        "benchmark_globs": ["**/*_test.go"],
        "thresholds_ms": {"success_job": 15000},
    },
    "rustspider": {
        "runtime": "rust",
        "benchmark_globs": ["benches/*.rs", "tests/*scorecard.rs"],
        "thresholds_ms": {"success_job": 30000},
    },
}


def _count_assets(root: Path, framework: str) -> int:
    base = root / framework
    total = 0
    for pattern in FRAMEWORKS[framework]["benchmark_globs"]:
        total += len(list(base.glob(pattern)))
    return total


def _framework_report(readiness_framework: dict, root: Path, framework: str) -> dict:
    thresholds = FRAMEWORKS[framework]["thresholds_ms"]
    metrics = readiness_framework["metrics"]
    duration = int(metrics.get("durations_ms", {}).get("success_job", 0))
    assets = _count_assets(root, framework)
    meets_duration = duration <= thresholds["success_job"]
    assets_present = assets > 0
    passed = readiness_framework["summary"] == "passed" and meets_duration and assets_present

    checks = [
        {
            "name": "readiness-baseline",
            "status": "passed" if readiness_framework["summary"] == "passed" else "failed",
            "details": f"runtime readiness summary={readiness_framework['summary']}",
        },
        {
            "name": "success-job-sla",
            "status": "passed" if meets_duration else "failed",
            "details": f"measured={duration}ms threshold={thresholds['success_job']}ms",
        },
        {
            "name": "benchmark-assets",
            "status": "passed" if assets_present else "failed",
            "details": f"discovered {assets} benchmark/scorecard assets",
        },
    ]

    return {
        "name": framework,
        "runtime": FRAMEWORKS[framework]["runtime"],
        "summary": "passed" if passed else "failed",
        "exit_code": 0 if passed else 1,
        "sla": {
            "success_job_ms": {
                "measured": duration,
                "threshold": thresholds["success_job"],
                "passed": meets_duration,
            }
        },
        "benchmark_assets": assets,
        "checks": checks,
    }


def collect_benchmark_sla_report(root: Path, readiness_report: dict | None = None) -> dict:
    readiness_report = readiness_report or verify_runtime_readiness.collect_runtime_readiness_report(root)
    readiness_by_name = {item["name"]: item for item in readiness_report["frameworks"]}
    frameworks = [
        _framework_report(readiness_by_name[name], root, name)
        for name in FRAMEWORKS
    ]
    passed = sum(1 for item in frameworks if item["summary"] == "passed")
    failed = len(frameworks) - passed
    return {
        "command": "verify-benchmark-sla",
        "summary": "passed" if failed == 0 else "failed",
        "summary_text": f"{passed} frameworks met benchmark/SLA gates, {failed} frameworks failed",
        "exit_code": 0 if failed == 0 else 1,
        "frameworks": frameworks,
    }


def render_markdown(report: dict) -> str:
    lines = [
        "# Benchmark And SLA Report",
        "",
        "| Framework | Runtime | Summary | Success Job SLA | Assets |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in report["frameworks"]:
        sla = item["sla"]["success_job_ms"]
        lines.append(
            f"| {item['name']} | {item['runtime']} | {item['summary']} | "
            f"{sla['measured']}ms / {sla['threshold']}ms ({'pass' if sla['passed'] else 'fail'}) | "
            f"{item['benchmark_assets']} |"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a benchmark and SLA verification report")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent), help="repository root path")
    parser.add_argument("--json", action="store_true", help="print JSON report")
    parser.add_argument("--markdown-out", default="", help="optional markdown output path")
    args = parser.parse_args(argv)

    report = collect_benchmark_sla_report(Path(args.root).resolve())
    if args.markdown_out:
        Path(args.markdown_out).write_text(render_markdown(report), encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("verify-benchmark-sla:", report["summary"])
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
