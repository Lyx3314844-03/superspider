package com.javaspider.media.parser;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class GenericParserTest {

    @Test
    void parseHtmlDiscoversVideoObjectAndManifestUrls() {
        String html = """
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
                <video><source src="/dash/manifest.mpd" /></video>
              </body>
            </html>
            """;

        GenericParser parser = new GenericParser();
        VideoInfo info = parser.parseHtml("https://example.com/watch/demo", html, new VideoInfo());

        assertEquals("Universal Fixture", info.getTitle());
        assertEquals("fixture description", info.getDescription());
        assertEquals("https://example.com/cover.jpg", info.getCoverUrl());
        assertTrue(info.getVideoUrls().contains("https://example.com/streams/master.m3u8"));
        assertTrue(info.getVideoUrls().contains("https://example.com/dash/manifest.mpd"));
        assertTrue(info.getVideoUrls().contains("https://cdn.example.com/video.mp4"));
        assertEquals("https://example.com/streams/master.m3u8", info.getVideoUrl());
    }

    @Test
    void parseArtifactsDiscoversMediaFromNetworkPayload() {
        GenericParser parser = new GenericParser();
        VideoInfo info = parser.parseArtifacts(
            "https://example.com/watch/demo",
            "",
            java.util.List.of(
                """
                {
                  "player": {
                    "videoUrl": "https://cdn.example.com/direct.mp4",
                    "dashUrl": "https://cdn.example.com/manifest.mpd"
                  }
                }
                """
            )
        );

        assertTrue(info.getVideoUrls().contains("https://cdn.example.com/direct.mp4"));
        assertTrue(info.getVideoUrls().contains("https://cdn.example.com/manifest.mpd"));
        assertEquals("https://cdn.example.com/direct.mp4", info.getVideoUrl());
    }

    @Test
    void parseArtifactsDetectsBilibiliSurface() {
        GenericParser parser = new GenericParser();
        VideoInfo info = parser.parseArtifacts(
            "https://www.bilibili.com/video/BV1demo",
            """
            <html><head><title>示例 B站视频 - 哔哩哔哩</title></head><body>
              <script>
                {
                  "duration": 321,
                  "cover": "https://img.example.com/bili-cover.jpg",
                  "desc": "B站描述",
                  "baseUrl": "https://media.example.com/video.m4s"
                }
              </script>
            </body></html>
            """,
            java.util.List.of()
        );

        assertEquals("Bilibili", info.getPlatform());
        assertEquals("BV1demo", info.getVideoId());
        assertTrue(info.getVideoUrls().contains("https://media.example.com/video.m4s"));
        assertEquals("https://img.example.com/bili-cover.jpg", info.getCoverUrl());
        assertEquals(321, info.getDuration());
    }

    @Test
    void parseArtifactsDetectsIqiyiSurface() {
        GenericParser parser = new GenericParser();
        VideoInfo info = parser.parseArtifacts(
            "https://www.iqiyi.com/v_19rrdemo.html",
            """
            <html><head><title>示例爱奇艺 - 爱奇艺</title></head><body>
              <meta property="og:image" content="https://img.example.com/iqiyi-cover.jpg" />
              <script>
                {
                  "duration": 88,
                  "m3u8Url": "https://media.example.com/master.m3u8",
                  "dashUrl": "https://media.example.com/manifest.mpd"
                }
              </script>
            </body></html>
            """,
            java.util.List.of()
        );

        assertEquals("IQIYI", info.getPlatform());
        assertEquals("19rrdemo", info.getVideoId());
        assertTrue(info.getVideoUrls().contains("https://media.example.com/master.m3u8"));
        assertTrue(info.getVideoUrls().contains("https://media.example.com/manifest.mpd"));
        assertEquals("https://img.example.com/iqiyi-cover.jpg", info.getCoverUrl());
        assertEquals(88, info.getDuration());
    }

    @Test
    void parseArtifactsDetectsTencentSurface() {
        GenericParser parser = new GenericParser();
        VideoInfo info = parser.parseArtifacts(
            "https://v.qq.com/x/page/demo123.html",
            """
            <html><head><title>示例腾讯视频 - 腾讯视频</title></head><body>
              <script>
                {
                  "duration": 45,
                  "pic": "https://img.example.com/tencent-cover.jpg",
                  "url": "https://media.example.com/tencent.mp4"
                }
              </script>
            </body></html>
            """,
            java.util.List.of()
        );

        assertEquals("Tencent", info.getPlatform());
        assertEquals("demo123", info.getVideoId());
        assertTrue(info.getVideoUrls().contains("https://media.example.com/tencent.mp4"));
        assertEquals("https://img.example.com/tencent-cover.jpg", info.getCoverUrl());
        assertEquals(45, info.getDuration());
    }

    @Test
    void parseArtifactsDetectsYoukuSurface() {
        GenericParser parser = new GenericParser();
        VideoInfo info = parser.parseArtifacts(
            "https://v.youku.com/v_show/id_Xdemo=.html",
            """
            <html><head><title>示例优酷 - 优酷</title></head><body>
              <meta property="og:image" content="https://img.example.com/youku-cover.jpg" />
              <script>
                {
                  "poster": "https://img.example.com/youku-poster.jpg",
                  "m3u8Url": "https://media.example.com/youku/master.m3u8"
                }
              </script>
            </body></html>
            """,
            java.util.List.of()
        );

        assertEquals("Youku", info.getPlatform());
        assertEquals("Xdemo=", info.getVideoId());
        assertTrue(info.getVideoUrls().contains("https://media.example.com/youku/master.m3u8"));
        assertEquals("https://img.example.com/youku-cover.jpg", info.getCoverUrl());
    }

    @Test
    void parseArtifactsCollectsAudioUrlsAndDrmSignals() {
        GenericParser parser = new GenericParser();
        VideoInfo info = parser.parseArtifacts(
            "https://example.com/watch/demo",
            """
            <html><head><title>Audio Fixture</title></head><body>
              <audio src="/tracks/theme.m4a"></audio>
            </body></html>
            """,
            java.util.List.of(
                """
                #EXTM3U
                #EXT-X-KEY:METHOD=SAMPLE-AES,URI="https://license.example.com/widevine"
                #EXTINF:4.0,
                https://media.example.com/segment.ts
                """
            )
        );

        assertTrue(info.getAudioUrls().contains("https://example.com/tracks/theme.m4a"));
        assertTrue(info.isDRMProtected());
    }

    @Test
    void parseArtifactsDetectsDouyinSurface() {
        GenericParser parser = new GenericParser();
        VideoInfo info = parser.parseArtifacts(
            "https://www.douyin.com/video/123456789",
            """
            <html><head><title>示例抖音 - 抖音</title></head><body>
              <script>
                {
                  "duration": 18,
                  "dynamic_cover": "https://img.example.com/dy.jpg",
                  "desc": "抖音描述",
                  "playAddr": "https://media.example.com/douyin.mp4"
                }
              </script>
            </body></html>
            """,
            java.util.List.of()
        );

        assertEquals("Douyin", info.getPlatform());
        assertEquals("123456789", info.getVideoId());
        assertTrue(info.getVideoUrls().contains("https://media.example.com/douyin.mp4"));
        assertEquals("https://img.example.com/dy.jpg", info.getCoverUrl());
        assertEquals(18, info.getDuration());
    }
}
