from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[1]


def test_ultimate_contract_is_documented_and_schema_exists():
    contract = (ROOT / "docs" / "framework-contract.md").read_text(encoding="utf-8")
    schema = json.loads((ROOT / "schemas" / "spider-ultimate-report.schema.json").read_text(encoding="utf-8"))

    assert "Ultimate JSON Envelope" in contract
    assert schema["properties"]["command"]["const"] == "ultimate"
    assert schema["properties"]["runtime"]["enum"] == ["java", "go", "rust", "python"]
    assert schema["properties"]["summary"]["enum"] == ["passed", "failed"]
    assert schema["properties"]["results"]["items"]["required"] == [
        "task_id",
        "url",
        "success",
        "error",
        "duration",
        "anti_bot_level",
        "anti_bot_signals",
    ]
