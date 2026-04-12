package com.javaspider.selector;

import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;

class HtmlSelectorContractTest {

    @Test
    void jsonPathSupportsNestedFieldsAndIndexes() {
        Html html = new Html("""
            {
              "data": {
                "items": [
                  {"title": "alpha"},
                  {"title": "beta"}
                ]
              }
            }
            """);

        assertEquals("alpha", html.jsonPath("$.data.items[0].title").get());
        assertEquals(List.of("alpha", "beta"), html.jsonPath("$.data.items[*].title").all());
    }

    @Test
    void jsonPathReturnsNullWhenDocumentIsNotJson() {
        Html html = new Html("<html><head><title>Demo</title></head><body><p>Hello</p></body></html>");

        assertNull(html.jsonPath("$.data.title").get());
        assertEquals(List.of(), html.jsonPath("$.data.title").all());
    }

    @Test
    void aiExtractUsesTitleDescriptionAndLinksHeuristics() {
        Html html = new Html("""
            <html>
              <head>
                <title>Demo Title</title>
                <meta name="description" content="Demo Description" />
              </head>
              <body>
                <a href="https://example.com/a">A</a>
                <a href="/b">B</a>
                <p>Paragraph text</p>
              </body>
            </html>
            """, "https://example.com/root");

        assertEquals("Demo Title", html.aiExtract("extract title").get());
        assertEquals("Demo Description", html.aiExtract("extract description").get());
        assertEquals(List.of("https://example.com/a", "https://example.com/b"), html.aiExtract("extract links").all());
    }

    @Test
    void aiExtractUsesInjectedAiResponderForSingleValue() {
        Html.setAiResponderForTests((content, prompt) -> "AI Title");
        try {
            Html html = new Html("<html><head><title>Fallback</title></head><body><p>Body</p></body></html>");
            assertEquals("AI Title", html.aiExtract("extract title with ai").get());
        } finally {
            Html.resetAiResponderForTests();
        }
    }

    @Test
    void aiExtractUsesInjectedAiResponderForArrayPayload() {
        Html.setAiResponderForTests((content, prompt) -> "[\"https://example.com/1\",\"https://example.com/2\"]");
        try {
            Html html = new Html("<html><body><a href=\"/fallback\">Fallback</a></body></html>", "https://example.com/root");
            assertEquals(
                List.of("https://example.com/1", "https://example.com/2"),
                html.aiExtract("extract links with ai").all()
            );
        } finally {
            Html.resetAiResponderForTests();
        }
    }

    @Test
    void aiExtractStructuredUsesInjectedStructuredResponder() {
        Html.setStructuredAiResponderForTests((content, instructions, schema) -> Map.of(
            "title", "AI Structured Title",
            "links", List.of("https://example.com/structured")
        ));
        try {
            Html html = new Html("<html><head><title>Fallback</title></head><body></body></html>");
            Map<String, Object> extracted = html.aiExtractStructured(
                "extract structured data",
                Map.of(
                    "type", "object",
                    "properties", Map.of(
                        "title", Map.of("type", "string"),
                        "links", Map.of("type", "array")
                    )
                )
            );

            assertEquals("AI Structured Title", extracted.get("title"));
            assertEquals(List.of("https://example.com/structured"), extracted.get("links"));
        } finally {
            Html.resetStructuredAiResponderForTests();
        }
    }

    @Test
    void aiExtractStructuredFallsBackToSchemaDrivenHeuristics() {
        Html html = new Html("""
            <html>
              <head>
                <title>Schema Title</title>
                <meta name="description" content="Schema Description" />
              </head>
              <body>
                <a href="https://example.com/a">A</a>
                <img src="/image.png" />
                <p>Body Text</p>
              </body>
            </html>
            """, "https://example.com/root");

        Map<String, Object> extracted = html.aiExtractStructured(
            "extract schema fields",
            Map.of(
                "type", "object",
                "properties", Map.of(
                    "title", Map.of("type", "string"),
                    "description", Map.of("type", "string"),
                    "links", Map.of("type", "array"),
                    "images", Map.of("type", "array"),
                    "content", Map.of("type", "string")
                )
            )
        );

        assertEquals("Schema Title", extracted.get("title"));
        assertEquals("Schema Description", extracted.get("description"));
        assertEquals(List.of("https://example.com/a"), extracted.get("links"));
        assertEquals(List.of("https://example.com/image.png"), extracted.get("images"));
    }

    @Test
    void aiExtractStructuredNormalizesAiPayloadAndBackfillsMissingFields() {
        Html.setStructuredAiResponderForTests((content, instructions, schema) -> Map.of(
            "title", List.of("AI Title"),
            "description", 99,
            "links", "https://example.com/from-ai"
        ));
        try {
            Html html = new Html("""
                <html>
                  <head>
                    <title>Fallback Title</title>
                    <meta name="description" content="Fallback Description" />
                  </head>
                  <body>
                    <img src="/cover.png" />
                  </body>
                </html>
                """, "https://example.com/root");

            Map<String, Object> extracted = html.aiExtractStructured(
                "extract structured data",
                Map.of(
                    "type", "object",
                    "properties", Map.of(
                        "title", Map.of("type", "string"),
                        "description", Map.of("type", "string"),
                        "links", Map.of(
                            "type", "array",
                            "items", Map.of("type", "string")
                        ),
                        "images", Map.of(
                            "type", "array",
                            "items", Map.of("type", "string")
                        )
                    )
                )
            );

            assertEquals("AI Title", extracted.get("title"));
            assertEquals("99", extracted.get("description"));
            assertEquals(List.of("https://example.com/from-ai"), extracted.get("links"));
            assertEquals(List.of("https://example.com/cover.png"), extracted.get("images"));
        } finally {
            Html.resetStructuredAiResponderForTests();
        }
    }
}
