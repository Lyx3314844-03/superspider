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
}
