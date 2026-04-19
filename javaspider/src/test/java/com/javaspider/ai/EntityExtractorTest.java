package com.javaspider.ai;

import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;

class EntityExtractorTest {

    @Test
    void extractsStructuredAndRegexEntities() {
        Map<String, java.util.List<String>> result = new EntityExtractor().extract("""
            <html>
              <head><meta name="author" content="Lan"></head>
              <body>
                <div class="organization">OpenAI</div>
                <div class="address">Shanghai</div>
                <div class="product-title">Spider Pro</div>
                联系 support@example.com 价格 $19.99 发布于 2026-04-13
              </body>
            </html>
            """);

        assertEquals("Lan", result.get("persons").get(0));
        assertEquals("OpenAI", result.get("organizations").get(0));
        assertEquals("Spider Pro", result.get("products").get(0));
        assertEquals("support@example.com", result.get("email").get(0));
    }
}
