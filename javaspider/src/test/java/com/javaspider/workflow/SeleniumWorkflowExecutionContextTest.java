package com.javaspider.workflow;

import com.javaspider.session.SessionProfile;
import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class SeleniumWorkflowExecutionContextTest {

    @Test
    void resolveUserAgentUsesFingerprintPreset() {
        SessionProfile session = new SessionProfile(
            "session-1",
            "account-1",
            "default",
            "mobile-stealth",
            Map.of()
        );

        String userAgent = SeleniumWorkflowExecutionContext.resolveUserAgent(session);

        assertFalse(userAgent.isBlank());
        assertTrue(userAgent.contains("Mobile") || userAgent.contains("iPhone") || userAgent.contains("Android"));
    }

    @Test
    void resolveProxyUsesScopedSystemProperty() {
        System.setProperty("javaspider.proxy.group.residential", "http://127.0.0.1:7890");
        try {
            SessionProfile session = new SessionProfile(
                "session-1",
                "account-1",
                "residential",
                "chrome-stealth",
                Map.of()
            );

            String proxy = SeleniumWorkflowExecutionContext.resolveProxy(session);
            assertTrue(proxy.contains("127.0.0.1"));
        } finally {
            System.clearProperty("javaspider.proxy.group.residential");
        }
    }
}
