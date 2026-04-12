from pathlib import Path

import verify_framework_standards


ROOT = Path(__file__).resolve().parents[1]


def _scorecard():
    evidence = {
        "test_files": 30,
        "test_status": "moderate",
        "distributed": "verified",
        "anti_bot_verified": True,
        "browser_verified": True,
        "monitor_verified": True,
        "deploy_verified": True,
        "readme_present": True,
        "stability_verified": True,
        "stability_trends_verified": True,
        "core_contracts_verified": True,
        "control_plane_verified": True,
        "maturity_governance_verified": True,
        "legacy_isolation_verified": True,
        "ecosystem_verified": True,
    }
    return {
        "frameworks": {
            "javaspider": {"runtime": "java", "evidence": dict(evidence)},
            "pyspider": {"runtime": "python", "evidence": dict(evidence)},
            "gospider": {"runtime": "go", "evidence": dict(evidence)},
            "rustspider": {"runtime": "rust", "evidence": dict(evidence)},
        }
    }


def test_framework_standards_report_passes_current_matrix(monkeypatch):
    monkeypatch.setattr(verify_framework_standards.generate_framework_scorecard, "collect_framework_scorecard", lambda root: _scorecard())
    report = verify_framework_standards.collect_framework_standards(ROOT)

    assert report["summary"] == "passed"
    assert report["frameworks"]["javaspider"]["standards"]["tests"]["actual"] > 20
    assert report["frameworks"]["rustspider"]["standards"]["tests"]["actual"] > 20


def test_framework_standards_report_marks_docs_and_distributed_as_present(monkeypatch):
    monkeypatch.setattr(verify_framework_standards.generate_framework_scorecard, "collect_framework_scorecard", lambda root: _scorecard())
    report = verify_framework_standards.collect_framework_standards(ROOT)

    for framework in ("javaspider", "pyspider", "gospider", "rustspider"):
        assert report["frameworks"][framework]["standards"]["documentation"]["summary"] == "passed"
        assert report["frameworks"][framework]["standards"]["distributed"]["summary"] == "passed"
        assert report["frameworks"][framework]["standards"]["stability"]["summary"] == "passed"
        assert report["frameworks"][framework]["standards"]["stability_trends"]["summary"] == "passed"
        assert report["frameworks"][framework]["standards"]["governance"]["summary"] == "passed"
        assert report["frameworks"][framework]["standards"]["control_plane"]["summary"] == "passed"
        assert report["frameworks"][framework]["standards"]["legacy_isolation"]["summary"] == "passed"


def test_framework_standards_markdown_contains_matrix_headers(monkeypatch):
    monkeypatch.setattr(verify_framework_standards.generate_framework_scorecard, "collect_framework_scorecard", lambda root: _scorecard())
    report = verify_framework_standards.collect_framework_standards(ROOT)
    markdown = verify_framework_standards.render_markdown(report)

    assert "| 标准 | JavaSpider | PySpider | GoSpider | RustSpider |" in markdown
    assert "代码量>100" in markdown
    assert "测试>20" in markdown
    assert "稳定性" in markdown
    assert "统一控制面" in markdown
    assert "Legacy隔离" in markdown
