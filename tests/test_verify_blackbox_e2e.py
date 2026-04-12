from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import verify_blackbox_e2e


ROOT = Path(__file__).resolve().parents[1]


def _smoke(summary: str = "passed") -> dict:
    return {
        "checks": [
            {"name": "javaspider", "runtime": "java", "summary": summary, "details": "ok"},
            {"name": "pyspider", "runtime": "python", "summary": summary, "details": "ok"},
            {"name": "gospider", "runtime": "go", "summary": summary, "details": "ok"},
            {"name": "rustspider", "runtime": "rust", "summary": summary, "details": "ok"},
        ]
    }


def _readiness(metric_value: float = 1.0) -> dict:
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
            "metrics": {
                "success_rate": metric_value,
                "resilience_rate": metric_value,
                "artifact_integrity_rate": metric_value,
                "anti_bot_scenario_rate": metric_value,
                "recovery_signal_rate": metric_value,
                "control_plane_rate": metric_value,
            },
        })
    return {"frameworks": frameworks}


def test_collect_blackbox_e2e_report_has_expected_contract():
    report = verify_blackbox_e2e.collect_blackbox_e2e_report(ROOT, _smoke(), _readiness())

    assert report["command"] == "verify-blackbox-e2e"
    assert report["summary"] == "passed"
    assert len(report["frameworks"]) == 4


def test_render_markdown_includes_check_columns():
    markdown = verify_blackbox_e2e.render_markdown({
        "frameworks": [
            {
                "name": "pyspider",
                "runtime": "python",
                "summary": "passed",
                "checks": [
                    {"name": "version-probe", "status": "passed"},
                    {"name": "success_rate", "status": "passed"},
                    {"name": "resilience_rate", "status": "passed"},
                    {"name": "artifact_integrity_rate", "status": "passed"},
                    {"name": "anti_bot_scenario_rate", "status": "passed"},
                    {"name": "recovery_signal_rate", "status": "passed"},
                    {"name": "control_plane_rate", "status": "passed"},
                ],
            }
        ]
    })
    assert "| pyspider | python | passed | passed | passed | passed | passed | passed | passed | passed |" in markdown


def test_blackbox_e2e_schema_exists():
    schema = json.loads((ROOT / "schemas" / "spider-blackbox-e2e.schema.json").read_text(encoding="utf-8"))
    assert schema["properties"]["command"]["const"] == "verify-blackbox-e2e"
