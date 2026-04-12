from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import verify_public_install_chain


ROOT = Path(__file__).resolve().parents[1]


def test_collect_report_aggregates_doc_and_build_checks(monkeypatch):
    monkeypatch.setattr(
        verify_public_install_chain,
        "_doc_check",
        lambda root: {"name": "public-docs", "status": "passed", "details": "ok"},
    )
    monkeypatch.setattr(
        verify_public_install_chain,
        "_run",
        lambda command, cwd, timeout=600: {
            "command": command,
            "exit_code": 0,
            "status": "passed",
            "details": "command completed",
        },
    )
    monkeypatch.setattr(Path, "exists", lambda self: True)

    report = verify_public_install_chain.collect_report(ROOT)

    assert report["command"] == "verify-public-install-chain"
    assert report["summary"] == "passed"
    assert report["summary_text"] == "9 passed, 0 failed"
    assert report["exit_code"] == 0


def test_render_markdown_includes_commands_and_statuses():
    markdown = verify_public_install_chain.render_markdown(
        {
            "summary_text": "2 passed, 1 failed",
            "checks": [
                {"name": "public-docs", "status": "passed", "details": "ok"},
                {"name": "gospider-public-build", "status": "failed", "details": "missing", "command": ["go", "build"]},
            ],
        }
    )

    assert "Public Install Chain Report" in markdown
    assert "gospider-public-build" in markdown
    assert "`go build`" in markdown


def test_main_prints_json_report(monkeypatch, capsys):
    monkeypatch.setattr(
        verify_public_install_chain,
        "collect_report",
        lambda root: {
            "command": "verify-public-install-chain",
            "summary": "passed",
            "summary_text": "9 passed, 0 failed",
            "exit_code": 0,
            "checks": [],
        },
    )

    exit_code = verify_public_install_chain.main(["--root", str(ROOT), "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["command"] == "verify-public-install-chain"
