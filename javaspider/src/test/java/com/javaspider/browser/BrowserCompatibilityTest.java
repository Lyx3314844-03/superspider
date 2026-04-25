package com.javaspider.browser;

import com.javaspider.cli.SuperSpiderCLI;
import org.junit.jupiter.api.Test;

import java.io.ByteArrayOutputStream;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.time.Duration;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class BrowserCompatibilityTest {

    @Test
    void describeReportsSeleniumAndPlaywrightSurfaces() {
        var payload = BrowserCompatibility.describe();
        @SuppressWarnings("unchecked")
        var surfaces = (java.util.Map<String, Object>) payload.get("surfaces");
        @SuppressWarnings("unchecked")
        var playwright = (java.util.Map<String, Object>) surfaces.get("playwright");
        @SuppressWarnings("unchecked")
        var selenium = (java.util.Map<String, Object>) surfaces.get("selenium");

        assertEquals("selenium-webdriver+node-playwright", payload.get("base_engine"));
        assertEquals("node-playwright", playwright.get("adapter_engine"));
        assertEquals("selenium-webdriver", selenium.get("adapter_engine"));
    }

    @Test
    void capabilitiesCommandIncludesBrowserCompatibilityMatrix() {
        String output = captureStdout(() ->
            SuperSpiderCLI.main(new String[]{"capabilities"})
        );

        assertTrue(output.contains("\"browser_compatibility\""));
        assertTrue(output.contains("\"node-playwright\""));
        assertTrue(output.contains("\"selenium-webdriver\""));
    }

    @Test
    void playwrightManagerBuildsNodeHelperCommand() {
        var manager = new PlaywrightBrowserManager(
            PlaywrightBrowserManager.Options.defaults()
                .withNodeCommand("node")
                .withHelperScript(Path.of("tools", "playwright_fetch.mjs"))
                .withUserAgent("FixtureBrowser/1.0")
                .withTimeout(Duration.ofSeconds(12))
        );

        var command = manager.buildCommandForTests(
            "https://example.com",
            Path.of("target", "browser", "page.png"),
            Path.of("target", "browser", "page.html")
        );
        String joined = String.join(" ", command);

        assertTrue(joined.contains("tools\\playwright_fetch.mjs") || joined.contains("tools/playwright_fetch.mjs"));
        assertTrue(joined.contains("--url https://example.com"));
        assertTrue(joined.contains("--timeout-seconds 12"));
        assertTrue(joined.contains("--headless"));
        assertTrue(joined.contains("--user-agent FixtureBrowser/1.0"));
        assertTrue(joined.contains("--screenshot"));
        assertTrue(joined.contains("--html"));
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
}
