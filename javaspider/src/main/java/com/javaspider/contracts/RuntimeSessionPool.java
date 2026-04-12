package com.javaspider.contracts;

import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;

public final class RuntimeSessionPool {
    private RuntimeSessionPool() {
    }

    public static final class SessionHandle {
        private final String sessionId;
        private final long createdAtUnix;
        private long lastUsedAtUnix;
        private final Map<String, String> headers = new LinkedHashMap<>();
        private final Map<String, String> cookies = new LinkedHashMap<>();
        private final String fingerprintProfile;
        private final String proxyId;
        private int leaseCount;
        private int failureCount;
        private boolean inUse;

        private SessionHandle(String fingerprintProfile, String proxyId) {
            this.sessionId = "session-" + UUID.randomUUID().toString().replace("-", "").substring(0, 12);
            this.createdAtUnix = Instant.now().getEpochSecond();
            this.lastUsedAtUnix = createdAtUnix;
            this.fingerprintProfile = fingerprintProfile;
            this.proxyId = proxyId;
            this.leaseCount = 1;
            this.inUse = true;
        }

        public String getSessionId() {
            return sessionId;
        }

        public long getLastUsedAtUnix() {
            return lastUsedAtUnix;
        }
    }

    public static final class SessionPool {
        private final int maxSessions;
        private final Map<String, SessionHandle> sessions = new LinkedHashMap<>();

        public SessionPool(int maxSessions) {
            this.maxSessions = Math.max(maxSessions, 1);
        }

        public synchronized SessionHandle acquire(String proxyId, String fingerprintProfile) {
            for (SessionHandle handle : sessions.values()) {
                if (!handle.inUse
                    && Objects.equals(handle.proxyId, proxyId)
                    && Objects.equals(handle.fingerprintProfile, fingerprintProfile)) {
                    handle.inUse = true;
                    handle.leaseCount += 1;
                    handle.lastUsedAtUnix = Instant.now().getEpochSecond();
                    return handle;
                }
            }
            if (sessions.size() >= maxSessions) {
                return sessions.values().stream()
                    .min((left, right) -> Long.compare(left.lastUsedAtUnix, right.lastUsedAtUnix))
                    .map(handle -> {
                        handle.inUse = true;
                        handle.leaseCount += 1;
                        handle.lastUsedAtUnix = Instant.now().getEpochSecond();
                        return handle;
                    })
                    .orElseThrow();
            }
            SessionHandle handle = new SessionHandle(
                fingerprintProfile == null ? "default" : fingerprintProfile,
                proxyId
            );
            sessions.put(handle.sessionId, handle);
            return handle;
        }

        public synchronized void release(String sessionId, boolean success) {
            SessionHandle handle = sessions.get(sessionId);
            if (handle == null) {
                return;
            }
            handle.inUse = false;
            handle.lastUsedAtUnix = Instant.now().getEpochSecond();
            if (!success) {
                handle.failureCount += 1;
            }
        }
    }
}
