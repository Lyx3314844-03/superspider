package com.javaspider.audit;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

public class InMemoryAuditTrail implements AuditTrail {
    private final List<AuditEvent> events = new ArrayList<>();

    @Override
    public synchronized void append(AuditEvent event) {
        events.add(event);
    }

    @Override
    public synchronized List<AuditEvent> list() {
        return Collections.unmodifiableList(new ArrayList<>(events));
    }
}
