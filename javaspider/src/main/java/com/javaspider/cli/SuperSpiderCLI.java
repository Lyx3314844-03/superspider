package com.javaspider.cli;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.javaspider.EnhancedSpider;
import com.javaspider.audit.AuditTrail;
import com.javaspider.audit.CompositeAuditTrail;
import com.javaspider.audit.FileAuditTrail;
import com.javaspider.audit.InMemoryAuditTrail;
import com.javaspider.connector.FileConnector;
import com.javaspider.connector.InMemoryConnector;
import com.javaspider.graph.GraphBuilder;
import com.javaspider.session.SessionProfile;
import com.javaspider.util.JsonlWriterRegistry;
import com.javaspider.workflow.ExecutionPolicy;
import com.javaspider.workflow.FlowJob;
import com.javaspider.workflow.FlowResult;
import com.javaspider.workflow.FlowStep;
import com.javaspider.workflow.FlowStepType;
import com.javaspider.workflow.WorkflowExecutionContext;
import com.javaspider.workflow.WorkflowSpider;

import java.io.IOException;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;

public final class SuperSpiderCLI {
    private static final ObjectMapper MAPPER = new ObjectMapper();

    private SuperSpiderCLI() {
    }

    public static void main(String[] args) {
        if (args.length == 0) {
            printUsage();
            return;
        }

        String command = args[0];
        String[] rest = slice(args, 1);
        switch (command) {
            case "config", "crawl", "browser", "ai", "doctor", "export", "curl", "jobdir", "http-cache", "console" -> EnhancedSpider.main(args);
            case "workflow" -> WorkflowSpiderCLI.main(rest);
            case "media" -> MediaDownloaderCLI.main(rest);
            case "job" -> handleJob(rest);
            case "capabilities" -> printCapabilities();
            case "version", "-v", "--version" -> EnhancedSpider.main(new String[]{"version"});
            case "help", "--help", "-h" -> printUsage();
            default -> {
                System.out.println("Unknown command: " + command);
                printUsage();
            }
        }
    }

    private static void handleJob(String[] args) {
        if (args.length < 2 || !"--file".equals(args[0])) {
            System.out.println("Usage: SuperSpiderCLI job --file <job.json>");
            return;
        }

        JobSpec spec = null;
        long startedAt = System.nanoTime();
        try {
            spec = loadJobSpec(Path.of(args[1]));
            enforceJobPolicies(spec);
            String injectedFailure = stringValue(spec.metadata.get("fail_job"), "");
            if (!injectedFailure.isBlank()) {
                throw new IllegalStateException("injected failure: " + injectedFailure);
            }
            applyRateLimit(spec);
            FlowResult result = executeJob(spec);
            Map<String, Object> extracted = resolveStructuredExtract(spec, result);
            List<String> artifacts = augmentArtifactsWithGraph(spec, result.getArtifacts(), extracted);
            enforceResultBudget(spec, result, extracted, elapsedMillis(startedAt));
            String rendered = renderJobPayload(
                spec,
                "succeeded",
                extracted,
                artifacts,
                "",
                result.getJobId(),
                result.getRunId(),
                elapsedMillis(startedAt)
            );
            persistEnvelopeIfRequested(spec, rendered);
            System.out.println(rendered);
        } catch (Exception e) {
            try {
                String rendered = renderJobPayload(
                    spec,
                    "failed",
                    Map.of(),
                    List.of(),
                    stringValue(e.getMessage(), "job execution failed"),
                    "",
                    "",
                    elapsedMillis(startedAt)
                );
                persistEnvelopeIfRequested(spec, rendered);
                System.out.println(rendered);
            } catch (IOException ignored) {
                // Best effort: keep the original exception path even if payload rendering fails.
            }
            throw new RuntimeException("job execution failed", e);
        }
    }

    private static void enforceJobPolicies(JobSpec spec) {
        if (spec == null || spec.target == null) {
            return;
        }
        if (!List.of("http", "browser", "media", "ai").contains(stringValue(spec.runtime, "browser"))) {
            throw new IllegalArgumentException("unsupported runtime in JavaSpider job runtime: " + spec.runtime);
        }
        List<String> allowedDomains = effectiveAllowedDomains(spec);
        if (allowedDomains.isEmpty()) {
            return;
        }
        String host = extractHost(spec.target.url);
        if (host.isBlank()) {
            throw new IllegalArgumentException("target.url is missing host");
        }
        String normalizedHost = host.toLowerCase(Locale.ROOT);
        for (String allowedDomain : allowedDomains) {
            String normalizedAllowed = stringValue(allowedDomain, "").trim().toLowerCase(Locale.ROOT);
            if (!normalizedAllowed.isBlank() &&
                (normalizedHost.equals(normalizedAllowed) || normalizedHost.endsWith("." + normalizedAllowed))) {
                return;
            }
        }
        throw new IllegalArgumentException("target host " + host + " is outside allowed_domains");
    }

    private static List<String> effectiveAllowedDomains(JobSpec spec) {
        if (spec.target != null && spec.target.allowedDomains != null && !spec.target.allowedDomains.isEmpty()) {
            return spec.target.allowedDomains;
        }
        if (spec.policy != null && spec.policy.sameDomainOnly) {
            String host = extractHost(spec.target != null ? spec.target.url : "");
            if (!host.isBlank()) {
                return List.of(host);
            }
        }
        return List.of();
    }

    private static String extractHost(String url) {
        if (url == null || url.isBlank()) {
            return "";
        }
        try {
            URI uri = URI.create(url);
            return stringValue(uri.getHost(), "");
        } catch (IllegalArgumentException ignored) {
            return "";
        }
    }

    private static void applyRateLimit(JobSpec spec) {
        if (spec == null || spec.resources == null || spec.resources.rateLimitPerSec <= 0D) {
            return;
        }
        long delayMillis = Math.max(1L, (long) Math.ceil(1000D / spec.resources.rateLimitPerSec));
        try {
            Thread.sleep(delayMillis);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("rate limit wait interrupted", e);
        }
    }

    private static void enforceResultBudget(JobSpec spec, FlowResult result, Map<String, Object> extracted, long latencyMillis) {
        if (spec == null || spec.policy == null || spec.policy.budget == null || spec.policy.budget.isEmpty()) {
            return;
        }
        long wallTimeBudget = longValue(spec.policy.budget.get("wall_time_ms"), 0L);
        if (wallTimeBudget > 0 && latencyMillis > wallTimeBudget) {
            throw new IllegalStateException(
                "job exceeded budget.wall_time_ms: used=" + latencyMillis + " limit=" + wallTimeBudget
            );
        }
        long bytesBudget = longValue(spec.policy.budget.get("bytes_in"), 0L);
        if (bytesBudget > 0) {
            long bytesIn = estimateBytesIn(spec, result, extracted);
            if (bytesIn > bytesBudget) {
                throw new IllegalStateException(
                    "job exceeded budget.bytes_in: used=" + bytesIn + " limit=" + bytesBudget
                );
            }
        }
    }

    private static long estimateBytesIn(JobSpec spec, FlowResult result, Map<String, Object> extracted) {
        if (result != null && result.getExtracted() != null) {
            Object html = result.getExtracted().get("html");
            if (html instanceof String htmlString && !htmlString.isBlank()) {
                return htmlString.getBytes(StandardCharsets.UTF_8).length;
            }
            Object dom = result.getExtracted().get("dom");
            if (dom instanceof String domString && !domString.isBlank()) {
                return domString.getBytes(StandardCharsets.UTF_8).length;
            }
        }
        if (spec != null && spec.metadata != null) {
            String mockHtml = stringValue(spec.metadata.get("mock_html"), "");
            if (!mockHtml.isBlank()) {
                return mockHtml.getBytes(StandardCharsets.UTF_8).length;
            }
            String content = stringValue(spec.metadata.get("content"), "");
            if (!content.isBlank()) {
                return content.getBytes(StandardCharsets.UTF_8).length;
            }
        }
        if (spec != null && spec.target != null) {
            return stringValue(spec.target.body, "").getBytes(StandardCharsets.UTF_8).length;
        }
        if (extracted != null && !extracted.isEmpty()) {
            try {
                return MAPPER.writeValueAsBytes(extracted).length;
            } catch (IOException ignored) {
                return 0L;
            }
        }
        return 0L;
    }

    private static void printCapabilities() {
        try {
            System.out.println(MAPPER.writerWithDefaultPrettyPrinter().writeValueAsString(Map.ofEntries(
                Map.entry("command", "capabilities"),
                Map.entry("framework", "javaspider"),
                Map.entry("runtime", "java"),
                Map.entry("version", "2.1.0"),
                Map.entry("entrypoints", List.of(
                    "config",
                    "crawl",
                    "browser",
                    "ai",
                    "doctor",
                    "export",
                    "curl",
                    "ultimate",
                    "sitemap-discover",
                    "plugins",
                    "selector-studio",
                    "scrapy",
                    "profile-site",
                    "node-reverse",
                    "anti-bot",
                    "workflow",
                    "media",
                    "job",
                    "jobdir",
                    "http-cache",
                    "console",
                    "capabilities",
                    "version"
                )),
                Map.entry("runtimes", List.of("http", "browser", "media", "ai")),
                Map.entry("modules", List.of(
                    "EnhancedSpider",
                    "workflow.WorkflowSpider",
                    "cli.MediaDownloaderCLI",
                    "converter.CurlToJavaConverter",
                    "contracts.AutoscaledFrontier",
                    "contracts.RuntimeArtifactStore",
                    "audit.InMemoryAuditTrail",
                    "connector.InMemoryConnector",
                    "session.SessionProfile",
                    "nodereverse.NodeReverseClient",
                    "antibot.AntiBotHandler"
                )),
                Map.entry("shared_contracts", List.of(
                    "shared-cli",
                    "shared-config",
                    "runtime-core",
                    "autoscaled-frontier",
                    "incremental-cache",
                    "observability-envelope",
                    "scrapy-project",
                    "scrapy-plugins-manifest",
                    "web-control-plane"
                )),
                Map.entry("operator_products", Map.of(
                    "jobdir", Map.of(
                        "pause_resume", true,
                        "state_file", "job-state.json"
                    ),
                    "http_cache", Map.of(
                        "status_seed_clear", true,
                        "backends", List.of("file-json", "memory"),
                        "strategies", List.of("revalidate", "delta-fetch")
                    ),
                    "browser_tooling", Map.of(
                        "trace", true,
                        "har", true,
                        "route_mocking", true,
                        "codegen", true
                    ),
                    "autoscaling_pools", Map.of(
                        "frontier", true,
                        "request_queue", "priority-scheduler",
                        "session_pool", true,
                        "browser_pool", true
                    ),
                    "debug_console", Map.of(
                        "snapshot", true,
                        "tail", true,
                        "control_plane_jsonl", true
                    )
                )),
                Map.entry("control_plane", Map.of(
                    "task_api", true,
                    "result_envelope", true,
                    "artifact_refs", true,
                    "graph_artifact", true,
                    "graph_extract", true
                )),
                Map.entry("kernel_contracts", Map.of(
                    "request", List.of("core.Request"),
                    "fingerprint", List.of("contracts.RequestFingerprint"),
                    "frontier", List.of("contracts.AutoscaledFrontier"),
                    "scheduler", List.of("scheduler.Scheduler"),
                    "middleware", List.of("scrapy.SpiderMiddleware", "scrapy.DownloaderMiddleware"),
                    "artifact_store", List.of("contracts.RuntimeArtifactStore"),
                    "session_pool", List.of("contracts.RuntimeSessionPool.SessionPool"),
                    "proxy_policy", List.of("contracts.RuntimeProxyPolicy.ProxyPolicy"),
                    "observability", List.of("contracts.RuntimeObservability.ObservabilityCollector"),
                    "cache", List.of("core.IncrementalCrawler")
                )),
                Map.entry("observability", List.of(
                    "doctor",
                    "profile-site",
                    "selector-studio",
                    "scrapy doctor",
                    "scrapy profile",
                    "scrapy bench",
                    "prometheus",
                    "opentelemetry-json"
                ))
            )));
        } catch (IOException e) {
            throw new RuntimeException("failed to print capabilities", e);
        }
    }

    private static FlowResult executeJob(JobSpec spec) {
        InMemoryAuditTrail inMemoryAuditTrail = new InMemoryAuditTrail();
        InMemoryConnector inMemoryConnector = new InMemoryConnector();
        WorkflowSpider spider = new WorkflowSpider(buildAuditTrail(spec, inMemoryAuditTrail))
            .addConnector(inMemoryConnector);
        fileConnector(spec).ifPresent(spider::addConnector);
        if (shouldUseMockExecutionContext(spec)) {
            spider.setExecutionContextFactory(session -> new MockWorkflowExecutionContext(spec));
        }
        return spider.execute(buildFlowJob(spec));
    }

    private static AuditTrail buildAuditTrail(JobSpec spec, InMemoryAuditTrail inMemoryAuditTrail) {
        return fileAuditTrail(spec)
            .<AuditTrail>map(fileAudit -> new CompositeAuditTrail(inMemoryAuditTrail, fileAudit))
            .orElse(inMemoryAuditTrail);
    }

    private static java.util.Optional<FileAuditTrail> fileAuditTrail(JobSpec spec) {
        Path sinkDir = resolveSinkDirectory(spec);
        return sinkDir == null
            ? java.util.Optional.empty()
            : java.util.Optional.of(new FileAuditTrail(sinkDir.resolve(spec.name + "-audit.jsonl")));
    }

    private static java.util.Optional<FileConnector> fileConnector(JobSpec spec) {
        Path sinkDir = resolveSinkDirectory(spec);
        return sinkDir == null
            ? java.util.Optional.empty()
            : java.util.Optional.of(new FileConnector(sinkDir.resolve(spec.name + "-connector.jsonl")));
    }

    private static Path resolveSinkDirectory(JobSpec spec) {
        if (spec == null || spec.output == null) {
            return Path.of("artifacts", "control-plane");
        }
        if (spec.output.path != null && !spec.output.path.isBlank()) {
            Path outputPath = Path.of(spec.output.path);
            Path parent = outputPath.getParent();
            if (parent != null) {
                return parent.resolve("control-plane");
            }
        }
        return Path.of("artifacts", "control-plane");
    }

    private static FlowJob buildFlowJob(JobSpec spec) {
        return new FlowJob(
            "job-" + UUID.randomUUID(),
            spec.name,
            buildSessionProfile(spec),
            buildFlowSteps(spec),
            buildOutputContract(spec),
            new ExecutionPolicy(resolveStepTimeoutMillis(spec), resolveMaxRetries(spec))
        );
    }

    private static SessionProfile buildSessionProfile(JobSpec spec) {
        String proxyGroup = spec.antiBot != null
            ? stringValue(spec.antiBot.proxyPool, "default")
            : "default";
        String fingerprintPreset = spec.browser != null
            ? stringValue(spec.browser.profile, "chrome-stealth")
            : "chrome-stealth";
        if (fingerprintPreset.isBlank()) {
            fingerprintPreset = "chrome-stealth";
        }
        return new SessionProfile(
            "session-cli",
            "local-user",
            proxyGroup,
            fingerprintPreset,
            spec.target != null && spec.target.cookies != null ? spec.target.cookies : Map.of()
        );
    }

    private static List<FlowStep> buildFlowSteps(JobSpec spec) {
        List<FlowStep> steps = new ArrayList<>();
        boolean hasBrowserActions = spec.browser != null && spec.browser.actions != null && !spec.browser.actions.isEmpty();
        if (!hasBrowserActions && spec.target != null && !stringValue(spec.target.url, "").isBlank()) {
            steps.add(new FlowStep("goto", FlowStepType.GOTO, spec.target.url, null, Map.of("url", spec.target.url)));
        }
        appendBrowserActions(spec, steps);
        appendExtractSteps(spec, steps);
        appendCaptureSteps(spec, steps);
        appendDefaultArtifactStep(spec, steps);
        return steps;
    }

    private static void appendBrowserActions(JobSpec spec, List<FlowStep> steps) {
        if (spec.browser == null || spec.browser.actions == null) {
            return;
        }
        for (int index = 0; index < spec.browser.actions.size(); index++) {
            ActionSpec action = spec.browser.actions.get(index);
            FlowStep mapped = mapActionStep(spec, action, index);
            if (mapped != null) {
                steps.add(mapped);
            }
        }
    }

    private static FlowStep mapActionStep(JobSpec spec, ActionSpec action, int index) {
        String type = stringValue(action.type, "").toLowerCase();
        Map<String, Object> metadata = new LinkedHashMap<>();
        if (action.timeoutMs > 0) {
            metadata.put("timeout_ms", action.timeoutMs);
        }
        if (action.saveAs != null && !action.saveAs.isBlank()) {
            metadata.put("save_as", action.saveAs);
        }
        metadata.putAll(action.extra != null ? action.extra : Map.of());
        return switch (type) {
            case "goto" -> {
                String url = stringValue(action.url, stringValue(action.selector, spec.target != null ? spec.target.url : ""));
                metadata.put("url", url);
                yield new FlowStep("browser-goto-" + index, FlowStepType.GOTO, url, null, metadata);
            }
            case "wait" -> new FlowStep("browser-wait-" + index, FlowStepType.WAIT, null, null, metadata);
            case "click" -> new FlowStep("browser-click-" + index, FlowStepType.CLICK, stringValue(action.selector, ""), null, metadata);
            case "type" -> new FlowStep("browser-type-" + index, FlowStepType.TYPE, stringValue(action.selector, ""), stringValue(action.value, ""), metadata);
            case "select" -> new FlowStep("browser-select-" + index, FlowStepType.SELECT, stringValue(action.selector, ""), stringValue(action.value, ""), metadata);
            case "hover" -> new FlowStep("browser-hover-" + index, FlowStepType.HOVER, stringValue(action.selector, ""), null, metadata);
            case "scroll" -> {
                if (action.selector != null && !action.selector.isBlank()) {
                    metadata.put("mode", "element");
                }
                yield new FlowStep("browser-scroll-" + index, FlowStepType.SCROLL, stringValue(action.selector, ""), null, metadata);
            }
            case "eval" -> {
                String field = stringValue(action.saveAs, "");
                if (!field.isBlank()) {
                    metadata.put("field", field);
                }
                yield new FlowStep("browser-eval-" + index, FlowStepType.EVAL, null, stringValue(action.value, ""), metadata);
            }
            case "listen_network" -> {
                String field = stringValue(action.saveAs, "network_requests");
                metadata.put("field", field);
                yield new FlowStep("browser-network-" + index, FlowStepType.LISTEN_NETWORK, null, null, metadata);
            }
            case "screenshot" -> {
                String artifact = stringValue(action.value, resolveArtifactPath(spec, index));
                metadata.put("artifact", artifact);
                yield new FlowStep("browser-shot-" + index, FlowStepType.SCREENSHOT, null, artifact, metadata);
            }
            default -> {
                spec.warnings.add("unsupported browser action type in JavaSpider job runtime: " + type);
                yield null;
            }
        };
    }

    private static void appendExtractSteps(JobSpec spec, List<FlowStep> steps) {
    }

    private static Map<String, Object> resolveStructuredExtract(JobSpec spec, FlowResult result) {
        Map<String, Object> merged = new LinkedHashMap<>();
        if (result != null && result.getExtracted() != null) {
            merged.putAll(result.getExtracted());
        }
        if (spec != null && spec.metadata != null) {
            merged.putAll(mapValue(spec.metadata.get("mock_extract")));
        }
        if (spec == null || spec.extract == null || spec.extract.isEmpty()) {
            return merged;
        }

        String source = extractSourceDocument(spec, merged);
        if (source.isBlank()) {
            return merged;
        }
        com.javaspider.parser.HtmlParser htmlParser = new com.javaspider.parser.HtmlParser(source);
        JsonNode jsonNode = looksLikeJson(source) ? parseJson(source) : null;
        for (Map<String, Object> extractSpec : spec.extract) {
            String field = stringValue(extractSpec.get("field"), "");
            if (field.isBlank()) {
                continue;
            }
            Object value = evaluateExtractSpec(extractSpec, field, htmlParser, jsonNode, source, spec);
            boolean required = boolValue(extractSpec.get("required"), false);
            if (value == null || (value instanceof String str && str.isBlank())) {
                if (required) {
                    throw new IllegalStateException("required extract field \"" + field + "\" could not be resolved");
                }
                continue;
            }
            validateSchema(field, value, mapValue(extractSpec.get("schema")));
            merged.put(field, value);
        }
        return merged;
    }

    private static Object evaluateExtractSpec(
        Map<String, Object> extractSpec,
        String field,
        com.javaspider.parser.HtmlParser htmlParser,
        JsonNode jsonNode,
        String source,
        JobSpec spec
    ) {
        String type = stringValue(extractSpec.get("type"), "").toLowerCase(Locale.ROOT);
        String expr = stringValue(extractSpec.get("expr"), "");
        String attr = stringValue(extractSpec.get("attr"), "");
        String path = stringValue(extractSpec.get("path"), expr);
        return switch (type) {
            case "css" -> htmlParser.cssFirst(expr);
            case "css_attr" -> htmlParser.cssAttrFirst(expr, attr);
            case "xpath" -> htmlParser.xpathFirst(expr);
            case "regex" -> htmlParser.regexFirst(expr);
            case "json_path" -> jsonPathValue(jsonNode, path);
            case "ai" -> "title".equals(field) ? htmlParser.title() : ("url".equals(field) ? spec.target.url : null);
            default -> switch (field) {
                case "url" -> spec.target.url;
                case "html", "dom" -> source;
                default -> null;
            };
        };
    }

    private static String extractSourceDocument(JobSpec spec, Map<String, Object> extracted) {
        if (extracted != null) {
            Object html = extracted.get("html");
            if (html instanceof String htmlString && !htmlString.isBlank()) {
                return htmlString;
            }
            Object dom = extracted.get("dom");
            if (dom instanceof String domString && !domString.isBlank()) {
                return domString;
            }
            Object title = extracted.get("title");
            if (title instanceof String titleString && !titleString.isBlank()) {
                return "<html><head><title>" + titleString + "</title></head><body></body></html>";
            }
        }
        if (spec != null && spec.metadata != null) {
            String mockHtml = stringValue(spec.metadata.get("mock_html"), "");
            if (!mockHtml.isBlank()) {
                return mockHtml;
            }
            String content = stringValue(spec.metadata.get("content"), "");
            if (!content.isBlank()) {
                return content;
            }
        }
        if (spec != null && spec.target != null && spec.target.body != null && !spec.target.body.isBlank()) {
            return spec.target.body;
        }
        return "";
    }

    private static List<String> augmentArtifactsWithGraph(JobSpec spec, List<String> artifacts, Map<String, Object> extracted) {
        List<String> merged = new ArrayList<>(artifacts == null ? List.of() : artifacts);
        String source = extractSourceDocument(spec, extracted);
        if (source.isBlank()) {
            return merged;
        }
        try {
            Path sinkDir = resolveSinkDirectory(spec).resolve("graphs");
            Files.createDirectories(sinkDir);
            GraphBuilder builder = new GraphBuilder().buildFromHtml(source);
            Map<String, Object> payload = new LinkedHashMap<>();
            payload.put("root_id", builder.rootId());
            payload.put("nodes", builder.nodes());
            payload.put("edges", builder.edges());
            payload.put("stats", builder.stats());
            String base = spec != null && spec.name != null && !spec.name.isBlank() ? spec.name : "java-job";
            Path path = sinkDir.resolve(base + "-graph.json");
            Files.writeString(path, MAPPER.writerWithDefaultPrettyPrinter().writeValueAsString(payload), StandardCharsets.UTF_8);
            if (!merged.contains(path.toString())) {
                merged.add(path.toString());
            }
        } catch (IOException ignored) {
            // Best effort graph artifact generation should not fail the main job path.
        }
        return merged;
    }

    private static boolean looksLikeJson(String source) {
        String trimmed = source.trim();
        return trimmed.startsWith("{") || trimmed.startsWith("[");
    }

    private static JsonNode parseJson(String source) {
        try {
            return MAPPER.readTree(source);
        } catch (IOException ignored) {
            return null;
        }
    }

    private static Object jsonPathValue(JsonNode root, String path) {
        if (root == null || path == null || path.isBlank()) {
            return null;
        }
        JsonNode current = root;
        for (String part : path.split("\\.")) {
            if (current == null) {
                return null;
            }
            if (current.isArray()) {
                try {
                    current = current.path(Integer.parseInt(part));
                } catch (NumberFormatException e) {
                    return null;
                }
            } else {
                current = current.path(part);
            }
            if (current.isMissingNode()) {
                return null;
            }
        }
        if (current.isTextual()) {
            return current.asText();
        }
        if (current.isBoolean()) {
            return current.asBoolean();
        }
        if (current.isNumber()) {
            return current.numberValue();
        }
        return current.toString();
    }

    private static void validateSchema(String field, Object value, Map<String, Object> schema) {
        String expectedType = stringValue(schema.get("type"), "");
        if (expectedType.isBlank()) {
            return;
        }
        boolean valid = switch (expectedType) {
            case "string" -> value instanceof String;
            case "boolean" -> value instanceof Boolean;
            case "number", "integer" -> value instanceof Number;
            case "object" -> value instanceof Map<?, ?> || value instanceof JsonNode;
            case "array" -> value instanceof List<?>;
            default -> true;
        };
        if (!valid) {
            throw new IllegalStateException("extract field \"" + field + "\" violates schema.type=" + expectedType);
        }
    }

    private static void appendCaptureSteps(JobSpec spec, List<FlowStep> steps) {
        if (spec.browser == null || spec.browser.capture == null) {
            return;
        }
        for (String capture : spec.browser.capture) {
            String normalized = stringValue(capture, "").toLowerCase();
            switch (normalized) {
                case "html", "dom" -> steps.add(new FlowStep(
                    "capture-" + normalized,
                    FlowStepType.EXTRACT,
                    "html",
                    null,
                    Map.of("field", normalized.equals("dom") ? "dom" : "html")
                ));
                case "screenshot" -> steps.add(new FlowStep(
                    "capture-screenshot",
                    FlowStepType.SCREENSHOT,
                    null,
                    resolveArtifactPath(spec, steps.size()),
                    Map.of("artifact", resolveArtifactPath(spec, steps.size()))
                ));
                default -> spec.warnings.add("unsupported browser.capture value in JavaSpider job runtime: " + normalized);
            }
        }
    }

    private static void appendDefaultArtifactStep(JobSpec spec, List<FlowStep> steps) {
        boolean hasArtifactStep = steps.stream().anyMatch(step -> step.getType() == FlowStepType.SCREENSHOT || step.getType() == FlowStepType.DOWNLOAD);
        if (hasArtifactStep) {
            return;
        }
        String artifactPath = resolveArtifactPath(spec, 0);
        steps.add(new FlowStep(
            "artifact",
            FlowStepType.SCREENSHOT,
            null,
            artifactPath,
            Map.of("artifact", artifactPath)
        ));
    }

    private static String resolveArtifactPath(JobSpec spec, int index) {
        if (spec.output != null && spec.output.path != null && !spec.output.path.isBlank() && !spec.output.path.toLowerCase().endsWith(".json")) {
            return spec.output.path;
        }
        String prefix = spec.output != null ? stringValue(spec.output.artifactPrefix, "") : "";
        if (!prefix.isBlank()) {
            return "artifacts/" + prefix + "-" + index + ".png";
        }
        return "artifacts/" + spec.name + ".png";
    }

    private static Map<String, Object> buildOutputContract(JobSpec spec) {
        Map<String, Object> outputContract = new LinkedHashMap<>();
        outputContract.put("format", spec.output != null ? stringValue(spec.output.format, "json") : "json");
        if (spec.resources != null && spec.resources.timeoutMs > 0) {
            outputContract.put("stepTimeoutMillis", spec.resources.timeoutMs);
        }
        if (spec.resources != null && spec.resources.retries > 0) {
            outputContract.put("maxRetries", spec.resources.retries);
        }
        if (spec.antiBot != null) {
            outputContract.put("anti_bot", spec.antiBot.toMap());
        }
        if (spec.policy != null) {
            outputContract.put("policy", spec.policy.toMap());
        }
        if (spec.schedule != null) {
            outputContract.put("schedule", spec.schedule.toMap());
        }
        if (spec.browser != null) {
            outputContract.put("browser", spec.browser.toMap());
        }
        if (!spec.warnings.isEmpty()) {
            outputContract.put("warnings", List.copyOf(spec.warnings));
        }
        return outputContract;
    }

    private static long resolveStepTimeoutMillis(JobSpec spec) {
        if (spec.resources != null && spec.resources.timeoutMs > 0) {
            return spec.resources.timeoutMs;
        }
        if (spec.target != null && spec.target.timeoutMs > 0) {
            return spec.target.timeoutMs;
        }
        return 5000L;
    }

    private static int resolveMaxRetries(JobSpec spec) {
        if (spec.resources != null && spec.resources.retries > 0) {
            return spec.resources.retries;
        }
        return 1;
    }

    private static boolean shouldUseMockExecutionContext(JobSpec spec) {
        if (spec == null || spec.metadata == null || spec.metadata.isEmpty()) {
            return false;
        }
        return spec.metadata.containsKey("mock_extract")
            || spec.metadata.containsKey("mock_html")
            || spec.metadata.containsKey("mock_title")
            || spec.metadata.containsKey("mock_artifact_content")
            || spec.metadata.containsKey("mock_url");
    }

    private static void persistEnvelopeIfRequested(JobSpec spec, String rendered) throws IOException {
        persistSharedControlPlaneArtifacts(spec, rendered);
        if (spec == null || spec.output == null || spec.output.path == null || spec.output.path.isBlank()) {
            return;
        }
        String format = stringValue(spec.output.format, "json");
        if (!"json".equalsIgnoreCase(format) || !spec.output.path.toLowerCase().endsWith(".json")) {
            return;
        }
        Path outputPath = Path.of(spec.output.path);
        Path parent = outputPath.getParent();
        if (parent != null) {
            Files.createDirectories(parent);
        }
        Files.writeString(outputPath, rendered, StandardCharsets.UTF_8);
    }

    private static void persistSharedControlPlaneArtifacts(JobSpec spec, String rendered) throws IOException {
        if (spec == null) {
            return;
        }
        Path sinkDir = resolveSinkDirectory(spec);
        Map<String, Object> payload = MAPPER.readValue(rendered, new TypeReference<Map<String, Object>>() {});
        Map<String, Object> resultRecord = new LinkedHashMap<>();
        resultRecord.put("job_name", stringValue(payload.get("job_name"), spec.name));
        resultRecord.put("runtime", stringValue(payload.get("runtime"), spec.runtime));
        resultRecord.put("state", stringValue(payload.get("state"), ""));
        resultRecord.put("url", stringValue(payload.get("url"), spec.target != null ? spec.target.url : ""));
        resultRecord.put("extract", mapValue(payload.get("extract")));
        resultRecord.put("artifacts", payload.get("artifacts"));
        resultRecord.put("output", mapValue(payload.get("output")));
        resultRecord.put("error", stringValue(payload.get("error"), ""));
        resultRecord.put("metrics", mapValue(payload.get("metrics")));
        appendJsonlRecord(sinkDir.resolve("results.jsonl"), resultRecord);

        Map<String, Object> eventRecord = new LinkedHashMap<>();
        eventRecord.put("type", "job_state");
        eventRecord.put("job_name", stringValue(payload.get("job_name"), spec.name));
        eventRecord.put("runtime", stringValue(payload.get("runtime"), spec.runtime));
        eventRecord.put("state", stringValue(payload.get("state"), ""));
        eventRecord.put("url", stringValue(payload.get("url"), spec.target != null ? spec.target.url : ""));
        eventRecord.put("error", stringValue(payload.get("error"), ""));
        eventRecord.put("timestamp", java.time.Instant.now().toString());
        appendJsonlRecord(sinkDir.resolve("events.jsonl"), eventRecord);
    }

    private static void appendJsonlRecord(Path path, Map<String, Object> payload) throws IOException {
        JsonlWriterRegistry.append(
            path,
            (MAPPER.writeValueAsString(payload) + System.lineSeparator()).getBytes(StandardCharsets.UTF_8)
        );
    }

    private static String renderJobPayload(
        JobSpec spec,
        String state,
        Map<String, Object> extract,
        List<String> artifacts,
        String error,
        String jobId,
        String runId,
        long latencyMillis
    ) throws IOException {
        Map<String, Object> payload = new LinkedHashMap<>();
        Map<String, Object> artifactEnvelope = artifactEnvelopeFromPaths(artifacts);
        payload.put("job_name", spec != null ? spec.name : "");
        payload.put("runtime", spec != null ? spec.runtime : "");
        payload.put("state", state);
        payload.put("url", spec != null && spec.target != null ? spec.target.url : "");
        payload.put("extract", extract);
        payload.put("artifacts", artifactEnvelope);
        payload.put("artifact_refs", artifactEnvelope);
        payload.put("output", Map.of(
            "format", spec != null && spec.output != null ? stringValue(spec.output.format, "json") : "json",
            "path", spec != null && spec.output != null ? stringValue(spec.output.path, "") : "",
            "directory", spec != null && spec.output != null ? stringValue(spec.output.directory, "") : "",
            "artifact_prefix", spec != null && spec.output != null ? stringValue(spec.output.artifactPrefix, "") : ""
        ));
        Map<String, Object> metadata = spec != null ? spec.metadata : Map.of();
        Map<String, Object> antiBot = effectiveAntiBot(spec, metadata);
        if (!antiBot.isEmpty()) {
            payload.put("anti_bot", antiBot);
        }
        if (spec != null && spec.browser != null) {
            payload.put("browser", spec.browser.toMap());
        }
        if (spec != null && spec.resources != null) {
            payload.put("resources", spec.resources.toMap());
        }
        if (spec != null && spec.policy != null) {
            payload.put("policy", spec.policy.toMap());
        }
        if (spec != null && spec.schedule != null) {
            payload.put("schedule", spec.schedule.toMap());
        }
        Map<String, Object> recovery = mapValue(metadata.get("mock_recovery"));
        if (!recovery.isEmpty()) {
            payload.put("recovery", recovery);
        }
        List<String> warnings = new ArrayList<>();
        if (spec != null) {
            warnings.addAll(spec.warnings);
        }
        warnings.addAll(listOfStrings(metadata.get("mock_warnings")));
        if (!warnings.isEmpty()) {
            payload.put("warnings", warnings);
        }
        payload.put("error", stringValue(error, ""));
        payload.put("metrics", Map.of("latency_ms", Math.max(latencyMillis, 0L)));
        payload.put("job_id", stringValue(jobId, ""));
        payload.put("run_id", stringValue(runId, ""));
        return MAPPER.writerWithDefaultPrettyPrinter().writeValueAsString(payload);
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
            String lower = fileName.toLowerCase(Locale.ROOT);
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
                    // keep path-only artifact envelope on read failure
                }
            }
            envelope.putIfAbsent(key, artifact);
        }
        return envelope;
    }

    private static long elapsedMillis(long startedAt) {
        return (System.nanoTime() - startedAt) / 1_000_000L;
    }

    private static JobSpec loadJobSpec(Path path) throws IOException {
        Map<String, Object> raw = MAPPER.readValue(Files.readString(path), new TypeReference<Map<String, Object>>() {});
        JobSpec spec = new JobSpec();
        spec.name = stringValue(raw.get("name"), "job");
        spec.runtime = stringValue(raw.get("runtime"), "browser");
        spec.priority = intValue(raw.get("priority"), 0);
        spec.target = parseTargetSpec(mapValue(raw.get("target")));
        spec.output = parseOutputSpec(mapValue(raw.get("output")));
        spec.extract = listOfMaps(raw.get("extract"));
        spec.browser = parseBrowserSpec(mapValue(raw.get("browser")));
        spec.resources = parseResourceSpec(mapValue(raw.get("resources")));
        spec.antiBot = parseAntiBotSpec(mapValue(raw.get("anti_bot")));
        spec.policy = parsePolicySpec(mapValue(raw.get("policy")));
        spec.schedule = parseScheduleSpec(mapValue(raw.get("schedule")));
        spec.metadata = new LinkedHashMap<>(mapValue(raw.get("metadata")));
        spec.warnings = new ArrayList<>();
        return spec;
    }

    private static TargetSpec parseTargetSpec(Map<String, Object> raw) {
        TargetSpec spec = new TargetSpec();
        spec.url = stringValue(raw.get("url"), "");
        spec.method = stringValue(raw.get("method"), "GET");
        spec.headers = mapOfStrings(raw.get("headers"));
        spec.cookies = mapOfStrings(raw.get("cookies"));
        spec.body = stringValue(raw.get("body"), "");
        spec.proxy = stringValue(raw.get("proxy"), "");
        spec.timeoutMs = longValue(raw.get("timeout_ms"), 0L);
        spec.allowedDomains = listOfStrings(raw.get("allowed_domains"));
        return spec;
    }

    private static OutputSpec parseOutputSpec(Map<String, Object> raw) {
        OutputSpec spec = new OutputSpec();
        spec.format = stringValue(raw.get("format"), "json");
        spec.path = stringValue(raw.get("path"), "");
        spec.directory = stringValue(raw.get("directory"), "");
        spec.artifactPrefix = stringValue(raw.get("artifact_prefix"), "");
        return spec;
    }

    private static BrowserSpec parseBrowserSpec(Map<String, Object> raw) {
        if (raw.isEmpty()) {
            return null;
        }
        BrowserSpec spec = new BrowserSpec();
        spec.headless = !raw.containsKey("headless") || boolValue(raw.get("headless"), true);
        spec.profile = stringValue(raw.get("profile"), "chrome-stealth");
        spec.capture = listOfStrings(raw.get("capture"));
        spec.actions = parseActionSpecs(raw.get("actions"));
        return spec;
    }

    private static List<ActionSpec> parseActionSpecs(Object value) {
        List<ActionSpec> actions = new ArrayList<>();
        for (Map<String, Object> raw : listOfMaps(value)) {
            ActionSpec action = new ActionSpec();
            action.type = stringValue(raw.get("type"), "");
            action.selector = stringValue(raw.get("selector"), "");
            action.value = stringValue(raw.get("value"), "");
            action.url = stringValue(raw.get("url"), "");
            action.timeoutMs = longValue(raw.get("timeout_ms"), 0L);
            action.optional = boolValue(raw.get("optional"), false);
            action.saveAs = stringValue(raw.get("save_as"), "");
            action.extra = new LinkedHashMap<>(mapValue(raw.get("extra")));
            actions.add(action);
        }
        return actions;
    }

    private static ResourceSpec parseResourceSpec(Map<String, Object> raw) {
        if (raw.isEmpty()) {
            return null;
        }
        ResourceSpec spec = new ResourceSpec();
        spec.concurrency = intValue(raw.get("concurrency"), 0);
        spec.retries = intValue(raw.get("retries"), 0);
        spec.timeoutMs = longValue(raw.get("timeout_ms"), 0L);
        spec.rateLimitPerSec = doubleValue(raw.get("rate_limit_per_sec"), 0D);
        spec.downloadDir = stringValue(raw.get("download_dir"), "");
        spec.tempDir = stringValue(raw.get("temp_dir"), "");
        return spec;
    }

    private static AntiBotSpec parseAntiBotSpec(Map<String, Object> raw) {
        if (raw.isEmpty()) {
            return null;
        }
        AntiBotSpec spec = new AntiBotSpec();
        spec.identityProfile = stringValue(raw.get("identity_profile"), "");
        spec.proxyPool = stringValue(raw.get("proxy_pool"), "");
        spec.sessionMode = stringValue(raw.get("session_mode"), "");
        spec.stealth = boolValue(raw.get("stealth"), false);
        spec.fallbackRuntime = stringValue(raw.get("fallback_runtime"), "");
        spec.challengePolicy = stringValue(raw.get("challenge_policy"), "");
        return spec;
    }

    private static PolicySpec parsePolicySpec(Map<String, Object> raw) {
        if (raw.isEmpty()) {
            return null;
        }
        PolicySpec spec = new PolicySpec();
        spec.maxPages = intValue(raw.get("max_pages"), 0);
        spec.maxDepth = intValue(raw.get("max_depth"), 0);
        spec.respectRobotsTxt = boolValue(raw.get("respect_robots_txt"), false);
        spec.sameDomainOnly = boolValue(raw.get("same_domain_only"), false);
        spec.budget = new LinkedHashMap<>(mapValue(raw.get("budget")));
        return spec;
    }

    private static ScheduleSpec parseScheduleSpec(Map<String, Object> raw) {
        if (raw.isEmpty()) {
            return null;
        }
        ScheduleSpec spec = new ScheduleSpec();
        spec.mode = stringValue(raw.get("mode"), "");
        spec.cron = stringValue(raw.get("cron"), "");
        spec.queueName = stringValue(raw.get("queue_name"), "");
        spec.delaySeconds = intValue(raw.get("delay_seconds"), 0);
        return spec;
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

    @SuppressWarnings("unchecked")
    private static Map<String, String> mapOfStrings(Object value) {
        if (!(value instanceof Map<?, ?> map)) {
            return Map.of();
        }
        Map<String, String> result = new LinkedHashMap<>();
        for (Map.Entry<?, ?> entry : map.entrySet()) {
            if (entry.getKey() != null && entry.getValue() != null) {
                result.put(String.valueOf(entry.getKey()), String.valueOf(entry.getValue()));
            }
        }
        return result;
    }

    private static String stringValue(Object value, String defaultValue) {
        if (value == null) {
            return defaultValue;
        }
        String stringValue = String.valueOf(value);
        return stringValue.isBlank() ? defaultValue : stringValue;
    }

    private static int intValue(Object value, int defaultValue) {
        if (value instanceof Number number) {
            return number.intValue();
        }
        if (value == null) {
            return defaultValue;
        }
        try {
            return Integer.parseInt(String.valueOf(value));
        } catch (NumberFormatException ignored) {
            return defaultValue;
        }
    }

    private static long longValue(Object value, long defaultValue) {
        if (value instanceof Number number) {
            return number.longValue();
        }
        if (value == null) {
            return defaultValue;
        }
        try {
            return Long.parseLong(String.valueOf(value));
        } catch (NumberFormatException ignored) {
            return defaultValue;
        }
    }

    private static double doubleValue(Object value, double defaultValue) {
        if (value instanceof Number number) {
            return number.doubleValue();
        }
        if (value == null) {
            return defaultValue;
        }
        try {
            return Double.parseDouble(String.valueOf(value));
        } catch (NumberFormatException ignored) {
            return defaultValue;
        }
    }

    private static boolean boolValue(Object value, boolean defaultValue) {
        if (value instanceof Boolean bool) {
            return bool;
        }
        if (value == null) {
            return defaultValue;
        }
        String normalized = String.valueOf(value).trim().toLowerCase();
        if (normalized.isBlank()) {
            return defaultValue;
        }
        if (List.of("true", "1", "yes", "y", "on").contains(normalized)) {
            return true;
        }
        if (List.of("false", "0", "no", "n", "off").contains(normalized)) {
            return false;
        }
        return defaultValue;
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

    private static Map<String, Object> effectiveAntiBot(JobSpec spec, Map<String, Object> metadata) {
        Map<String, Object> merged = new LinkedHashMap<>();
        if (spec != null && spec.antiBot != null) {
            merged.putAll(spec.antiBot.toMap());
        }
        merged.putAll(mapValue(metadata.get("mock_antibot")));
        return merged;
    }

    private static String[] slice(String[] args, int start) {
        if (start >= args.length) {
            return new String[0];
        }
        String[] result = new String[args.length - start];
        System.arraycopy(args, start, result, 0, result.length);
        return result;
    }

    private static void printUsage() {
        System.out.println("Usage: SuperSpiderCLI <command> [options]");
        System.out.println();
        System.out.println("Shared framework commands:");
        System.out.println("  config init --output <path>");
        System.out.println("  crawl --url <url> [--config <path>]");
        System.out.println("  browser fetch --url <url> [--config <path>] [--screenshot <path>]");
        System.out.println("  doctor [--config <path>] [--json]");
        System.out.println("  export --input <path> --format <json|csv|md> --output <path>");
        System.out.println("  curl convert --command <curl> [--target <java|http|okhttp|apache>]");
        System.out.println("  jobdir <init|status|pause|resume|clear> --path <path>");
        System.out.println("  http-cache <status|clear|seed> --path <path>");
        System.out.println("  console <snapshot|tail> --control-plane <dir>");
        System.out.println();
        System.out.println("Extended commands:");
        System.out.println("  workflow ...");
        System.out.println("  media ...");
        System.out.println("  curl convert ...");
        System.out.println("  job --file <job.json>");
        System.out.println("  capabilities");
        System.out.println("  version");
    }

    private static final class JobSpec {
        private String name;
        private String runtime;
        private int priority;
        private TargetSpec target;
        private BrowserSpec browser;
        private OutputSpec output;
        private List<Map<String, Object>> extract;
        private Map<String, Object> metadata;
        private ResourceSpec resources;
        private AntiBotSpec antiBot;
        private PolicySpec policy;
        private ScheduleSpec schedule;
        private List<String> warnings;
    }

    private static final class TargetSpec {
        private String url;
        private String method;
        private Map<String, String> headers;
        private Map<String, String> cookies;
        private String body;
        private String proxy;
        private long timeoutMs;
        private List<String> allowedDomains;
    }

    private static final class BrowserSpec {
        private boolean headless;
        private String profile;
        private List<String> capture;
        private List<ActionSpec> actions;

        private Map<String, Object> toMap() {
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("headless", headless);
            result.put("profile", stringValue(profile, ""));
            result.put("capture", capture == null ? List.of() : capture);
            if (actions != null && !actions.isEmpty()) {
                result.put("actions", actions.stream().map(ActionSpec::toMap).toList());
            }
            return result;
        }
    }

    private static final class ActionSpec {
        private String type;
        private String selector;
        private String value;
        private String url;
        private long timeoutMs;
        private boolean optional;
        private String saveAs;
        private Map<String, Object> extra;

        private Map<String, Object> toMap() {
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("type", stringValue(type, ""));
            if (selector != null && !selector.isBlank()) {
                result.put("selector", selector);
            }
            if (value != null && !value.isBlank()) {
                result.put("value", value);
            }
            if (url != null && !url.isBlank()) {
                result.put("url", url);
            }
            if (timeoutMs > 0) {
                result.put("timeout_ms", timeoutMs);
            }
            if (optional) {
                result.put("optional", true);
            }
            if (saveAs != null && !saveAs.isBlank()) {
                result.put("save_as", saveAs);
            }
            if (extra != null && !extra.isEmpty()) {
                result.put("extra", extra);
            }
            return result;
        }
    }

    private static final class OutputSpec {
        private String format;
        private String path;
        private String directory;
        private String artifactPrefix;
    }

    private static final class ResourceSpec {
        private int concurrency;
        private int retries;
        private long timeoutMs;
        private double rateLimitPerSec;
        private String downloadDir;
        private String tempDir;

        private Map<String, Object> toMap() {
            Map<String, Object> result = new LinkedHashMap<>();
            if (concurrency > 0) {
                result.put("concurrency", concurrency);
            }
            if (retries > 0) {
                result.put("retries", retries);
            }
            if (timeoutMs > 0) {
                result.put("timeout_ms", timeoutMs);
            }
            if (rateLimitPerSec > 0) {
                result.put("rate_limit_per_sec", rateLimitPerSec);
            }
            if (downloadDir != null && !downloadDir.isBlank()) {
                result.put("download_dir", downloadDir);
            }
            if (tempDir != null && !tempDir.isBlank()) {
                result.put("temp_dir", tempDir);
            }
            return result;
        }
    }

    private static final class AntiBotSpec {
        private String identityProfile;
        private String proxyPool;
        private String sessionMode;
        private boolean stealth;
        private String fallbackRuntime;
        private String challengePolicy;

        private Map<String, Object> toMap() {
            Map<String, Object> result = new LinkedHashMap<>();
            if (identityProfile != null && !identityProfile.isBlank()) {
                result.put("identity_profile", identityProfile);
            }
            if (proxyPool != null && !proxyPool.isBlank()) {
                result.put("proxy_pool", proxyPool);
            }
            if (sessionMode != null && !sessionMode.isBlank()) {
                result.put("session_mode", sessionMode);
            }
            result.put("stealth", stealth);
            if (fallbackRuntime != null && !fallbackRuntime.isBlank()) {
                result.put("fallback_runtime", fallbackRuntime);
            }
            if (challengePolicy != null && !challengePolicy.isBlank()) {
                result.put("challenge_policy", challengePolicy);
            }
            return result;
        }
    }

    private static final class PolicySpec {
        private int maxPages;
        private int maxDepth;
        private boolean respectRobotsTxt;
        private boolean sameDomainOnly;
        private Map<String, Object> budget;

        private Map<String, Object> toMap() {
            Map<String, Object> result = new LinkedHashMap<>();
            if (maxPages > 0) {
                result.put("max_pages", maxPages);
            }
            if (maxDepth > 0) {
                result.put("max_depth", maxDepth);
            }
            result.put("respect_robots_txt", respectRobotsTxt);
            result.put("same_domain_only", sameDomainOnly);
            if (budget != null && !budget.isEmpty()) {
                result.put("budget", budget);
            }
            return result;
        }
    }

    private static final class ScheduleSpec {
        private String mode;
        private String cron;
        private String queueName;
        private int delaySeconds;

        private Map<String, Object> toMap() {
            Map<String, Object> result = new LinkedHashMap<>();
            if (mode != null && !mode.isBlank()) {
                result.put("mode", mode);
            }
            if (cron != null && !cron.isBlank()) {
                result.put("cron", cron);
            }
            if (queueName != null && !queueName.isBlank()) {
                result.put("queue_name", queueName);
            }
            if (delaySeconds > 0) {
                result.put("delay_seconds", delaySeconds);
            }
            return result;
        }
    }

    private static final class MockWorkflowExecutionContext implements WorkflowExecutionContext {
        private final JobSpec spec;
        private String currentUrl;

        private MockWorkflowExecutionContext(JobSpec spec) {
            this.spec = spec;
            this.currentUrl = spec != null && spec.target != null ? stringValue(spec.target.url, "") : "";
        }

        @Override
        public void gotoUrl(String url) {
            this.currentUrl = stringValue(url, currentUrl);
        }

        @Override
        public void waitFor(long timeoutMillis) {
        }

        @Override
        public void click(String selector) {
        }

        @Override
        public void type(String selector, String value) {
        }

        @Override
        public void select(String selector, String value, Map<String, Object> options) {
        }

        @Override
        public void hover(String selector) {
        }

        @Override
        public void scroll(String selector, Map<String, Object> options) {
        }

        @Override
        public Object evaluate(String script) {
            if (spec.metadata != null && spec.metadata.containsKey("mock_eval_result")) {
                return spec.metadata.get("mock_eval_result");
            }
            return null;
        }

        @Override
        public List<Map<String, Object>> listenNetwork(Map<String, Object> options) {
            return listOfMaps(spec.metadata.get("mock_network_requests"));
        }

        @Override
        public String captureHtml() {
            String html = stringValue(spec.metadata.get("mock_html"), "");
            if (!html.isBlank()) {
                return html;
            }
            String content = stringValue(spec.metadata.get("content"), "");
            if (!content.isBlank()) {
                return content;
            }
            return "<html><title>" + title() + "</title><body>mock</body></html>";
        }

        @Override
        public void captureScreenshot(String artifactPath) {
            try {
                Path path = Path.of(artifactPath);
                Path parent = path.getParent();
                if (parent != null) {
                    Files.createDirectories(parent);
                }
                String content = stringValue(spec.metadata.get("mock_artifact_content"), "mock-artifact:" + spec.name);
                Files.writeString(path, content, StandardCharsets.UTF_8);
            } catch (IOException e) {
                throw new RuntimeException("failed to write mock artifact", e);
            }
        }

        @Override
        public String currentUrl() {
            String mockUrl = stringValue(spec.metadata.get("mock_url"), "");
            return mockUrl.isBlank() ? currentUrl : mockUrl;
        }

        @Override
        public String title() {
            String mockTitle = stringValue(spec.metadata.get("mock_title"), "");
            if (!mockTitle.isBlank()) {
                return mockTitle;
            }
            Map<String, Object> mockExtract = mapValue(spec.metadata.get("mock_extract"));
            return stringValue(mockExtract.get("title"), "Mock Title");
        }

        @Override
        public boolean challengeDetected() {
            return false;
        }

        @Override
        public boolean captchaDetected() {
            return false;
        }

        @Override
        public String proxyHealth() {
            return "not-configured";
        }

        @Override
        public void close() {
        }
    }
}
