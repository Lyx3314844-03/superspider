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
    assert "org.codehaus.mojo:exec-maven-plugin:3.6.1:java" in command_text


def test_linux_javaspider_command_does_not_require_powershell():
    commands = verify_env.build_framework_commands("Linux")
    command = commands["javaspider"]["command"]

    assert command[0] == "mvn"
    assert "powershell" not in command
    assert "org.codehaus.mojo:exec-maven-plugin:3.6.1:java" in command


def test_windows_javaspider_command_uses_powershell_wrapper():
    commands = verify_env.build_framework_commands("Windows")
    command = commands["javaspider"]["command"]
    command_text = " ".join(command)

    assert command[:3] == ["powershell", "-NoProfile", "-Command"]
    assert "mvn -q compile" in command_text


def test_gospider_doctor_command_skips_external_network_probe():
    command = verify_env.FRAMEWORK_COMMANDS["gospider"]["command"]

    assert "--skip-network" in command


def test_aggregate_results_normalizes_framework_reports(monkeypatch):
    responses = {
        "javaspider": _CompletedProcess(
            returncode=1,
            stdout=json.dumps(
                {
                    "command": "doctor",
                    "runtime": "java",
                    "summary": "failed",
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
                    "exit_code": 0,
                    "checks": [{"name": "配置", "status": "passed", "details": "ok"}],
                }
            ),
        ),
        "rustspider": _CompletedProcess(
            stdout=json.dumps(
                {
                    "command": "preflight",
                    "runtime": "rust",
                    "summary": "passed",
                    "exit_code": 0,
                    "checks": [{"name": "filesystem:data", "status": "passed", "details": "ok"}],
                }
            ),
        ),
    }

    def fake_run(command, cwd, capture_output, text, check):
        command_text = " ".join(command)
        if "pyspider.cli.video_downloader" in command_text:
            framework = "pyspider"
        elif "cmd/gospider" in command_text:
            framework = "gospider"
        elif "--bin preflight" in command_text:
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
