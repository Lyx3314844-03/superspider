from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import verify_operator_products


ROOT = Path(__file__).resolve().parents[1]


def test_collect_operator_products_report_passes_for_repo():
    report = verify_operator_products.collect_operator_products_report(ROOT)

    assert report["command"] == "verify-operator-products"
    assert report["summary"] == "passed"
    assert report["exit_code"] == 0


def test_render_markdown_contains_operator_checks():
    markdown = verify_operator_products.render_markdown(
        {
            "summary_text": "6 passed, 0 failed",
            "checks": [
                {"name": "jobdir-tool", "status": "passed", "details": "ok"},
            ],
        }
    )

    assert "| Check | Status | Details |" in markdown
    assert "jobdir-tool" in markdown


def test_operator_products_schema_exists():
    schema = json.loads((ROOT / "schemas" / "spider-operator-products.schema.json").read_text(encoding="utf-8"))

    assert schema["properties"]["command"]["const"] == "verify-operator-products"
