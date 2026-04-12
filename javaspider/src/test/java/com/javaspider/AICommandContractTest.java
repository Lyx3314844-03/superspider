package com.javaspider;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.ByteArrayOutputStream;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.assertEquals;

class AICommandContractTest {

    @TempDir
    Path tempDir;

    @Test
    void aiCommandFallsBackToHeuristicsWhenNeeded() throws Exception {
        Path htmlFile = tempDir.resolve("page.html");
        Files.writeString(
            htmlFile,
            "<html><head><title>Java AI Demo</title><meta name=\"description\" content=\"Java summary\"></head><body><h1>Java AI Demo</h1></body></html>",
            StandardCharsets.UTF_8
        );

        PrintStream originalOut = System.out;
        ByteArrayOutputStream captured = new ByteArrayOutputStream();
        try {
            System.setOut(new PrintStream(captured, true, StandardCharsets.UTF_8));
            EnhancedSpider.main(new String[]{
                "ai",
                "--html-file", htmlFile.toString(),
                "--instructions", "提取标题和摘要",
                "--schema-json", "{\"type\":\"object\",\"properties\":{\"title\":{\"type\":\"string\"},\"summary\":{\"type\":\"string\"},\"url\":{\"type\":\"string\"}}}"
            });
        } finally {
            System.setOut(originalOut);
        }

        JsonNode payload = new ObjectMapper().readTree(captured.toString(StandardCharsets.UTF_8));
        assertEquals("ai", payload.path("command").asText());
        assertEquals("java", payload.path("runtime").asText());
        assertEquals("Java AI Demo", payload.path("result").path("title").asText());
        assertEquals("Java summary", payload.path("result").path("summary").asText());
    }
}
