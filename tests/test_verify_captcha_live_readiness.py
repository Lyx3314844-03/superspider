from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import verify_captcha_live_readiness


ROOT = Path(__file__).resolve().parents[1]


def test_collect_captcha_live_readiness_report_aggregates_frameworks(monkeypatch):
    monkeypatch.setattr(
        verify_captcha_live_readiness.verify_javaspider_captcha_live,
        "run_javaspider_captcha_live",
        lambda root: {
            "runtime": "java",
            "summary": "passed",
            "summary_text": "java live ready",
            "checks": [],
            "metrics": {"live_ready": True},
        },
    )
    monkeypatch.setattr(
        verify_captcha_live_readiness.verify_pyspider_captcha_live,
        "run_pyspider_captcha_live",
        lambda root: {
            "runtime": "python",
            "summary": "skipped",
            "summary_text": "python live skipped",
            "checks": [],
            "metrics": {"live_ready": False},
        },
    )
    monkeypatch.setattr(
        verify_captcha_live_readiness.verify_rust_captcha_live,
        "run_rust_captcha_live",
        lambda root: {
            "runtime": "rust",
            "summary": "passed",
            "summary_text": "rust live ready",
            "checks": [],
            "metrics": {"live_ready": True},
        },
    )
    monkeypatch.setattr(
        verify_captcha_live_readiness.verify_gospider_captcha_live,
        "run_gospider_captcha_live",
        lambda root: {
            "runtime": "go",
            "summary": "skipped",
            "summary_text": "go live skipped",
            "checks": [],
            "metrics": {"live_ready": False},
        },
    )

    report = verify_captcha_live_readiness.collect_captcha_live_readiness_report(ROOT)

    assert report["command"] == "verify-captcha-live-readiness"
    assert report["summary"] == "passed"
    assert report["frameworks"]["javaspider"]["summary"] == "passed"
    assert report["frameworks"]["pyspider"]["summary"] == "skipped"
    assert report["frameworks"]["rustspider"]["summary"] == "passed"
    assert report["frameworks"]["gospider"]["summary"] == "skipped"


def test_render_markdown_contains_framework_rows():
    markdown = verify_captcha_live_readiness.render_markdown(
        {
            "summary_text": "javaspider=passed, pyspider=skipped, rustspider=passed, gospider=unsupported",
            "frameworks": {
                "javaspider": {
                    "runtime": "java",
                    "summary": "passed",
                    "summary_text": "java live ready",
                },
                "gospider": {
                    "runtime": "go",
                    "summary": "skipped",
                    "summary_text": "go live skipped",
                },
            },
        }
    )

    assert "| javaspider | java | passed | java live ready |" in markdown
    assert "| gospider | go | skipped | go live skipped |" in markdown


def test_captcha_live_readiness_schema_exists():
    schema = json.loads(
        (ROOT / "schemas" / "spider-captcha-live-readiness.schema.json").read_text(
            encoding="utf-8"
        )
    )
    assert schema["properties"]["command"]["const"] == "verify-captcha-live-readiness"
