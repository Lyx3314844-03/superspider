from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import verify_pyspider_concurrency_summary


ROOT = Path(__file__).resolve().parents[1]


def test_pyspider_concurrency_summary_contract_is_documented_and_schema_exists():
    schema = json.loads((ROOT / "schemas" / "spider-pyspider-concurrency-summary.schema.json").read_text(encoding="utf-8"))

    assert schema["properties"]["command"]["const"] == "verify-pyspider-concurrency-summary"
    assert schema["properties"]["runtime"]["const"] == "python"


def test_run_pyspider_concurrency_summary_returns_expected_shape():
    report = verify_pyspider_concurrency_summary.run_pyspider_concurrency_summary(ROOT)

    assert report["command"] == "verify-pyspider-concurrency-summary"
    assert report["runtime"] == "python"
    assert report["summary"] == "passed"
    assert report["metrics"]["bounded_concurrency_ready"] is True
    assert report["metrics"]["soak_ready"] is True
