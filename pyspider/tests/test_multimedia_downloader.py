from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pyspider.media.multimedia_downloader import (
    BilibiliMultiMediaSpider,
    DouyinMultiMediaSpider,
    IqiyiMultiMediaSpider,
    MultiMediaSpider,
    TencentMultiMediaSpider,
    YoukuMultiMediaSpider,
    create_multimedia_spider,
)
from pyspider.media.video_parser import VideoData, _discover_video_data_from_html


class FakeResponse:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        return None


def test_multimedia_spider_extracts_generic_media_urls():
    html = """
    <html>
      <head>
        <title>Demo Gallery</title>
        <meta property="og:image" content="/cover.jpg" />
        <meta property="og:video" content="https://cdn.example.com/hero.mp4" />
      </head>
      <body>
        <video src="/movie.mp4"></video>
        <audio src="/sound.mp3"></audio>
        <img src="/image-a.png" />
        <img src="https://cdn.example.com/image-b.webp" />
        <a href="/download/theme.flac">Download</a>
      </body>
    </html>
    """

    spider = MultiMediaSpider(["https://example.com/page"])
    spider.downloader.session.get = lambda url, timeout=30: FakeResponse(html)

    videos = spider.crawl_videos()
    images = spider.crawl_images()
    audios = spider.crawl_audios()

    assert [video.url for video in videos] == [
        "https://cdn.example.com/hero.mp4",
        "https://example.com/movie.mp4",
    ]
    assert [image.url for image in images] == [
        "https://example.com/cover.jpg",
        "https://example.com/image-a.png",
        "https://cdn.example.com/image-b.webp",
    ]
    assert [audio.url for audio in audios] == [
        "https://example.com/sound.mp3",
        "https://example.com/download/theme.flac",
    ]


def test_multimedia_spider_handles_fetch_failures():
    spider = MultiMediaSpider(["https://example.com/page"])

    def fail(*args, **kwargs):
        raise RuntimeError("network down")

    spider.downloader.session.get = fail

    assert spider.crawl_videos() == []
    assert spider.crawl_images() == []
    assert spider.crawl_audios() == []


def test_universal_video_parser_discovers_video_object_and_manifest_urls():
    html = """
    <html>
      <head>
        <title>Fallback Title</title>
        <meta property="og:video" content="/streams/master.m3u8" />
        <meta property="og:image" content="/cover.jpg" />
        <script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@type": "VideoObject",
          "name": "Universal Fixture",
          "description": "fixture description",
          "contentUrl": "https://cdn.example.com/video.mp4",
          "thumbnailUrl": "https://cdn.example.com/poster.png"
        }
        </script>
      </head>
      <body>
        <video>
          <source src="/dash/manifest.mpd" />
        </video>
      </body>
    </html>
    """

    video = _discover_video_data_from_html("https://example.com/watch/demo", html)

    assert video is not None
    assert video.title == "Universal Fixture"
    assert video.description == "fixture description"
    assert video.m3u8_url == "https://example.com/streams/master.m3u8"
    assert video.dash_url == "https://example.com/dash/manifest.mpd"
    assert video.mp4_url == "https://cdn.example.com/video.mp4"
    assert video.cover_url == "https://example.com/cover.jpg"


def test_universal_video_parser_discovers_media_from_artifact_payloads():
    from pyspider.media.video_parser import UniversalParser

    parser = UniversalParser()
    video = parser.parse_artifacts(
        "https://example.com/watch/demo",
        artifact_texts=[
            """
            {
              "player": {
                "videoUrl": "https://cdn.example.com/direct.mp4",
                "dashUrl": "https://cdn.example.com/manifest.mpd"
              }
            }
            """
        ],
    )

    assert video is not None
    assert video.mp4_url == "https://cdn.example.com/direct.mp4"
    assert video.dash_url == "https://cdn.example.com/manifest.mpd"


def test_multimedia_factory_selects_platform_specific_spider():
    assert isinstance(
        create_multimedia_spider(["https://v.youku.com/v_show/id_demo.html"]),
        YoukuMultiMediaSpider,
    )
    assert isinstance(
        create_multimedia_spider(["https://www.iqiyi.com/v_demo.html"]),
        IqiyiMultiMediaSpider,
    )
    assert isinstance(
        create_multimedia_spider(["https://v.qq.com/x/page/demo.html"]),
        TencentMultiMediaSpider,
    )
    assert isinstance(
        create_multimedia_spider(["https://www.bilibili.com/video/BV1xx411c7mD"]),
        BilibiliMultiMediaSpider,
    )
    assert isinstance(
        create_multimedia_spider(["https://www.douyin.com/video/1234567890"]),
        DouyinMultiMediaSpider,
    )


def test_youku_multimedia_spider_uses_platform_parser(monkeypatch):
    monkeypatch.setattr(
        "pyspider.media.video_parser.YoukuParser.parse",
        lambda self, url: VideoData(
            title="Fixture Youku",
            video_id="youku123",
            platform="youku",
            m3u8_url="https://media.example.com/master.m3u8",
            cover_url="https://static.example.com/cover.jpg",
            duration=180,
            description="fixture description",
            quality_options=["1080p", "720p"],
        ),
    )

    spider = YoukuMultiMediaSpider(["https://v.youku.com/v_show/id_demo.html"])
    videos = spider.crawl_videos()
    images = spider.crawl_images()
    audios = spider.crawl_audios()

    assert len(videos) == 1
    assert videos[0].title == "Fixture Youku"
    assert videos[0].url == "https://media.example.com/master.m3u8"
    assert videos[0].format == "hls"
    assert videos[0].quality == "1080p, 720p"
    assert [image.url for image in images] == ["https://static.example.com/cover.jpg"]
    assert [audio.url for audio in audios] == ["https://media.example.com/master.m3u8"]


def test_bilibili_multimedia_spider_uses_platform_parser(monkeypatch):
    monkeypatch.setattr(
        "pyspider.media.video_parser.BilibiliParser.parse",
        lambda self, url: VideoData(
            title="Fixture Bilibili",
            video_id="BV1demo",
            platform="bilibili",
            dash_url="https://media.example.com/video.mpd",
            cover_url="https://static.example.com/bili-cover.jpg",
            duration=99,
            description="bili fixture",
        ),
    )

    spider = BilibiliMultiMediaSpider(["https://www.bilibili.com/video/BV1demo"])
    videos = spider.crawl_videos()
    images = spider.crawl_images()
    audios = spider.crawl_audios()

    assert len(videos) == 1
    assert videos[0].format == "dash"
    assert videos[0].url == "https://media.example.com/video.mpd"
    assert [image.url for image in images] == [
        "https://static.example.com/bili-cover.jpg"
    ]
    assert [audio.url for audio in audios] == ["https://media.example.com/video.mpd"]


def test_iqiyi_parser_extracts_hls_and_dash(monkeypatch):
    from pyspider.media.video_parser import IqiyiParser

    html = """
    <html>
      <head>
        <title>示例爱奇艺 - 爱奇艺</title>
      </head>
      <body>
        <script>
          {
            "duration": 88,
            "m3u8Url": "https://media.example.com/master.m3u8",
            "dashUrl": "https://media.example.com/manifest.mpd"
          }
        </script>
      </body>
    </html>
    """

    parser = IqiyiParser()
    monkeypatch.setattr(parser.session, "get", lambda url, timeout=30: FakeResponse(html))

    video = parser.parse("https://www.iqiyi.com/v_19rrdemo.html")

    assert video is not None
    assert video.platform == "iqiyi"
    assert video.video_id == "19rrdemo"
    assert video.m3u8_url == "https://media.example.com/master.m3u8"
    assert video.dash_url == "https://media.example.com/manifest.mpd"


def test_tencent_parser_extracts_mp4_cover_and_duration(monkeypatch):
    from pyspider.media.video_parser import TencentParser

    html = """
    <html>
      <head>
        <title>示例腾讯视频 - 腾讯视频</title>
      </head>
      <body>
        <script>
          {
            "duration": 45,
            "pic": "https://img.example.com/tencent-cover.jpg",
            "url": "https://media.example.com/tencent.mp4"
          }
        </script>
      </body>
    </html>
    """

    parser = TencentParser()
    monkeypatch.setattr(parser.session, "get", lambda url, timeout=30: FakeResponse(html))

    video = parser.parse("https://v.qq.com/x/page/demo123.html")

    assert video is not None
    assert video.platform == "tencent"
    assert video.video_id == "demo123"
    assert video.mp4_url == "https://media.example.com/tencent.mp4"
    assert video.cover_url == "https://img.example.com/tencent-cover.jpg"
