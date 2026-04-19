package com.javaspider.events;

import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.function.Consumer;

public final class EventBus {
    public static final String TOPIC_TASK_CREATED = "task:created";
    public static final String TOPIC_TASK_QUEUED = "task:queued";
    public static final String TOPIC_TASK_RUNNING = "task:running";
    public static final String TOPIC_TASK_SUCCEEDED = "task:succeeded";
    public static final String TOPIC_TASK_FAILED = "task:failed";
    public static final String TOPIC_TASK_CANCELLED = "task:cancelled";
    public static final String TOPIC_TASK_DELETED = "task:deleted";
    public static final String TOPIC_TASK_RESULT = "task:result";

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private final Map<String, List<Consumer<Event>>> subscribers = new ConcurrentHashMap<>();
    private final List<Event> history = new CopyOnWriteArrayList<>();
    private final Path sinkPath;

    public EventBus() {
        this(null);
    }

    public EventBus(Path sinkPath) {
        this.sinkPath = sinkPath;
    }

    public void subscribe(String topic, Consumer<Event> consumer) {
        subscribers.computeIfAbsent(topic, ignored -> new CopyOnWriteArrayList<>()).add(consumer);
    }

    public Event publish(String topic, Object payload) {
        Event event = Event.now(topic, payload);
        history.add(event);
        dispatch(topic, event);
        dispatch("*", event);
        persist(event);
        return event;
    }

    public List<Event> recent(String topic) {
        List<Event> events = new ArrayList<>();
        for (Event event : history) {
            if (topic == null || topic.isBlank() || topic.equals(event.topic())) {
                events.add(event);
            }
        }
        return events;
    }

    private void dispatch(String topic, Event event) {
        List<Consumer<Event>> consumers = subscribers.get(topic);
        if (consumers == null) {
            return;
        }
        for (Consumer<Event> consumer : consumers) {
            consumer.accept(event);
        }
    }

    private void persist(Event event) {
        if (sinkPath == null) {
            return;
        }
        try {
            Files.createDirectories(sinkPath.getParent());
            Map<String, Object> record = new LinkedHashMap<>();
            record.put("topic", event.topic());
            record.put("timestamp", event.timestamp().getEpochSecond());
            record.put("payload", normalize(event.payload()));
            Files.writeString(
                sinkPath,
                MAPPER.writeValueAsString(record) + "\n",
                StandardCharsets.UTF_8,
                StandardOpenOption.CREATE,
                StandardOpenOption.APPEND
            );
        } catch (IOException e) {
            throw new RuntimeException("failed to persist event", e);
        }
    }

    private Object normalize(Object value) {
        if (value == null) {
            return null;
        }
        if (value instanceof Instant instant) {
            return instant.toString();
        }
        if (value instanceof Map<?, ?> map) {
            Map<String, Object> normalized = new LinkedHashMap<>();
            for (Map.Entry<?, ?> entry : map.entrySet()) {
                normalized.put(String.valueOf(entry.getKey()), normalize(entry.getValue()));
            }
            return normalized;
        }
        if (value instanceof Iterable<?> iterable) {
            List<Object> normalized = new ArrayList<>();
            for (Object item : iterable) {
                normalized.add(normalize(item));
            }
            return normalized;
        }
        if (value.getClass().isRecord()) {
            Map<String, Object> normalized = new LinkedHashMap<>();
            for (var component : value.getClass().getRecordComponents()) {
                try {
                    normalized.put(component.getName(), normalize(component.getAccessor().invoke(value)));
                } catch (ReflectiveOperationException e) {
                    throw new RuntimeException("failed to normalize record payload", e);
                }
            }
            return normalized;
        }
        return value;
    }

    public record TaskLifecyclePayload(
        String taskId,
        String state,
        String runtime,
        String url,
        String workerId,
        Instant updatedAt,
        boolean hasResult
    ) {
    }

    public record ArtifactRef(
        String kind,
        String uri,
        String path,
        long size,
        Map<String, Object> metadata
    ) {
    }

    public record TaskResultPayload(
        String taskId,
        String state,
        String runtime,
        String url,
        int statusCode,
        List<String> artifacts,
        Map<String, ArtifactRef> artifactRefs,
        Instant updatedAt
    ) {
    }

    public record TaskDeletedPayload(String taskId, Instant deletedAt) {
    }
}
