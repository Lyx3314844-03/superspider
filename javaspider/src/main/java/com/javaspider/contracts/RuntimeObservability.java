package com.javaspider.contracts;

import com.javaspider.core.Request;

import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

public final class RuntimeObservability {
    private RuntimeObservability() {
    }

    public record StructuredEvent(long timestampUnix, String level, String event, String traceId, Map<String, Object> fields) {
    }

    public static final class ObservabilityCollector {
        private final List<StructuredEvent> events = new ArrayList<>();
        private final Map<String, Double> metrics = new LinkedHashMap<>();
        private final Map<String, List<StructuredEvent>> traces = new LinkedHashMap<>();

        public synchronized String startTrace(String name) {
            String traceId = "trace-" + UUID.randomUUID().toString().replace("-", "").substring(0, 12);
            log("info", name, traceId, Map.of("phase", "start"));
            return traceId;
        }

        public synchronized void endTrace(String traceId, Map<String, Object> fields) {
            log("info", "trace.complete", traceId, fields);
        }

        public synchronized void log(String level, String event, String traceId, Map<String, Object> fields) {
            StructuredEvent structuredEvent = new StructuredEvent(
                Instant.now().getEpochSecond(),
                level,
                event,
                traceId,
                fields == null ? Map.of() : new LinkedHashMap<>(fields)
            );
            events.add(structuredEvent);
            metrics.merge("events." + event, 1.0d, Double::sum);
            if (traceId != null && !traceId.isBlank()) {
                traces.computeIfAbsent(traceId, ignored -> new ArrayList<>()).add(structuredEvent);
            }
        }

        public synchronized void recordRequest(Request request, String traceId) {
            metrics.merge("requests.total", 1.0d, Double::sum);
            log("info", "request.enqueued", traceId, Map.of(
                "url", request.getUrl(),
                "priority", request.getPriority()
            ));
        }

        public synchronized String recordResult(Request request, long latencyMs, Integer statusCode, Throwable error, String traceId) {
            String classification = classifyFailure(statusCode, error, "");
            metrics.merge("requests.latency_ms.total", (double) Math.max(latencyMs, 0), Double::sum);
            metrics.merge("results." + classification, 1.0d, Double::sum);
            Map<String, Object> fields = new LinkedHashMap<>();
            fields.put("url", request == null ? "" : request.getUrl());
            fields.put("latency_ms", Math.max(latencyMs, 0));
            fields.put("classification", classification);
            if (statusCode != null) {
                fields.put("status_code", statusCode);
            }
            if (error != null) {
                fields.put("error", error.getMessage());
            }
            log(("ok".equals(classification) || "not_modified".equals(classification)) ? "info" : "error", "request.completed", traceId, fields);
            return classification;
        }

        public synchronized Map<String, Object> summary() {
            double requests = metrics.getOrDefault("requests.total", 0.0d);
            double totalLatency = metrics.getOrDefault("requests.latency_ms.total", 0.0d);
            return Map.of(
                "events", events.size(),
                "traces", traces.size(),
                "metrics", new LinkedHashMap<>(metrics),
                "average_latency_ms", requests == 0.0d ? 0.0d : totalLatency / requests
            );
        }

        public synchronized String toPrometheusText(String prefix) {
            String safePrefix = (prefix == null || prefix.isBlank()) ? "spider_runtime" : prefix;
            Map<String, Object> summary = summary();
            StringBuilder builder = new StringBuilder();
            builder.append("# HELP ").append(safePrefix).append("_events_total Total structured events emitted by the runtime\n");
            builder.append("# TYPE ").append(safePrefix).append("_events_total counter\n");
            builder.append(safePrefix).append("_events_total ").append(summary.get("events")).append('\n');
            builder.append("# HELP ").append(safePrefix).append("_traces_total Total traces recorded by the runtime\n");
            builder.append("# TYPE ").append(safePrefix).append("_traces_total gauge\n");
            builder.append(safePrefix).append("_traces_total ").append(summary.get("traces")).append('\n');
            @SuppressWarnings("unchecked")
            Map<String, Double> metricValues = (Map<String, Double>) summary.get("metrics");
            for (Map.Entry<String, Double> entry : metricValues.entrySet()) {
                builder.append(safePrefix)
                    .append('_')
                    .append(entry.getKey().replace('.', '_'))
                    .append(' ')
                    .append(entry.getValue())
                    .append('\n');
            }
            builder.append(safePrefix).append("_average_latency_ms ").append(summary.get("average_latency_ms")).append('\n');
            return builder.toString();
        }

        public synchronized Map<String, Object> toOtelPayload(String serviceName) {
            String safeServiceName = (serviceName == null || serviceName.isBlank()) ? "spider-runtime" : serviceName;
            Map<String, Object> summary = summary();
            @SuppressWarnings("unchecked")
            Map<String, Double> metricValues = (Map<String, Double>) summary.get("metrics");
            List<Map<String, Object>> points = new ArrayList<>();
            for (Map.Entry<String, Double> entry : metricValues.entrySet()) {
                points.add(Map.of(
                    "name", entry.getKey(),
                    "value", entry.getValue(),
                    "unit", "1"
                ));
            }
            points.add(Map.of(
                "name", "average_latency_ms",
                "value", summary.get("average_latency_ms"),
                "unit", "ms"
            ));
            return Map.of(
                "resource", Map.of("service.name", safeServiceName),
                "scope", "javaspider.contracts.RuntimeObservability",
                "metrics", points,
                "events", summary.get("events"),
                "traces", summary.get("traces")
            );
        }
    }

    public static String classifyFailure(Integer statusCode, Throwable error, String body) {
        String message = ((error == null ? "" : error.getMessage()) + " " + (body == null ? "" : body)).toLowerCase();
        if (statusCode != null) {
            if (statusCode == 304) return "not_modified";
            if (statusCode == 401 || statusCode == 403) return "blocked";
            if (statusCode == 404) return "not_found";
            if (statusCode == 408) return "timeout";
            if (statusCode == 429) return "throttled";
            if (statusCode >= 500) return "server";
        }
        if (message.contains("timeout")) return "timeout";
        if (message.contains("rate limit") || message.contains("too many requests")) return "throttled";
        if (message.contains("captcha") || message.contains("challenge")) return "anti_bot";
        if (message.contains("proxy")) return "proxy";
        if (error != null) return "runtime";
        return "ok";
    }
}
