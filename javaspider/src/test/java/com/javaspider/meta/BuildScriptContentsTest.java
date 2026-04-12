package com.javaspider.meta;

import org.junit.jupiter.api.Test;

import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.assertTrue;

class BuildScriptContentsTest {

    @Test
    void buildScriptsReferenceMavenAndFrameworkCli() throws Exception {
        Path root = Path.of(System.getProperty("user.dir"));
        String build = Files.readString(root.resolve("build.sh"));
        String runFramework = Files.readString(root.resolve("run-framework.sh"));

        assertTrue(build.contains("mvn"));
        assertTrue(runFramework.contains("com.javaspider.EnhancedSpider"));
        assertTrue(runFramework.contains("target/dependency/*"));
    }
}
