from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import verify_javaspider_captcha_summary


ROOT = Path(__file__).resolve().parents[1]


def test_javaspider_captcha_summary_contract_is_documented_and_schema_exists():
    schema = json.loads((ROOT / "schemas" / "spider-javaspider-captcha-summary.schema.json").read_text(encoding="utf-8"))

    assert schema["properties"]["command"]["const"] == "verify-javaspider-captcha-summary"
    assert schema["properties"]["runtime"]["const"] == "java"


def test_run_javaspider_captcha_summary_returns_expected_shape():
    report = verify_javaspider_captcha_summary.run_javaspider_captcha_summary(ROOT)

    assert report["command"] == "verify-javaspider-captcha-summary"
    assert report["runtime"] == "java"
    assert report["summary"] == "passed"
    assert report["metrics"]["captcha_closed_loop_ready"] is True
    assert report["metrics"]["artifact_ready"] is True
