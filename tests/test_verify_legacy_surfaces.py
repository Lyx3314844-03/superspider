from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import verify_legacy_surfaces


ROOT = Path(__file__).resolve().parents[1]


def test_collect_legacy_surfaces_report_passes_for_repo():
    report = verify_legacy_surfaces.collect_legacy_surfaces_report(ROOT)

    assert report["command"] == "verify-legacy-surfaces"
    assert report["summary"] == "passed"
    assert report["exit_code"] == 0


def test_main_prints_json_report(monkeypatch, capsys):
    monkeypatch.setattr(
        verify_legacy_surfaces,
        "collect_legacy_surfaces_report",
        lambda root: {
            "command": "verify-legacy-surfaces",
            "summary": "passed",
            "summary_text": "5 passed, 0 failed",
            "exit_code": 0,
            "checks": [],
        },
    )

    exit_code = verify_legacy_surfaces.main(["--root", str(ROOT), "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["command"] == "verify-legacy-surfaces"
