from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pyspider.media.hls_downloader import DASHDownloader, DASHParser


def test_dash_parser_extracts_segment_list_initialization():
    parser = DASHParser()
    mpd = """<?xml version="1.0" encoding="UTF-8"?>
<MPD xmlns="urn:mpeg:dash:schema:mpd:2011">
  <Period>
    <AdaptationSet mimeType="video/mp4">
      <Representation id="video-1" bandwidth="1000" width="1280" height="720">
        <SegmentList>
          <Initialization sourceURL="init.mp4" />
          <SegmentURL media="seg-1.m4s" />
          <SegmentURL media="seg-2.m4s" />
        </SegmentList>
      </Representation>
    </AdaptationSet>
  </Period>
</MPD>
"""

    parsed = parser.parse_mpd(mpd, "https://media.example.com/")
    representation = parsed["periods"][0]["adaptations"][0]["representations"][0]

    assert representation["initialization"] == "init.mp4"
    assert representation["segments"] == [
        {"media": "seg-1.m4s", "media_range": None},
        {"media": "seg-2.m4s", "media_range": None},
    ]


def test_dash_downloader_merges_initialization_and_segments_into_output_file(tmp_path):
    class FakeResponse:
        def __init__(self, text="", content=b""):
            self.text = text
            self.content = content

        def raise_for_status(self):
            return None

    downloader = DASHDownloader(output_dir=str(tmp_path))
    downloader.parser.parse_mpd = lambda content, base_url: {
        "periods": [
            {
                "adaptations": [
                    {
                        "mimeType": "video/mp4",
                        "representations": [
                            {
                                "id": "video-1",
                                "bandwidth": "1000",
                                "width": "1280",
                                "height": "720",
                                "initialization": "init.mp4",
                                "segments": [
                                    {"media": "seg-1.m4s", "media_range": None},
                                    {"media": "seg-2.m4s", "media_range": None},
                                ],
                            }
                        ],
                    }
                ]
            }
        ]
    }

    def fake_get(url, timeout):
        if url.endswith(".mpd"):
            return FakeResponse(text="<MPD />")
        if url.endswith("init.mp4"):
            return FakeResponse(content=b"INIT")
        if url.endswith("seg-1.m4s"):
            return FakeResponse(content=b"AAA")
        if url.endswith("seg-2.m4s"):
            return FakeResponse(content=b"BBB")
        raise AssertionError(url)

    downloader.session.get = fake_get

    success = downloader.download("https://media.example.com/manifest.mpd", "video-1")

    assert success is True
    assert (tmp_path / "video-1.mp4").read_bytes() == b"INITAAABBB"
    assert not (tmp_path / "video-1_temp").exists()


def test_dash_downloader_fails_when_any_required_segment_is_missing(tmp_path):
    class FakeResponse:
        def __init__(self, text="", content=b"", error=None):
            self.text = text
            self.content = content
            self._error = error

        def raise_for_status(self):
            if self._error:
                raise self._error
            return None

    downloader = DASHDownloader(output_dir=str(tmp_path))
    downloader.parser.parse_mpd = lambda content, base_url: {
        "periods": [
            {
                "adaptations": [
                    {
                        "mimeType": "video/mp4",
                        "representations": [
                            {
                                "id": "video-1",
                                "bandwidth": "1000",
                                "initialization": "init.mp4",
                                "segments": [
                                    {"media": "seg-1.m4s", "media_range": None},
                                    {"media": "seg-2.m4s", "media_range": None},
                                ],
                            }
                        ],
                    }
                ]
            }
        ]
    }

    def fake_get(url, timeout):
        if url.endswith(".mpd"):
            return FakeResponse(text="<MPD />")
        if url.endswith("init.mp4"):
            return FakeResponse(content=b"INIT")
        if url.endswith("seg-1.m4s"):
            return FakeResponse(content=b"AAA")
        if url.endswith("seg-2.m4s"):
            return FakeResponse(error=RuntimeError("missing segment"))
        raise AssertionError(url)

    downloader.session.get = fake_get

    success = downloader.download("https://media.example.com/manifest.mpd", "video-2")

    assert success is False
    assert not (tmp_path / "video-2.mp4").exists()


def test_dash_downloader_supports_static_segment_template_urls(tmp_path):
    class FakeResponse:
        def __init__(self, text="", content=b""):
            self.text = text
            self.content = content

        def raise_for_status(self):
            return None

    mpd = """<?xml version="1.0" encoding="UTF-8"?>
<MPD xmlns="urn:mpeg:dash:schema:mpd:2011" type="static">
  <Period duration="PT6S">
    <AdaptationSet mimeType="video/mp4">
      <Representation id="video-1" bandwidth="1000" width="1280" height="720">
        <SegmentTemplate
          initialization="init-$RepresentationID$.mp4"
          media="chunk-$RepresentationID$-$Number%04d$.m4s"
          startNumber="1"
          timescale="1"
          duration="2" />
      </Representation>
    </AdaptationSet>
  </Period>
</MPD>
"""

    downloader = DASHDownloader(output_dir=str(tmp_path))

    def fake_get(url, timeout):
        if url.endswith(".mpd"):
            return FakeResponse(text=mpd)
        if url.endswith("init-video-1.mp4"):
            return FakeResponse(content=b"INIT")
        if url.endswith("chunk-video-1-0001.m4s"):
            return FakeResponse(content=b"AAA")
        if url.endswith("chunk-video-1-0002.m4s"):
            return FakeResponse(content=b"BBB")
        if url.endswith("chunk-video-1-0003.m4s"):
            return FakeResponse(content=b"CCC")
        raise AssertionError(url)

    downloader.session.get = fake_get

    success = downloader.download("https://media.example.com/manifest.mpd", "video-3")

    assert success is True
    assert (tmp_path / "video-3.mp4").read_bytes() == b"INITAAABBBCCC"


def test_dash_downloader_rounds_segment_template_count_up_for_partial_tail_segment(tmp_path):
    class FakeResponse:
        def __init__(self, text="", content=b""):
            self.text = text
            self.content = content

        def raise_for_status(self):
            return None

    mpd = """<?xml version="1.0" encoding="UTF-8"?>
<MPD xmlns="urn:mpeg:dash:schema:mpd:2011" type="static">
  <Period duration="PT5S">
    <AdaptationSet mimeType="video/mp4">
      <Representation id="video-1" bandwidth="1000" width="1280" height="720">
        <SegmentTemplate
          initialization="init-$RepresentationID$.mp4"
          media="chunk-$RepresentationID$-$Number%04d$.m4s"
          startNumber="1"
          timescale="1"
          duration="2" />
      </Representation>
    </AdaptationSet>
  </Period>
</MPD>
"""

    downloader = DASHDownloader(output_dir=str(tmp_path))

    def fake_get(url, timeout):
        if url.endswith(".mpd"):
            return FakeResponse(text=mpd)
        if url.endswith("init-video-1.mp4"):
            return FakeResponse(content=b"INIT")
        if url.endswith("chunk-video-1-0001.m4s"):
            return FakeResponse(content=b"AAA")
        if url.endswith("chunk-video-1-0002.m4s"):
            return FakeResponse(content=b"BBB")
        if url.endswith("chunk-video-1-0003.m4s"):
            return FakeResponse(content=b"CCC")
        raise AssertionError(url)

    downloader.session.get = fake_get

    success = downloader.download("https://media.example.com/manifest.mpd", "video-4")

    assert success is True
    assert (tmp_path / "video-4.mp4").read_bytes() == b"INITAAABBBCCC"


def test_dash_downloader_downloads_audio_track_and_muxes_with_video(tmp_path, monkeypatch):
    class FakeResponse:
        def __init__(self, text=""):
            self.text = text

        def raise_for_status(self):
            return None

    downloader = DASHDownloader(output_dir=str(tmp_path))
    downloader.parser.parse_mpd = lambda content, base_url: {
        "periods": [
            {
                "adaptations": [
                    {
                        "mimeType": "video/mp4",
                        "representations": [
                            {
                                "id": "video-1",
                                "bandwidth": "1000",
                                "initialization": "video-init.mp4",
                                "segments": [{"media": "video-seg-1.m4s", "media_range": None}],
                            }
                        ],
                    },
                    {
                        "mimeType": "audio/mp4",
                        "representations": [
                            {
                                "id": "audio-1",
                                "bandwidth": "128",
                                "initialization": "audio-init.mp4",
                                "segments": [{"media": "audio-seg-1.m4s", "media_range": None}],
                            }
                        ],
                    },
                ]
            }
        ]
    }

    calls = []

    def fake_get(url, timeout):
        assert url.endswith(".mpd")
        return FakeResponse(text="<MPD />")

    def fake_download(rep, base_url, output_dir):
        output_dir.mkdir(parents=True, exist_ok=True)
        calls.append(("download", rep["id"], output_dir.name))
        (output_dir / "init.mp4").write_bytes(f"INIT-{rep['id']}".encode())
        (output_dir / "000000.m4s").write_bytes(f"SEG-{rep['id']}".encode())
        return True

    def fake_mux(video_file, audio_file, output_file):
        calls.append(("mux", video_file.name, audio_file.name, output_file.name))
        output_file.write_bytes(video_file.read_bytes() + b"|" + audio_file.read_bytes())
        return True

    monkeypatch.setattr(downloader.session, "get", fake_get)
    monkeypatch.setattr(downloader, "_download_dash_segments", fake_download)
    monkeypatch.setattr(downloader, "_mux_dash_tracks", fake_mux, raising=False)

    success = downloader.download("https://media.example.com/manifest.mpd", "video-5")

    assert success is True
    assert ("download", "video-1", "video") in calls
    assert ("download", "audio-1", "audio") in calls
    assert ("mux", "video.mp4", "audio.mp4", "video-5.mp4") in calls
    assert (tmp_path / "video-5.mp4").read_bytes() == b"INIT-video-1SEG-video-1|INIT-audio-1SEG-audio-1"
    assert not (tmp_path / "video-5_temp").exists()


def test_dash_downloader_returns_false_when_audio_mux_fails(tmp_path, monkeypatch):
    class FakeResponse:
        def __init__(self, text=""):
            self.text = text

        def raise_for_status(self):
            return None

    downloader = DASHDownloader(output_dir=str(tmp_path))
    downloader.parser.parse_mpd = lambda content, base_url: {
        "periods": [
            {
                "adaptations": [
                    {
                        "mimeType": "video/mp4",
                        "representations": [
                            {
                                "id": "video-1",
                                "bandwidth": "1000",
                                "initialization": "video-init.mp4",
                                "segments": [{"media": "video-seg-1.m4s", "media_range": None}],
                            }
                        ],
                    },
                    {
                        "mimeType": "audio/mp4",
                        "representations": [
                            {
                                "id": "audio-1",
                                "bandwidth": "128",
                                "initialization": "audio-init.mp4",
                                "segments": [{"media": "audio-seg-1.m4s", "media_range": None}],
                            }
                        ],
                    },
                ]
            }
        ]
    }

    def fake_get(url, timeout):
        assert url.endswith(".mpd")
        return FakeResponse(text="<MPD />")

    def fake_download(rep, base_url, output_dir):
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "init.mp4").write_bytes(b"INIT")
        (output_dir / "000000.m4s").write_bytes(b"SEG")
        return True

    def fake_mux(video_file, audio_file, output_file):
        return False

    monkeypatch.setattr(downloader.session, "get", fake_get)
    monkeypatch.setattr(downloader, "_download_dash_segments", fake_download)
    monkeypatch.setattr(downloader, "_mux_dash_tracks", fake_mux, raising=False)

    success = downloader.download("https://media.example.com/manifest.mpd", "video-6")

    assert success is False
    assert not (tmp_path / "video-6.mp4").exists()
    assert not (tmp_path / "video-6_temp").exists()


def test_dash_downloader_accepts_content_type_when_mime_type_is_missing(tmp_path):
    class FakeResponse:
        def __init__(self, text="", content=b""):
            self.text = text
            self.content = content

        def raise_for_status(self):
            return None

    mpd = """<?xml version="1.0" encoding="UTF-8"?>
<MPD xmlns="urn:mpeg:dash:schema:mpd:2011">
  <Period>
    <AdaptationSet contentType="video">
      <Representation id="video-1" bandwidth="1000" width="1280" height="720">
        <SegmentList>
          <Initialization sourceURL="init.mp4" />
          <SegmentURL media="seg-1.m4s" />
        </SegmentList>
      </Representation>
    </AdaptationSet>
  </Period>
</MPD>
"""

    downloader = DASHDownloader(output_dir=str(tmp_path))

    def fake_get(url, timeout):
        if url.endswith(".mpd"):
            return FakeResponse(text=mpd)
        if url.endswith("init.mp4"):
            return FakeResponse(content=b"INIT")
        if url.endswith("seg-1.m4s"):
            return FakeResponse(content=b"AAA")
        raise AssertionError(url)

    downloader.session.get = fake_get

    success = downloader.download("https://media.example.com/manifest.mpd", "video-7")

    assert success is True
    assert (tmp_path / "video-7.mp4").read_bytes() == b"INITAAA"


def test_dash_downloader_supports_adaptation_set_level_segment_template(tmp_path):
    class FakeResponse:
        def __init__(self, text="", content=b""):
            self.text = text
            self.content = content

        def raise_for_status(self):
            return None

    mpd = """<?xml version="1.0" encoding="UTF-8"?>
<MPD xmlns="urn:mpeg:dash:schema:mpd:2011" type="static">
  <Period duration="PT4S">
    <AdaptationSet mimeType="video/mp4">
      <SegmentTemplate
        initialization="init-$RepresentationID$.mp4"
        media="chunk-$RepresentationID$-$Number%04d$.m4s"
        startNumber="1"
        timescale="1"
        duration="2" />
      <Representation id="video-1" bandwidth="1000" width="1280" height="720" />
    </AdaptationSet>
  </Period>
</MPD>
"""

    downloader = DASHDownloader(output_dir=str(tmp_path))

    def fake_get(url, timeout):
        if url.endswith(".mpd"):
            return FakeResponse(text=mpd)
        if url.endswith("init-video-1.mp4"):
            return FakeResponse(content=b"INIT")
        if url.endswith("chunk-video-1-0001.m4s"):
            return FakeResponse(content=b"AAA")
        if url.endswith("chunk-video-1-0002.m4s"):
            return FakeResponse(content=b"BBB")
        raise AssertionError(url)

    downloader.session.get = fake_get

    success = downloader.download("https://media.example.com/manifest.mpd", "video-8")

    assert success is True
    assert (tmp_path / "video-8.mp4").read_bytes() == b"INITAAABBB"
