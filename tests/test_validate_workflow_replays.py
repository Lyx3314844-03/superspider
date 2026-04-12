from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import validate_workflow_replays


ROOT = Path(__file__).resolve().parents[1]


def test_collect_workflow_replay_report_passes_for_repo_corpus():
    report = validate_workflow_replays.collect_workflow_replay_report(ROOT)

    assert report["command"] == "validate-workflow-replays"
    assert report["summary"] == "passed"
    assert report["exit_code"] == 0
    assert len(report["checks"]) >= 2


def test_validate_workflow_replay_rejects_missing_fixture(tmp_path):
    replay = tmp_path / "broken.json"
    replay.write_text(
        json.dumps({
            "name": "broken",
            "framework": "gospider",
            "fixture_path": "missing.html",
        }),
        encoding="utf-8",
    )

    check = validate_workflow_replays.validate_workflow_replay(tmp_path, replay)

    assert check["status"] == "failed"
    assert "fixture_path not found" in check["details"]


def test_workflow_replay_contract_is_documented_and_schema_exists():
    schema = json.loads((ROOT / "schemas" / "spider-workflow-replay-report.schema.json").read_text(encoding="utf-8"))

    assert schema["properties"]["command"]["const"] == "validate-workflow-replays"
    assert schema["properties"]["checks"]["items"]["properties"]["status"]["enum"] == ["passed", "failed"]
