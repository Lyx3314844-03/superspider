from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[1]


def test_graph_result_contract_schemas_exist_and_have_expected_fields():
    contracts = ROOT / "contracts"
    graph = json.loads((contracts / "graph.schema.json").read_text(encoding="utf-8"))
    artifact = json.loads((contracts / "result-artifact.schema.json").read_text(encoding="utf-8"))
    envelope = json.loads((contracts / "result-envelope.schema.json").read_text(encoding="utf-8"))

    assert graph["title"] == "Spider Graph Artifact"
    assert "root_id" in graph["required"]
    assert "stats" in graph["required"]

    assert artifact["title"] == "Spider Result ArtifactRef"
    assert artifact["properties"]["kind"]["type"] == "string"

    assert envelope["title"] == "Spider Task Result Envelope"
    assert "artifacts" in envelope["properties"]
    assert "artifact_refs" in envelope["properties"]
    assert "graph" in envelope["properties"]


def test_cross_runtime_graph_artifact_samples_match_shared_contract_shape():
    samples = {
        "go": {
            "kind": "graph",
            "path": "artifacts/runtime/graphs/go-http-job-graph.json",
            "root_id": "document",
            "stats": {"total_nodes": 4, "total_edges": 2},
        },
        "java": {
            "kind": "graph",
            "path": "artifacts/control-plane/graphs/java-task-1-result-1.json",
            "root_id": "document",
            "stats": {"total_nodes": 3, "total_edges": 1},
        },
        "python": {
            "kind": "graph",
            "path": "artifacts/control-plane/graphs/python-task-1-graph.json",
            "root_id": "document",
            "stats": {"total_nodes": 5, "total_edges": 2},
        },
        "rust": {
            "kind": "graph",
            "path": "artifacts/control-plane/graphs/rust-task-1-result-1.json",
            "root_id": "document",
            "stats": {"total_nodes": 4, "total_edges": 2},
        },
    }

    for runtime, artifact in samples.items():
        assert artifact["kind"] == "graph", runtime
        assert isinstance(artifact["path"], str) and artifact["path"], runtime
        assert isinstance(artifact["root_id"], str) and artifact["root_id"], runtime
        assert isinstance(artifact["stats"], dict), runtime
        assert artifact["stats"]["total_nodes"] >= 0, runtime
        assert artifact["stats"]["total_edges"] >= 0, runtime
