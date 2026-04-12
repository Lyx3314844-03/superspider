from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import generate_maturity_gap_report


ROOT = Path(__file__).resolve().parents[1]


def test_collect_maturity_gap_report_returns_gap_summary():
    report = generate_maturity_gap_report.collect_maturity_gap_report(ROOT)

    assert report["command"] == "generate-maturity-gap-report"
    assert report["exit_code"] == 0
    assert "proven" in report
    assert "gaps" in report


def test_render_markdown_contains_sections():
    markdown = generate_maturity_gap_report.render_markdown(
        {
            "summary_text": "4 proven areas, 2 remaining gap areas",
            "proven": [{"name": "release-gates", "status": "passed", "details": "ok"}],
            "gaps": [{"name": "third-party-adopter-evidence", "severity": "medium", "details": "missing"}],
        }
    )

    assert "## Proven" in markdown
    assert "## Remaining Gaps" in markdown
    assert "third-party-adopter-evidence" in markdown
