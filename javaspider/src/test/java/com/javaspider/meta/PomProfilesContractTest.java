package com.javaspider.meta;

import org.junit.jupiter.api.Test;

import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.assertTrue;

class PomProfilesContractTest {

    @Test
    void pomDeclaresFeatureProfilesAndResourceFiltering() throws Exception {
        Path root = Path.of(System.getProperty("user.dir"));
        String pom = Files.readString(root.resolve("pom.xml"));
        String properties = Files.readString(root.resolve("src").resolve("main").resolve("resources").resolve("spider.properties"));

        assertTrue(pom.contains("<profiles>"));
        assertTrue(pom.contains("<id>lite</id>"));
        assertTrue(pom.contains("<id>browser</id>"));
        assertTrue(pom.contains("<id>distributed</id>"));
        assertTrue(pom.contains("<id>ai</id>"));
        assertTrue(pom.contains("<filtering>true</filtering>"));
        assertTrue(properties.contains("feature.ai.enabled=${feature.ai}"));
        assertTrue(properties.contains("feature.browser.enabled=${feature.browser}"));
        assertTrue(properties.contains("feature.distributed.enabled=${feature.distributed}"));
    }
}
