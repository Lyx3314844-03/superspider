from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import verify_result_contracts


ROOT = Path(__file__).resolve().parents[1]


def test_collect_result_contracts_report_has_contract_shape():
    report = verify_result_contracts.collect_result_contracts_report(ROOT)

    assert report["command"] == "verify-result-contracts"
    assert "checks" in report
    assert report["exit_code"] in (0, 1)


def test_result_contracts_schema_exists():
    schema = json.loads((ROOT / "schemas" / "spider-result-contracts.schema.json").read_text(encoding="utf-8"))

    assert schema["properties"]["command"]["const"] == "verify-result-contracts"
