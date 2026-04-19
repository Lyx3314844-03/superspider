package com.javaspider.browser;

import com.javaspider.cli.SuperSpiderCLI;
import org.junit.jupiter.api.Test;

import java.io.ByteArrayOutputStream;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;

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

        assertEquals("selenium-webdriver", payload.get("base_engine"));
        assertEquals("playwright-helper", playwright.get("adapter_engine"));
        assertEquals("selenium-webdriver", selenium.get("adapter_engine"));
    }

    @Test
    void capabilitiesCommandIncludesBrowserCompatibilityMatrix() {
        String output = captureStdout(() ->
            SuperSpiderCLI.main(new String[]{"capabilities"})
        );

        assertTrue(output.contains("\"browser_compatibility\""));
        assertTrue(output.contains("\"playwright-helper\""));
        assertTrue(output.contains("\"selenium-webdriver\""));
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
