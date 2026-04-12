from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import verify_ultimate_contract


ROOT = Path(__file__).resolve().parents[1]


def test_validate_ultimate_payload_accepts_valid_contract():
    payload = {
        "command": "ultimate",
        "runtime": "python",
        "summary": "passed",
        "summary_text": "1 results, 0 failed",
        "exit_code": 0,
        "url_count": 1,
        "result_count": 1,
        "results": [
            {
                "task_id": "task-1",
                "url": "https://example.com",
                "success": True,
                "error": "",
                "duration": "10ms",
                "anti_bot_level": "medium",
                "anti_bot_signals": ["vendor:test"],
            }
        ],
    }

    assert verify_ultimate_contract.validate_ultimate_payload(payload, "python") == []


def test_validate_ultimate_payload_rejects_missing_fields():
    payload = {
        "command": "ultimate",
        "runtime": "python",
        "summary": "passed",
        "summary_text": "1 results, 0 failed",
        "exit_code": 0,
        "url_count": 1,
        "result_count": 1,
        "results": [{}],
    }

    errors = verify_ultimate_contract.validate_ultimate_payload(payload, "python")
    assert any("missing task_id" in error for error in errors)


def test_collect_ultimate_contract_report_aggregates_framework_statuses(monkeypatch):
    canned = {
        "javaspider": {"name": "javaspider", "runtime": "java", "summary": "passed", "exit_code": 0, "stdout": "", "stderr": "", "report": {"command": "ultimate"}},
        "pyspider": {"name": "pyspider", "runtime": "python", "summary": "passed", "exit_code": 0, "stdout": "", "stderr": "", "report": {"command": "ultimate"}},
        "gospider": {"name": "gospider", "runtime": "go", "summary": "failed", "exit_code": 1, "stdout": "", "stderr": "contract failure", "report": None},
        "rustspider": {"name": "rustspider", "runtime": "rust", "summary": "passed", "exit_code": 0, "stdout": "", "stderr": "", "report": {"command": "ultimate"}},
    }

    class FakeServer:
        def __init__(self, *_args, **_kwargs):
            self.url = "http://127.0.0.1:0"

        def close(self):
            return None

    monkeypatch.setattr(verify_ultimate_contract, "LocalServer", FakeServer)
    monkeypatch.setattr(
        verify_ultimate_contract,
        "run_framework_ultimate",
        lambda root, framework, page_url, reverse_url, checkpoint_dir: canned[framework],
    )

    report = verify_ultimate_contract.collect_ultimate_contract_report(ROOT)
    assert report["command"] == "verify-ultimate-contract"
    assert report["summary"] == "failed"
    assert report["summary_text"] == "3 frameworks passed, 1 frameworks failed"
    assert report["exit_code"] == 1


def test_main_prints_json_report(monkeypatch, capsys):
    monkeypatch.setattr(
        verify_ultimate_contract,
        "collect_ultimate_contract_report",
        lambda root: {
            "command": "verify-ultimate-contract",
            "summary": "passed",
            "summary_text": "4 frameworks passed, 0 frameworks failed",
            "exit_code": 0,
            "frameworks": [],
        },
    )

    exit_code = verify_ultimate_contract.main(["--root", str(ROOT), "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["command"] == "verify-ultimate-contract"


def test_ultimate_verifier_contract_is_documented_and_schema_exists():
    schema = json.loads((ROOT / "schemas" / "spider-ultimate-report.schema.json").read_text(encoding="utf-8"))
    contract = (ROOT / "docs" / "framework-contract.md").read_text(encoding="utf-8")

    assert "Ultimate JSON Envelope" in contract
    assert schema["properties"]["command"]["const"] == "ultimate"
