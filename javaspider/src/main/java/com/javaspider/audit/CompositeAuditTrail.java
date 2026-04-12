package com.javaspider.audit;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

public class CompositeAuditTrail implements AuditTrail {
    private final List<AuditTrail> delegates = new ArrayList<>();

    public CompositeAuditTrail(AuditTrail... delegates) {
        this.delegates.addAll(Arrays.asList(delegates));
    }

    @Override
    public void append(AuditEvent event) {
        for (AuditTrail delegate : delegates) {
            delegate.append(event);
        }
    }

    @Override
    public List<AuditEvent> list() {
        if (delegates.isEmpty()) {
            return List.of();
        }
        return delegates.get(0).list();
    }
}
