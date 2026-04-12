from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_starter_catalog_and_docs_exist():
    assert (ROOT / "docs" / "STARTERS.md").exists()
    assert (ROOT / "examples" / "starters" / "README.md").exists()


def test_all_runtime_starters_exist_with_expected_files():
    starters = [
        "pyspider-starter",
        "gospider-starter",
        "javaspider-starter",
        "rustspider-starter",
    ]
    for name in starters:
        starter = ROOT / "examples" / "starters" / name
        assert (starter / "README.md").exists(), name
        assert (starter / "spider-framework.yaml").exists(), name
        assert (starter / "job.json").exists(), name
        assert (starter / "run.sh").exists(), name
        assert (starter / "run.ps1").exists(), name


def test_public_benchmark_workflow_is_nightly_and_emits_trend_artifacts():
    workflow = (ROOT / ".github" / "workflows" / "public-benchmarks.yml").read_text(encoding="utf-8")
    assert 'cron: "0 3 * * *"' in workflow
    assert "runtime-stability.json" in workflow
    assert "ecosystem-readiness.json" in workflow
    assert "verify_benchmark_trends.py" in workflow
    assert "benchmark-history/current-benchmark.json" in workflow
    assert "generate_public_benchmark_site.py" in workflow


def test_external_control_plane_demo_exists():
    demo = ROOT / "examples" / "external" / "control-plane-demo"
    assert (demo / "README.md").exists()
    assert (demo / "index.html").exists()
