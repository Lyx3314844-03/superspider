package com.javaspider.workflow;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;

public class FlowStep {
    private final String id;
    private final FlowStepType type;
    private final String selector;
    private final String value;
    private final Map<String, Object> metadata;

    public FlowStep(String id, FlowStepType type, String selector, String value, Map<String, Object> metadata) {
        this.id = id;
        this.type = type;
        this.selector = selector;
        this.value = value;
        this.metadata = metadata == null
            ? Collections.emptyMap()
            : Collections.unmodifiableMap(new LinkedHashMap<>(metadata));
    }

    public String getId() {
        return id;
    }

    public FlowStepType getType() {
        return type;
    }

    public String getSelector() {
        return selector;
    }

    public String getValue() {
        return value;
    }

    public Map<String, Object> getMetadata() {
        return metadata;
    }
}
