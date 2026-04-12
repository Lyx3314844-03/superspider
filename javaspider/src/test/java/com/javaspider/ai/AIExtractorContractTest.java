package com.javaspider.ai;

import org.junit.jupiter.api.Test;

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
}
