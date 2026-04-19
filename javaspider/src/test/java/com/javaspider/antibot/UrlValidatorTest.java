package com.javaspider.antibot;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class UrlValidatorTest {

    @Test
    void allowsPublicHttpsUrl() {
        assertTrue(UrlValidator.isValidUrl("https://example.com"));
    }

    @Test
    void blocksMetadataAndLoopbackUrls() {
        assertFalse(UrlValidator.isValidUrl("http://169.254.169.254/latest/meta-data"));
        assertFalse(UrlValidator.isValidUrl("http://localhost/admin"));
    }

    @Test
    void canBypassPrivateHostsWhenExplicitlyAllowed() {
        assertTrue(UrlValidator.isValidUrl("http://localhost:8080/health", true));
    }
}
