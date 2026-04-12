from pathlib import Path
import json
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import generate_public_benchmark_site


ROOT = Path(__file__).resolve().parents[1]


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_render_site_contains_sections():
    html = generate_public_benchmark_site.render_site({
        "runtime_readiness": {
            "summary": "passed",
            "frameworks": [
                {
                    "name": "gospider",
                    "runtime": "go",
                    "summary": "passed",
                    "metrics": {
                        "success_rate": 1.0,
                        "workflow_replay_rate": 1.0,
                        "control_plane_rate": 1.0,
                    },
                }
            ],
        },
        "framework_deep_surfaces": {
            "summary": "passed",
            "frameworks": {
                "gospider": {
                    "runtime": "go",
                    "capability_status": "passed",
                    "extended_entrypoints": ["profile-site", "selector-studio", "plugins"],
                    "modules": ["runtime.dispatch", "site_profiler", "api"],
                    "live_surfaces": [
                        {"name": "captcha-live-readiness", "summary": "skipped"}
                    ],
                }
            },
        },
        "framework_scorecard": {},
        "benchmark_sla": {
            "summary": "passed",
            "frameworks": [
                {
                    "name": "gospider",
                    "runtime": "go",
                    "summary": "passed",
                    "sla": {"success_job_ms": {"measured": 10, "threshold": 100, "passed": True}},
                }
            ],
        },
        "blackbox_e2e": {
            "summary": "passed",
            "frameworks": [{"name": "gospider", "runtime": "go", "summary": "passed"}],
        },
        "runtime_stability": {
            "summary": "passed",
            "frameworks": [
                {
                    "name": "gospider",
                    "runtime": "go",
                    "summary": "passed",
                    "metrics": {
                        "frontier_stress_rate": 1.0,
                        "recovery_rate": 1.0,
                        "distributed_longevity_rate": 1.0,
                        "soak_ready": True,
                    },
                }
            ],
        },
        "result_contracts": {
            "summary": "passed",
            "checks": [
                {"name": "contract-schemas", "status": "passed", "details": "ok"},
            ],
        },
        "superspider_control_plane_benchmark": {
            "summary": "passed",
            "checks": [
                {"name": "executions-total", "status": "passed", "details": "ok"},
            ],
        },
        "superspider_control_plane": {
            "summary": "passed",
            "summary_text": "11 passed, 0 failed",
            "checks": [],
        },
        "superspider_control_plane_package": {
            "summary": "passed",
            "summary_text": "4 passed, 0 failed",
            "checks": [],
        },
        "superspider_control_plane_release": {
            "summary": "passed",
            "summary_text": "10 passed, 0 failed",
            "checks": [],
        },
        "operator_products": {
            "summary": "passed",
            "checks": [
                {"name": "jobdir-tool", "status": "passed", "details": "ok"},
            ],
        },
        "kernel_homogeneity": {
            "summary": "passed",
            "checks": [
                {"name": "manifest-alignment", "status": "passed", "details": "ok"},
            ],
        },
        "observability_evidence": {
            "summary": "passed",
            "checks": [
                {"name": "monitoring-surface", "status": "passed", "details": "ok"},
            ],
        },
        "cache_incremental_evidence": {
            "summary": "passed",
            "checks": [
                {"name": "schema-cache-envelope", "status": "passed", "details": "ok"},
            ],
        },
        "ecosystem_marketplace": {
            "summary": "passed",
            "checks": [
                {"name": "catalog-entrypoints", "status": "passed", "details": "ok"},
            ],
        },
        "ecosystem_readiness": {
            "summary": "passed",
            "checks": [
                {"name": "docs-surface", "status": "passed", "details": "ok"},
            ],
        },
        "captcha_live_readiness": {
            "summary": "skipped",
            "frameworks": {
                "javaspider": {
                    "runtime": "java",
                    "summary": "skipped",
                    "summary_text": "java live not enabled",
                },
                "gospider": {
                    "runtime": "go",
                    "summary": "unsupported",
                    "summary_text": "no live captcha surface",
                },
            },
        },
        "industry_proof_surface": {
            "summary": "passed",
            "checks": [
                {"name": "public-benchmark-surface", "status": "passed", "details": "ok"},
            ],
        },
        "benchmark_trends": {
            "summary": "passed",
            "history_depth": 2,
            "benchmark_trends": {
                "gospider": {
                    "runtime": "go",
                    "current": {"measured": 10, "threshold": 100, "passed": True},
                    "delta_ms": -5,
                    "summary_changed": False,
                }
            },
            "readiness_trends": {
                "gospider": {
                    "runtime": "go",
                    "current": {"summary": "passed", "control_plane_rate": 1.0},
                    "previous": {"summary": "passed", "control_plane_rate": 1.0},
                    "delta": {"control_plane_rate": 0.0},
                    "summary_changed": False,
                }
            },
            "alerts": [
                {
                    "framework": "gospider",
                    "source": "benchmark-sla",
                    "severity": "warning",
                    "details": "success_job_ms regressed from 8ms to 10ms",
                }
            ],
        },
    })

    assert "Spider Public Benchmarks" in html
    assert "Runtime Readiness" in html
    assert "Framework Deep Surfaces" in html
    assert "Runtime Stability" in html
    assert "Result Contracts" in html
    assert "SuperSpider Control Plane Benchmark" in html
    assert "SuperSpider Control Plane Release" in html
    assert "Operator Products" in html
    assert "Kernel Homogeneity" in html
    assert "Observability Evidence" in html
    assert "Cache And Incremental Evidence" in html
    assert "Benchmark SLA" in html
    assert "Blackbox E2E" in html
    assert "Ecosystem Readiness" in html
    assert "Ecosystem Marketplace" in html
    assert "Captcha Live Readiness" in html
    assert "Industry Proof Surface" in html
    assert "Benchmark Trends" in html
    assert "Runtime Readiness Trends" in html
    assert "Current Alerts" in html
    assert "success_job_ms regressed from 8ms to 10ms" in html


def test_collect_site_data_reads_artifacts():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        artifacts = root / "artifacts"
        _write(
            artifacts / "runtime-readiness.json",
            {
                "command": "verify-runtime-readiness",
                "summary": "passed",
                "frameworks": [
                    {
                        "name": "gospider",
                        "runtime": "go",
                        "summary": "passed",
                        "metrics": {
                            "success_rate": 1.0,
                            "workflow_replay_rate": 1.0,
                            "control_plane_rate": 1.0,
                        },
                    }
                ],
            },
        )
        _write(artifacts / "framework-deep-surfaces.json", {"command": "generate-framework-deep-surfaces-report", "summary": "passed", "frameworks": {}})
        _write(artifacts / "framework-scorecard.json", {"command": "generate-framework-scorecard"})
        _write(artifacts / "benchmark-sla.json", {"command": "verify-benchmark-sla", "summary": "passed", "frameworks": []})
        _write(artifacts / "blackbox-e2e.json", {"command": "verify-blackbox-e2e", "summary": "passed", "frameworks": []})
        _write(artifacts / "runtime-stability.json", {"command": "verify-runtime-stability", "summary": "passed", "frameworks": []})
        _write(artifacts / "result-contracts.json", {"command": "verify-result-contracts", "summary": "passed", "checks": []})
        _write(artifacts / "superspider-control-plane-benchmark.json", {"command": "verify-superspider-control-plane-benchmark", "summary": "passed", "checks": []})
        _write(artifacts / "superspider-control-plane.json", {"command": "verify-superspider-control-plane", "summary": "passed", "summary_text": "ok", "checks": []})
        _write(artifacts / "superspider-control-plane-package.json", {"command": "verify-superspider-control-plane-package", "summary": "passed", "summary_text": "ok", "checks": []})
        _write(artifacts / "superspider-control-plane-release.json", {"command": "verify-superspider-control-plane-release", "summary": "passed", "summary_text": "ok", "checks": []})
        _write(artifacts / "operator-products.json", {"command": "verify-operator-products", "summary": "passed", "checks": []})
        _write(artifacts / "kernel-homogeneity.json", {"command": "verify-kernel-homogeneity", "summary": "passed", "checks": []})
        _write(artifacts / "observability-evidence.json", {"command": "verify-observability-evidence", "summary": "passed", "checks": []})
        _write(artifacts / "cache-incremental-evidence.json", {"command": "verify-cache-incremental-evidence", "summary": "passed", "checks": []})
        _write(artifacts / "ecosystem-marketplace.json", {"command": "verify-ecosystem-marketplace", "summary": "passed", "checks": []})
        _write(artifacts / "ecosystem-readiness.json", {"command": "verify-ecosystem-readiness", "summary": "passed", "checks": []})
        _write(artifacts / "captcha-live-readiness.json", {"command": "verify-captcha-live-readiness", "summary": "skipped", "frameworks": {}})
        _write(artifacts / "industry-proof-surface.json", {"command": "verify-industry-proof-surface", "summary": "passed", "checks": []})
        _write(artifacts / "benchmark-trends.json", {"command": "verify-benchmark-trends", "summary": "passed", "history_depth": 0, "benchmark_trends": {}})

        payload = generate_public_benchmark_site.collect_site_data(root)
        assert payload["framework_deep_surfaces"]["command"] == "generate-framework-deep-surfaces-report"
        assert payload["benchmark_sla"]["command"] == "verify-benchmark-sla"
        assert payload["blackbox_e2e"]["command"] == "verify-blackbox-e2e"
        assert payload["runtime_stability"]["command"] == "verify-runtime-stability"
        assert payload["result_contracts"]["command"] == "verify-result-contracts"
        assert payload["superspider_control_plane_benchmark"]["command"] == "verify-superspider-control-plane-benchmark"
        assert payload["superspider_control_plane"]["command"] == "verify-superspider-control-plane"
        assert payload["superspider_control_plane_package"]["command"] == "verify-superspider-control-plane-package"
        assert payload["superspider_control_plane_release"]["command"] == "verify-superspider-control-plane-release"
        assert payload["operator_products"]["command"] == "verify-operator-products"
        assert payload["kernel_homogeneity"]["command"] == "verify-kernel-homogeneity"
        assert payload["observability_evidence"]["command"] == "verify-observability-evidence"
        assert payload["cache_incremental_evidence"]["command"] == "verify-cache-incremental-evidence"
        assert payload["ecosystem_marketplace"]["command"] == "verify-ecosystem-marketplace"
        assert payload["ecosystem_readiness"]["command"] == "verify-ecosystem-readiness"
        assert payload["captcha_live_readiness"]["command"] == "verify-captcha-live-readiness"
        assert payload["industry_proof_surface"]["command"] == "verify-industry-proof-surface"


def test_public_benchmark_generator_script_exists():
    assert (ROOT / "generate_public_benchmark_site.py").exists()
