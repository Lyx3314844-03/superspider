package com.javaspider.audit;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.javaspider.util.JsonlWriterRegistry;

import java.io.IOException;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public class FileAuditTrail implements AuditTrail {
    private static final ObjectMapper MAPPER = new ObjectMapper();

    private final Path path;
    private final List<AuditEvent> events = new ArrayList<>();

    public FileAuditTrail(Path path) {
        this.path = path;
    }

    @Override
    public synchronized void append(AuditEvent event) {
        events.add(event);
        try {
            JsonlWriterRegistry.append(
                path,
                (MAPPER.writeValueAsString(toRecord(event)) + System.lineSeparator())
                    .getBytes(java.nio.charset.StandardCharsets.UTF_8)
            );
        } catch (IOException e) {
            throw new RuntimeException("failed to append audit event", e);
        }
    }

    @Override
    public synchronized List<AuditEvent> list() {
        return Collections.unmodifiableList(new ArrayList<>(events));
    }

    private Map<String, Object> toRecord(AuditEvent event) {
        Map<String, Object> record = new LinkedHashMap<>();
        record.put("job_id", event.getJobId());
        record.put("step_id", event.getStepId());
        record.put("type", event.getType());
        record.put("timestamp", event.getTimestamp().toString());
        record.put("payload", event.getPayload());
        return record;
    }
}
