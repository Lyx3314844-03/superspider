package com.javaspider.meta;

import org.junit.jupiter.api.Test;

import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.assertTrue;

class ReplayFixturesContractTest {

    @Test
    void workflowReplayFixtureAndScenarioContainCaptchaSelectors() throws Exception {
        Path repoRoot = Path.of(System.getProperty("user.dir")).getParent();
        Path scenario = repoRoot.resolve("replays").resolve("workflow").resolve("java-captcha-recovery.json");
        Path fixture = repoRoot.resolve("replays").resolve("workflow").resolve("fixtures").resolve("java-captcha-recovery.html");

        String scenarioText = Files.readString(scenario);
        String fixtureText = Files.readString(fixture);

        assertTrue(scenarioText.contains("#captcha"));
        assertTrue(scenarioText.contains("#continue"));
        assertTrue(scenarioText.contains("captcha.detected"));
        assertTrue(fixtureText.contains("id=\"captcha\""));
        assertTrue(fixtureText.contains("id=\"continue\""));
    }
}
