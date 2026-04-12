from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import verify_ecosystem_readiness


ROOT = Path(__file__).resolve().parents[1]


def test_collect_ecosystem_readiness_report_passes_for_repo():
    report = verify_ecosystem_readiness.collect_ecosystem_readiness_report(ROOT)

    assert report["command"] == "verify-ecosystem-readiness"
    assert report["summary"] == "passed"
    assert report["exit_code"] == 0
    assert any(check["name"] == "adopter-validation-surface" for check in report["checks"])


def test_render_markdown_contains_table():
    markdown = verify_ecosystem_readiness.render_markdown(
        {
            "summary_text": "4 passed, 0 failed",
            "checks": [
                {"name": "docs-surface", "status": "passed", "details": "ok"},
            ],
        }
    )

    assert "| Check | Status | Details |" in markdown
    assert "docs-surface" in markdown


def test_ecosystem_readiness_schema_exists():
    schema = json.loads((ROOT / "schemas" / "spider-ecosystem-readiness.schema.json").read_text(encoding="utf-8"))

    assert schema["properties"]["command"]["const"] == "verify-ecosystem-readiness"
