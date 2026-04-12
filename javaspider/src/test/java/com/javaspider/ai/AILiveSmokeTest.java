package com.javaspider.ai;

import org.junit.jupiter.api.Assumptions;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.util.LinkedHashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class AILiveSmokeTest {

    @Test
    void extractStructuredWithLiveApi() throws IOException {
        String enabled = System.getenv("JAVASPIDER_LIVE_AI_SMOKE");
        String apiKey = firstNonBlank(System.getenv("OPENAI_API_KEY"), System.getenv("AI_API_KEY"));

        Assumptions.assumeTrue(
            enabled != null && (enabled.equals("1") || enabled.equalsIgnoreCase("true")),
            "live AI smoke is disabled"
        );
        Assumptions.assumeTrue(apiKey != null && !apiKey.isBlank(), "AI API key is missing");

        AIExtractor extractor = AIExtractor.fromEnv();
        Map<String, Object> schema = new LinkedHashMap<>();
        schema.put("type", "object");
        schema.put("properties", Map.of(
            "title", Map.of("type", "string"),
            "description", Map.of("type", "string"),
            "links", Map.of(
                "type", "array",
                "items", Map.of("type", "string")
            )
        ));

        Map<String, Object> extracted = extractor.extractStructured(
            """
            <html>
              <head>
                <title>Live Demo Title</title>
                <meta name="description" content="Live Demo Description" />
              </head>
              <body>
                <a href="https://example.com/a">Alpha</a>
                <a href="https://example.com/b">Beta</a>
              </body>
            </html>
            """,
            "提取标题、描述和链接列表。links 必须是字符串数组。",
            schema
        );

        assertEquals("Live Demo Title", String.valueOf(extracted.get("title")));
        assertTrue(String.valueOf(extracted.get("description")).contains("Live Demo Description"));
        Object links = extracted.get("links");
        assertTrue(links instanceof Iterable<?>, "links should be iterable");
    }

    private static String firstNonBlank(String first, String second) {
        if (first != null && !first.isBlank()) {
            return first;
        }
        if (second != null && !second.isBlank()) {
            return second;
        }
        return null;
    }
}
