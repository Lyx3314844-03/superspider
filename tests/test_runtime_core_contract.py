from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[1]


def test_runtime_core_contract_schema_covers_frontier_observability_and_cache():
    schema = json.loads((ROOT / "contracts" / "runtime-core.schema.json").read_text(encoding="utf-8"))

    assert schema["title"] == "Spider Runtime Core Contract"
    assert "frontier" in schema["required"]
    assert "observability" in schema["required"]
    assert "cache" in schema["required"]
    assert "sha256" in schema["properties"]["fingerprint"]["properties"]["algorithm"]["enum"]
    assert schema["properties"]["frontier"]["properties"]["max_inflight_per_domain"]["minimum"] == 1
    assert schema["properties"]["cache"]["properties"]["delta_fetch"]["type"] == "boolean"
