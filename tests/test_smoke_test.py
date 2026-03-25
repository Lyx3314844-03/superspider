from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import smoke_test


def test_linux_smoke_commands_use_native_javaspider_invocation():
    commands = smoke_test.build_smoke_commands("Linux")
    command = commands["javaspider"]["command"]

    assert command[0] == "mvn"
    assert "powershell" not in command
    assert "-Dexec.args=version" in command


def test_windows_smoke_commands_use_powershell_for_javaspider():
    commands = smoke_test.build_smoke_commands("Windows")
    command = commands["javaspider"]["command"]
    command_text = " ".join(command)

    assert command[:3] == ["powershell", "-NoProfile", "-Command"]
    assert "-Dexec.args=version" in command_text


def test_smoke_commands_cover_all_framework_entrypoints():
    commands = smoke_test.build_smoke_commands("Linux")

    assert commands["pyspider"]["command"][-1] == "--help"
    assert commands["gospider"]["command"][-1] == "version"
    assert commands["rustspider"]["command"][-1] == "--help"
