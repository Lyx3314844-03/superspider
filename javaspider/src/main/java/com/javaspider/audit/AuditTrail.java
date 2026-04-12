package com.javaspider.audit;

import java.util.List;

public interface AuditTrail {
    void append(AuditEvent event);

    List<AuditEvent> list();
}
