from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import verify_maturity_governance


ROOT = Path(__file__).resolve().parents[1]


def test_collect_maturity_governance_report_passes_for_repo():
    report = verify_maturity_governance.collect_maturity_governance_report(ROOT)

    assert report["command"] == "verify-maturity-governance"
    assert report["summary"] == "passed"
    assert report["exit_code"] == 0


def test_main_prints_json_report(monkeypatch, capsys):
    monkeypatch.setattr(
        verify_maturity_governance,
        "collect_maturity_governance_report",
        lambda root: {
            "command": "verify-maturity-governance",
            "summary": "passed",
            "summary_text": "7 passed, 0 failed",
            "exit_code": 0,
            "checks": [],
        },
    )

    exit_code = verify_maturity_governance.main(["--root", str(ROOT), "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["command"] == "verify-maturity-governance"
