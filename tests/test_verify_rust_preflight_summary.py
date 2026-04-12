from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import verify_rust_preflight_summary


ROOT = Path(__file__).resolve().parents[1]


def test_rust_preflight_summary_contract_is_documented_and_schema_exists():
    schema = json.loads((ROOT / "schemas" / "spider-rust-preflight-summary.schema.json").read_text(encoding="utf-8"))

    assert schema["properties"]["command"]["const"] == "verify-rust-preflight-summary"
    assert schema["properties"]["runtime"]["const"] == "rust"


def test_run_rust_preflight_returns_expected_shape():
    report = verify_rust_preflight_summary.run_rust_preflight(ROOT)

    assert report["command"] == "verify-rust-preflight-summary"
    assert report["runtime"] == "rust"
    assert "metrics" in report
    assert isinstance(report["metrics"]["browser_ready"], bool)
