package com.javaspider.ai;

import org.junit.jupiter.api.Test;

import com.sun.net.httpserver.HttpServer;

import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;

class AIExtractorContractTest {

    @Test
    void fromEnvironmentSupportsConfigurableEndpointAndModel() {
        Map<String, String> env = new LinkedHashMap<>();
        env.put("AI_API_KEY", "test-key");
        env.put("AI_BASE_URL", "https://proxy.example.com/v1");
        env.put("AI_MODEL", "gpt-test");
        env.put("AI_MAX_TOKENS", "4096");
        env.put("AI_TEMPERATURE", "0.2");

        AIExtractor extractor = AIExtractor.fromEnvironment(env);

        assertEquals("https://proxy.example.com/v1", extractor.baseUrl());
        assertEquals("gpt-test", extractor.model());
        assertEquals(4096, extractor.maxTokens());
        assertEquals(0.2d, extractor.temperature());
        assertEquals("openai", extractor.provider());
    }

    @Test
    void fromEnvironmentSupportsAnthropicEndpointAndModel() {
        Map<String, String> env = new LinkedHashMap<>();
        env.put("AI_PROVIDER", "anthropic");
        env.put("ANTHROPIC_API_KEY", "anthropic-key");
        env.put("ANTHROPIC_BASE_URL", "https://api.anthropic.test/v1");
        env.put("ANTHROPIC_MODEL", "claude-sonnet-4-20250514");

        AIExtractor extractor = AIExtractor.fromEnvironment(env);

        assertEquals("https://api.anthropic.test/v1", extractor.baseUrl());
        assertEquals("claude-sonnet-4-20250514", extractor.model());
        assertEquals("anthropic", extractor.provider());
    }

    @Test
    void parseJsonSupportsNestedObjectsAndArrays() {
        AIExtractor extractor = new AIExtractor("test-key", "https://api.example.com/v1", "test-model");

        Map<String, Object> payload = extractor.parseJson("""
            {
              "title": "Demo",
              "count": 2,
              "flags": {
                "ok": true
              },
              "items": [
                {"name": "alpha"},
                {"name": "beta"}
              ]
            }
            """);

        assertEquals("Demo", payload.get("title"));
        assertEquals(2L, payload.get("count"));
        assertEquals(true, ((Map<?, ?>) payload.get("flags")).get("ok"));
        Object items = payload.get("items");
        assertInstanceOf(List.class, items);
        assertEquals("alpha", ((Map<?, ?>) ((List<?>) items).get(0)).get("name"));
    }

    @Test
    void parseJsonExtractsEmbeddedJsonFromTextResponses() {
        AIExtractor extractor = new AIExtractor("test-key", "https://api.example.com/v1", "test-model");

        Map<String, Object> payload = extractor.parseJson("""
            Here is the result:
            {
              "result": "done",
              "score": 0.98
            }
            Thank you.
            """);

        assertEquals("done", payload.get("result"));
        assertEquals(0.98d, payload.get("score"));
    }

    @Test
    void extractStructuredNormalizesPayloadAgainstSchema() throws Exception {
        AIExtractor extractor = new AIExtractor("test-key", "https://api.example.com/v1", "test-model") {
            @Override
            String callLLM(String prompt) {
                return """
                    结果如下：
                    {
                      "title": ["Demo"],
                      "views": "42",
                      "published": "true",
                      "links": "https://example.com/a",
                      "meta": {
                        "score": "9.5"
                      }
                    }
                    """;
            }
        };

        Map<String, Object> payload = extractor.extractStructured(
            "<html><head><title>Demo</title></head></html>",
            "提取标题和指标",
            Map.of(
                "type", "object",
                "properties", Map.of(
                    "title", Map.of("type", "string"),
                    "views", Map.of("type", "integer"),
                    "published", Map.of("type", "boolean"),
                    "links", Map.of(
                        "type", "array",
                        "items", Map.of("type", "string")
                    ),
                    "meta", Map.of(
                        "type", "object",
                        "properties", Map.of(
                            "score", Map.of("type", "number")
                        )
                    )
                )
            )
        );

        assertEquals("Demo", payload.get("title"));
        assertInstanceOf(Number.class, payload.get("views"));
        assertEquals(42L, ((Number) payload.get("views")).longValue());
        assertEquals(true, payload.get("published"));
        assertEquals(List.of("https://example.com/a"), payload.get("links"));
        assertEquals(9.5d, ((Map<?, ?>) payload.get("meta")).get("score"));
    }

    @Test
    void understandPageSupportsAnthropicMessagesEndpoint() throws Exception {
        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/messages", exchange -> {
            byte[] body = """
                {
                  "content": [
                    { "type": "text", "text": "anthropic-response" }
                  ]
                }
                """.getBytes(java.nio.charset.StandardCharsets.UTF_8);
            exchange.getResponseHeaders().add("Content-Type", "application/json");
            exchange.sendResponseHeaders(200, body.length);
            try (OutputStream out = exchange.getResponseBody()) {
                out.write(body);
            }
        });
        server.start();

        try {
            AIExtractor extractor = new AIExtractor(
                "anthropic-key",
                "http://127.0.0.1:" + server.getAddress().getPort(),
                "claude-sonnet-4-20250514",
                256,
                0.1,
                "anthropic"
            );

            String response = extractor.understandPage("<html></html>", "是什么页面？");
            assertEquals("anthropic-response", response);
        } finally {
            server.stop(0);
        }
    }

    @Test
    void understandPageFewShotSendsExamplesToOpenAIStyleEndpoint() throws Exception {
        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/chat/completions", exchange -> {
            byte[] requestBody = exchange.getRequestBody().readAllBytes();
            String request = new String(requestBody, java.nio.charset.StandardCharsets.UTF_8);
            org.junit.jupiter.api.Assertions.assertTrue(request.contains("\"role\":\"assistant\""));
            org.junit.jupiter.api.Assertions.assertTrue(request.contains("示例回答"));

            byte[] body = """
                {
                  "choices": [
                    { "message": { "content": "few-shot-response" } }
                  ]
                }
                """.getBytes(java.nio.charset.StandardCharsets.UTF_8);
            exchange.getResponseHeaders().add("Content-Type", "application/json");
            exchange.sendResponseHeaders(200, body.length);
            try (OutputStream out = exchange.getResponseBody()) {
                out.write(body);
            }
        });
        server.start();

        try {
            AIExtractor extractor = new AIExtractor(
                "openai-key",
                "http://127.0.0.1:" + server.getAddress().getPort(),
                "gpt-5.2",
                256,
                0.1,
                "openai"
            );
            String response = extractor.understandPageFewShot(
                "<html></html>",
                "这是什么？",
                List.of(Map.of("user", "示例问题", "assistant", "示例回答"))
            );
            assertEquals("few-shot-response", response);
        } finally {
            server.stop(0);
        }
    }
}
