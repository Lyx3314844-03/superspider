from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import verify_version


ROOT = Path(__file__).resolve().parents[1]


def test_version_file_exists_and_contains_single_repo_version():
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()

    assert version == "1.0.0"


def test_collect_version_report_uses_root_version_and_all_targets():
    report = verify_version.collect_version_report(ROOT)

    assert report["expected_version"] == "1.0.0"
    assert report["summary"] == "passed"
    assert report["summary_text"] == "6 targets passed, 0 targets failed, 1 checks passed, 0 checks failed, 0 checks skipped"
    assert report["exit_code"] == 0
    assert {item["path"] for item in report["targets"]} == {
        "javaspider/pom.xml",
        "pyspider/__init__.py",
        "pyspider/setup.py",
        "rustspider/Cargo.toml",
        "helm/superspider/Chart.yaml:version",
        "helm/superspider/Chart.yaml:appVersion",
    }


def test_collect_version_report_rejects_tag_version_mismatch():
    report = verify_version.collect_version_report(ROOT, git_ref="refs/tags/v9.9.9")

    assert report["summary"] == "failed"
    assert report["summary_text"] == "6 targets passed, 0 targets failed, 1 checks passed, 1 checks failed, 0 checks skipped"
    assert report["exit_code"] == 1
    assert any(check["name"] == "git-tag" and check["status"] == "failed" for check in report["checks"])


def test_collect_version_report_accepts_matching_tag():
    report = verify_version.collect_version_report(ROOT, git_ref="refs/tags/v1.0.0")

    assert report["summary"] == "passed"
    assert report["summary_text"] == "6 targets passed, 0 targets failed, 2 checks passed, 0 checks failed, 0 checks skipped"
    assert report["exit_code"] == 0
    assert any(check["name"] == "git-tag" and check["status"] == "passed" for check in report["checks"])


def test_main_prints_json_report(capsys):
    exit_code = verify_version.main(["--root", str(ROOT), "--json"])
    output = capsys.readouterr().out
    report = json.loads(output)

    assert exit_code == 0
    assert report["expected_version"] == "1.0.0"


def test_verify_version_contract_is_documented_and_schema_exists():
    contract = (ROOT / "docs" / "framework-contract.md").read_text(encoding="utf-8")
    schema = json.loads((ROOT / "schemas" / "spider-version-report.schema.json").read_text(encoding="utf-8"))

    assert "Root Verify-Version JSON Envelope" in contract
    assert schema["properties"]["command"]["const"] == "verify-version"
    assert schema["properties"]["checks"]["items"]["properties"]["status"]["enum"] == [
        "passed",
        "failed",
        "skipped",
    ]
