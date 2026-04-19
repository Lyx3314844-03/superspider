package com.javaspider.antibot;

import java.time.LocalTime;

/**
 * 夜间模式策略
 * 在低活跃时段主动放慢抓取节奏，降低触发风控的概率。
 */
public record NightModePolicy(
    boolean enabled,
    int startHour,
    int endHour,
    double delayMultiplier,
    double rateLimitFactor
) {
    public NightModePolicy {
        validateHour(startHour);
        validateHour(endHour);
        if (delayMultiplier <= 0) {
            throw new IllegalArgumentException("delayMultiplier must be > 0");
        }
        if (rateLimitFactor <= 0) {
            throw new IllegalArgumentException("rateLimitFactor must be > 0");
        }
    }

    public static NightModePolicy defaultPolicy() {
        return new NightModePolicy(true, 23, 6, 1.5, 0.5);
    }

    public boolean isActive(LocalTime time) {
        if (!enabled) {
            return false;
        }
        int hour = time.getHour();
        if (startHour == endHour) {
            return true;
        }
        if (startHour < endHour) {
            return hour >= startHour && hour < endHour;
        }
        return hour >= startHour || hour < endHour;
    }

    public long applyDelay(long baseDelayMs, LocalTime time) {
        if (baseDelayMs <= 0 || !isActive(time)) {
            return baseDelayMs;
        }
        long adjusted = Math.round(baseDelayMs * delayMultiplier);
        return Math.max(baseDelayMs, adjusted);
    }

    public double applyRateLimit(double baseRate, LocalTime time) {
        if (baseRate <= 0 || !isActive(time)) {
            return baseRate;
        }
        double adjusted = baseRate * rateLimitFactor;
        return adjusted > 0 ? adjusted : baseRate;
    }

    private static void validateHour(int hour) {
        if (hour < 0 || hour > 23) {
            throw new IllegalArgumentException("hour must be between 0 and 23");
        }
    }
}
