from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import verify_quality_policy_governance


ROOT = Path(__file__).resolve().parents[1]


def test_collect_quality_policy_governance_report_passes_for_repo():
    report = verify_quality_policy_governance.collect_quality_policy_governance_report(ROOT)

    assert report["command"] == "verify-quality-policy-governance"
    assert report["summary"] == "passed"
    assert report["exit_code"] == 0


def test_quality_policy_governance_contract_is_documented_and_schema_exists():
    schema = json.loads((ROOT / "schemas" / "spider-quality-policy-governance.schema.json").read_text(encoding="utf-8"))

    assert schema["properties"]["command"]["const"] == "verify-quality-policy-governance"
