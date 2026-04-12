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
        HttpServer server = HttpServer.create(new InetSocketAddress(0), 0);
        server.createContext("/", exchange -> {
            byte[] body = "<html><head><title>Java Task Demo</title></head><body>ok</body></html>"
                .getBytes(java.nio.charset.StandardCharsets.UTF_8);
            exchange.getResponseHeaders().add("Content-Type", "text/html; charset=utf-8");
            exchange.sendResponseHeaders(200, body.length);
            exchange.getResponseBody().write(body);
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
