package com.javaspider.api;

import com.javaspider.cli.SuperSpiderCLI;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.List;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;

public final class ApiServer {
    private static final ObjectMapper MAPPER = new ObjectMapper();

    private final HttpServer server;
    private final Map<String, Map<String, Object>> jobs = new ConcurrentHashMap<>();

    public ApiServer(String host, int port) throws IOException {
        this.server = HttpServer.create(new InetSocketAddress(host, port), 0);
        server.createContext("/health", exchange -> writeJson(exchange, 200, Map.of(
            "status", "ok",
            "runtime", "java",
            "server", "api"
        )));
        server.createContext("/jobs", new JobsHandler());
    }

    public void start() {
        server.start();
    }

    public void stop() {
        server.stop(0);
    }

    public int port() {
        return server.getAddress().getPort();
    }

    private final class JobsHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            String method = exchange.getRequestMethod();
            String path = exchange.getRequestURI().getPath();
            if ("POST".equalsIgnoreCase(method) && "/jobs".equals(path)) {
                Map<String, Object> spec = readJson(exchange.getRequestBody());
                String jobId = "job-" + UUID.randomUUID();
                Map<String, Object> payload = new LinkedHashMap<>();
                payload.put("job_id", jobId);
                payload.put("status", "accepted");
                payload.put("received_at", Instant.now().toString());
                payload.put("runtime", String.valueOf(spec.getOrDefault("runtime", "")));
                Object targetRaw = spec.getOrDefault("target", Map.of());
                Map<?, ?> target = targetRaw instanceof Map<?, ?> map ? map : Map.of();
                Object targetUrl = target.containsKey("url") ? target.get("url") : "";
                payload.put("url", String.valueOf(targetUrl));
                payload.put("spec", spec);
                payload.put("started_at", "");
                payload.put("finished_at", "");
                payload.put("result", Map.of());
                jobs.put(jobId, payload);
                CompletableFuture.runAsync(() -> executeJob(jobId, spec));
                writeJson(exchange, 202, payload);
                return;
            }
            if ("GET".equalsIgnoreCase(method) && "/jobs".equals(path)) {
                writeJson(exchange, 200, Map.of("jobs", jobs.values()));
                return;
            }
            if ("GET".equalsIgnoreCase(method) && path.startsWith("/jobs/")) {
                String jobId = jobIdFromPath(path);
                Map<String, Object> payload = jobs.get(jobId);
                if (payload == null) {
                    writeJson(exchange, 404, Map.of("error", "job not found", "job_id", jobId));
                    return;
                }
                if (path.endsWith("/result")) {
                    writeJson(exchange, 200, payload.getOrDefault("result", Map.of()));
                    return;
                }
                writeJson(exchange, 200, payload);
                return;
            }
            writeJson(exchange, 404, Map.of("error", "not found"));
        }
    }

    private void executeJob(String jobId, Map<String, Object> spec) {
        Map<String, Object> current = jobs.get(jobId);
        if (current == null) {
            return;
        }
        current.put("status", "running");
        current.put("started_at", Instant.now().toString());

        try {
            Map<String, Object> result = SuperSpiderCLI.runJobSpec(spec);
            current.put("status", String.valueOf(result.getOrDefault("state", "succeeded")));
            current.put("finished_at", Instant.now().toString());
            current.put("result", result);
        } catch (Exception e) {
            current.put("status", "failed");
            current.put("finished_at", Instant.now().toString());
            current.put("result", Map.of(
                "job_id", jobId,
                "state", "failed",
                "error", String.valueOf(e.getMessage())
            ));
        }
    }

    private static String jobIdFromPath(String path) {
        String suffix = path.substring("/jobs/".length());
        if (suffix.endsWith("/result")) {
            return suffix.substring(0, suffix.length() - "/result".length());
        }
        return suffix;
    }

    private static Map<String, Object> readJson(InputStream stream) throws IOException {
        return MAPPER.readValue(stream, new TypeReference<Map<String, Object>>() {});
    }

    private static void writeJson(HttpExchange exchange, int status, Object payload) throws IOException {
        byte[] body = MAPPER.writeValueAsString(payload).getBytes(StandardCharsets.UTF_8);
        exchange.getResponseHeaders().set("Content-Type", "application/json");
        exchange.sendResponseHeaders(status, body.length);
        try (OutputStream output = exchange.getResponseBody()) {
            output.write(body);
        }
    }
}
