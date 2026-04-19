package com.javaspider.cli;

import com.javaspider.media.parser.VideoInfo;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.Test;

import java.io.OutputStream;
import java.io.ByteArrayOutputStream;
import java.io.PrintStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class MediaDownloaderCLITest {

    @Test
    void printsHelpWhenNoArgumentsAreProvided() {
        String output = captureStdout(() -> MediaDownloaderCLI.main(new String[]{}));

        assertTrue(output.contains("MediaDownloader CLI v1.0.0"));
        assertTrue(output.contains("Usage: <command> [options]"));
    }

    @Test
    void printsVersionCommand() {
        String output = captureStdout(() -> MediaDownloaderCLI.main(new String[]{"version"}));

        assertTrue(output.contains("MediaDownloader CLI v1.0.0"));
    }

    @Test
    void youtubeInfoCommandUsesNonNullFallbackTitle() {
        String output = captureStdout(() ->
            MediaDownloaderCLI.main(new String[]{"info", "https://youtu.be/abc123"})
        );

        assertTrue(output.contains("Platform: YouTube"));
        assertFalse(output.contains("Title: null"));
        assertTrue(output.contains("Title: abc123"));
    }

    @Test
    void convertCommandWithoutEnoughArgumentsPrintsUsage() {
        String output = captureStdout(() ->
            MediaDownloaderCLI.main(new String[]{"convert", "input.mp4"})
        );

        assertTrue(output.contains("Usage: convert <input> <format>"));
    }

    @Test
    void convertCommandReportsMissingFFmpegDependency() {
        String output = captureStdoutWithProperty(
            MediaDownloaderCLI.FFMPEG_PATH_PROPERTY,
            "missing-ffmpeg-for-tests",
            () -> MediaDownloaderCLI.main(new String[]{"convert", "input.mp4", "avi"})
        );

        assertTrue(output.contains("FFmpeg dependency check failed for convert."));
        assertTrue(output.contains("missing or unusable at missing-ffmpeg-for-tests"));
    }

    @Test
    void mergeCommandReportsMissingFFmpegDependency() {
        String output = captureStdoutWithProperty(
            MediaDownloaderCLI.FFMPEG_PATH_PROPERTY,
            "missing-ffmpeg-for-tests",
            () -> MediaDownloaderCLI.main(new String[]{"merge", "output.mp4", "part1.mp4", "part2.mp4"})
        );

        assertTrue(output.contains("FFmpeg dependency check failed for merge."));
        assertTrue(output.contains("missing or unusable at missing-ffmpeg-for-tests"));
    }

    @Test
    void doctorCommandPrintsDependencyStatus() {
        String output = captureStdoutWithProperty(
            MediaDownloaderCLI.FFMPEG_PATH_PROPERTY,
            "missing-ffmpeg-for-tests",
            () -> MediaDownloaderCLI.main(new String[]{"doctor"})
        );

        assertTrue(output.contains("========== MediaDownloader Doctor =========="));
        assertTrue(output.contains("Java: "));
        assertTrue(output.contains("Working directory: "));
        assertTrue(output.contains("FFmpeg: missing or unusable at missing-ffmpeg-for-tests"));
    }

    @Test
    void doctorCommandCanRenderJson() {
        String output = captureStdoutWithProperty(
            MediaDownloaderCLI.FFMPEG_PATH_PROPERTY,
            "missing-ffmpeg-for-tests",
            () -> MediaDownloaderCLI.main(new String[]{"doctor", "--json"})
        ).trim();

        assertTrue(output.startsWith("{"));
        assertTrue(output.contains("\"command\":\"doctor\""));
        assertTrue(output.contains("\"runtime\":\"java\""));
        assertTrue(output.contains("\"exit_code\":1"));
        assertTrue(output.contains("\"name\":\"ffmpeg\""));
        assertTrue(output.contains("\"status\":\"failed\""));
        assertTrue(output.contains("\"details\":\"missing or unusable at missing-ffmpeg-for-tests"));
        assertTrue(output.contains("\"summary\":\"failed\""));
        assertEquals('}', output.charAt(output.length() - 1));
    }

    @Test
    void downloadCommandAudioOnlyReportsMissingFfmpegWhenTranscodeIsRequired() {
        String output = captureStdoutWithProperty(
            MediaDownloaderCLI.FFMPEG_PATH_PROPERTY,
            "missing-ffmpeg-for-tests",
            () -> MediaDownloaderCLI.main(new String[]{"download", "https://example.com/demo.mp4", "--audio-only"})
        );

        assertTrue(output.contains("Audio only: true"));
        assertTrue(output.contains("FFmpeg dependency check failed for audio-only."));
        assertTrue(output.contains("missing or unusable at missing-ffmpeg-for-tests"));
    }

    @Test
    void drmCommandDetectsProtectedM3u8FromInlineContent() {
        String output = captureStdout(() ->
            MediaDownloaderCLI.main(new String[]{
                "drm",
                "--content",
                "#EXTM3U\n#EXT-X-KEY:METHOD=SAMPLE-AES,URI=\"https://license.example.com/widevine\"\n#EXTINF:4.0,\nsegment.ts"
            })
        );

        assertTrue(output.contains("\"command\":\"drm\""));
        assertTrue(output.contains("\"protected\":true"));
        assertTrue(output.contains("\"drm_type\":\"WIDEVINE\""));
        assertTrue(output.contains("license.example.com/widevine"));
    }

    @Test
    void parseVideoInfoFallsBackToGenericParserForYoukuStyleUrl() throws Exception {
        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/youku/v_show/id_Xdemo=.html", exchange -> {
            byte[] body = """
                <html><head><title>Fixture Youku - 优酷</title></head><body>
                  <script>{"m3u8Url":"https://media.example.com/youku/master.m3u8"}</script>
                </body></html>
                """.getBytes(StandardCharsets.UTF_8);
            exchange.getResponseHeaders().add("Content-Type", "text/html; charset=utf-8");
            exchange.sendResponseHeaders(200, body.length);
            try (OutputStream out = exchange.getResponseBody()) {
                out.write(body);
            }
        });
        server.start();

        try {
            String url = "http://127.0.0.1:" + server.getAddress().getPort() + "/youku/v_show/id_Xdemo=.html";
            VideoInfo info = MediaDownloaderCLI.parseVideoInfo(url, true);

            assertEquals("Youku", info.getPlatform());
            assertEquals("Fixture Youku - 优酷", info.getTitle());
            assertTrue(info.getVideoUrls().contains("https://media.example.com/youku/master.m3u8"));
        } finally {
            server.stop(0);
        }
    }

    private String captureStdout(Runnable runnable) {
        PrintStream originalOut = System.out;
        ByteArrayOutputStream buffer = new ByteArrayOutputStream();

        try (PrintStream capture = new PrintStream(buffer, true, StandardCharsets.UTF_8)) {
            System.setOut(capture);
            runnable.run();
        } finally {
            System.setOut(originalOut);
        }

        return buffer.toString(StandardCharsets.UTF_8);
    }

    private String captureStdoutWithProperty(String key, String value, Runnable runnable) {
        String originalValue = System.getProperty(key);
        if (value == null) {
            System.clearProperty(key);
        } else {
            System.setProperty(key, value);
        }

        try {
            return captureStdout(runnable);
        } finally {
            if (originalValue == null) {
                System.clearProperty(key);
            } else {
                System.setProperty(key, originalValue);
            }
        }
    }
}
