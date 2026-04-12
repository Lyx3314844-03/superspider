from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import verify_rust_browser_summary


ROOT = Path(__file__).resolve().parents[1]


def test_rust_browser_summary_contract_is_documented_and_schema_exists():
    schema = json.loads((ROOT / "schemas" / "spider-rust-browser-summary.schema.json").read_text(encoding="utf-8"))

    assert schema["properties"]["command"]["const"] == "verify-rust-browser-summary"
    assert schema["properties"]["runtime"]["const"] == "rust"


def test_run_rust_browser_summary_returns_expected_shape():
    report = verify_rust_browser_summary.run_rust_browser_summary(ROOT)

    assert report["command"] == "verify-rust-browser-summary"
    assert report["runtime"] == "rust"
    assert report["summary"] == "passed"
    assert report["metrics"]["browser_proof_ready"] is True
