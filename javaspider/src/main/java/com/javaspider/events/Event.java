package com.javaspider.events;

import java.time.Instant;

public record Event(String topic, Instant timestamp, Object payload) {
    public static Event now(String topic, Object payload) {
        return new Event(topic, Instant.now(), payload);
    }
}
