package com.javaspider.meta;

import org.junit.jupiter.api.Test;

import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.assertTrue;

class CliEntrypointsContractTest {

    @Test
    void cliSourcesExistForJobWorkflowAndReplayEntrypoints() {
        Path root = Path.of(System.getProperty("user.dir"))
                .resolve("src")
                .resolve("main")
                .resolve("java")
                .resolve("com")
                .resolve("javaspider");
        Path cliRoot = root.resolve("cli");

        assertTrue(Files.exists(root.resolve("EnhancedSpider.java")));
        assertTrue(Files.exists(cliRoot.resolve("SuperSpiderCLI.java")));
        assertTrue(Files.exists(cliRoot.resolve("WorkflowSpiderCLI.java")));
        assertTrue(Files.exists(cliRoot.resolve("WorkflowReplayCLI.java")));
    }
}
