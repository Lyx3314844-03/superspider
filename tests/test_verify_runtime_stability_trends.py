from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import verify_runtime_stability_trends


ROOT = Path(__file__).resolve().parents[1]


def _stability(summary: str = "passed", rate: float = 1.0) -> dict:
    frameworks = []
    for name, runtime in (
        ("javaspider", "java"),
        ("pyspider", "python"),
        ("gospider", "go"),
        ("rustspider", "rust"),
    ):
        frameworks.append(
            {
                "name": name,
                "runtime": runtime,
                "summary": summary,
                "metrics": {
                    "frontier_stress_rate": rate,
                    "recovery_rate": rate,
                    "control_plane_rate": rate,
                    "distributed_longevity_rate": rate,
                },
            }
        )
    return {"frameworks": frameworks}


def test_collect_runtime_stability_trend_report_contract():
    report = verify_runtime_stability_trends.collect_runtime_stability_trend_report(
        ROOT,
        current_report=_stability(),
    )

    assert report["command"] == "verify-runtime-stability-trends"
    assert "stability_trends" in report


def test_collect_runtime_stability_trend_report_emits_failed_alert_on_regression(tmp_path):
    previous = verify_runtime_stability_trends.snapshot_payload(_stability(rate=1.0))
    history_dir = tmp_path / "history"
    history_dir.mkdir()
    (history_dir / "snapshot.json").write_text(json.dumps(previous), encoding="utf-8")

    report = verify_runtime_stability_trends.collect_runtime_stability_trend_report(
        ROOT,
        history_dir=history_dir,
        current_report=_stability(rate=0.5),
    )

    assert report["summary"] == "failed"
    assert any("frontier_stress_rate regressed" in alert["details"] for alert in report["alerts"])


def test_runtime_stability_trends_contract_schema_exists():
    schema = json.loads((ROOT / "schemas" / "spider-runtime-stability-trends.schema.json").read_text(encoding="utf-8"))

    assert schema["properties"]["command"]["const"] == "verify-runtime-stability-trends"
