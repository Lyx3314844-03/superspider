from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import verify_replay_dashboard


ROOT = Path(__file__).resolve().parents[1]


def test_collect_replay_dashboard_passes_for_repo():
    report = verify_replay_dashboard.collect_replay_dashboard(ROOT)

    assert report["command"] == "verify-replay-dashboard"
    assert report["summary"] == "passed"
    assert report["exit_code"] == 0
    assert "gospider" in report["framework_scores"]
    assert "gospider_distributed_summary" in report["sections"]
    assert "javaspider_captcha_summary" in report["sections"]
    assert "pyspider_concurrency_summary" in report["sections"]
    assert "rust_browser_summary" in report["sections"]
    assert "quality_policy_governance" in report["sections"]
    assert "rust_distributed_summary" in report["sections"]
    assert "rust_preflight_summary" in report["sections"]
    assert "captcha_pass_rate" in report["framework_scores"]["javaspider"]
    assert "captcha_closed_loop_ready" in report["framework_scores"]["javaspider"]
    assert "concurrency_pass_rate" in report["framework_scores"]["pyspider"]
    assert "soak_ready" in report["framework_scores"]["pyspider"]
    assert "distributed_pass_rate" in report["framework_scores"]["gospider"]
    assert "soak_ready" in report["framework_scores"]["gospider"]
    assert "browser_pass_rate" in report["framework_scores"]["rustspider"]
    assert "browser_proof_ready" in report["framework_scores"]["rustspider"]
    assert "preflight_pass_rate" in report["framework_scores"]["rustspider"]
    assert "distributed_pass_rate" in report["framework_scores"]["rustspider"]


def test_verify_replay_dashboard_contract_is_documented_and_schema_exists():
    schema = json.loads((ROOT / "schemas" / "spider-replay-dashboard.schema.json").read_text(encoding="utf-8"))

    assert schema["properties"]["command"]["const"] == "verify-replay-dashboard"
    assert "framework_scores" in schema["properties"]
