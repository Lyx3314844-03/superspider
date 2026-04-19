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
            "mode", "compatibility-bridge",
            "adapter_engine", "playwright-helper"
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

        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("base_engine", "selenium-webdriver");
        payload.put("bridge_style", "webdriver-and-helper");
        payload.put("surfaces", surfaces);
        payload.put("artifacts", artifacts);
        payload.put("constraints", List.of(
            "pdf/har support depends on Chromium-backed driver paths; Firefox is not equivalent for that surface"
        ));
        return payload;
    }
}
