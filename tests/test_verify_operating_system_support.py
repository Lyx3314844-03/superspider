from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import verify_operating_system_support


ROOT = Path(__file__).resolve().parents[1]


def test_collect_report_passes_for_repo():
    report = verify_operating_system_support.collect_operating_system_support_report(ROOT)

    assert report["command"] == "verify-operating-system-support"
    assert report["summary"] == "passed"
    assert report["platforms"]["windows"]["runner"] == "windows-latest"
    assert report["platforms"]["linux"]["runner"] == "ubuntu-latest"
    assert report["platforms"]["macos"]["runner"] == "macos-latest"
    assert any(check["name"] == "framework-os-matrix-workflow" for check in report["checks"])


def test_render_markdown_contains_three_operating_systems():
    report = verify_operating_system_support.collect_operating_system_support_report(ROOT)

    markdown = verify_operating_system_support.render_markdown(report)

    assert "`windows` via `windows-latest`" in markdown
    assert "`linux` via `ubuntu-latest`" in markdown
    assert "`macos` via `macos-latest`" in markdown


def test_collect_report_uses_actual_os_artifacts_when_present(tmp_path):
    artifact_dir = tmp_path / "artifacts" / "os-support-artifacts"
    artifact_dir.mkdir(parents=True)
    for runner in ("ubuntu-latest", "windows-latest", "macos-latest"):
        for prefix in ("verify-env", "smoke-test", "operating-system-support"):
            (artifact_dir / f"{prefix}-{runner}.json").write_text("{}", encoding="utf-8")

    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "framework-os-matrix.yml").write_text(
        "\n".join(
            [
                "ubuntu-latest",
                "windows-latest",
                "macos-latest",
                "python verify_operating_system_support.py --json",
                "python verify_env.py --json",
                "python smoke_test.py --json",
            ]
        ),
        encoding="utf-8",
    )

    for relative in (
        "pyspider/run-framework.bat",
        "pyspider/run-framework.sh",
        "gospider/build.bat",
        "gospider/build.sh",
        "gospider/run-framework.bat",
        "gospider/run-framework.sh",
        "javaspider/build.bat",
        "javaspider/build.sh",
        "javaspider/run-framework.bat",
        "javaspider/run-framework.sh",
        "rustspider/build.bat",
        "rustspider/build.sh",
        "rustspider/run-framework.bat",
        "rustspider/run-framework.sh",
    ):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")

    report = verify_operating_system_support.collect_operating_system_support_report(tmp_path)

    assert report["summary"] == "passed"
    assert any(check["name"] == "framework-os-matrix-artifacts" and check["status"] == "passed" for check in report["checks"])


def test_main_prints_json(monkeypatch, capsys):
    monkeypatch.setattr(
        verify_operating_system_support,
        "collect_operating_system_support_report",
        lambda root: {
            "command": "verify-operating-system-support",
            "summary": "passed",
            "summary_text": "14 passed, 0 failed",
            "exit_code": 0,
            "checks": [],
            "platforms": {},
        },
    )

    exit_code = verify_operating_system_support.main(["--root", str(ROOT), "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["command"] == "verify-operating-system-support"
