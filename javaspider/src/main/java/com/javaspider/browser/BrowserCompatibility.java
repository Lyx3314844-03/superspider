package com.javaspider.browser;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public final class BrowserCompatibility {
    private BrowserCompatibility() {
    }

    public static Map<String, Object> describe() {
        Map<String, Object> surfaces = new LinkedHashMap<>();
        surfaces.put("playwright", Map.of(
            "supported", true,
            "mode", "native-process",
            "adapter_engine", "node-playwright"
        ));
        surfaces.put("selenium", Map.of(
            "supported", true,
            "mode", "native",
            "adapter_engine", "selenium-webdriver"
        ));
        surfaces.put("webdriver", Map.of(
            "supported", true,
            "mode", "native",
            "adapter_engine", "selenium-webdriver"
        ));

        Map<String, Object> artifacts = new LinkedHashMap<>();
        artifacts.put("html", true);
        artifacts.put("screenshot", true);
        artifacts.put("har", true);
        artifacts.put("trace", true);
        artifacts.put("pdf", true);

        Map<String, Object> accessFriction = new LinkedHashMap<>();
        accessFriction.put("classifier", true);
        accessFriction.put("signals", List.of("captcha", "rate-limited", "managed-browser-challenge", "auth-required", "waf-vendor"));
        accessFriction.put("actions", List.of("honor-retry-after", "render-with-browser", "persist-session-state", "pause-for-human-access"));

        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("base_engine", "selenium-webdriver+node-playwright");
        payload.put("bridge_style", "webdriver-and-native-playwright-helper");
        payload.put("surfaces", surfaces);
        payload.put("artifacts", artifacts);
        payload.put("access_friction", accessFriction);
        payload.put("constraints", List.of(
            "Playwright live runs require Node.js plus the npm playwright package and browser binaries",
            "pdf/har support depends on Chromium-backed driver paths; Firefox is not equivalent for that surface"
        ));
        return payload;
    }
}
