package com.javaspider.cli;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.javaspider.audit.AuditEvent;
import com.javaspider.audit.InMemoryAuditTrail;
import com.javaspider.connector.InMemoryConnector;
import com.javaspider.graph.GraphBuilder;
import com.javaspider.session.SessionProfile;
import com.javaspider.workflow.CaptchaRecoveryResult;
import com.javaspider.workflow.ExecutionPolicy;
import com.javaspider.workflow.FlowJob;
import com.javaspider.workflow.FlowResult;
import com.javaspider.workflow.FlowStep;
import com.javaspider.workflow.FlowStepType;
import com.javaspider.workflow.WorkflowExecutionContext;
import com.javaspider.workflow.WorkflowSpider;
import org.jsoup.Jsoup;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public final class WorkflowReplayCLI {
    private static final ObjectMapper MAPPER = new ObjectMapper();

    private WorkflowReplayCLI() {
    }

    public static void main(String[] args) {
        if (args.length < 2 || !"--file".equals(args[0])) {
            System.out.println("Usage: WorkflowReplayCLI --file <replay.json>");
            return;
        }

        long startedAt = System.nanoTime();
        ReplaySpec spec = null;
        try {
            spec = loadSpec(Path.of(args[1]));
            ReplaySpec loadedSpec = spec;
            InMemoryAuditTrail auditTrail = new InMemoryAuditTrail();
            InMemoryConnector connector = new InMemoryConnector();
            WorkflowSpider spider = new WorkflowSpider(auditTrail)
                .addConnector(connector)
                .setExecutionContextFactory(session -> new ReplayWorkflowExecutionContext(loadedSpec));

            FlowResult result = spider.execute(buildJob(loadedSpec));
            FlowResult normalized = withGraphArtifact(loadedSpec, result);
            String rendered = renderPayload(normalized, loadedSpec, auditTrail.list(), "", elapsedMillis(startedAt));
            persistIfRequested(loadedSpec, rendered);
            System.out.println(rendered);
        } catch (Exception e) {
            try {
                String rendered = renderFailurePayload(spec, e, elapsedMillis(startedAt));
                persistIfRequested(spec, rendered);
                System.out.println(rendered);
            } catch (IOException ignored) {
                // Preserve original failure path when payload rendering also fails.
            }
            throw new RuntimeException("workflow replay failed", e);
        }
    }

    private static ReplaySpec loadSpec(Path path) throws IOException {
        Map<String, Object> raw = MAPPER.readValue(Files.readString(path), new TypeReference<Map<String, Object>>() {});
        ReplaySpec spec = new ReplaySpec();
        spec.name = stringValue(raw.get("name"), path.getFileName().toString());
        spec.targetUrl = stringValue(mapValue(raw.get("target")).get("url"), "https://example.com");
        spec.output = mapValue(raw.get("output"));
        spec.outputPath = stringValue(spec.output.get("path"), "");
        spec.metadata = new LinkedHashMap<>(mapValue(raw.get("metadata")));
        spec.outputContract = mapValue(raw.get("output_contract"));
        spec.steps = listOfMaps(raw.get("steps"));
        hydrateFixtureHtml(spec, path, stringValue(raw.get("fixture_path"), ""));
        if (spec.steps.isEmpty()) {
            spec.steps = List.of(
                Map.of("id", "goto", "type", "GOTO", "metadata", Map.of("url", spec.targetUrl)),
                Map.of("id", "extract-title", "type", "EXTRACT", "metadata", Map.of("field", "title")),
                Map.of("id", "capture", "type", "SCREENSHOT", "value", "artifacts/workflow-replay.png", "metadata", Map.of("artifact", "artifacts/workflow-replay.png"))
            );
        }
        return spec;
    }

    private static void hydrateFixtureHtml(ReplaySpec spec, Path specPath, String fixturePath) throws IOException {
        if (fixturePath.isBlank() || spec.metadata.containsKey("mock_html")) {
            return;
        }

        Path resolved = resolveFixturePath(specPath, fixturePath);
        if (resolved != null && Files.exists(resolved)) {
            spec.metadata.put("mock_html", Files.readString(resolved, StandardCharsets.UTF_8));
        }
    }

    private static Path resolveFixturePath(Path specPath, String fixturePath) {
        Path candidate = Path.of(fixturePath);
        if (candidate.isAbsolute()) {
            return candidate;
        }

        List<Path> candidates = List.of(
            specPath.getParent().resolve(fixturePath).normalize(),
            specPath.getParent().getParent().getParent().resolve(fixturePath).normalize()
        );
        for (Path path : candidates) {
            if (Files.exists(path)) {
                return path;
            }
        }
        return candidates.get(candidates.size() - 1);
    }

    private static FlowJob buildJob(ReplaySpec spec) {
        List<FlowStep> steps = new ArrayList<>();
        for (Map<String, Object> step : spec.steps) {
            Map<String, Object> metadata = mapValue(step.get("metadata"));
            steps.add(new FlowStep(
                stringValue(step.get("id"), "step"),
                FlowStepType.valueOf(stringValue(step.get("type"), "WAIT")),
                stringValue(step.get("selector"), ""),
                stringValue(step.get("value"), ""),
                metadata
            ));
        }

        return new FlowJob(
            "workflow-replay-" + Instant.now().toEpochMilli(),
            spec.name,
            new SessionProfile("session-replay", "local-user", "replay", "chrome-stealth", Map.of()),
            steps,
            spec.outputContract,
            new ExecutionPolicy(5_000L, 1)
        );
    }

    private static String renderPayload(
        FlowResult result,
        ReplaySpec spec,
        List<AuditEvent> auditEvents,
        String error,
        long latencyMillis
    ) throws IOException {
        Map<String, Object> payload = new LinkedHashMap<>();
        Map<String, Object> artifactEnvelope = artifactEnvelopeFromPaths(result.getArtifacts());
        payload.put("job_name", spec.name);
        payload.put("state", error.isBlank() ? "succeeded" : "failed");
        payload.put("target_url", spec.targetUrl);
        payload.put("extract", result.getExtracted());
        payload.put("artifacts", artifactEnvelope);
        payload.put("artifact_refs", artifactEnvelope);
        payload.put("actions", listOfStrings(spec.metadata.get("mock_action_log")));
        payload.put("audit_events", auditEvents.stream().map(WorkflowReplayCLI::auditEventToMap).toList());
        payload.put("output", Map.of(
            "path", spec.outputPath,
            "format", stringValue(spec.output.get("format"), "json")
        ));
        payload.put("error", error);
        payload.put("metrics", Map.of(
            "latency_ms", Math.max(latencyMillis, 0L),
            "audit_event_count", auditEvents.size()
        ));
        return MAPPER.writerWithDefaultPrettyPrinter().writeValueAsString(payload);
    }

    private static String renderFailurePayload(ReplaySpec spec, Exception error, long latencyMillis) throws IOException {
        FlowResult empty = new FlowResult("", "", Map.of(), List.of());
        return renderPayload(
            empty,
            spec == null ? new ReplaySpec() : spec,
            List.of(),
            stringValue(error.getMessage(), "workflow replay failed"),
            latencyMillis
        );
    }

    private static FlowResult withGraphArtifact(ReplaySpec spec, FlowResult result) {
        List<String> artifacts = new ArrayList<>(result.getArtifacts());
        String html = stringValue(spec.metadata.get("mock_html"), "");
        if (!html.isBlank()) {
            try {
                Path path = persistReplayGraph(spec, html);
                if (!artifacts.contains(path.toString())) {
                    artifacts.add(path.toString());
                }
            } catch (IOException ignored) {
                // Best effort graph artifact generation should not fail workflow replay.
            }
        }
        return new FlowResult(result.getJobId(), result.getRunId(), result.getExtracted(), artifacts);
    }

    private static Path persistReplayGraph(ReplaySpec spec, String html) throws IOException {
        GraphBuilder builder = new GraphBuilder().buildFromHtml(html);
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("root_id", builder.rootId());
        payload.put("nodes", builder.nodes());
        payload.put("edges", builder.edges());
        payload.put("stats", builder.stats());
        Path base = spec.outputPath.isBlank() ? Path.of("artifacts", "workflow-replay") : Path.of(spec.outputPath).getParent();
        if (base == null) {
            base = Path.of("artifacts", "workflow-replay");
        }
        Path graphDir = base.resolve("graphs");
        Files.createDirectories(graphDir);
        Path path = graphDir.resolve(spec.name + "-graph.json");
        Files.writeString(path, MAPPER.writerWithDefaultPrettyPrinter().writeValueAsString(payload), StandardCharsets.UTF_8);
        return path;
    }

    private static Map<String, Object> artifactEnvelopeFromPaths(List<String> artifacts) {
        Map<String, Object> envelope = new LinkedHashMap<>();
        if (artifacts == null) {
            return envelope;
        }
        int counter = 1;
        for (String pathValue : artifacts) {
            if (pathValue == null || pathValue.isBlank()) {
                continue;
            }
            Path path = Path.of(pathValue);
            String fileName = path.getFileName() != null ? path.getFileName().toString() : pathValue;
            String key = fileName.contains("-graph.json") ? "graph" : "artifact_" + counter++;
            String lower = fileName.toLowerCase();
            String kind = lower.endsWith(".png") ? "screenshot" : (lower.endsWith(".html") ? "html" : (lower.endsWith(".json") ? "graph" : "artifact"));
            Map<String, Object> artifact = new LinkedHashMap<>();
            artifact.put("kind", kind);
            artifact.put("path", pathValue);
            if ("graph".equals(key) && Files.exists(path)) {
                try {
                    Map<String, Object> graphPayload = MAPPER.readValue(Files.readString(path), new TypeReference<Map<String, Object>>() {});
                    artifact.put("root_id", stringValue(graphPayload.get("root_id"), "document"));
                    artifact.put("stats", mapValue(graphPayload.get("stats")));
                } catch (IOException ignored) {
                    // keep minimal envelope
                }
            }
            envelope.putIfAbsent(key, artifact);
        }
        return envelope;
    }

    private static Map<String, Object> auditEventToMap(AuditEvent event) {
        return Map.of(
            "job_id", event.getJobId(),
            "step_id", event.getStepId(),
            "type", event.getType(),
            "timestamp", event.getTimestamp().toString(),
            "payload", event.getPayload()
        );
    }

    private static void persistIfRequested(ReplaySpec spec, String rendered) throws IOException {
        if (spec == null || spec.outputPath.isBlank() || !"json".equalsIgnoreCase(stringValue(spec.output.get("format"), "json"))) {
            return;
        }
        Path outputPath = Path.of(spec.outputPath);
        Path parent = outputPath.getParent();
        if (parent != null) {
            Files.createDirectories(parent);
        }
        Files.writeString(outputPath, rendered, StandardCharsets.UTF_8);
    }

    private static long elapsedMillis(long startedAt) {
        return (System.nanoTime() - startedAt) / 1_000_000L;
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> mapValue(Object value) {
        if (value instanceof Map<?, ?> map) {
            return (Map<String, Object>) map;
        }
        return Map.of();
    }

    @SuppressWarnings("unchecked")
    private static List<Map<String, Object>> listOfMaps(Object value) {
        if (value instanceof List<?> list) {
            List<Map<String, Object>> result = new ArrayList<>();
            for (Object item : list) {
                if (item instanceof Map<?, ?> map) {
                    result.add((Map<String, Object>) map);
                }
            }
            return result;
        }
        return List.of();
    }

    private static String stringValue(Object value, String fallback) {
        if (value == null) {
            return fallback;
        }
        String text = String.valueOf(value);
        return text.isBlank() ? fallback : text;
    }

    private static boolean boolValue(Object value, boolean fallback) {
        if (value instanceof Boolean bool) {
            return bool;
        }
        if (value == null) {
            return fallback;
        }
        return Boolean.parseBoolean(String.valueOf(value));
    }

    private static int intValue(Object value, int fallback) {
        if (value instanceof Number number) {
            return number.intValue();
        }
        if (value == null) {
            return fallback;
        }
        try {
            return Integer.parseInt(String.valueOf(value));
        } catch (NumberFormatException ignored) {
            return fallback;
        }
    }

    private static List<String> listOfStrings(Object value) {
        if (!(value instanceof List<?> list)) {
            return List.of();
        }
        List<String> result = new ArrayList<>();
        for (Object item : list) {
            String text = stringValue(item, "");
            if (!text.isBlank()) {
                result.add(text);
            }
        }
        return result;
    }

    private static final class ReplaySpec {
        private String name = "workflow-replay";
        private String targetUrl = "https://example.com";
        private String outputPath = "";
        private Map<String, Object> output = Map.of();
        private Map<String, Object> metadata = Map.of();
        private Map<String, Object> outputContract = Map.of();
        private List<Map<String, Object>> steps = List.of();
    }

    private static final class ReplayWorkflowExecutionContext implements WorkflowExecutionContext {
        private final ReplaySpec spec;
        private String currentUrl;

        private ReplayWorkflowExecutionContext(ReplaySpec spec) {
            this.spec = spec;
            this.currentUrl = spec.targetUrl;
        }

        @Override
        public void gotoUrl(String url) {
            currentUrl = stringValue(url, currentUrl);
            appendAction("goto:" + currentUrl);
        }

        @Override
        public void waitFor(long timeoutMillis) {
        }

        @Override
        public void click(String selector) {
            requireSelectorExists(selector);
            appendAction("click:" + selector);
        }

        @Override
        public void type(String selector, String value) {
            requireSelectorExists(selector);
            appendAction("type:" + selector + "=" + value);
        }

        @Override
        public void select(String selector, String value, Map<String, Object> options) {
            requireSelectorExists(selector);
            appendAction("select:" + selector + "=" + value);
        }

        @Override
        public void hover(String selector) {
            requireSelectorExists(selector);
            appendAction("hover:" + selector);
        }

        @Override
        public void scroll(String selector, Map<String, Object> options) {
            if (selector != null && !selector.isBlank()) {
                requireSelectorExists(selector);
                appendAction("scroll:" + selector);
                return;
            }
            String mode = stringValue(options.get("mode"), "bottom");
            appendAction("scroll-mode:" + mode);
        }

        @Override
        public Object evaluate(String script) {
            appendAction("eval:" + script);
            return spec.metadata.get("mock_eval_result");
        }

        @Override
        public List<Map<String, Object>> listenNetwork(Map<String, Object> options) {
            appendAction("listen_network");
            return listOfMaps(spec.metadata.get("mock_network_requests"));
        }

        @Override
        public String captureHtml() {
            String html = stringValue(spec.metadata.get("mock_html"), "");
            if (!html.isBlank()) {
                return html;
            }
            return "<html><title>" + title() + "</title><body>captcha challenge</body></html>";
        }

        @Override
        public void captureScreenshot(String artifactPath) {
            try {
                Path path = Path.of(artifactPath);
                Path parent = path.getParent();
                if (parent != null) {
                    Files.createDirectories(parent);
                }
                Files.writeString(path, stringValue(spec.metadata.get("mock_artifact_content"), "workflow-replay-artifact"), StandardCharsets.UTF_8);
                appendAction("shot:" + artifactPath);
            } catch (IOException e) {
                throw new RuntimeException("failed to write replay artifact", e);
            }
        }

        @Override
        public String currentUrl() {
            return stringValue(spec.metadata.get("mock_url"), currentUrl);
        }

        @Override
        public String title() {
            return stringValue(spec.metadata.get("mock_title"), "Workflow Replay");
        }

        @Override
        public boolean challengeDetected() {
            return boolValue(spec.metadata.get("mock_challenge_detected"), captureHtml().toLowerCase().contains("challenge"));
        }

        @Override
        public boolean captchaDetected() {
            return boolValue(spec.metadata.get("mock_captcha_detected"), captureHtml().toLowerCase().contains("captcha"));
        }

        @Override
        public CaptchaRecoveryResult recoverCaptcha(Map<String, Object> options) {
            Map<String, Object> recovery = mapValue(spec.metadata.get("mock_recovery_result"));
            if (!recovery.isEmpty()) {
                boolean solved = boolValue(recovery.get("solved"), true);
                String solver = stringValue(recovery.get("solver"), "mock");
                boolean continued = boolValue(recovery.get("continued"), true);
                int solutionLength = intValue(recovery.get("solution_length"), 4);
                if (solved) {
                    return CaptchaRecoveryResult.solved(solver, continued, solutionLength);
                }
                return CaptchaRecoveryResult.failed(solver, stringValue(recovery.get("reason"), "replay recovery failed"));
            }
            String mockSolution = stringValue(options.get("mock_solution"), "");
            if (!mockSolution.isBlank()) {
                return CaptchaRecoveryResult.solved("mock", true, mockSolution.length());
            }
            return CaptchaRecoveryResult.notAttempted();
        }

        @Override
        public String proxyHealth() {
            return stringValue(spec.metadata.get("mock_proxy_health"), "not-configured");
        }

        @Override
        public void close() {
        }

        @SuppressWarnings("unchecked")
        private void appendAction(String action) {
            Object existing = spec.metadata.get("mock_action_log");
            if (existing instanceof List<?> list) {
                ((List<Object>) list).add(action);
                return;
            }
            List<String> actions = new ArrayList<>();
            actions.add(action);
            spec.metadata = new LinkedHashMap<>(spec.metadata);
            spec.metadata.put("mock_action_log", actions);
        }

        private void requireSelectorExists(String selector) {
            String html = captureHtml();
            if (selector.isBlank()) {
                return;
            }
            if (Jsoup.parse(html).select(selector).isEmpty()) {
                throw new IllegalStateException("selector not found in replay fixture: " + selector);
            }
        }
    }
}
