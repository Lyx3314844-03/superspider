package com.javaspider.audit;

import java.time.Instant;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;

public class AuditEvent {
    private final String jobId;
    private final String stepId;
    private final String type;
    private final Instant timestamp;
    private final Map<String, Object> payload;

    public AuditEvent(String jobId, String stepId, String type, Map<String, Object> payload) {
        this.jobId = jobId;
        this.stepId = stepId;
        this.type = type;
        this.timestamp = Instant.now();
        this.payload = payload == null
            ? Collections.emptyMap()
            : Collections.unmodifiableMap(new LinkedHashMap<>(payload));
    }

    public String getJobId() {
        return jobId;
    }

    public String getStepId() {
        return stepId;
    }

    public String getType() {
        return type;
    }

    public Instant getTimestamp() {
        return timestamp;
    }

    public Map<String, Object> getPayload() {
        return payload;
    }
}
