from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import verify_env


class _CompletedProcess:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_javaspider_doctor_command_compiles_before_exec():
    command = verify_env.FRAMEWORK_COMMANDS["javaspider"]["command"]
    command_text = " ".join(command)

    assert "mvn -q compile" in command_text
    assert "EnhancedSpider doctor --json" in command_text


def test_linux_javaspider_command_does_not_require_powershell():
    commands = verify_env.build_framework_commands("Linux")
    command = commands["javaspider"]["command"]

    assert command[:2] == ["bash", "-lc"]
    assert "powershell" not in command
    assert "EnhancedSpider doctor --json" in command[2]


def test_macos_javaspider_command_uses_unix_shell_surface():
    commands = verify_env.build_framework_commands("Darwin")
    command = commands["javaspider"]["command"]

    assert command[:2] == ["bash", "-lc"]
    assert "EnhancedSpider doctor --json" in command[2]


def test_windows_javaspider_command_uses_powershell_wrapper():
    commands = verify_env.build_framework_commands("Windows")
    command = commands["javaspider"]["command"]
    command_text = " ".join(command)

    assert command[:3] == ["powershell", "-NoProfile", "-Command"]
    assert "mvn -q compile" in command_text
    assert "EnhancedSpider doctor --json" in command_text


def test_gospider_doctor_command_skips_external_network_probe():
    command = verify_env.FRAMEWORK_COMMANDS["gospider"]["command"]

    assert command[-2:] == ["doctor", "--json"]


def test_pyspider_doctor_command_falls_back_to_module_entrypoint(monkeypatch):
    fake_python = Path("C:/Python314/python.exe")
    monkeypatch.setattr(verify_env.sys, "executable", str(fake_python))

    command = verify_env.build_pyspider_command("Windows")

    assert command == [str(fake_python), "-m", "pyspider", "doctor", "--json"]


def test_pyspider_doctor_command_uses_unix_entrypoint_on_macos(monkeypatch):
    fake_python = Path("/opt/homebrew/bin/python3")
    monkeypatch.setattr(verify_env.sys, "executable", str(fake_python))

    command = verify_env.build_pyspider_command("Darwin")

    assert command == [str(fake_python), "-m", "pyspider", "doctor", "--json"]


def test_aggregate_results_normalizes_framework_reports(monkeypatch):
    responses = {
        "javaspider": _CompletedProcess(
            returncode=1,
            stdout=json.dumps(
                {
                    "command": "doctor",
                    "runtime": "java",
                    "summary": "failed",
                    "summary_text": "0 passed, 1 failed",
                    "exit_code": 1,
                    "checks": [{"name": "ffmpeg", "status": "failed", "details": "missing"}],
                }
            ),
        ),
        "pyspider": _CompletedProcess(
            stdout=json.dumps(
                {
                    "command": "doctor",
                    "runtime": "python",
                    "summary": "passed",
                    "summary_text": "1 passed, 0 failed",
                    "exit_code": 0,
                    "checks": [{"name": "Python", "status": "passed", "details": "3.13.0"}],
                }
            ),
        ),
        "gospider": _CompletedProcess(
            stdout=json.dumps(
                {
                    "command": "doctor",
                    "runtime": "go",
                    "summary": "passed",
                    "summary_text": "1 passed, 0 failed",
                    "exit_code": 0,
                    "checks": [{"name": "配置", "status": "passed", "details": "ok"}],
                }
            ),
        ),
        "rustspider": _CompletedProcess(
            stdout=json.dumps(
                {
                    "command": "doctor",
                    "runtime": "rust",
                    "summary": "passed",
                    "summary_text": "1 passed, 0 failed",
                    "exit_code": 0,
                    "checks": [{"name": "filesystem:data", "status": "passed", "details": "ok"}],
                }
            ),
        ),
    }

    def fake_run(command, cwd, capture_output, text, check):
        command_text = " ".join(command)
        if "pyspider" in command_text and "doctor" in command_text:
            framework = "pyspider"
        elif "cmd/gospider" in command_text:
            framework = "gospider"
        elif "cargo" in command_text and "doctor" in command_text:
            framework = "rustspider"
        else:
            framework = Path(cwd).name
        return responses[framework]

    monkeypatch.setattr(verify_env.subprocess, "run", fake_run)

    result = verify_env.aggregate_framework_reports(Path("C:/Users/Administrator/spider"))

    assert result["summary"] == "failed"
    assert result["exit_code"] == 1
    assert len(result["frameworks"]) == 4
    assert result["frameworks"][0]["name"] == "javaspider"
    assert result["frameworks"][0]["report"]["checks"][0]["name"] == "ffmpeg"
    assert result["frameworks"][3]["report"]["runtime"] == "rust"
    assert result["frameworks"][3]["report"]["command"] == "doctor"


def test_extract_json_payload_skips_log_prefixes():
    payload = verify_env._extract_json_payload("noise line\n{\"summary\":\"passed\"}")
    assert payload == "{\"summary\":\"passed\"}"


def test_invalid_doctor_contract_marks_framework_failed(monkeypatch):
    def fake_run(command, cwd, capture_output, text, check):
        return _CompletedProcess(
            returncode=0,
            stdout=json.dumps(
                {
                    "command": "doctor",
                    "runtime": "go",
                    "summary": "passed",
                    "exit_code": 0,
                    "checks": [{"name": "配置", "status": "passed", "details": "ok"}],
                }
            ),
        )

    monkeypatch.setattr(verify_env.subprocess, "run", fake_run)

    report = verify_env.run_framework_doctor(Path("C:/Users/Administrator/spider"), "gospider")

    assert report["summary"] == "failed"
    assert "doctor contract violation" in report["stderr"]


def test_framework_contract_documents_doctor_json_contract():
    root = Path(__file__).resolve().parents[1]
    contract = (root / "docs" / "framework-contract.md").read_text(encoding="utf-8")
    schema = json.loads((root / "schemas" / "spider-doctor-report.schema.json").read_text(encoding="utf-8"))

    assert "Shared Doctor JSON Envelope" in contract
    assert "summary_text" in contract
    assert schema["properties"]["command"]["const"] == "doctor"
    assert set(schema["properties"]["checks"]["items"]["properties"]["status"]["enum"]) == {
        "passed",
        "failed",
        "warning",
        "skipped",
    }
