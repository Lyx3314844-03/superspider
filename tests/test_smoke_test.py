from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import smoke_test


def test_linux_smoke_commands_use_native_javaspider_invocation():
    commands = smoke_test.build_smoke_commands("Linux")
    command = commands["javaspider"]["command"]

    assert command[:2] == ["bash", "-lc"]
    assert "powershell" not in command
    assert "EnhancedSpider version" in command[2]


def test_macos_smoke_commands_use_unix_javaspider_invocation():
    commands = smoke_test.build_smoke_commands("Darwin")
    command = commands["javaspider"]["command"]

    assert command[:2] == ["bash", "-lc"]
    assert "EnhancedSpider version" in command[2]


def test_windows_smoke_commands_use_powershell_for_javaspider():
    commands = smoke_test.build_smoke_commands("Windows")
    command = commands["javaspider"]["command"]
    command_text = " ".join(command)

    assert command[:3] == ["powershell", "-NoProfile", "-Command"]
    assert "EnhancedSpider version" in command_text


def test_smoke_commands_cover_all_framework_entrypoints():
    commands = smoke_test.build_smoke_commands("Linux")

    assert commands["pyspider"]["command"][-1] == "version"
    assert any("pyspider" in part for part in commands["pyspider"]["command"])
    assert commands["gospider"]["command"][-1] == "version"
    assert commands["rustspider"]["command"][-1] == "version"


def test_pyspider_smoke_command_falls_back_to_module_entrypoint(monkeypatch):
    fake_python = Path("C:/Python314/python.exe")
    monkeypatch.setattr(smoke_test.sys, "executable", str(fake_python))

    command = smoke_test.build_pyspider_command("Windows", "version")

    assert command == [str(fake_python), "-m", "pyspider", "version"]


def test_pyspider_smoke_command_uses_unix_entrypoint_on_macos(monkeypatch):
    fake_python = Path("/opt/homebrew/bin/python3")
    monkeypatch.setattr(smoke_test.sys, "executable", str(fake_python))

    command = smoke_test.build_pyspider_command("Darwin", "version")

    assert command == [str(fake_python), "-m", "pyspider", "version"]


def test_run_smoke_suite_builds_contract_shape(monkeypatch):
    class _CompletedProcess:
        def __init__(self, returncode=0, stdout="", stderr=""):
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    def fake_run(command, cwd, capture_output, text, check):
        return _CompletedProcess(stdout="ok")

    monkeypatch.setattr(smoke_test.subprocess, "run", fake_run)

    report = smoke_test.run_smoke_suite(Path("C:/Users/Administrator/spider"))

    assert report["command"] == "smoke-test"
    assert report["summary"] == "failed"
    assert report["summary_text"] == "0 passed, 4 failed"
    assert len(report["checks"]) == 4


def test_smoke_contract_is_documented_and_schema_exists():
    root = Path(__file__).resolve().parents[1]
    contract = (root / "docs" / "framework-contract.md").read_text(encoding="utf-8")
    schema = json.loads((root / "schemas" / "spider-smoke-report.schema.json").read_text(encoding="utf-8"))

    assert "Root Smoke-Test JSON Envelope" in contract
    assert schema["properties"]["command"]["const"] == "smoke-test"
    assert schema["properties"]["checks"]["items"]["required"] == [
        "name",
        "runtime",
        "summary",
        "exit_code",
        "details",
    ]
