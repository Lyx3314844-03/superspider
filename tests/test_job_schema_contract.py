from pathlib import Path
import json
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pyspider.__main__ as pyspider_cli


ROOT = Path(__file__).resolve().parents[1]


def test_job_schema_exists_and_supports_all_runtimes():
    schema = json.loads((ROOT / "contracts" / "job.schema.json").read_text(encoding="utf-8"))

    assert schema["properties"]["runtime"]["enum"] == ["http", "browser", "media", "ai"]
    assert schema["properties"]["target"]["$ref"] == "#/$defs/target"
    assert schema["properties"]["browser"]["$ref"] == "#/$defs/browser"
    assert schema["properties"]["jobdir"]["$ref"] == "#/$defs/jobdir"
    assert schema["properties"]["cache"]["$ref"] == "#/$defs/cache"
    assert schema["properties"]["pools"]["$ref"] == "#/$defs/pools"
    assert schema["properties"]["debug"]["$ref"] == "#/$defs/debug"
    assert "trace_path" in schema["$defs"]["browser"]["properties"]
    assert "har_path" in schema["$defs"]["browser"]["properties"]
    assert "route_manifest" in schema["$defs"]["browser"]["properties"]
    assert "codegen_out" in schema["$defs"]["browser"]["properties"]


def test_pyspider_job_cli_accepts_schema_shaped_job():
    with tempfile.TemporaryDirectory() as tmpdir:
        job_path = Path(tmpdir) / "job.json"
        job_path.write_text(json.dumps({
            "name": "schema-job",
            "runtime": "ai",
            "target": {
                "url": "https://example.com",
                "method": "GET",
            },
            "extract": [
                {"field": "title", "type": "ai"}
            ],
            "output": {
                "format": "json"
            },
            "metadata": {
                "content": "<title>Schema Title</title>"
            }
        }), encoding="utf-8")

        exit_code = pyspider_cli.main(["job", "--file", str(job_path)])
        assert exit_code == 0
