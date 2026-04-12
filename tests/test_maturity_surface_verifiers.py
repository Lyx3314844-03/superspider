from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import verify_cache_incremental_evidence
import verify_ecosystem_marketplace
import verify_industry_proof_surface
import verify_kernel_homogeneity
import verify_observability_evidence


ROOT = Path(__file__).resolve().parents[1]


def test_kernel_homogeneity_report_passes_for_repo():
    report = verify_kernel_homogeneity.collect_kernel_homogeneity_report(ROOT)

    assert report["command"] == "verify-kernel-homogeneity"
    assert report["summary"] == "passed"
    assert report["exit_code"] == 0


def test_observability_evidence_report_passes_for_repo():
    report = verify_observability_evidence.collect_observability_evidence_report(ROOT)

    assert report["command"] == "verify-observability-evidence"
    assert report["summary"] == "passed"
    assert report["exit_code"] == 0


def test_cache_incremental_evidence_report_passes_for_repo():
    report = verify_cache_incremental_evidence.collect_cache_incremental_evidence_report(ROOT)

    assert report["command"] == "verify-cache-incremental-evidence"
    assert report["summary"] == "passed"
    assert report["exit_code"] == 0


def test_ecosystem_marketplace_report_passes_for_repo():
    report = verify_ecosystem_marketplace.collect_ecosystem_marketplace_report(ROOT)

    assert report["command"] == "verify-ecosystem-marketplace"
    assert report["summary"] == "passed"
    assert report["exit_code"] == 0


def test_industry_proof_surface_report_passes_for_repo():
    report = verify_industry_proof_surface.collect_industry_proof_surface_report(ROOT)

    assert report["command"] == "verify-industry-proof-surface"
    assert report["summary"] == "passed"
    assert report["exit_code"] == 0


def test_new_maturity_surface_schemas_exist():
    schema_names = {
        "verify-kernel-homogeneity": "spider-kernel-homogeneity.schema.json",
        "verify-observability-evidence": "spider-observability-evidence.schema.json",
        "verify-cache-incremental-evidence": "spider-cache-incremental-evidence.schema.json",
        "verify-ecosystem-marketplace": "spider-ecosystem-marketplace.schema.json",
        "verify-industry-proof-surface": "spider-industry-proof-surface.schema.json",
    }

    for command, filename in schema_names.items():
        schema = json.loads((ROOT / "schemas" / filename).read_text(encoding="utf-8"))
        assert schema["properties"]["command"]["const"] == command


def test_marketplace_catalog_contains_new_entrypoints_and_plugins():
    catalog = json.loads((ROOT / "contracts" / "integration-catalog.json").read_text(encoding="utf-8"))

    entrypoint_ids = {entrypoint["id"] for entrypoint in catalog["entrypoints"]}
    plugin_ids = {plugin["id"] for plugin in catalog["plugins"]}

    assert {"marketplace", "support"}.issubset(entrypoint_ids)
    assert {"http-cache", "incremental-crawl", "observability-monitor"}.issubset(plugin_ids)
