from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import verify_benchmark_trends


ROOT = Path(__file__).resolve().parents[1]


def _benchmark(summary: str = "passed", measured: int = 100) -> dict:
    frameworks = []
    for name, runtime in (
        ("javaspider", "java"),
        ("pyspider", "python"),
        ("gospider", "go"),
        ("rustspider", "rust"),
    ):
        frameworks.append({
            "name": name,
            "runtime": runtime,
            "summary": summary,
            "sla": {"success_job_ms": {"measured": measured, "threshold": 1000, "passed": True}},
        })
    return {"frameworks": frameworks}


def _blackbox(summary: str = "passed") -> dict:
    frameworks = []
    for name, runtime in (
        ("javaspider", "java"),
        ("pyspider", "python"),
        ("gospider", "go"),
        ("rustspider", "rust"),
    ):
        frameworks.append({
            "name": name,
            "runtime": runtime,
            "summary": summary,
        })
    return {"frameworks": frameworks}


def _readiness(summary: str = "passed", control_plane_rate: float = 1.0) -> dict:
    frameworks = []
    for name, runtime in (
        ("javaspider", "java"),
        ("pyspider", "python"),
        ("gospider", "go"),
        ("rustspider", "rust"),
    ):
        frameworks.append({
            "name": name,
            "runtime": runtime,
            "summary": summary,
            "metrics": {"control_plane_rate": control_plane_rate},
        })
    return {"frameworks": frameworks}


def test_collect_benchmark_trend_report_contract():
    report = verify_benchmark_trends.collect_benchmark_trend_report(
        ROOT,
        current_benchmark=_benchmark(),
        current_blackbox=_blackbox(),
        current_readiness=_readiness(),
    )

    assert report["command"] == "verify-benchmark-trends"
    assert "benchmark_trends" in report
    assert "blackbox_trends" in report
    assert "readiness_trends" in report


def test_render_markdown_contains_sections():
    markdown = verify_benchmark_trends.render_markdown({
        "summary": "passed",
        "history_depth": 0,
        "benchmark_trends": {
            "gospider": {
                "runtime": "go",
                "current": {"measured": 20, "threshold": 100, "passed": True},
                "delta_ms": None,
                "summary_changed": None,
            }
        },
        "blackbox_trends": {
            "gospider": {
                "runtime": "go",
                "current": "passed",
                "previous": None,
                "changed": None,
            }
        },
        "readiness_trends": {
            "gospider": {
                "runtime": "go",
                "current": {"summary": "passed", "control_plane_rate": 1.0},
                "previous": {"summary": None, "control_plane_rate": None},
                "delta": {"control_plane_rate": None},
                "summary_changed": None,
            }
        },
        "alerts": [],
    })
    assert "## Benchmark Trends" in markdown
    assert "## Blackbox Trends" in markdown
    assert "## Runtime Readiness Trends" in markdown


def test_snapshot_payload_contains_reports():
    payload = verify_benchmark_trends.snapshot_payload(_benchmark(), _blackbox(), _readiness())
    assert "generated_at" in payload
    assert "benchmark_sla" in payload["report"]
    assert "blackbox_e2e" in payload["report"]
    assert "runtime_readiness" in payload["report"]


def test_collect_benchmark_trend_report_emits_failed_alert_on_control_plane_regression(tmp_path):
    previous = verify_benchmark_trends.snapshot_payload(_benchmark(), _blackbox(), _readiness(control_plane_rate=1.0))
    history_dir = tmp_path / "history"
    history_dir.mkdir()
    (history_dir / "snapshot.json").write_text(json.dumps(previous), encoding="utf-8")

    report = verify_benchmark_trends.collect_benchmark_trend_report(
        ROOT,
        history_dir=history_dir,
        current_benchmark=_benchmark(),
        current_blackbox=_blackbox(),
        current_readiness=_readiness(control_plane_rate=0.5),
    )

    assert report["summary"] == "failed"
    assert any(
        alert["source"] == "runtime-readiness" and "control_plane_rate regressed" in alert["details"]
        for alert in report["alerts"]
    )
