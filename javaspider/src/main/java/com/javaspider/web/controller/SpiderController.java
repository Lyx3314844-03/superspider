package com.javaspider.web.controller;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.javaspider.audit.InMemoryAuditTrail;
import com.javaspider.connector.InMemoryConnector;
import com.javaspider.core.Page;
import com.javaspider.core.Site;
import com.javaspider.core.Spider;
import com.javaspider.graph.GraphBuilder;
import com.javaspider.processor.PageProcessor;
import com.javaspider.research.AsyncResearchConfig;
import com.javaspider.research.AsyncResearchResult;
import com.javaspider.research.AsyncResearchRuntime;
import com.javaspider.research.ResearchJob;
import com.javaspider.research.ResearchRuntime;
import com.javaspider.session.SessionProfile;
import com.javaspider.util.JsonlWriterRegistry;
import com.javaspider.workflow.*;
import com.sun.net.httpserver.HttpServer;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.Headers;

import java.io.*;
import java.net.InetSocketAddress;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.stream.Collectors;

/**
 * Spider 管理控制器 - 纯 Java 实现 (无需 Spring)
 * 使用 Java 内置的 HttpServer
 */
public class SpiderController {
    private static final ObjectMapper MAPPER = new ObjectMapper();

    private final Map<String, SpiderInstance> spiders = new ConcurrentHashMap<>();
    private final Map<String, FlowJob> workflowJobs = new ConcurrentHashMap<>();
    private final Map<String, FlowResult> workflowResults = new ConcurrentHashMap<>();
    private final List<Map<String, Object>> researchHistory = Collections.synchronizedList(new ArrayList<>());
    private final InMemoryAuditTrail auditTrail = new InMemoryAuditTrail();
    private final InMemoryConnector outputConnector = new InMemoryConnector();
    private final String apiToken;
    private HttpServer server;
    private ExecutorService executor;

    public SpiderController() {
        this(resolveApiToken(System.getenv()));
    }

    SpiderController(String apiToken) {
        this.apiToken = apiToken == null ? "" : apiToken.trim();
    }

    /**
     * 启动 Web 服务器
     */
    public void start(int port) throws IOException {
        server = HttpServer.create(new InetSocketAddress(port), 0);
        executor = Executors.newFixedThreadPool(4);
        server.setExecutor(executor);

        // 设置路由
        server.createContext("/api/spiders", withApiAuth(new SpidersHandler()));
        server.createContext("/api/spiders/", withApiAuth(new SpiderDetailHandler()));
        server.createContext("/api/tasks", withApiAuth(new TasksAliasHandler()));
        server.createContext("/api/tasks/", withApiAuth(new TaskDetailAliasHandler()));
        server.createContext("/api/stats", withApiAuth(new StatsHandler()));
        server.createContext("/api/graph/extract", withApiAuth(new GraphExtractHandler()));
        server.createContext("/api/v1/graph/extract", withApiAuth(new GraphExtractHandler()));
        server.createContext("/api/research", withApiAuth(new ResearchHandler()));
        server.createContext("/api/research/", withApiAuth(new ResearchHandler()));
        server.createContext("/api/v1/research", withApiAuth(new ResearchHandler()));
        server.createContext("/api/v1/research/", withApiAuth(new ResearchHandler()));
        server.createContext("/api/research/history", withApiAuth(new ResearchHistoryHandler()));
        server.createContext("/api/v1/research/history", withApiAuth(new ResearchHistoryHandler()));
        server.createContext("/api/workflows", withApiAuth(new WorkflowsHandler()));
        server.createContext("/api/workflows/", withApiAuth(new WorkflowDetailHandler()));
        server.createContext("/api/workflows/run", withApiAuth(new WorkflowRunHandler()));
        server.createContext("/", new IndexHandler());

        server.start();
        System.out.println("Web UI started at http://localhost:" + port);
    }

    /**
     * 停止 Web 服务器
     */
    public void stop() {
        if (server != null) {
            server.stop(0);
        }
        if (executor != null) {
            executor.shutdown();
        }
    }

    /**
     * 注册爬虫实例
     */
    public void registerSpider(String id, Spider spider) {
        spiders.put(id, new SpiderInstance(spider));
    }

    HttpHandler withApiAuth(HttpHandler delegate) {
        return exchange -> {
            if (!isAuthorizedRequest(exchange.getRequestURI().getPath(), exchange.getRequestMethod(), exchange.getRequestHeaders())) {
                sendError(exchange, HttpURLConnection.HTTP_UNAUTHORIZED, "unauthorized");
                return;
            }
            delegate.handle(exchange);
        };
    }

    boolean isAuthorizedRequest(String path, String method, Headers headers) {
        if (!authEnabled()) {
            return true;
        }
        if (method != null && "OPTIONS".equalsIgnoreCase(method)) {
            return true;
        }
        if (path == null || !path.startsWith("/api/")) {
            return true;
        }
        String token = authToken(headers);
        return !token.isBlank() && token.equals(apiToken);
    }

    boolean authEnabled() {
        return apiToken != null && !apiToken.isBlank();
    }

    private String authToken(Headers headers) {
        if (headers == null) {
            return "";
        }
        String authorization = firstHeader(headers, "Authorization");
        if (authorization.toLowerCase(Locale.ROOT).startsWith("bearer ")) {
            authorization = authorization.substring(7).trim();
        }
        if (!authorization.isBlank()) {
            return authorization;
        }
        return firstHeader(headers, "X-API-Token");
    }

    private String firstHeader(Headers headers, String name) {
        String value = headers.getFirst(name);
        return value == null ? "" : value.trim();
    }

    private static String resolveApiToken(Map<String, String> env) {
        String direct = rawStringValue(env.get("JAVASPIDER_API_TOKEN"));
        if (!direct.isBlank()) {
            return direct;
        }
        return rawStringValue(env.get("SPIDER_API_TOKEN"));
    }

    private static String rawStringValue(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
    }

    private static int intValue(Object value, int defaultValue) {
        if (value instanceof Number number) {
            return number.intValue();
        }
        if (value == null) {
            return defaultValue;
        }
        try {
            return Integer.parseInt(String.valueOf(value).trim());
        } catch (NumberFormatException ignored) {
            return defaultValue;
        }
    }

    // ==================== Request Handlers ====================

    private class IndexHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            String response = """
                <!DOCTYPE html>
                <html lang="zh-CN">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>JavaSpider Web UI</title>
                    <style>
                        * { box-sizing: border-box; }
                        body { margin: 0; font-family: 'Segoe UI', sans-serif; background: linear-gradient(135deg, #fef7f0 0%, #fde7d9 100%); color: #1f2937; }
                        .container { max-width: 1200px; margin: 0 auto; padding: 24px; }
                        header, .panel { background: white; border-radius: 16px; padding: 20px; box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08); }
                        header { margin-bottom: 20px; }
                        h1 { margin: 0 0 8px 0; color: #c2410c; }
                        p { color: #475569; }
                        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 20px; }
                        .pill { display: inline-block; padding: 4px 10px; border-radius: 999px; background: #ffedd5; color: #c2410c; font-size: 12px; font-weight: 700; margin-bottom: 12px; }
                        .field { margin-bottom: 12px; }
                        .field label { display: block; margin-bottom: 6px; font-size: 13px; color: #475569; }
                        .field input, .field textarea, .field select { width: 100%; padding: 10px 12px; border: 1px solid #cbd5e1; border-radius: 10px; font-size: 14px; }
                        .field textarea { min-height: 96px; resize: vertical; }
                        .btn-row { display: flex; gap: 10px; flex-wrap: wrap; }
                        button { border: none; border-radius: 10px; padding: 11px 16px; cursor: pointer; font-weight: 600; }
                        .primary { background: #ea580c; color: white; }
                        .secondary { background: #e2e8f0; color: #0f172a; }
                        pre { background: #111827; color: #fed7aa; border-radius: 12px; padding: 14px; overflow: auto; max-height: 420px; font-size: 12px; }
                        a { color: #c2410c; text-decoration: none; margin-right: 12px; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <header>
                            <h1>☕ JavaSpider 控制台</h1>
                            <p>任务控制、workflow 和 research runtime 已经合并到同一个 Web UI。下面的 research 面板可以直接调用 run / async / soak。</p>
                            <div>
                                <a href="/api/tasks">/api/tasks</a>
                                <a href="/api/research/run">/api/research/run</a>
                                <a href="/api/v1/research/run">/api/v1/research/run</a>
                            </div>
                        </header>
                        <div class="grid">
                            <section class="panel">
                                <div class="pill">Task Panel</div>
                                <h2>任务面板</h2>
                                <div class="field">
                                    <label>任务名称</label>
                                    <input id="task-name" value="java-task" />
                                </div>
                                <div class="field">
                                    <label>URL</label>
                                    <input id="task-url" value="https://example.com" />
                                </div>
                                <div class="btn-row">
                                    <button class="primary" onclick="createTask()">创建任务</button>
                                    <button class="secondary" onclick="refreshTasks()">刷新任务</button>
                                </div>
                                <pre id="task-output">等待任务数据...</pre>
                            </section>
                            <section class="panel">
                                <div class="pill">Research Panel</div>
                                <h2>Research 面板</h2>
                                <div class="field">
                                    <label>模式</label>
                                    <select id="research-mode">
                                        <option value="run">run</option>
                                        <option value="async">async</option>
                                        <option value="soak">soak</option>
                                    </select>
                                </div>
                                <div class="field">
                                    <label>URL 列表（每行一个）</label>
                                    <textarea id="research-urls">https://example.com/article
https://example.com/list</textarea>
                                </div>
                                <div class="field">
                                    <label>Schema JSON</label>
                                    <textarea id="research-schema">{"properties":{"title":{"type":"string"}}}</textarea>
                                </div>
                                <div class="field">
                                    <label>Inline Content</label>
                                    <textarea id="research-content"><title>Research Demo</title></textarea>
                                </div>
                                <div class="btn-row">
                                    <button class="primary" onclick="runResearch()">执行 research</button>
                                    <button class="secondary" onclick="loadExample()">示例</button>
                                </div>
                                <pre id="research-output">等待 research 结果...</pre>
                                <div class="pill" style="margin-top:16px;">Recent Research</div>
                                <pre id="research-history">等待 research 历史...</pre>
                            </section>
                        </div>
                    </div>
                    <script>
                        async function refreshTasks() {
                            const res = await fetch('/api/tasks');
                            document.getElementById('task-output').textContent = JSON.stringify(await res.json(), null, 2);
                        }
                        async function createTask() {
                            const res = await fetch('/api/tasks', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({
                                    name: document.getElementById('task-name').value,
                                    url: document.getElementById('task-url').value
                                })
                            });
                            document.getElementById('task-output').textContent = JSON.stringify(await res.json(), null, 2);
                        }
                        function loadExample() {
                            document.getElementById('research-schema').value = '{"properties":{"title":{"type":"string"},"price":{"type":"string"}}}';
                            document.getElementById('research-content').value = '<title>Research Demo</title>\\nprice: 42';
                        }
                        async function runResearch() {
                            const mode = document.getElementById('research-mode').value;
                            const urls = document.getElementById('research-urls').value.split('\\n').map(v => v.trim()).filter(Boolean);
                            const payload = {
                                url: urls[0] || '',
                                urls,
                                content: document.getElementById('research-content').value,
                                schema_json: document.getElementById('research-schema').value,
                                concurrency: 2,
                                rounds: 2
                            };
                            const res = await fetch('/api/research/' + mode, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify(payload)
                            });
                            document.getElementById('research-output').textContent = JSON.stringify(await res.json(), null, 2);
                            refreshResearchHistory();
                        }
                        async function refreshResearchHistory() {
                            const res = await fetch('/api/research/history');
                            document.getElementById('research-history').textContent = JSON.stringify(await res.json(), null, 2);
                        }
                        refreshTasks();
                        refreshResearchHistory();
                    </script>
                </body>
                </html>
                """;
            sendResponse(exchange, 200, response, "text/html");
        }
    }

    private class SpidersHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            String method = exchange.getRequestMethod();

            if ("GET".equals(method)) {
                listSpiders(exchange);
            } else if ("POST".equals(method)) {
                createSpider(exchange);
            } else {
                sendError(exchange, 405, "Method not allowed");
            }
        }

        private void listSpiders(HttpExchange exchange) throws IOException {
            List<Map<String, Object>> list = new ArrayList<>();
            for (Map.Entry<String, SpiderInstance> entry : spiders.entrySet()) {
                list.add(taskPayload(entry.getKey(), entry.getValue()));
            }

            String response = toJson(list);
            sendResponse(exchange, 200, response, "application/json");
        }

        private void createSpider(HttpExchange exchange) throws IOException {
            String body = readBody(exchange);
            Map<String, Object> payload = parseJson(body);
            try {
                Map<String, Object> response = new LinkedHashMap<>();
                response.put("success", true);
                response.put("data", registerSpider(payload, "spider_"));
                sendResponse(exchange, 201, toJson(response), "application/json");
            } catch (IllegalArgumentException e) {
                sendError(exchange, 400, e.getMessage());
            } catch (IllegalStateException e) {
                sendError(exchange, HttpURLConnection.HTTP_CONFLICT, e.getMessage());
            }
        }
    }

    private class SpiderDetailHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            String path = exchange.getRequestURI().getPath();
            String[] parts = path.split("/");

            if (parts.length < 4) {
                sendError(exchange, 400, "Invalid path");
                return;
            }

            String id = parts[3];
            String action = parts.length > 4 ? parts[4] : "";

            if ("".equals(action)) {
                getSpider(exchange, id);
            } else if ("start".equals(action) && "POST".equals(exchange.getRequestMethod())) {
                startSpider(exchange, id);
            } else if ("stop".equals(action) && "POST".equals(exchange.getRequestMethod())) {
                stopSpider(exchange, id);
            } else if ("results".equals(action) && "GET".equals(exchange.getRequestMethod())) {
                getResults(exchange, id);
            } else if ("logs".equals(action) && "GET".equals(exchange.getRequestMethod())) {
                getLogs(exchange, id);
            } else if ("status".equals(action)) {
                getStatus(exchange, id);
            } else {
                sendError(exchange, 404, "Not found");
            }
        }

        private void getSpider(HttpExchange exchange, String id) throws IOException {
            SpiderInstance instance = spiders.get(id);
            if (instance == null) {
                sendError(exchange, 404, "Spider not found");
                return;
            }

            String response = toJson(taskPayload(id, instance));
            sendResponse(exchange, 200, response, "application/json");
        }

        private void startSpider(HttpExchange exchange, String id) throws IOException {
            SpiderInstance instance = spiders.get(id);
            if (instance == null) {
                sendError(exchange, 404, "Spider not found");
                return;
            }

            instance.start();
            String response = "{\"success\":true,\"message\":\"Spider started\"}";
            sendResponse(exchange, 200, response, "application/json");
        }

        private void stopSpider(HttpExchange exchange, String id) throws IOException {
            SpiderInstance instance = spiders.get(id);
            if (instance == null) {
                sendError(exchange, 404, "Spider not found");
                return;
            }

            instance.stop();
            String response = "{\"success\":true,\"message\":\"Spider stopped\"}";
            sendResponse(exchange, 200, response, "application/json");
        }

        private void getStatus(HttpExchange exchange, String id) throws IOException {
            SpiderInstance instance = spiders.get(id);
            if (instance == null) {
                sendError(exchange, 404, "Spider not found");
                return;
            }

            Map<String, Object> status = new HashMap<>();
            status.put("id", id);
            status.put("running", instance.running);
            status.put("stats", instance.getStats());
            status.put("result_count", instance.snapshotResults().size());
            status.put("log_count", instance.snapshotLogs().size());

            String response = toJson(status);
            sendResponse(exchange, 200, response, "application/json");
        }

        private void getResults(HttpExchange exchange, String id) throws IOException {
            SpiderInstance instance = spiders.get(id);
            if (instance == null) {
                sendError(exchange, 404, "Spider not found");
                return;
            }
            sendResponse(exchange, 200, toJson(instance.snapshotResults()), "application/json");
        }

        private void getLogs(HttpExchange exchange, String id) throws IOException {
            SpiderInstance instance = spiders.get(id);
            if (instance == null) {
                sendError(exchange, 404, "Spider not found");
                return;
            }
            sendResponse(exchange, 200, toJson(instance.snapshotLogs()), "application/json");
        }
    }

    private class StatsHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            Map<String, Object> stats = new HashMap<>();
            stats.put("total_spiders", spiders.size());
            stats.put("running_spiders", countRunning());

            String response = toJson(stats);
            sendResponse(exchange, 200, response, "application/json");
        }

        private int countRunning() {
            int count = 0;
            for (SpiderInstance instance : spiders.values()) {
                if (instance.running) count++;
            }
            return count;
        }
    }

    // ==================== Workflow Handlers ====================

    private class WorkflowsHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            String method = exchange.getRequestMethod();

            if ("GET".equals(method)) {
                listWorkflows(exchange);
            } else if ("POST".equals(method)) {
                createWorkflow(exchange);
            } else {
                sendError(exchange, 405, "Method not allowed");
            }
        }

        private void listWorkflows(HttpExchange exchange) throws IOException {
            List<Map<String, Object>> list = new ArrayList<>();
            for (Map.Entry<String, FlowJob> entry : workflowJobs.entrySet()) {
                Map<String, Object> info = new HashMap<>();
                info.put("id", entry.getKey());
                info.put("name", entry.getValue().getName());
                info.put("steps", entry.getValue().getSteps().size());
                info.put("session", entry.getValue().getSessionProfile().getAccountId());

                FlowResult result = workflowResults.get(entry.getKey());
                if (result != null) {
                    info.put("status", "completed");
                    info.put("extracted_fields", result.getExtracted().size());
                    info.put("artifacts", result.getArtifacts().size());
                } else {
                    info.put("status", "pending");
                }
                list.add(info);
            }

            String response = toJson(list);
            sendResponse(exchange, 200, response, "application/json");
        }

        @SuppressWarnings("unchecked")
        private void createWorkflow(HttpExchange exchange) throws IOException {
            String body = readBody(exchange);
            Map<String, Object> payload = parseJson(body);

            String id = (String) payload.getOrDefault("id", "wf_" + System.currentTimeMillis());
            String name = (String) payload.getOrDefault("name", "Workflow " + id);

            // 解析 session profile
            Map<String, Object> sessionData = (Map<String, Object>) payload.get("session");
            SessionProfile session = new SessionProfile(
                "session-" + id,
                (String) sessionData.getOrDefault("accountId", "default"),
                (String) sessionData.getOrDefault("proxyGroup", "residential"),
                (String) sessionData.getOrDefault("fingerprintPreset", "chrome-stealth"),
                Collections.emptyMap()
            );

            // 解析 steps
            List<Map<String, Object>> stepsData = (List<Map<String, Object>>) payload.get("steps");
            List<FlowStep> steps = new ArrayList<>();
            for (int i = 0; i < stepsData.size(); i++) {
                Map<String, Object> stepData = stepsData.get(i);
                FlowStepType type = FlowStepType.valueOf((String) stepData.get("type"));
                steps.add(new FlowStep(
                    (String) stepData.getOrDefault("id", "step-" + i),
                    type,
                    (String) stepData.getOrDefault("selector", ""),
                    (String) stepData.getOrDefault("value", ""),
                    (Map<String, Object>) stepData.getOrDefault("metadata", Collections.emptyMap())
                ));
            }

            // 解析 execution policy
            Map<String, Object> policyData = (Map<String, Object>) payload.getOrDefault("policy", Collections.emptyMap());
            ExecutionPolicy policy = new ExecutionPolicy(
                (Long) policyData.getOrDefault("stepTimeoutMillis", 5000L),
                (Integer) policyData.getOrDefault("maxRetries", 1)
            );

            Map<String, Object> outputContract = (Map<String, Object>) payload.getOrDefault("outputContract", Collections.emptyMap());
            FlowJob job = new FlowJob(id, name, session, steps, outputContract, policy);
            workflowJobs.put(id, job);

            Map<String, Object> response = new HashMap<>();
            response.put("success", true);
            response.put("data", Map.of("id", id, "name", name, "steps", steps.size()));
            sendResponse(exchange, 201, toJson(response), "application/json");
        }
    }

    private class WorkflowDetailHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            String path = exchange.getRequestURI().getPath();
            String[] parts = path.split("/");

            if (parts.length < 4) {
                sendError(exchange, 400, "Invalid path");
                return;
            }

            String id = parts[3];
            String action = parts.length > 4 ? parts[4] : "";

            if ("".equals(action)) {
                getWorkflow(exchange, id);
            } else if ("audit".equals(action)) {
                getWorkflowAudit(exchange, id);
            } else {
                sendError(exchange, 404, "Not found");
            }
        }

        private void getWorkflow(HttpExchange exchange, String id) throws IOException {
            FlowJob job = workflowJobs.get(id);
            if (job == null) {
                sendError(exchange, 404, "Workflow not found");
                return;
            }

            Map<String, Object> info = new HashMap<>();
            info.put("id", job.getId());
            info.put("name", job.getName());
            info.put("session", Map.of(
                "accountId", job.getSessionProfile().getAccountId(),
                "proxyGroup", job.getSessionProfile().getProxyGroup(),
                "fingerprintPreset", job.getSessionProfile().getFingerprintPreset()
            ));
            info.put("steps", job.getSteps().stream().map(s -> {
                Map<String, Object> stepInfo = new HashMap<>();
                stepInfo.put("id", s.getId());
                stepInfo.put("type", s.getType().name());
                stepInfo.put("selector", s.getSelector());
                stepInfo.put("value", s.getValue());
                stepInfo.put("metadata", s.getMetadata());
                return stepInfo;
            }).toList());
            info.put("policy", Map.of(
                "stepTimeoutMillis", job.getPolicy().getStepTimeoutMillis(),
                "maxRetries", job.getPolicy().getMaxRetries()
            ));

            FlowResult result = workflowResults.get(id);
            if (result != null) {
                info.put("result", Map.of(
                    "runId", result.getRunId(),
                    "extracted", result.getExtracted(),
                    "artifacts", result.getArtifacts()
                ));
            }

            sendResponse(exchange, 200, toJson(info), "application/json");
        }

        private void getWorkflowAudit(HttpExchange exchange, String id) throws IOException {
            FlowJob job = workflowJobs.get(id);
            if (job == null) {
                sendError(exchange, 404, "Workflow not found");
                return;
            }

            List<Map<String, Object>> events = new ArrayList<>();
            for (var e : auditTrail.list()) {
                if (e.getJobId().equals(id)) {
                    Map<String, Object> eventInfo = new HashMap<>();
                    eventInfo.put("timestamp", e.getTimestamp().toString());
                    eventInfo.put("type", e.getType());
                    eventInfo.put("stepId", e.getStepId());
                    eventInfo.put("payload", e.getPayload());
                    events.add(eventInfo);
                }
            }

            sendResponse(exchange, 200, toJson(events), "application/json");
        }
    }

    private class WorkflowRunHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            if (!"POST".equals(exchange.getRequestMethod())) {
                sendError(exchange, 405, "Method not allowed");
                return;
            }

            String body = readBody(exchange);
            Map<String, Object> payload = parseJson(body);
            String id = (String) payload.get("id");

            if (id == null || !workflowJobs.containsKey(id)) {
                sendError(exchange, 404, "Workflow not found");
                return;
            }

            FlowJob job = workflowJobs.get(id);
            WorkflowSpider spider = new WorkflowSpider(auditTrail).addConnector(outputConnector);

            try {
                FlowResult result = spider.execute(job);
                workflowResults.put(id, result);

                Map<String, Object> response = new HashMap<>();
                response.put("success", true);
                response.put("data", Map.of(
                    "runId", result.getRunId(),
                    "extracted_fields", result.getExtracted().size(),
                    "artifacts", result.getArtifacts().size()
                ));
                sendResponse(exchange, 200, toJson(response), "application/json");
            } catch (Exception e) {
                Map<String, Object> response = new HashMap<>();
                response.put("success", false);
                response.put("error", e.getMessage());
                sendResponse(exchange, 500, toJson(response), "application/json");
            }
        }
    }

    // ==================== Helper Methods ====================

    private String readBody(HttpExchange exchange) throws IOException {
        try (InputStream is = exchange.getRequestBody()) {
            return new String(is.readAllBytes(), StandardCharsets.UTF_8);
        }
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> parseJson(String json) {
        if (json == null || json.isBlank()) {
            return new HashMap<>();
        }
        try {
            return MAPPER.readValue(json, new TypeReference<Map<String, Object>>() {});
        } catch (IOException e) {
            return new HashMap<>();
        }
    }

    private class GraphExtractHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            if (!"POST".equals(exchange.getRequestMethod())) {
                sendError(exchange, 405, "Method not allowed");
                return;
            }
            try {
                Map<String, Object> response = new LinkedHashMap<>();
                response.put("success", true);
                response.put("data", buildGraphPayload(parseJson(readBody(exchange))));
                sendResponse(exchange, 200, toJson(response), "application/json");
            } catch (IllegalArgumentException e) {
                sendError(exchange, 400, e.getMessage());
            }
        }
    }

    private class ResearchHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            if (!"POST".equals(exchange.getRequestMethod())) {
                sendError(exchange, 405, "Method not allowed");
                return;
            }
            String path = exchange.getRequestURI().getPath();
            Map<String, Object> payload = parseJson(readBody(exchange));
            try {
                Object response;
                if (path.endsWith("/async")) {
                    response = buildResearchAsyncResponse(payload);
                } else if (path.endsWith("/soak")) {
                    response = buildResearchSoakResponse(payload);
                } else {
                    response = buildResearchRunResponse(payload);
                }
                recordResearchHistory((Map<String, Object>) response);
                sendResponse(exchange, 200, toJson(response), "application/json");
            } catch (IllegalArgumentException e) {
                sendError(exchange, 400, e.getMessage());
            }
        }
    }

    private class ResearchHistoryHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            if (!"GET".equals(exchange.getRequestMethod())) {
                sendError(exchange, 405, "Method not allowed");
                return;
            }
            sendResponse(exchange, 200, toJson(Map.of("success", true, "data", List.copyOf(researchHistory))), "application/json");
        }
    }

    private Map<String, Object> buildResearchRunResponse(Map<String, Object> payload) {
        ResearchJob job = buildResearchJob(payload);
        String content = rawStringValue(payload.get("content"));
        return Map.of(
            "command", "research run",
            "runtime", "java",
            "result", new ResearchRuntime().run(job, content)
        );
    }

    private Map<String, Object> buildResearchAsyncResponse(Map<String, Object> payload) {
        List<ResearchJob> jobs = buildResearchJobs(payload);
        List<String> contents = buildResearchContents(payload, jobs.size());
        int concurrency = intValue(payload.get("concurrency"), 5);
        try (AsyncResearchRuntime runtime = new AsyncResearchRuntime(new AsyncResearchConfig(concurrency, 30.0, false))) {
            List<AsyncResearchResult> results = runtime.runMultiple(jobs, contents);
            return Map.of(
                "command", "research async",
                "runtime", "java",
                "results", results,
                "metrics", runtime.snapshotMetrics()
            );
        }
    }

    private Map<String, Object> buildResearchSoakResponse(Map<String, Object> payload) {
        List<ResearchJob> jobs = buildResearchJobs(payload);
        List<String> contents = buildResearchContents(payload, jobs.size());
        int concurrency = intValue(payload.get("concurrency"), 5);
        int rounds = intValue(payload.get("rounds"), 1);
        try (AsyncResearchRuntime runtime = new AsyncResearchRuntime(new AsyncResearchConfig(concurrency, 30.0, false))) {
            return Map.of(
                "command", "research soak",
                "runtime", "java",
                "report", runtime.runSoak(jobs, contents, rounds)
            );
        }
    }

    private ResearchJob buildResearchJob(Map<String, Object> payload) {
        List<String> urls = buildResearchUrls(payload);
        if (urls.isEmpty()) {
            throw new IllegalArgumentException("research request requires url or urls");
        }
        return new ResearchJob(
            List.of(urls.get(0)),
            Map.of(),
            parseResearchSchema(payload),
            List.of(),
            mapValue(payload.get("policy")),
            mapValue(payload.get("output"))
        );
    }

    private List<ResearchJob> buildResearchJobs(Map<String, Object> payload) {
        List<String> urls = buildResearchUrls(payload);
        if (urls.isEmpty()) {
            throw new IllegalArgumentException("research request requires url or urls");
        }
        Map<String, Object> schema = parseResearchSchema(payload);
        Map<String, Object> policy = mapValue(payload.get("policy"));
        Map<String, Object> output = mapValue(payload.get("output"));
        List<ResearchJob> jobs = new ArrayList<>();
        for (String url : urls) {
            jobs.add(new ResearchJob(List.of(url), Map.of(), schema, List.of(), policy, output));
        }
        return jobs;
    }

    private List<String> buildResearchUrls(Map<String, Object> payload) {
        List<String> urls = new ArrayList<>();
        Object url = payload.get("url");
        if (url != null && !rawStringValue(url).isBlank()) {
            urls.add(rawStringValue(url));
        }
        Object rawUrls = payload.get("urls");
        if (rawUrls instanceof List<?> list) {
            for (Object item : list) {
                String text = rawStringValue(item);
                if (!text.isBlank()) {
                    urls.add(text);
                }
            }
        }
        return urls;
    }

    private List<String> buildResearchContents(Map<String, Object> payload, int size) {
        List<String> contents = new ArrayList<>();
        String inline = rawStringValue(payload.get("content"));
        Object rawContents = payload.get("contents");
        List<?> list = rawContents instanceof List<?> values ? values : List.of();
        for (int index = 0; index < size; index++) {
            if (index < list.size() && !rawStringValue(list.get(index)).isBlank()) {
                contents.add(rawStringValue(list.get(index)));
            } else if (!inline.isBlank()) {
                contents.add(inline);
            } else {
                contents.add("<title>Research " + (index + 1) + "</title>");
            }
        }
        return contents;
    }

    private Map<String, Object> parseResearchSchema(Map<String, Object> payload) {
        if (payload.get("schema") instanceof Map<?, ?>) {
            return mapValue(payload.get("schema"));
        }
        String schemaJson = rawStringValue(payload.get("schema_json"));
        if (schemaJson.isBlank()) {
            return Map.of();
        }
        try {
            return MAPPER.readValue(schemaJson, new TypeReference<Map<String, Object>>() {});
        } catch (IOException e) {
            throw new IllegalArgumentException("invalid schema_json");
        }
    }

    private void recordResearchHistory(Map<String, Object> response) {
        Map<String, Object> record = new LinkedHashMap<>();
        record.put("id", "research-" + System.nanoTime());
        record.put("created_at", System.currentTimeMillis());
        record.put("command", response.get("command"));
        record.put("runtime", response.get("runtime"));
        record.put("status", "completed");
        record.put("result", response);
        researchHistory.add(0, record);
        if (researchHistory.size() > 20) {
            researchHistory.remove(researchHistory.size() - 1);
        }
        try {
            JsonlWriterRegistry.append(
                Path.of("artifacts", "control-plane", "research-history.jsonl"),
                (toJson(record) + System.lineSeparator()).getBytes(StandardCharsets.UTF_8)
            );
        } catch (RuntimeException ignored) {
            // best-effort persistence
        }
    }

    private void sendResponse(HttpExchange exchange, int code, String body, String contentType) throws IOException {
        byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
        exchange.getResponseHeaders().set("Content-Type", contentType);
        exchange.getResponseHeaders().set("Access-Control-Allow-Origin", "*");
        exchange.sendResponseHeaders(code, bytes.length);

        try (OutputStream os = exchange.getResponseBody()) {
            os.write(bytes);
        }
    }

    private void sendError(HttpExchange exchange, int code, String message) throws IOException {
        String response = toJson(Map.of("success", false, "error", message));
        sendResponse(exchange, code, response, "application/json");
    }

    private int parseQueryInt(HttpExchange exchange, String key, int defaultValue) {
        String query = exchange.getRequestURI().getRawQuery();
        if (query == null || query.isBlank()) {
            return defaultValue;
        }
        for (String pair : query.split("&")) {
            String[] parts = pair.split("=", 2);
            if (parts.length == 2 && key.equals(parts[0])) {
                try {
                    return Math.max(1, Integer.parseInt(parts[1]));
                } catch (NumberFormatException ignored) {
                    return defaultValue;
                }
            }
        }
        return defaultValue;
    }

    private Map<String, Object> paginationEnvelope(int total, int page, int perPage) {
        Map<String, Object> pagination = new LinkedHashMap<>();
        pagination.put("page", page);
        pagination.put("per_page", perPage);
        pagination.put("total", total);
        return pagination;
    }

    private <T> List<T> paginate(List<T> items, int page, int perPage) {
        int start = Math.max(0, (page - 1) * perPage);
        if (start >= items.size()) {
            return List.of();
        }
        int end = Math.min(items.size(), start + perPage);
        return new ArrayList<>(items.subList(start, end));
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> mapValue(Object value) {
        if (value instanceof Map<?, ?> map) {
            return map.entrySet().stream().collect(Collectors.toMap(
                entry -> String.valueOf(entry.getKey()),
                Map.Entry::getValue,
                (left, right) -> right,
                LinkedHashMap::new
            ));
        }
        return new LinkedHashMap<>();
    }

    private Map<String, Object> taskPayload(String id, SpiderInstance instance) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("id", id);
        payload.put("name", instance.spider.getSpiderName() != null
            ? instance.spider.getSpiderName()
            : instance.spider.getClass().getSimpleName());
        payload.put("status", instance.running ? "running" : instance.currentStatus());
        payload.put("running", instance.running);
        payload.put("url", instance.targetUrl);
        payload.put("config", instance.config);
        payload.put("created_at", instance.createdAt);
        payload.put("started_at", instance.startedAt);
        payload.put("finished_at", instance.finishedAt);
        payload.put("stats", instance.getStats());
        payload.put("results", instance.snapshotResults());
        payload.put("logs", instance.snapshotLogs());
        return payload;
    }

    private Map<String, Object> buildGraphPayload(Map<String, Object> payload) {
        Map<String, Object> normalized = payload == null ? new LinkedHashMap<>() : payload;
        String html = stringValue(normalized.get("html"));
        String url = stringValue(normalized.get("url"));
        if (html.isBlank() && url.isBlank()) {
            throw new IllegalArgumentException("Graph html or url is required");
        }
        if (html.isBlank()) {
            html = fetchText(url);
        }

        GraphBuilder builder = new GraphBuilder().buildFromHtml(html);
        Map<String, Object> response = new LinkedHashMap<>();
        response.put("root_id", builder.rootId());
        response.put("nodes", builder.nodes());
        response.put("edges", builder.edges());
        response.put("stats", builder.stats());
        return response;
    }

    private String fetchText(String url) {
        try {
            HttpURLConnection connection = (HttpURLConnection) new URL(url).openConnection();
            connection.setConnectTimeout(15000);
            connection.setReadTimeout(15000);
            try (InputStream stream = connection.getInputStream()) {
                return new String(stream.readAllBytes(), StandardCharsets.UTF_8);
            }
        } catch (IOException e) {
            throw new IllegalArgumentException("Failed to fetch graph url: " + e.getMessage(), e);
        }
    }

    private Map<String, Object> registerSpider(Map<String, Object> payload, String defaultPrefix) {
        Map<String, Object> normalized = payload == null ? new LinkedHashMap<>() : new LinkedHashMap<>(payload);
        String id = stringValue(normalized.getOrDefault("id", defaultPrefix + System.currentTimeMillis()));
        if (id.isBlank()) {
            throw new IllegalArgumentException("Task id is required");
        }
        if (spiders.containsKey(id)) {
            throw new IllegalStateException("Task already exists: " + id);
        }

        List<String> urls = collectUrls(normalized);
        if (urls.isEmpty()) {
            throw new IllegalArgumentException("Task url is required");
        }

        String name = stringValue(normalized.getOrDefault("name", normalized.getOrDefault("spider", "Unnamed Task")));
        if (name.isBlank()) {
            name = "Unnamed Task";
        }

        normalized.put("id", id);
        normalized.put("name", name);
        normalized.put("url", urls.get(0));
        if (!normalized.containsKey("urls")) {
            normalized.put("urls", urls);
        }

        Spider spider = new Spider(new TaskPageProcessor()).name(name);
        spider.addUrl(urls.toArray(String[]::new));

        SpiderInstance instance = new SpiderInstance(spider, urls.get(0), normalized);
        spiders.put(id, instance);

        if (shouldAutoStart(normalized)) {
            instance.start();
        }
        return taskPayload(id, instance);
    }

    private List<String> collectUrls(Map<String, Object> payload) {
        List<String> urls = new ArrayList<>();
        addUrlCandidate(urls, payload.get("url"));

        Map<String, Object> target = mapValue(payload.get("target"));
        addUrlCandidate(urls, target.get("url"));

        Map<String, Object> config = mapValue(payload.get("config"));
        addUrlCandidate(urls, config.get("url"));

        Object listValue = payload.get("urls");
        if (listValue instanceof Collection<?> collection) {
            for (Object candidate : collection) {
                addUrlCandidate(urls, candidate);
            }
        }

        return urls;
    }

    private void addUrlCandidate(List<String> urls, Object candidate) {
        String url = stringValue(candidate);
        if (!url.isBlank() && !urls.contains(url)) {
            urls.add(url);
        }
    }

    private boolean shouldAutoStart(Map<String, Object> payload) {
        return booleanValue(payload.get("auto_start"))
            || booleanValue(payload.get("start_immediately"))
            || booleanValue(payload.get("run"));
    }

    private String stringValue(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
    }

    private boolean booleanValue(Object value) {
        if (value instanceof Boolean bool) {
            return bool;
        }
        if (value instanceof Number number) {
            return number.intValue() != 0;
        }
        String text = stringValue(value).toLowerCase(Locale.ROOT);
        return "true".equals(text) || "1".equals(text) || "yes".equals(text);
    }

    private String toJson(Object obj) {
        try {
            return MAPPER.writeValueAsString(obj);
        } catch (IOException e) {
            throw new RuntimeException("failed to serialize payload", e);
        }
    }

    // ==================== Inner Classes ====================

    static class SpiderInstance {
        private final Spider spider;
        private final String targetUrl;
        private final Map<String, Object> config;
        private final String createdAt;
        private String startedAt;
        private String finishedAt;
        private Thread thread;
        private volatile boolean running;
        private final List<Map<String, Object>> results = Collections.synchronizedList(new ArrayList<>());
        private final List<Map<String, Object>> logs = Collections.synchronizedList(new ArrayList<>());

        SpiderInstance(Spider spider) {
            this(spider, "", Map.of());
        }

        SpiderInstance(Spider spider, String targetUrl, Map<String, Object> config) {
            this.spider = spider;
            this.targetUrl = targetUrl == null ? "" : targetUrl;
            this.config = config == null ? new LinkedHashMap<>() : new LinkedHashMap<>(config);
            this.createdAt = java.time.Instant.now().toString();
            recordLog("info", "spider registered");
        }

        void start() {
            if (running) {
                recordLog("warning", "start ignored because spider is already running");
                return;
            }
            running = true;
            startedAt = java.time.Instant.now().toString();
            finishedAt = null;
            recordLog("info", "spider started");
            thread = new Thread(() -> {
                try {
                    if (targetUrl != null && !targetUrl.isBlank()) {
                        executeTaskRequest();
                    } else {
                        recordResult("running", "spider execution started");
                        spider.start();
                    }
                } catch (Exception e) {
                    recordLog("error", "spider start failed: " + e.getMessage());
                    recordResult("failed", e.getMessage());
                } finally {
                    running = false;
                    finishedAt = java.time.Instant.now().toString();
                    recordLog("info", "spider execution thread finished");
                }
            });
            thread.start();
        }

        void stop() {
            running = false;
            finishedAt = java.time.Instant.now().toString();
            recordLog("warning", "spider stop requested");
            recordResult("stopped", "spider stop requested");
            spider.stop();
            if (thread != null) {
                thread.interrupt();
            }
        }

        Map<String, Object> getStats() {
            Map<String, Object> stats = new HashMap<>();
            List<Map<String, Object>> snapshot = snapshotResults();
            long total = snapshot.stream().filter(entry -> entry.containsKey("status")).count();
            long success = snapshot.stream().filter(entry -> "completed".equals(entry.get("status"))).count();
            long failed = snapshot.stream().filter(entry -> "failed".equals(entry.get("status"))).count();
            long totalBytes = snapshot.stream()
                .mapToLong(entry -> longValue(entry.get("bytes")))
                .sum();
            List<Long> durations = snapshot.stream()
                .map(entry -> longValue(entry.get("duration_ms")))
                .filter(value -> value > 0)
                .sorted()
                .toList();
            long elapsedMillis = elapsedMillis();
            long resolved = success + failed;
            stats.put("total_requests", total);
            stats.put("success_requests", success);
            stats.put("failed_requests", failed);
            stats.put("success_rate", resolved > 0 ? (double) success / resolved * 100.0 : 0.0);
            stats.put("qps", elapsedMillis > 0 ? (double) success * 1000.0 / elapsedMillis : 0.0);
            stats.put("duration_ms", elapsedMillis);
            stats.put("total_bytes", totalBytes);
            stats.put("avg_duration_ms", averageDurationMillis(durations));
            stats.put("p95_duration_ms", percentileDurationMillis(durations, 0.95));
            stats.put("p99_duration_ms", percentileDurationMillis(durations, 0.99));
            return stats;
        }

        String currentStatus() {
            synchronized (results) {
                if (!results.isEmpty()) {
                    Object status = results.get(results.size() - 1).get("status");
                    if (status != null) {
                        return String.valueOf(status);
                    }
                }
            }
            return "pending";
        }

        List<Map<String, Object>> snapshotResults() {
            synchronized (results) {
                return new ArrayList<>(results);
            }
        }

        List<Map<String, Object>> snapshotLogs() {
            synchronized (logs) {
                return new ArrayList<>(logs);
            }
        }

        private void recordResult(String status, String message) {
            Map<String, Object> payload = new LinkedHashMap<>();
            payload.put("id", "result-" + System.currentTimeMillis());
            payload.put("task_id", spider.getSpiderId());
            payload.put("url", targetUrl);
            payload.put("final_url", targetUrl);
            payload.put("status", status);
            payload.put("http_status", 0);
            payload.put("content_type", "");
            payload.put("title", "");
            payload.put("bytes", 0);
            payload.put("duration_ms", 0);
            payload.put("created_at", java.time.Instant.now().toString());
            payload.put("message", message);
            payload.put("artifacts", Map.of());
            payload.put("artifact_refs", Map.of());
            synchronized (results) {
                results.add(payload);
            }
        }

        private void recordLog(String level, String message) {
            Map<String, Object> payload = new LinkedHashMap<>();
            payload.put("id", "log-" + System.currentTimeMillis());
            payload.put("task_id", spider.getSpiderId());
            payload.put("level", level);
            payload.put("message", message);
            payload.put("created_at", java.time.Instant.now().toString());
            synchronized (logs) {
                logs.add(payload);
            }
        }

        private long elapsedMillis() {
            if (startedAt == null || startedAt.isBlank()) {
                return 0L;
            }
            try {
                java.time.Instant started = java.time.Instant.parse(startedAt);
                java.time.Instant ended = (finishedAt == null || finishedAt.isBlank())
                    ? java.time.Instant.now()
                    : java.time.Instant.parse(finishedAt);
                return Math.max(0L, java.time.Duration.between(started, ended).toMillis());
            } catch (Exception ignored) {
                return 0L;
            }
        }

        private long longValue(Object value) {
            if (value instanceof Number number) {
                return number.longValue();
            }
            if (value == null) {
                return 0L;
            }
            try {
                return Long.parseLong(String.valueOf(value));
            } catch (NumberFormatException ignored) {
                return 0L;
            }
        }

        private double averageDurationMillis(List<Long> durations) {
            if (durations.isEmpty()) {
                return 0.0;
            }
            long total = durations.stream().mapToLong(Long::longValue).sum();
            return (double) total / durations.size();
        }

        private double percentileDurationMillis(List<Long> durations, double percentile) {
            if (durations.isEmpty()) {
                return 0.0;
            }
            int index = (int) Math.ceil(percentile * durations.size()) - 1;
            index = Math.max(0, Math.min(index, durations.size() - 1));
            return durations.get(index);
        }

        private void executeTaskRequest() {
            try {
                long started = System.currentTimeMillis();
                recordLog("info", "fetching " + targetUrl);
                HttpURLConnection connection = (HttpURLConnection) new URL(targetUrl).openConnection();
                connection.setConnectTimeout(15000);
                connection.setReadTimeout(15000);
                connection.setRequestProperty("User-Agent", "JavaSpider-WebUI/1.0");
                int statusCode = connection.getResponseCode();
                String finalUrl = connection.getURL().toString();
                String contentType = Optional.ofNullable(connection.getContentType()).orElse("");
                InputStream stream = statusCode >= 400 ? connection.getErrorStream() : connection.getInputStream();
                byte[] bytes = stream != null ? stream.readAllBytes() : new byte[0];
                String body = new String(bytes, StandardCharsets.UTF_8);
                if (!running) {
                    recordLog("warning", "task finished after stop request; result discarded");
                    return;
                }
                Map<String, Object> payload = new LinkedHashMap<>();
                payload.put("id", "result-" + System.currentTimeMillis());
                payload.put("task_id", spider.getSpiderId());
                payload.put("url", targetUrl);
                payload.put("final_url", finalUrl);
                payload.put("status", statusCode >= 200 && statusCode < 400 ? "completed" : "failed");
                payload.put("http_status", statusCode);
                payload.put("content_type", contentType);
                payload.put("title", extractTitle(body));
                payload.put("bytes", bytes.length);
                payload.put("duration_ms", System.currentTimeMillis() - started);
                payload.put("created_at", java.time.Instant.now().toString());
                Map<String, Object> artifacts = buildArtifactsPayload(spider.getSpiderId(), body);
                payload.put("artifacts", artifacts);
                payload.put("artifact_refs", artifacts);
                synchronized (results) {
                    results.add(payload);
                }
                recordLog("info", "task finished with status " + statusCode);
            } catch (IOException e) {
                throw new RuntimeException(e);
            }
        }

        private String extractTitle(String body) {
            String lower = body.toLowerCase(Locale.ROOT);
            int start = lower.indexOf("<title>");
            int end = lower.indexOf("</title>");
            if (start < 0 || end <= start + 7) {
                return "";
            }
            return body.substring(start + 7, end).trim();
        }

        private Map<String, Object> buildArtifactsPayload(String taskId, String html) {
            if (html == null || html.isBlank()) {
                return Map.of();
            }
            try {
                GraphBuilder builder = new GraphBuilder().buildFromHtml(html);
                Map<String, Object> graphPayload = new LinkedHashMap<>();
                graphPayload.put("root_id", builder.rootId());
                graphPayload.put("nodes", builder.nodes());
                graphPayload.put("edges", builder.edges());
                graphPayload.put("stats", builder.stats());

                Path path = Path.of("artifacts", "control-plane", "graphs",
                    "java-" + taskId + "-" + System.nanoTime() + ".json");
                Files.createDirectories(path.getParent());
                Files.writeString(path, MAPPER.writerWithDefaultPrettyPrinter().writeValueAsString(graphPayload), StandardCharsets.UTF_8);

                Map<String, Object> artifact = new LinkedHashMap<>();
                artifact.put("kind", "graph");
                artifact.put("path", path.toString());
                artifact.put("root_id", builder.rootId());
                artifact.put("stats", builder.stats());
                return Map.of("graph", artifact);
            } catch (IOException e) {
                recordLog("warning", "graph artifact skipped: " + e.getMessage());
                return Map.of();
            }
        }
    }

    private class TasksAliasHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            String method = exchange.getRequestMethod();
            if ("GET".equals(method)) {
                listTasks(exchange);
            } else if ("POST".equals(method)) {
                createTask(exchange);
            } else {
                sendError(exchange, 405, "Method not allowed");
            }
        }

        private void listTasks(HttpExchange exchange) throws IOException {
            int page = parseQueryInt(exchange, "page", 1);
            int perPage = parseQueryInt(exchange, "per_page", 20);
            List<Map<String, Object>> list = new ArrayList<>();
            for (Map.Entry<String, SpiderInstance> entry : spiders.entrySet()) {
                list.add(taskPayload(entry.getKey(), entry.getValue()));
            }
            Map<String, Object> response = new LinkedHashMap<>();
            response.put("success", true);
            response.put("data", paginate(list, page, perPage));
            response.put("pagination", paginationEnvelope(list.size(), page, perPage));
            sendResponse(exchange, 200, toJson(response), "application/json");
        }

        private void createTask(HttpExchange exchange) throws IOException {
            String body = readBody(exchange);
            Map<String, Object> payload = parseJson(body);
            try {
                Map<String, Object> response = new LinkedHashMap<>();
                response.put("success", true);
                response.put("data", registerSpider(payload, "task_"));
                sendResponse(exchange, 201, toJson(response), "application/json");
            } catch (IllegalArgumentException e) {
                sendError(exchange, 400, e.getMessage());
            } catch (IllegalStateException e) {
                sendError(exchange, HttpURLConnection.HTTP_CONFLICT, e.getMessage());
            }
        }
    }

    private class TaskDetailAliasHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            String path = exchange.getRequestURI().getPath();
            String[] parts = path.split("/");
            if (parts.length < 4) {
                sendError(exchange, 400, "Invalid path");
                return;
            }

            String id = parts[3];
            String action = parts.length > 4 ? parts[4] : "";
            SpiderInstance instance = spiders.get(id);
            if (instance == null) {
                sendError(exchange, 404, "Task not found");
                return;
            }

            if ("".equals(action) && "GET".equals(exchange.getRequestMethod())) {
                Map<String, Object> response = new LinkedHashMap<>();
                response.put("success", true);
                response.put("data", taskPayload(id, instance));
                sendResponse(exchange, 200, toJson(response), "application/json");
                return;
            }
            if ("start".equals(action) && "POST".equals(exchange.getRequestMethod())) {
                instance.start();
                sendResponse(exchange, 200, toJson(Map.of(
                    "success", true,
                    "message", "Task started",
                    "data", Map.of("message", "Task started")
                )), "application/json");
                return;
            }
            if ("stop".equals(action) && "POST".equals(exchange.getRequestMethod())) {
                instance.stop();
                sendResponse(exchange, 200, toJson(Map.of(
                    "success", true,
                    "message", "Task stopped",
                    "data", Map.of("message", "Task stopped")
                )), "application/json");
                return;
            }
            if ("".equals(action) && "DELETE".equals(exchange.getRequestMethod())) {
                spiders.remove(id);
                sendResponse(exchange, 200, toJson(Map.of(
                    "success", true,
                    "message", "Task deleted",
                    "data", Map.of("message", "Task deleted")
                )), "application/json");
                return;
            }
            if ("results".equals(action) && "GET".equals(exchange.getRequestMethod())) {
                int page = parseQueryInt(exchange, "page", 1);
                int perPage = parseQueryInt(exchange, "per_page", 20);
                List<Map<String, Object>> results = instance.snapshotResults();
                Map<String, Object> response = new LinkedHashMap<>();
                response.put("success", true);
                response.put("data", paginate(results, page, perPage));
                response.put("pagination", paginationEnvelope(results.size(), page, perPage));
                sendResponse(exchange, 200, toJson(response), "application/json");
                return;
            }
            if ("artifacts".equals(action) && "GET".equals(exchange.getRequestMethod())) {
                Map<String, Object> response = new LinkedHashMap<>();
                response.put("success", true);
                response.put("data", collectArtifacts(instance.snapshotResults()));
                sendResponse(exchange, 200, toJson(response), "application/json");
                return;
            }
            if ("logs".equals(action) && "GET".equals(exchange.getRequestMethod())) {
                int page = parseQueryInt(exchange, "page", 1);
                int perPage = parseQueryInt(exchange, "per_page", 50);
                List<Map<String, Object>> logs = instance.snapshotLogs();
                Map<String, Object> response = new LinkedHashMap<>();
                response.put("success", true);
                response.put("data", paginate(logs, page, perPage));
                response.put("pagination", paginationEnvelope(logs.size(), page, perPage));
                sendResponse(exchange, 200, toJson(response), "application/json");
                return;
            }

            sendError(exchange, 404, "Not found");
        }
    }

    private static class TaskPageProcessor implements PageProcessor {
        @Override
        public void process(Page page) {
        }

        @Override
        public Site getSite() {
            return new Site();
        }
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> collectArtifacts(List<Map<String, Object>> results) {
        Map<String, Object> artifacts = new LinkedHashMap<>();
        for (Map<String, Object> result : results) {
            Object value = result.get("artifacts");
            if (value instanceof Map<?, ?> current) {
                for (Map.Entry<?, ?> entry : current.entrySet()) {
                    String key = String.valueOf(entry.getKey());
                    artifacts.putIfAbsent(key, entry.getValue());
                }
            }
        }
        return artifacts;
    }
}
