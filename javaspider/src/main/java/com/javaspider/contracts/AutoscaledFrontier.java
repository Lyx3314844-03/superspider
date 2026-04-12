package com.javaspider.contracts;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.javaspider.core.CheckpointManager;
import com.javaspider.core.Request;

import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.PriorityQueue;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

public final class AutoscaledFrontier {
    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();

    public static final class FrontierConfig {
        public String checkpointDir = "artifacts/checkpoints/frontier";
        public String checkpointId = "runtime-frontier";
        public boolean autoscale = true;
        public int minConcurrency = 1;
        public int maxConcurrency = 16;
        public long targetLatencyMs = 1200;
        public int leaseTtlSeconds = 30;
        public int maxInflightPerDomain = 2;
    }

    private record FrontierEntry(Map<String, Object> payload, int priority, int sequence) {
    }

    private static final class FrontierLease {
        private final Request request;
        private final String fingerprint;
        private long expiresAtUnix;

        private FrontierLease(Request request, String fingerprint, long expiresAtUnix) {
            this.request = request;
            this.fingerprint = fingerprint;
            this.expiresAtUnix = expiresAtUnix;
        }
    }

    private final FrontierConfig config;
    private final CheckpointManager checkpointManager;
    private final RuntimeObservability.ObservabilityCollector observabilityCollector = new RuntimeObservability.ObservabilityCollector();
    private final PriorityQueue<FrontierEntry> pending = new PriorityQueue<>(
        Comparator.<FrontierEntry>comparingInt(FrontierEntry::priority).reversed()
            .thenComparingInt(FrontierEntry::sequence)
    );
    private final Set<String> known = ConcurrentHashMap.newKeySet();
    private final Map<String, FrontierLease> leases = new LinkedHashMap<>();
    private final Map<String, Integer> domainInflight = new LinkedHashMap<>();
    private final List<Long> latencies = new ArrayList<>();
    private final List<Boolean> outcomes = new ArrayList<>();
    private final List<Map<String, Object>> deadLetters = new ArrayList<>();
    private int recommendedConcurrency;
    private int sequence;

    public AutoscaledFrontier(FrontierConfig config) {
        this.config = config;
        this.recommendedConcurrency = Math.max(config.minConcurrency, 1);
        this.checkpointManager = new CheckpointManager(config.checkpointDir, CheckpointManager.StorageType.JSON, 0);
    }

    public synchronized int getRecommendedConcurrency() {
        return recommendedConcurrency;
    }

    public synchronized int getDeadLetterCount() {
        return deadLetters.size();
    }

    public synchronized boolean push(Request request) {
        String fingerprint = RequestFingerprint.fromRequest(request).getValue();
        if (known.contains(fingerprint) || leases.containsKey(fingerprint)) {
            return false;
        }
        known.add(fingerprint);
        sequence += 1;
        pending.add(new FrontierEntry(serializeRequest(request, fingerprint), request.getPriority(), sequence));
        observabilityCollector.recordRequest(request, null);
        return true;
    }

    public synchronized Request lease() {
        reapExpiredLeases(3);
        List<FrontierEntry> blocked = new LinkedList<>();
        while (!pending.isEmpty()) {
            FrontierEntry entry = pending.poll();
            String domain = extractDomain(Objects.toString(entry.payload().get("url"), ""));
            if (!domain.isBlank() && domainInflight.getOrDefault(domain, 0) >= config.maxInflightPerDomain) {
                blocked.add(entry);
                continue;
            }
            Request request = deserializeRequest(entry.payload());
            String fingerprint = Objects.toString(entry.payload().get("fingerprint"), "");
            leases.put(fingerprint, new FrontierLease(request, fingerprint, Instant.now().getEpochSecond() + Math.max(config.leaseTtlSeconds, 1)));
            if (!domain.isBlank()) {
                domainInflight.merge(domain, 1, Integer::sum);
            }
            pending.addAll(blocked);
            return request;
        }
        pending.addAll(blocked);
        return null;
    }

    public synchronized boolean heartbeat(Request request, Integer ttlSeconds) {
        String fingerprint = RequestFingerprint.fromRequest(request).getValue();
        FrontierLease lease = leases.get(fingerprint);
        if (lease == null) {
            return false;
        }
        lease.expiresAtUnix = Instant.now().getEpochSecond() + Math.max(ttlSeconds == null ? config.leaseTtlSeconds : ttlSeconds, 1);
        return true;
    }

    public synchronized void ack(Request request, boolean success, long latencyMs, Throwable error, Integer statusCode, int maxRetries) {
        String fingerprint = RequestFingerprint.fromRequest(request).getValue();
        leases.remove(fingerprint);
        String domain = extractDomain(request.getUrl());
        if (!domain.isBlank()) {
            domainInflight.computeIfPresent(domain, (ignored, value) -> value <= 1 ? 0 : value - 1);
        }
        if (!success) {
            int retryCount = parseRetryCount(request.getMeta().get("retry_count"));
            if (retryCount >= maxRetries) {
                deadLetters.add(serializeRequest(request, fingerprint));
            } else {
                request.getMeta().put("retry_count", retryCount + 1);
                sequence += 1;
                pending.add(new FrontierEntry(serializeRequest(request, fingerprint), request.getPriority(), sequence));
            }
        }
        boundedAppend(latencies, Math.max(latencyMs, 0), 64);
        boundedAppend(outcomes, success, 64);
        adjustConcurrency();
        observabilityCollector.recordResult(request, latencyMs, statusCode, error, null);
    }

    public synchronized void persist() {
        List<String> pendingUrls = pending.stream().map(entry -> Objects.toString(entry.payload().get("url"), "")).toList();
        checkpointManager.save(
            config.checkpointId,
            new ArrayList<>(known),
            pendingUrls,
            Map.of("frontier", snapshot()),
            Map.of(),
            true
        );
    }

    public synchronized boolean load() {
        CheckpointManager.CheckpointState state = checkpointManager.load(config.checkpointId);
        if (state == null || state.getStats() == null) {
            return false;
        }
        Object raw = state.getStats().get("frontier");
        if (raw == null) {
            return false;
        }
        restore(OBJECT_MAPPER.convertValue(raw, new TypeReference<Map<String, Object>>() {}));
        return true;
    }

    public synchronized Map<String, Object> snapshot() {
        List<Map<String, Object>> pendingPayloads = pending.stream().map(FrontierEntry::payload).toList();
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("pending", pendingPayloads);
        payload.put("known", new ArrayList<>(known));
        payload.put("domain_inflight", new LinkedHashMap<>(domainInflight));
        payload.put("recommended_concurrency", recommendedConcurrency);
        payload.put("latencies", new ArrayList<>(latencies));
        payload.put("outcomes", new ArrayList<>(outcomes));
        payload.put("dead_letters", new ArrayList<>(deadLetters));
        return payload;
    }

    @SuppressWarnings("unchecked")
    public synchronized void restore(Map<String, Object> snapshot) {
        pending.clear();
        known.clear();
        leases.clear();
        domainInflight.clear();
        latencies.clear();
        outcomes.clear();
        deadLetters.clear();
        sequence = 0;

        if (snapshot.get("known") instanceof Collection<?> values) {
            for (Object value : values) {
                if (value != null) {
                    known.add(String.valueOf(value));
                }
            }
        }
        if (snapshot.get("pending") instanceof Collection<?> values) {
            for (Object value : values) {
                if (value instanceof Map<?, ?> rawMap) {
                    sequence += 1;
                    Object priorityValue = rawMap.get("priority");
                    int priority = priorityValue instanceof Number number ? number.intValue() : 0;
                    pending.add(new FrontierEntry((Map<String, Object>) rawMap, priority, sequence));
                }
            }
        }
        if (snapshot.get("domain_inflight") instanceof Map<?, ?> values) {
            for (Map.Entry<?, ?> entry : values.entrySet()) {
                if (entry.getKey() != null && entry.getValue() instanceof Number number) {
                    domainInflight.put(String.valueOf(entry.getKey()), number.intValue());
                }
            }
        }
        if (snapshot.get("latencies") instanceof Collection<?> values) {
            for (Object value : values) {
                if (value instanceof Number number) {
                    latencies.add(number.longValue());
                }
            }
        }
        if (snapshot.get("outcomes") instanceof Collection<?> values) {
            for (Object value : values) {
                if (value instanceof Boolean bool) {
                    outcomes.add(bool);
                }
            }
        }
        if (snapshot.get("dead_letters") instanceof Collection<?> values) {
            for (Object value : values) {
                if (value instanceof Map<?, ?> rawMap) {
                    deadLetters.add((Map<String, Object>) rawMap);
                }
            }
        }
        Object rawRecommended = snapshot.get("recommended_concurrency");
        if (rawRecommended instanceof Number number) {
            recommendedConcurrency = Math.max(config.minConcurrency, Math.min(config.maxConcurrency, number.intValue()));
        }
    }

    public synchronized int reapExpiredLeases(int maxRetries) {
        long now = Instant.now().getEpochSecond();
        List<String> expired = leases.entrySet().stream()
            .filter(entry -> entry.getValue().expiresAtUnix <= now)
            .map(Map.Entry::getKey)
            .toList();
        for (String fingerprint : expired) {
            FrontierLease lease = leases.remove(fingerprint);
            if (lease == null) {
                continue;
            }
            String domain = extractDomain(lease.request.getUrl());
            if (!domain.isBlank()) {
                domainInflight.computeIfPresent(domain, (ignored, value) -> value <= 1 ? 0 : value - 1);
            }
            int retryCount = parseRetryCount(lease.request.getMeta().get("retry_count"));
            if (retryCount >= maxRetries) {
                deadLetters.add(serializeRequest(lease.request, fingerprint));
                continue;
            }
            lease.request.getMeta().put("retry_count", retryCount + 1);
            sequence += 1;
            pending.add(new FrontierEntry(serializeRequest(lease.request, fingerprint), lease.request.getPriority(), sequence));
        }
        return expired.size();
    }

    private void adjustConcurrency() {
        if (!config.autoscale) {
            return;
        }
        double averageLatency = latencies.stream().mapToLong(Long::longValue).average().orElse(0.0d);
        double failureRate = outcomes.isEmpty() ? 0.0d : (double) outcomes.stream().filter(success -> !success).count() / outcomes.size();
        if (failureRate > 0.2d || averageLatency > config.targetLatencyMs * 1.4d) {
            recommendedConcurrency = Math.max(config.minConcurrency, recommendedConcurrency - 1);
        } else if (pending.size() > recommendedConcurrency && averageLatency < config.targetLatencyMs) {
            recommendedConcurrency = Math.min(config.maxConcurrency, recommendedConcurrency + 1);
        }
    }

    private static Map<String, Object> serializeRequest(Request request, String fingerprint) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("url", request.getUrl());
        payload.put("method", request.getMethod());
        payload.put("headers", new LinkedHashMap<>(request.getHeaders()));
        payload.put("body", request.getBody() == null ? null : new String(request.getBody(), StandardCharsets.UTF_8));
        payload.put("meta", new LinkedHashMap<>(request.getMeta()));
        payload.put("priority", request.getPriority());
        payload.put("fingerprint", fingerprint);
        return payload;
    }

    @SuppressWarnings("unchecked")
    private static Request deserializeRequest(Map<String, Object> payload) {
        Request request = new Request(Objects.toString(payload.get("url"), ""));
        request.setMethod(Objects.toString(payload.get("method"), "GET"));
        if (payload.get("headers") instanceof Map<?, ?> rawMap) {
            Map<String, String> headers = new LinkedHashMap<>();
            for (Map.Entry<?, ?> entry : rawMap.entrySet()) {
                headers.put(String.valueOf(entry.getKey()), String.valueOf(entry.getValue()));
            }
            request.setHeaders(headers);
        }
        if (payload.get("body") instanceof String body && !body.isEmpty()) {
            request.setBody(body.getBytes(StandardCharsets.UTF_8));
        }
        if (payload.get("meta") instanceof Map<?, ?> rawMap) {
            Map<String, Object> meta = new LinkedHashMap<>();
            for (Map.Entry<?, ?> entry : rawMap.entrySet()) {
                meta.put(String.valueOf(entry.getKey()), entry.getValue());
            }
            request.setMeta(meta);
        }
        if (payload.get("priority") instanceof Number number) {
            request.setPriority(number.intValue());
        }
        return request;
    }

    private static String extractDomain(String rawUrl) {
        try {
            return Objects.toString(java.net.URI.create(rawUrl).getHost(), "");
        } catch (Exception exception) {
            return "";
        }
    }

    private static int parseRetryCount(Object value) {
        if (value instanceof Number number) {
            return number.intValue();
        }
        if (value instanceof String text) {
            try {
                return Integer.parseInt(text);
            } catch (NumberFormatException ignored) {
                return 0;
            }
        }
        return 0;
    }

    private static <T> void boundedAppend(List<T> values, T next, int maxSize) {
        values.add(next);
        if (values.size() > maxSize) {
            values.subList(0, values.size() - maxSize).clear();
        }
    }
}
