package com.javaspider.events;

import org.junit.jupiter.api.Test;

import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class EventBusTest {

    @Test
    void publishesAndPersistsEvents() throws Exception {
        Path sink = Files.createTempFile("java-events", ".jsonl");
        EventBus bus = new EventBus(sink);
        List<Event> received = new ArrayList<>();
        bus.subscribe(EventBus.TOPIC_TASK_RUNNING, received::add);

        Event event = bus.publish(
            EventBus.TOPIC_TASK_RUNNING,
            new EventBus.TaskLifecyclePayload(
                "job-1",
                "running",
                "java",
                "https://example.com",
                "",
                Instant.now(),
                false
            )
        );

        assertEquals(EventBus.TOPIC_TASK_RUNNING, event.topic());
        assertEquals(1, received.size());
        assertEquals(1, bus.recent(EventBus.TOPIC_TASK_RUNNING).size());
        assertTrue(Files.readString(sink).contains("\"topic\":\"task:running\""));
    }

    @Test
    void wildcardSubscribersReceiveAllTopics() {
        EventBus bus = new EventBus();
        List<String> topics = new ArrayList<>();
        bus.subscribe("*", event -> topics.add(event.topic()));

        bus.publish(EventBus.TOPIC_TASK_CREATED, Map.of("task_id", "job-1"));
        bus.publish(EventBus.TOPIC_TASK_RESULT, Map.of("task_id", "job-1"));

        assertEquals(List.of(EventBus.TOPIC_TASK_CREATED, EventBus.TOPIC_TASK_RESULT), topics);
    }
}
