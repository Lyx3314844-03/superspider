package com.javaspider.meta;

import org.junit.jupiter.api.Test;

import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.assertTrue;

class ReadmeContractTest {

    @Test
    void readmeCoversQuickStartApiAndDeploy() throws Exception {
        String content = Files.readString(Path.of(System.getProperty("user.dir"), "README.md"));

        assertTrue(content.contains("Quick Start"));
        assertTrue(content.contains("API"));
        assertTrue(content.contains("Deploy"));
    }
}
