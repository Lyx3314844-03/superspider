from pathlib import Path
import logging
import sys
import types

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pyspider.cli import video_downloader
from pyspider.media.video_parser import VideoData


def test_resolve_download_url_falls_back_to_generic_download_url():
    video = VideoData(
        title="Example",
        video_id="video-1",
        platform="youku",
        download_url="https://media.example.com/download?id=1",
    )

    download_url = video_downloader.resolve_download_url(video, requested_quality=None, logger=logging.getLogger(__name__))

    assert download_url == "https://media.example.com/download?id=1"


def test_resolve_download_url_rejects_unavailable_quality(caplog):
    video = VideoData(
        title="Example",
        video_id="video-1",
        platform="youku",
        m3u8_url="https://media.example.com/playlist.m3u8",
        quality_options=["1080p", "720p"],
    )

    with caplog.at_level(logging.ERROR):
        download_url = video_downloader.resolve_download_url(
            video,
            requested_quality="480p",
            logger=logging.getLogger(__name__),
        )

    assert download_url is None
    assert "请求的质量不可用" in caplog.text


def test_convert_gif_uses_output_file_instead_of_extracting_frames(monkeypatch):
    calls = []

    class FakeTools:
        def create_gif(self, input_file, output_file, frame_rate=10):
            calls.append(("create_gif", input_file, output_file, frame_rate))
            return True

        def extract_frames(self, *args, **kwargs):
            calls.append(("extract_frames", args, kwargs))
            return ["frame_000001.jpg"]

    monkeypatch.setattr(video_downloader, "create_ffmpeg_tools", lambda config_path=None: FakeTools())
    monkeypatch.setattr(
        sys,
        "argv",
        ["pyspider", "convert", "input.mp4", "output.gif", "-f", "gif", "--fps", "12"],
    )

    exit_code = video_downloader.main()

    assert exit_code == 0
    assert calls == [("create_gif", "input.mp4", "output.gif", 12)]


def test_convert_avi_uses_generic_video_conversion(monkeypatch):
    calls = []

    class FakeTools:
        def convert_format(self, input_file, output_file, output_format="mp4", video_codec="libx264", audio_codec="aac", crf=23, preset="medium"):
            calls.append(
                (
                    "convert_format",
                    input_file,
                    output_file,
                    output_format,
                    video_codec,
                    audio_codec,
                    crf,
                    preset,
                )
            )
            return True

    monkeypatch.setattr(video_downloader, "create_ffmpeg_tools", lambda config_path=None: FakeTools())
    monkeypatch.setattr(
        sys,
        "argv",
        ["pyspider", "convert", "input.flv", "output.avi", "-f", "avi"],
    )

    exit_code = video_downloader.main()

    assert exit_code == 0
    assert calls == [
        ("convert_format", "input.flv", "output.avi", "avi", "libx264", "aac", 23, "medium")
    ]


def test_screenshot_batch_defaults_output_directory(monkeypatch):
    calls = []

    class FakeTools:
        def take_screenshots_batch(self, input_file, output_dir, interval=60, width=None):
            calls.append((input_file, output_dir, interval, width))
            return [str(Path(output_dir) / "screenshot_0000.jpg")]

    monkeypatch.setattr(video_downloader, "create_ffmpeg_tools", lambda config_path=None: FakeTools())
    monkeypatch.setattr(
        sys,
        "argv",
        ["pyspider", "screenshot", "input.mp4", "--batch", "--interval", "30"],
    )

    exit_code = video_downloader.main()

    assert exit_code == 0
    assert calls == [("input.mp4", "screenshots", 30, None)]


def test_screenshot_batch_returns_non_zero_when_no_images_are_generated(monkeypatch):
    class FakeTools:
        def take_screenshots_batch(self, input_file, output_dir, interval=60, width=None):
            return []

    monkeypatch.setattr(video_downloader, "create_ffmpeg_tools", lambda config_path=None: FakeTools())
    monkeypatch.setattr(
        sys,
        "argv",
        ["pyspider", "screenshot", "input.mp4", "--batch"],
    )

    exit_code = video_downloader.main()

    assert exit_code == 1


def test_screenshot_batch_rejects_non_positive_interval(monkeypatch):
    class FakeTools:
        def take_screenshots_batch(self, input_file, output_dir, interval=60, width=None):
            raise AssertionError("should not be called")

    monkeypatch.setattr(video_downloader, "create_ffmpeg_tools", lambda config_path=None: FakeTools())
    monkeypatch.setattr(
        sys,
        "argv",
        ["pyspider", "screenshot", "input.mp4", "--batch", "--interval", "0"],
    )

    exit_code = video_downloader.main()

    assert exit_code == 1


def test_download_with_convert_gif_uses_create_gif_after_hls_download(monkeypatch, tmp_path):
    calls = []

    class FakeParser:
        def parse(self, url):
            return VideoData(
                title="Example",
                video_id="video-1",
                platform="youku",
                m3u8_url="https://media.example.com/playlist.m3u8",
            )

    class FakeDownloader:
        def __init__(self, output_dir, max_workers, retry_times):
            calls.append(("hls_init", output_dir, max_workers, retry_times))

        def download(self, download_url, output_name):
            calls.append(("hls_download", download_url, output_name))
            return True

    class FakeTools:
        def create_gif(self, input_file, output_file, frame_rate=10):
            calls.append(("create_gif", input_file, output_file, frame_rate))
            return True

        def convert_format(self, *args, **kwargs):
            calls.append(("convert_format", args, kwargs))
            return True

        def extract_audio(self, *args, **kwargs):
            calls.append(("extract_audio", args, kwargs))
            return True

    monkeypatch.setattr(video_downloader, "UniversalParser", lambda: FakeParser())
    monkeypatch.setattr(video_downloader, "HLSDownloader", FakeDownloader)
    monkeypatch.setattr(video_downloader, "create_ffmpeg_tools", lambda config_path=None: FakeTools())
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "pyspider",
            "download",
            "https://example.com/watch/1",
            "--output-dir",
            str(tmp_path),
            "--convert",
            "gif",
        ],
    )

    exit_code = video_downloader.main()

    assert exit_code == 0
    assert ("hls_download", "https://media.example.com/playlist.m3u8", "video-1") in calls
    assert ("create_gif", str(tmp_path / "video-1.ts"), str(tmp_path / "video-1.gif"), 10) in calls


def test_download_with_convert_gif_uses_create_gif_after_direct_mp4_download(monkeypatch, tmp_path):
    calls = []

    class FakeParser:
        def parse(self, url):
            return VideoData(
                title="Example",
                video_id="video-2",
                platform="youku",
                mp4_url="https://media.example.com/video.mp4",
            )

    class FakeResponse:
        headers = {"content-length": "4"}

        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size):
            yield b"data"

    class FakeTools:
        def create_gif(self, input_file, output_file, frame_rate=10):
            calls.append(("create_gif", input_file, output_file, frame_rate))
            return True

        def convert_format(self, *args, **kwargs):
            calls.append(("convert_format", args, kwargs))
            return True

        def extract_audio(self, *args, **kwargs):
            calls.append(("extract_audio", args, kwargs))
            return True

    monkeypatch.setattr(video_downloader, "UniversalParser", lambda: FakeParser())
    monkeypatch.setattr(video_downloader, "create_ffmpeg_tools", lambda config_path=None: FakeTools())
    monkeypatch.setitem(
        sys.modules,
        "requests",
        types.SimpleNamespace(get=lambda *args, **kwargs: FakeResponse()),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "pyspider",
            "download",
            "https://example.com/watch/2",
            "--output-dir",
            str(tmp_path),
            "--convert",
            "gif",
        ],
    )

    exit_code = video_downloader.main()

    assert exit_code == 0
    assert ("create_gif", str(tmp_path / "video-2.mp4"), str(tmp_path / "video-2.gif"), 10) in calls


def test_download_returns_non_zero_when_post_download_conversion_fails(monkeypatch, tmp_path):
    class FakeParser:
        def parse(self, url):
            return VideoData(
                title="Example",
                video_id="video-3",
                platform="youku",
                m3u8_url="https://media.example.com/playlist.m3u8",
            )

    class FakeDownloader:
        def __init__(self, output_dir, max_workers, retry_times):
            pass

        def download(self, download_url, output_name):
            return True

    class FakeTools:
        def create_gif(self, input_file, output_file, frame_rate=10):
            return False

    monkeypatch.setattr(video_downloader, "UniversalParser", lambda: FakeParser())
    monkeypatch.setattr(video_downloader, "HLSDownloader", FakeDownloader)
    monkeypatch.setattr(video_downloader, "create_ffmpeg_tools", lambda config_path=None: FakeTools())
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "pyspider",
            "download",
            "https://example.com/watch/3",
            "--output-dir",
            str(tmp_path),
            "--convert",
            "gif",
        ],
    )

    exit_code = video_downloader.main()

    assert exit_code == 1


def test_dash_download_with_convert_gif_uses_create_gif_after_dash_download(monkeypatch, tmp_path):
    calls = []

    class FakeParser:
        def parse(self, url):
            return VideoData(
                title="Example",
                video_id="video-4",
                platform="youku",
                dash_url="https://media.example.com/manifest.mpd",
            )

    class FakeDownloader:
        def __init__(self, output_dir, max_workers):
            calls.append(("dash_init", output_dir, max_workers))

        def download(self, download_url, output_name):
            calls.append(("dash_download", download_url, output_name))
            return True

    class FakeTools:
        def create_gif(self, input_file, output_file, frame_rate=10):
            calls.append(("create_gif", input_file, output_file, frame_rate))
            return True

    monkeypatch.setattr(video_downloader, "UniversalParser", lambda: FakeParser())
    monkeypatch.setattr(video_downloader, "DASHDownloader", FakeDownloader)
    monkeypatch.setattr(video_downloader, "create_ffmpeg_tools", lambda config_path=None: FakeTools())
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "pyspider",
            "download",
            "https://example.com/watch/4",
            "--output-dir",
            str(tmp_path),
            "--convert",
            "gif",
        ],
    )

    exit_code = video_downloader.main()

    assert exit_code == 0
    assert ("dash_download", "https://media.example.com/manifest.mpd", "video-4") in calls
    assert ("create_gif", str(tmp_path / "video-4.mp4"), str(tmp_path / "video-4.gif"), 10) in calls
