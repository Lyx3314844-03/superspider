package com.javaspider.antibot;

import org.junit.jupiter.api.Test;

import java.time.ZonedDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class AccessFrictionAnalyzerTest {

    @Test
    void honorsRetryAfterForRateLimits() {
        AccessFrictionAnalyzer.AccessFrictionReport report = AccessFrictionAnalyzer.analyze(
            429,
            Map.of("Retry-After", "18"),
            "too many requests",
            "https://shop.example"
        );

        assertEquals("high", report.level());
        assertEquals(18, report.retryAfterSeconds());
        @SuppressWarnings("unchecked")
        Map<String, Object> throttle = (Map<String, Object>) report.capabilityPlan().get("throttle");
        assertEquals(30, throttle.get("crawl_delay_seconds"));
        assertEquals(1, report.capabilityPlan().get("retry_budget"));
        assertTrue(report.signals().contains("rate-limited"));
        assertTrue(report.recommendedActions().contains("honor-retry-after"));
        assertTrue(report.blocked());
    }

    @Test
    void recommendsBrowserAndHumanCheckpointForCaptcha() {
        AccessFrictionAnalyzer.AccessFrictionReport report = AccessFrictionAnalyzer.analyze(
            200,
            Map.of(),
            "<html><div>hcaptcha 安全验证</div></html>",
            "https://shop.example/challenge"
        );

        assertEquals("high", report.level());
        assertTrue(report.shouldUpgradeToBrowser());
        assertTrue(report.requiresHumanAccess());
        assertEquals(true, report.challengeHandoff().get("required"));
        assertEquals("human-authorized-browser-session", report.challengeHandoff().get("method"));
        @SuppressWarnings("unchecked")
        Map<String, Object> session = (Map<String, Object>) report.capabilityPlan().get("session");
        assertEquals(true, session.get("reuse_only_after_authorized_access"));
        assertTrue(report.recommendedActions().contains("pause-for-human-access"));
    }

    @Test
    void parsesRetryAfterHttpDate() {
        String retryAt = ZonedDateTime.now(java.time.ZoneOffset.UTC)
            .plusMinutes(2)
            .format(DateTimeFormatter.RFC_1123_DATE_TIME);

        AccessFrictionAnalyzer.AccessFrictionReport report = AccessFrictionAnalyzer.analyze(
            429,
            Map.of("Retry-After", retryAt),
            "too many requests",
            "https://shop.example"
        );

        assertTrue(report.retryAfterSeconds() > 0);
    }

    @Test
    void routesSignatureAndFingerprintPagesToDevToolsNodeReverse() {
        AccessFrictionAnalyzer.AccessFrictionReport report = AccessFrictionAnalyzer.analyze(
            200,
            Map.of(),
            "<script>window._signature='x'; const token = CryptoJS.MD5(navigator.webdriver + 'x-bogus').toString();</script>",
            "https://example.com/api/list?X-Bogus=abc"
        );

        assertEquals("medium", report.level());
        assertTrue(report.shouldUpgradeToBrowser());
        assertTrue(report.signals().contains("js-signature"));
        assertTrue(report.signals().contains("fingerprint-required"));
        assertTrue(report.recommendedActions().contains("capture-devtools-network"));
        assertTrue(report.recommendedActions().contains("run-nodejs-reverse-analysis"));
        @SuppressWarnings("unchecked")
        java.util.List<String> transport = (java.util.List<String>) report.capabilityPlan().get("transport_order");
        assertTrue(transport.contains("devtools-analysis"));
        assertTrue(transport.contains("node-reverse-analysis"));
    }
}
