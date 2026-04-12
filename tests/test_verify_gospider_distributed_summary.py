from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import verify_gospider_distributed_summary


ROOT = Path(__file__).resolve().parents[1]


def test_gospider_distributed_summary_contract_is_documented_and_schema_exists():
    schema = json.loads((ROOT / "schemas" / "spider-gospider-distributed-summary.schema.json").read_text(encoding="utf-8"))

    assert schema["properties"]["command"]["const"] == "verify-gospider-distributed-summary"
    assert schema["properties"]["runtime"]["const"] == "go"


def test_run_gospider_distributed_summary_returns_expected_shape():
    report = verify_gospider_distributed_summary.run_gospider_distributed_summary(ROOT)

    assert report["command"] == "verify-gospider-distributed-summary"
    assert report["runtime"] == "go"
    assert "metrics" in report
    assert isinstance(report["metrics"]["lease_ready"], bool)
    assert isinstance(report["metrics"]["soak_ready"], bool)
