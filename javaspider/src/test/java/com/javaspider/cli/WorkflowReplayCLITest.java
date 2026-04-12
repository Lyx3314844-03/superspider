package com.javaspider.cli;

import org.junit.jupiter.api.Test;

import java.io.ByteArrayOutputStream;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.assertTrue;

class WorkflowReplayCLITest {

    @Test
    void workflowReplayPersistsGraphArtifactWhenHtmlFixtureIsAvailable() throws Exception {
        Path dir = Files.createTempDirectory("workflow-replay-cli");
        Path outputPath = dir.resolve("workflow-replay.json");
        Path replay = dir.resolve("replay.json");
        Files.writeString(replay, """
            {
              "name": "workflow-replay-demo",
              "target": { "url": "https://example.com" },
              "output": { "format": "json", "path": "%s" },
              "metadata": {
                "mock_html": "<html><head><title>Replay Graph</title></head><body><a href='https://example.com/docs'>Docs</a></body></html>"
              }
            }
            """.formatted(outputPath.toString().replace("\\", "\\\\")));

        String stdout = captureStdout(() ->
            WorkflowReplayCLI.main(new String[]{"--file", replay.toString()})
        );

        assertTrue(stdout.contains("-graph.json"), stdout);
        String persisted = Files.readString(outputPath);
        assertTrue(persisted.contains("-graph.json"), persisted);
        assertTrue(Files.exists(dir.resolve("graphs").resolve("workflow-replay-demo-graph.json")));
    }

    private static String captureStdout(Runnable runnable) {
        PrintStream original = System.out;
        ByteArrayOutputStream buffer = new ByteArrayOutputStream();
        try (PrintStream stream = new PrintStream(buffer, true, StandardCharsets.UTF_8)) {
            System.setOut(stream);
            runnable.run();
        } catch (Exception e) {
            throw new RuntimeException(e);
        } finally {
            System.setOut(original);
        }
        return buffer.toString(StandardCharsets.UTF_8);
    }
}
