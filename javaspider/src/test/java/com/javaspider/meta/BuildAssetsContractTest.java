package com.javaspider.meta;

import org.junit.jupiter.api.Test;

import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.assertTrue;

class BuildAssetsContractTest {

    @Test
    void moduleContainsMavenAndShellBuildEntrypoints() {
        Path root = Path.of(System.getProperty("user.dir"));

        assertTrue(Files.exists(root.resolve("pom.xml")));
        assertTrue(Files.exists(root.resolve("build.sh")));
        assertTrue(Files.exists(root.resolve("build.bat")));
        assertTrue(Files.exists(root.resolve("run-framework.sh")));
        assertTrue(Files.exists(root.resolve("docker").resolve("Dockerfile")));
    }
}
