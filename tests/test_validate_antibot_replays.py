from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import validate_antibot_replays


ROOT = Path(__file__).resolve().parents[1]


def test_collect_antibot_replay_report_passes_for_repo_corpus():
    report = validate_antibot_replays.collect_antibot_replay_report(ROOT)

    assert report["command"] == "validate-antibot-replays"
    assert report["summary"] == "passed"
    assert report["exit_code"] == 0
    assert len(report["checks"]) >= 3


def test_validate_replay_rejects_missing_fixture(tmp_path):
    replay = tmp_path / "captcha.json"
    replay.write_text(
        json.dumps({
            "name": "captcha",
            "fixture_path": "missing.html",
            "marker_title": "Captcha Replay",
            "expected_tokens": ["captcha"],
            "anti_bot": {
                "challenge": "captcha",
                "fingerprint_profile": "synthetic-captcha",
                "session_mode": "sticky",
                "stealth": True,
            },
            "recovery": {
                "strategy": "captcha-solve",
                "recovered": True,
                "events": [
                    {"phase": "detect", "signal": "captcha", "status": "passed"}
                ],
            },
            "warning": "synthetic captcha recovery",
        }),
        encoding="utf-8",
    )

    check = validate_antibot_replays.validate_replay(replay, tmp_path)

    assert check["status"] == "failed"
    assert "fixture_path not found" in check["details"]


def test_validate_antibot_replay_contract_is_documented_and_schema_exists():
    schema = json.loads((ROOT / "schemas" / "spider-antibot-replay-report.schema.json").read_text(encoding="utf-8"))

    assert schema["properties"]["command"]["const"] == "validate-antibot-replays"
    assert schema["properties"]["checks"]["items"]["properties"]["status"]["enum"] == ["passed", "failed"]
