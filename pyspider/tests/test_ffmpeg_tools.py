from pathlib import Path
import sys
import os

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pyspider.media.ffmpeg_tools import FFmpegExecutor, FFmpegTools


class _FakeExecutor:
    def __init__(self, duration=125):
        self.duration = duration

    def get_duration(self, input_file):
        return self.duration


def test_take_screenshots_batch_uses_hh_mm_ss_timestamps(tmp_path, monkeypatch):
    tools = FFmpegTools(executor=_FakeExecutor(duration=125))
    captured = []

    def fake_take_screenshot(input_file, output_file, timestamp="00:00:01", width=None):
        captured.append((input_file, output_file, timestamp, width))
        return True

    monkeypatch.setattr(tools, "take_screenshot", fake_take_screenshot)

    outputs = tools.take_screenshots_batch("video.mp4", str(tmp_path), interval=60, width=320)

    assert outputs == [
        str(tmp_path / "screenshot_0000.jpg"),
        str(tmp_path / "screenshot_0001.jpg"),
        str(tmp_path / "screenshot_0002.jpg"),
    ]
    assert [item[2] for item in captured] == [
        "00:00:00",
        "00:01:00",
        "00:02:00",
    ]


def test_get_video_info_parses_fractional_frame_rate():
    executor = FFmpegExecutor(ffmpeg_path="ffmpeg", ffprobe_path="ffprobe")
    executor.probe = lambda _: {
        "format": {
            "duration": "12.5",
            "size": "2048",
            "format_name": "mov,mp4,m4a,3gp,3g2,mj2",
            "bit_rate": "320000",
        },
        "streams": [
            {
                "codec_type": "video",
                "codec_name": "h264",
                "width": 1920,
                "height": 1080,
                "r_frame_rate": "30000/1001",
            },
            {
                "codec_type": "audio",
                "codec_name": "aac",
            },
        ],
    }

    info = executor.get_video_info("sample.mp4")

    assert info is not None
    assert info.frame_rate == 30000 / 1001
    assert info.video_codec == "h264"
    assert info.audio_codec == "aac"


def test_get_video_info_handles_invalid_frame_rate_without_crashing():
    executor = FFmpegExecutor(ffmpeg_path="ffmpeg", ffprobe_path="ffprobe")
    executor.probe = lambda _: {
        "format": {
            "duration": "5",
            "size": "512",
            "format_name": "mp4",
            "bit_rate": "128000",
        },
        "streams": [
            {
                "codec_type": "video",
                "codec_name": "h264",
                "width": 1280,
                "height": 720,
                "r_frame_rate": "N/A",
            },
        ],
    }

    info = executor.get_video_info("sample.mp4")

    assert info is not None
    assert info.frame_rate == 0


def test_add_watermark_uses_video_as_main_overlay_input():
    class FakeExecutor:
        def __init__(self):
            self.calls = []

        def run(self, args, input_file=None, output_file=None, overwrite=True, capture_progress=False, progress_callback=None):
            self.calls.append(
                {
                    "args": args,
                    "input_file": input_file,
                    "output_file": output_file,
                }
            )
            return True

    executor = FakeExecutor()
    tools = FFmpegTools(executor=executor)

    success = tools.add_watermark(
        "input.mp4",
        "output.mp4",
        "watermark.png",
        position="bottomleft",
        opacity=0.5,
    )

    assert success is True
    assert executor.calls == [
        {
            "args": [
                "-i",
                "watermark.png",
                "-filter_complex",
                "[0][1]overlay=10:H-h-10:format=auto:alpha=0.5",
                "-c:a",
                "copy",
            ],
            "input_file": "input.mp4",
            "output_file": "output.mp4",
        }
    ]


def test_find_ffprobe_uses_same_directory_as_ffmpeg(monkeypatch):
    executor = FFmpegExecutor(ffmpeg_path="C:\\tools\\ffmpeg\\bin\\ffmpeg.exe", ffprobe_path="ffprobe.exe")

    expected = os.path.join("C:\\tools\\ffmpeg\\bin", "ffprobe.exe")

    monkeypatch.setattr(executor, "_which", lambda name: None)
    monkeypatch.setattr(os.path, "exists", lambda path: path == expected)

    assert executor._find_ffprobe() == expected
