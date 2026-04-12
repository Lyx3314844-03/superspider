from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import verify_benchmark_sla


ROOT = Path(__file__).resolve().parents[1]


def _readiness(summary: str, success_job_ms: int) -> dict:
    return {
        "summary": summary,
        "frameworks": [
            {
                "name": "javaspider",
                "runtime": "java",
                "summary": summary,
                "metrics": {"durations_ms": {"success_job": success_job_ms}},
            },
            {
                "name": "pyspider",
                "runtime": "python",
                "summary": summary,
                "metrics": {"durations_ms": {"success_job": success_job_ms}},
            },
            {
                "name": "gospider",
                "runtime": "go",
                "summary": summary,
                "metrics": {"durations_ms": {"success_job": success_job_ms}},
            },
            {
                "name": "rustspider",
                "runtime": "rust",
                "summary": summary,
                "metrics": {"durations_ms": {"success_job": success_job_ms}},
            },
        ],
    }


def test_collect_benchmark_sla_report_has_expected_contract():
    report = verify_benchmark_sla.collect_benchmark_sla_report(ROOT, _readiness("passed", 10))

    assert report["command"] == "verify-benchmark-sla"
    assert len(report["frameworks"]) == 4
    assert "success_job_ms" in report["frameworks"][0]["sla"]


def test_render_markdown_includes_sla_columns():
    markdown = verify_benchmark_sla.render_markdown({
        "frameworks": [
            {
                "name": "gospider",
                "runtime": "go",
                "summary": "passed",
                "sla": {"success_job_ms": {"measured": 25, "threshold": 100, "passed": True}},
                "benchmark_assets": 3,
            }
        ]
    })
    assert "| gospider | go | passed | 25ms / 100ms (pass) | 3 |" in markdown


def test_benchmark_sla_schema_exists():
    schema = json.loads((ROOT / "schemas" / "spider-benchmark-sla.schema.json").read_text(encoding="utf-8"))
    assert schema["properties"]["command"]["const"] == "verify-benchmark-sla"
