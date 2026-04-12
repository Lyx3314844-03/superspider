package com.javaspider;

import com.javaspider.contracts.AutoscaledFrontier;
import com.javaspider.core.Request;
import org.junit.jupiter.api.Test;

import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.*;

class SpiderRuntimeStabilityTest {
    @Test
    void frontierSyntheticSoakRecoversAfterFailures() throws Exception {
        Path checkpointDir = Files.createTempDirectory("javaspider-soak");
        AutoscaledFrontier.FrontierConfig config = new AutoscaledFrontier.FrontierConfig();
        config.checkpointDir = checkpointDir.resolve("checkpoints").toString();
        config.checkpointId = "soak-frontier";
        config.maxConcurrency = 8;
        config.maxInflightPerDomain = 2;

        AutoscaledFrontier frontier = new AutoscaledFrontier(config);
        for (int idx = 0; idx < 24; idx++) {
            Request request = new Request("https://example.com/item/" + idx);
            request.setPriority(idx % 3);
            request.getMeta().put("mode", idx % 7 == 0 ? "dead-letter" : "success");
            assertTrue(frontier.push(request));
        }

        int processed = 0;
        int failed = 0;
        for (int idx = 0; idx < 80; idx++) {
            Request leased = frontier.lease();
            if (leased == null) {
                break;
            }
            if ("dead-letter".equals(String.valueOf(leased.getMeta().get("mode")))) {
                failed++;
                frontier.ack(leased, false, 1800, new RuntimeException("synthetic timeout"), 408, 1);
            } else {
                processed++;
                frontier.ack(leased, true, 40, null, 200, 1);
            }
        }

        frontier.persist();

        AutoscaledFrontier restored = new AutoscaledFrontier(config);
        assertTrue(restored.load());
        assertTrue(processed > 0);
        assertTrue(failed > 0);
        assertTrue(frontier.getDeadLetterCount() >= 1);
        assertTrue(restored.getRecommendedConcurrency() >= 1);
        assertTrue(restored.getRecommendedConcurrency() <= 8);
    }
}
