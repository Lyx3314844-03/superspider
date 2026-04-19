package com.javaspider.web.controller;

import com.javaspider.core.Page;
import com.javaspider.core.Site;
import com.javaspider.core.Spider;
import com.javaspider.processor.PageProcessor;
import com.sun.net.httpserver.Headers;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.Test;

import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.net.InetSocketAddress;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class SpiderControllerTest {

    @Test
    void spiderInstanceTracksLogsAndResultsAcrossStartStop() throws Exception {
        Spider spider = new Spider(new NoopPageProcessor()).name("web-controller-test");
        SpiderController.SpiderInstance instance = new SpiderController.SpiderInstance(spider);

        instance.start();
        Thread.sleep(100);
        instance.stop();
        Thread.sleep(100);

        List<Map<String, Object>> logs = instance.snapshotLogs();
        List<Map<String, Object>> results = instance.snapshotResults();

        assertTrue(logs.stream().anyMatch(entry -> "spider started".equals(entry.get("message"))));
        assertTrue(logs.stream().anyMatch(entry -> "spider stop requested".equals(entry.get("message"))));
        assertTrue(results.stream().anyMatch(entry -> "running".equals(entry.get("status"))));
        assertTrue(results.stream().anyMatch(entry -> "stopped".equals(entry.get("status"))));
    }

    @Test
    void spiderInstanceFetchesTaskUrlAndProducesStructuredResult() throws Exception {
        byte[] expectedBody = "<html><head><title>Java Task Demo</title></head><body>ok</body></html>"
            .getBytes(java.nio.charset.StandardCharsets.UTF_8);
        HttpServer server = HttpServer.create(new InetSocketAddress(0), 0);
        server.createContext("/", exchange -> {
            exchange.getResponseHeaders().add("Content-Type", "text/html; charset=utf-8");
            exchange.sendResponseHeaders(200, expectedBody.length);
            exchange.getResponseBody().write(expectedBody);
            exchange.close();
        });
        server.start();
        try {
            String url = "http://127.0.0.1:" + server.getAddress().getPort() + "/";
            Spider spider = new Spider(new NoopPageProcessor()).name("java-task-demo");
            SpiderController.SpiderInstance instance = new SpiderController.SpiderInstance(
                spider,
                url,
                Map.of("mode", "test")
            );

            instance.start();
            List<Map<String, Object>> results = List.of();
            long deadline = System.currentTimeMillis() + 3000;
            while (System.currentTimeMillis() < deadline) {
                results = instance.snapshotResults();
                if (results.stream().anyMatch(entry -> "completed".equals(entry.get("status")))) {
                    break;
                }
                Thread.sleep(50);
            }
            assertTrue(results.stream().anyMatch(entry -> "completed".equals(entry.get("status"))));
            Map<String, Object> result = results.stream()
                .filter(entry -> "completed".equals(entry.get("status")))
                .findFirst()
                .orElseThrow();
            assertEquals("Java Task Demo", result.get("title"));
            assertEquals(url, result.get("url"));
            assertEquals(200, result.get("http_status"));
            assertEquals(spider.getSpiderId(), result.get("task_id"));
            @SuppressWarnings("unchecked")
            Map<String, Object> artifacts = (Map<String, Object>) result.get("artifacts");
            @SuppressWarnings("unchecked")
            Map<String, Object> graph = (Map<String, Object>) artifacts.get("graph");
            assertEquals("graph", graph.get("kind"));
            @SuppressWarnings("unchecked")
            Map<String, Object> artifactRefs = (Map<String, Object>) result.get("artifact_refs");
            assertTrue(artifactRefs.containsKey("graph"));
            assertTrue(Files.exists(Path.of(String.valueOf(graph.get("path")))));
            Method collectArtifacts = SpiderController.class.getDeclaredMethod("collectArtifacts", List.class);
            collectArtifacts.setAccessible(true);
            @SuppressWarnings("unchecked")
            Map<String, Object> artifactPayload = (Map<String, Object>) collectArtifacts.invoke(new SpiderController(), results);
            assertTrue(artifactPayload.containsKey("graph"));
            Map<String, Object> stats = instance.getStats();
            assertEquals(1, ((Number) stats.get("success_requests")).intValue());
            assertTrue(((Number) stats.get("qps")).doubleValue() > 0.0);
            assertTrue(((Number) stats.get("avg_duration_ms")).doubleValue() >= 0.0);
            assertTrue(((Number) stats.get("p95_duration_ms")).doubleValue() >= 0.0);
            assertTrue(((Number) stats.get("total_bytes")).longValue() >= expectedBody.length);
        } finally {
            server.stop(0);
        }
    }

    @Test
    void registerSpiderRejectsPayloadWithoutUrl() throws Exception {
        SpiderController controller = new SpiderController();
        Method registerSpider = SpiderController.class.getDeclaredMethod("registerSpider", Map.class, String.class);
        registerSpider.setAccessible(true);

        InvocationTargetException error = assertThrows(
            InvocationTargetException.class,
            () -> registerSpider.invoke(controller, Map.of("name", "missing-url"), "task_")
        );

        assertTrue(error.getCause() instanceof IllegalArgumentException);
        assertEquals("Task url is required", error.getCause().getMessage());
    }

    @Test
    void registerSpiderNormalizesTaskPayloadAndStoresUrls() throws Exception {
        SpiderController controller = new SpiderController();
        Method registerSpider = SpiderController.class.getDeclaredMethod("registerSpider", Map.class, String.class);
        registerSpider.setAccessible(true);

        @SuppressWarnings("unchecked")
        Map<String, Object> payload = (Map<String, Object>) registerSpider.invoke(
            controller,
            Map.of(
                "name", "normalized-task",
                "target", Map.of("url", "https://example.com/one"),
                "urls", List.of("https://example.com/two"),
                "auto_start", false
            ),
            "task_"
        );

        assertEquals("normalized-task", payload.get("name"));
        assertEquals("https://example.com/one", payload.get("url"));
        assertEquals("pending", payload.get("status"));
        assertFalse((Boolean) payload.get("running"));
    }

    @Test
    void javaControllerAuthProtectsApiRoutesOnlyWhenTokenConfigured() {
        SpiderController controller = new SpiderController("secret-token");
        Headers headers = new Headers();

        assertTrue(controller.isAuthorizedRequest("/", "GET", headers));
        assertFalse(controller.isAuthorizedRequest("/api/tasks", "GET", headers));

        headers.add("Authorization", "Bearer secret-token");
        assertTrue(controller.isAuthorizedRequest("/api/tasks", "GET", headers));
    }

    @Test
    void buildGraphPayloadReturnsNodesEdgesAndStats() throws Exception {
        SpiderController controller = new SpiderController();
        Method buildGraphPayload = SpiderController.class.getDeclaredMethod("buildGraphPayload", Map.class);
        buildGraphPayload.setAccessible(true);

        @SuppressWarnings("unchecked")
        Map<String, Object> payload = (Map<String, Object>) buildGraphPayload.invoke(
            controller,
            Map.of(
                "html",
                "<html><head><title>Java Graph API</title></head><body><a href='https://example.com/page'>Read</a><img src='https://example.com/image.png'/></body></html>"
            )
        );

        assertEquals("document", payload.get("root_id"));
        @SuppressWarnings("unchecked")
        Map<String, Object> stats = (Map<String, Object>) payload.get("stats");
        assertTrue(((Integer) stats.get("total_nodes")) >= 3);
    }

    @Test
    void researchResponsesRunAsyncAndSoak() throws Exception {
        SpiderController controller = new SpiderController();
        Method runMethod = SpiderController.class.getDeclaredMethod("buildResearchRunResponse", Map.class);
        Method asyncMethod = SpiderController.class.getDeclaredMethod("buildResearchAsyncResponse", Map.class);
        Method soakMethod = SpiderController.class.getDeclaredMethod("buildResearchSoakResponse", Map.class);
        runMethod.setAccessible(true);
        asyncMethod.setAccessible(true);
        soakMethod.setAccessible(true);

        @SuppressWarnings("unchecked")
        Map<String, Object> runPayload = (Map<String, Object>) runMethod.invoke(
            controller,
            Map.of(
                "url", "https://example.com",
                "content", "<title>Research API</title>",
                "schema_json", "{\"properties\":{\"title\":{\"type\":\"string\"}}}"
            )
        );
        @SuppressWarnings("unchecked")
        Map<String, Object> runResult = (Map<String, Object>) runPayload.get("result");
        @SuppressWarnings("unchecked")
        Map<String, Object> extract = (Map<String, Object>) runResult.get("extract");
        assertEquals("research run", runPayload.get("command"));
        assertEquals("Research API", extract.get("title"));

        @SuppressWarnings("unchecked")
        Map<String, Object> asyncPayload = (Map<String, Object>) asyncMethod.invoke(
            controller,
            Map.of(
                "urls", List.of("https://example.com/1", "https://example.com/2"),
                "content", "<title>Async API</title>",
                "schema_json", "{\"properties\":{\"title\":{\"type\":\"string\"}}}",
                "concurrency", 2
            )
        );
        assertEquals("research async", asyncPayload.get("command"));
        assertEquals(2, ((List<?>) asyncPayload.get("results")).size());

        @SuppressWarnings("unchecked")
        Map<String, Object> soakPayload = (Map<String, Object>) soakMethod.invoke(
            controller,
            Map.of(
                "urls", List.of("https://example.com/1", "https://example.com/2"),
                "content", "<title>Soak API</title>",
                "schema_json", "{\"properties\":{\"title\":{\"type\":\"string\"}}}",
                "concurrency", 2,
                "rounds", 2
            )
        );
        @SuppressWarnings("unchecked")
        Map<String, Object> report = (Map<String, Object>) soakPayload.get("report");
        assertEquals("research soak", soakPayload.get("command"));
        assertEquals(4, report.get("results"));
    }

    @Test
    void researchHistoryIsRecorded() throws Exception {
        SpiderController controller = new SpiderController();
        Method runMethod = SpiderController.class.getDeclaredMethod("buildResearchRunResponse", Map.class);
        Method recordMethod = SpiderController.class.getDeclaredMethod("recordResearchHistory", Map.class);
        recordMethod.setAccessible(true);
        runMethod.setAccessible(true);

        @SuppressWarnings("unchecked")
        Map<String, Object> payload = (Map<String, Object>) runMethod.invoke(
            controller,
            Map.of(
                "url", "https://example.com",
                "content", "<title>History Demo</title>",
                "schema_json", "{\"properties\":{\"title\":{\"type\":\"string\"}}}"
            )
        );
        recordMethod.invoke(controller, payload);

        java.lang.reflect.Field historyField = SpiderController.class.getDeclaredField("researchHistory");
        historyField.setAccessible(true);
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> history = (List<Map<String, Object>>) historyField.get(controller);
        assertEquals(1, history.size());
        assertEquals("research run", history.get(0).get("command"));
        assertTrue(Files.exists(Path.of("artifacts", "control-plane", "research-history.jsonl")));
    }

    private static class NoopPageProcessor implements PageProcessor {
        @Override
        public void process(Page page) {
        }

        @Override
        public Site getSite() {
            return new Site();
        }
    }
}
