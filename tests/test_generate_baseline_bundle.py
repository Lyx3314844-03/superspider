from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import generate_baseline_bundle


ROOT = Path(__file__).resolve().parents[1]


def test_collect_baseline_bundle_passes_for_repo():
    bundle = generate_baseline_bundle.collect_baseline_bundle(ROOT)

    assert bundle["command"] == "generate-baseline-bundle"
    assert bundle["summary"] == "passed"
    assert bundle["quality_profile"] == "strict"
    assert len(bundle["components"]) >= 7
    assert any(component["name"] == "framework_standards" for component in bundle["components"])


def test_render_markdown_mentions_framework_standards_component():
    bundle = generate_baseline_bundle.collect_baseline_bundle(ROOT)
    markdown = generate_baseline_bundle.render_markdown(bundle)

    assert "# Baseline Bundle" in markdown
    assert "framework_standards" in markdown


def test_baseline_bundle_contract_is_documented_and_schema_exists():
    schema = json.loads((ROOT / "schemas" / "spider-baseline-bundle.schema.json").read_text(encoding="utf-8"))

    assert schema["properties"]["command"]["const"] == "generate-baseline-bundle"
