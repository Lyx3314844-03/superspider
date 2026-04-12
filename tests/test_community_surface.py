from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_contributing_and_public_docs_exist():
    assert (ROOT / "CONTRIBUTING.md").exists()
    assert (ROOT / "docs" / "ECOSYSTEM.md").exists()
    assert (ROOT / "docs" / "PUBLIC_BENCHMARKS.md").exists()
    assert (ROOT / "docs" / "SCALE_VALIDATION.md").exists()
    assert (ROOT / "docs" / "OPERATIONS.md").exists()


def test_issue_templates_and_pr_template_exist():
    assert (ROOT / ".github" / "ISSUE_TEMPLATE" / "bug-report.yml").exists()
    assert (ROOT / ".github" / "ISSUE_TEMPLATE" / "feature-request.yml").exists()
    assert (ROOT / ".github" / "ISSUE_TEMPLATE" / "config.yml").exists()
    assert (ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md").exists()


def test_public_benchmark_workflow_exists_and_uses_reports():
    workflow = (ROOT / ".github" / "workflows" / "public-benchmarks.yml").read_text(encoding="utf-8")
    assert "verify_benchmark_sla.py" in workflow
    assert "verify_blackbox_e2e.py" in workflow
    assert "verify_runtime_stability.py" in workflow
    assert "verify_ecosystem_readiness.py" in workflow
    assert "generate_framework_scorecard.py" in workflow


def test_release_and_verify_workflows_include_public_evidence_artifacts():
    verify_workflow = (ROOT / ".github" / "workflows" / "four-framework-verify.yml").read_text(encoding="utf-8")
    nightly_workflow = (ROOT / ".github" / "workflows" / "nightly-scale.yml").read_text(encoding="utf-8")
    release_workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

    for content in (verify_workflow, release_workflow):
        assert "benchmark-sla.json" in content
        assert "blackbox-e2e.json" in content

    assert "runtime-stability.json" in release_workflow
    assert "verify_runtime_stability.py" in release_workflow
    assert "runtime-stability-trends.json" in release_workflow
    assert "verify_runtime_stability_trends.py" in release_workflow
    assert "runtime-stability.json" in nightly_workflow
    assert "verify_runtime_stability.py" in nightly_workflow
    assert "runtime-stability-trends.json" in nightly_workflow
    assert "verify_runtime_stability_trends.py" in nightly_workflow


def test_ecosystem_manifest_exists_and_covers_all_runtimes():
    content = (ROOT / "contracts" / "ecosystem-manifest.json").read_text(encoding="utf-8")
    assert '"javaspider"' in content
    assert '"gospider"' in content
    assert '"pyspider"' in content
    assert '"rustspider"' in content
