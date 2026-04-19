package com.javaspider.security;

import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class SSRFProtectionTest {

    @Test
    void filtersUnsafeUrlsAndValidatesRedirectChains() {
        List<String> safe = SSRFProtection.filterSafeUrls(List.of(
            "https://example.com",
            "http://localhost/admin",
            "http://169.254.169.254/latest/meta-data"
        ));

        assertEquals(List.of("https://example.com"), safe);
        assertTrue(SSRFProtection.validateRedirectChain(
            "https://example.com",
            List.of("https://example.com/next", "https://example.com/final")
        ));
        assertFalse(SSRFProtection.validateRedirectChain(
            "https://example.com",
            List.of("http://localhost/admin")
        ));
    }
}
