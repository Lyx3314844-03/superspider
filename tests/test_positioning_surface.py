from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_positioning_and_compare_docs_exist():
    assert (ROOT / "docs" / "POSITIONING.md").exists()
    assert (ROOT / "docs" / "COMPARE.md").exists()
    assert (ROOT / "docs" / "ADOPTERS.md").exists()
    assert (ROOT / "docs" / "INTEGRATIONS.md").exists()
    assert (ROOT / "docs" / "NIGHTLY_SCALE.md").exists()


def test_integration_catalog_and_external_examples_exist():
    assert (ROOT / "contracts" / "integration-catalog.json").exists()
    assert (ROOT / "examples" / "external" / "README.md").exists()
    assert (ROOT / "examples" / "external" / "platform-demo" / "docker-compose.yml").exists()
    assert (ROOT / "examples" / "external" / "platform-demo" / "gospider-server.Dockerfile").exists()
    assert (ROOT / "examples" / "external" / "platform-demo" / "pyspider-web.Dockerfile").exists()
    assert (ROOT / "examples" / "external" / "python-control-plane-client" / "client.py").exists()
    assert (ROOT / "examples" / "external" / "node-control-plane-client" / "client.mjs").exists()
    assert (ROOT / "examples" / "external" / "control-plane-demo" / "index.html").exists()


def test_nightly_scale_workflow_exists_and_covers_soak_and_history():
    workflow = (ROOT / ".github" / "workflows" / "nightly-scale.yml").read_text(encoding="utf-8")
    assert "TestRunSyntheticSoakProducesStableReport" in workflow
    assert "verify_benchmark_trends.py" in workflow
    assert "benchmark-history/current-benchmark.json" in workflow
    assert "generate_public_benchmark_site.py" in workflow


def test_public_benchmark_pages_workflow_exists():
    workflow = (ROOT / ".github" / "workflows" / "public-benchmark-pages.yml").read_text(encoding="utf-8")
    assert "actions/deploy-pages@v4" in workflow
    assert "generate_public_benchmark_site.py" in workflow
    assert "path: web-ui" in workflow


def test_adoption_issue_template_exists():
    assert (ROOT / ".github" / "ISSUE_TEMPLATE" / "adoption-story.yml").exists()
