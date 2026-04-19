package com.javaspider.antibot;

import org.junit.jupiter.api.Test;

import java.time.LocalTime;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class NightModePolicyTest {

    @Test
    void detectsCrossMidnightQuietHours() {
        NightModePolicy policy = NightModePolicy.defaultPolicy();

        assertTrue(policy.isActive(LocalTime.of(1, 30)));
        assertFalse(policy.isActive(LocalTime.of(14, 0)));
    }

    @Test
    void scalesDelayAndRateLimitDuringNightWindow() {
        NightModePolicy policy = NightModePolicy.defaultPolicy();

        assertEquals(1500L, policy.applyDelay(1000L, LocalTime.of(23, 15)));
        assertEquals(5.0, policy.applyRateLimit(10.0, LocalTime.of(2, 0)));
    }
}
