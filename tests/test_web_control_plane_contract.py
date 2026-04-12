from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_web_control_plane_contract_doc_exists():
    doc = ROOT / "docs" / "web-control-plane-contract.md"
    assert doc.exists()
    content = doc.read_text(encoding="utf-8")
    assert "GET /api/tasks" in content
    assert "DELETE /api/tasks/{id}" in content
    assert "GET /api/tasks/{id}/results" in content
    assert "GET /api/tasks/{id}/logs" in content
    assert "contracts/result-envelope.schema.json" in content
    assert "artifacts.graph" in content
    assert "artifact_refs.graph" in content
    assert "superspider_control_plane/compiler.py" in content
    assert "verify_superspider_control_plane.py" in content
    assert "Authorization: Bearer <token>" in content
    assert "401" in content
    assert "Authorization: Bearer <token>" in content


def test_readme_mentions_shared_web_control_plane():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "Shared Web Control Plane" in readme
    assert "`GET /api/tasks`" in readme


def test_runtime_sources_expose_task_endpoints():
    sources = {
        "go": ROOT / "gospider" / "web" / "server.go",
        "python": ROOT / "pyspider" / "web" / "app.py",
        "rust": ROOT / "rustspider" / "src" / "web" / "mod.rs",
        "java": ROOT / "javaspider" / "src" / "main" / "java" / "com" / "javaspider" / "web" / "controller" / "SpiderController.java",
    }
    for name, path in sources.items():
        content = path.read_text(encoding="utf-8")
        assert "/api/tasks" in content, f"{name} missing /api/tasks"
        assert "delete" in content.lower(), f"{name} missing delete support"
        assert "results" in content, f"{name} missing results support"
        assert "logs" in content, f"{name} missing logs support"


def test_rust_web_source_mentions_optional_api_auth():
    content = (ROOT / "rustspider" / "src" / "web" / "mod.rs").read_text(encoding="utf-8")

    assert "RUSTSPIDER_API_TOKEN" in content
    assert "SPIDER_API_TOKEN" in content
    assert "Authorization" in content
    assert "X-API-Token" in content


def test_runtime_sources_persist_shared_control_plane_jsonl_artifacts():
    sources = {
        "go": ROOT / "gospider" / "web" / "server.go",
        "python": ROOT / "pyspider" / "web" / "app.py",
        "rust": ROOT / "rustspider" / "src" / "web" / "mod.rs",
        "java": ROOT / "javaspider" / "src" / "main" / "java" / "com" / "javaspider" / "cli" / "SuperSpiderCLI.java",
    }

    for name, path in sources.items():
        content = path.read_text(encoding="utf-8")
        assert "results.jsonl" in content, f"{name} missing results.jsonl persistence"
        assert "events.jsonl" in content, f"{name} missing events.jsonl persistence"


def test_graph_and_result_contract_schemas_exist():
    contracts = ROOT / "contracts"
    assert (contracts / "graph.schema.json").exists()
    assert (contracts / "result-artifact.schema.json").exists()
    assert (contracts / "result-envelope.schema.json").exists()


def test_runtime_sources_expose_graph_artifact_refs_in_result_envelopes():
    sources = {
        "go": ROOT / "gospider" / "web" / "server.go",
        "python": ROOT / "pyspider" / "web" / "app.py",
        "rust": ROOT / "rustspider" / "src" / "web" / "mod.rs",
        "java": ROOT / "javaspider" / "src" / "main" / "java" / "com" / "javaspider" / "web" / "controller" / "SpiderController.java",
    }

    for name, path in sources.items():
        content = path.read_text(encoding="utf-8")
        assert "artifact_refs" in content, f"{name} missing artifact_refs in task result surface"
        assert "graph" in content, f"{name} missing graph artifact surface"


def test_rust_web_source_exposes_api_auth():
    rust_source = (ROOT / "rustspider" / "src" / "web" / "mod.rs").read_text(encoding="utf-8")
    assert "Authorization" in rust_source
    assert "Bearer " in rust_source
    assert "RUSTSPIDER_API_TOKEN" in rust_source


def test_runtime_capability_surfaces_expose_control_plane_flags():
    sources = {
        "go": ROOT / "gospider" / "cmd" / "gospider" / "main.go",
        "python": ROOT / "pyspider" / "__main__.py",
        "rust": ROOT / "rustspider" / "src" / "main.rs",
        "java": ROOT / "javaspider" / "src" / "main" / "java" / "com" / "javaspider" / "cli" / "SuperSpiderCLI.java",
    }

    for name, path in sources.items():
        content = path.read_text(encoding="utf-8")
        assert "control_plane" in content, f"{name} missing control_plane capability surface"
        assert "graph_artifact" in content, f"{name} missing graph_artifact capability flag"
