from pathlib import Path
from types import SimpleNamespace
import json
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pyspider.media.ffmpeg_tools import FFmpegNotFoundError
from pyspider.cli import video_downloader


def test_doctor_command_reports_dependency_status(monkeypatch, capsys):
    fake_report = SimpleNamespace(
        exit_code=0,
        statuses=[
            SimpleNamespace(level="ok", name="Python", message="3.11.9"),
            SimpleNamespace(
                level="ok",
                name="FFmpeg",
                message="available at C:/ffmpeg/bin/ffmpeg.exe",
            ),
            SimpleNamespace(
                level="warn", name="Playwright", message="module not installed"
            ),
        ],
        summary="2 passed, 1 warning, 0 failed, 0 skipped",
    )

    monkeypatch.setattr(
        video_downloader,
        "run_dependency_doctor",
        lambda args: fake_report,
        raising=False,
    )
    monkeypatch.setattr(sys, "argv", ["pyspider", "doctor"])

    exit_code = video_downloader.main()
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Python" in output
    assert "FFmpeg" in output
    assert "2 passed, 1 warning, 0 failed, 0 skipped" in output


def test_doctor_command_can_render_json(monkeypatch, capsys):
    fake_report = SimpleNamespace(
        exit_code=1,
        statuses=[
            SimpleNamespace(level="ok", name="Python", message="3.11.9"),
            SimpleNamespace(level="fail", name="FFmpeg", message="missing"),
        ],
        summary="1 passed, 0 warnings, 1 failed, 0 skipped",
    )

    monkeypatch.setattr(
        video_downloader,
        "run_dependency_doctor",
        lambda args: fake_report,
        raising=False,
    )
    monkeypatch.setattr(sys, "argv", ["pyspider", "doctor", "--json"])

    exit_code = video_downloader.main()
    output = capsys.readouterr().out
    payload = json.loads(output)

    assert exit_code == 1
    assert payload["exit_code"] == 1
    assert payload["command"] == "doctor"
    assert payload["runtime"] == "python"
    assert payload["summary"] == "failed"
    assert payload["summary_text"] == "1 passed, 0 warnings, 1 failed, 0 skipped"
    assert payload["checks"][1]["name"] == "FFmpeg"
    assert payload["checks"][1]["status"] == "failed"
    assert payload["checks"][1]["details"] == "missing"


@pytest.mark.parametrize(
    ("argv", "patch_target"),
    [
        (
            ["pyspider", "convert", "input.mp4", "output.mp4", "-f", "mp4"],
            "FFmpegTools",
        ),
        (["pyspider", "info", "input.mp4"], "FFmpegExecutor"),
        (["pyspider", "screenshot", "input.mp4"], "FFmpegTools"),
    ],
)
def test_media_commands_surface_dependency_guidance(
    monkeypatch, capsys, argv, patch_target
):
    class MissingDependency:
        def __init__(self, *args, **kwargs):
            raise FFmpegNotFoundError("ffmpeg missing for test")

    monkeypatch.setattr(video_downloader, patch_target, MissingDependency)
    monkeypatch.setattr(sys, "argv", argv)

    exit_code = video_downloader.main()
    output = capsys.readouterr().out

    assert exit_code == 1
    assert "FFmpeg 依赖检查失败" in output
    assert "pyspider doctor" in output
    assert "ffmpeg missing for test" in output
