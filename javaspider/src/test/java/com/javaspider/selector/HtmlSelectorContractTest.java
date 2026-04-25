package com.javaspider.selector;

import org.junit.jupiter.api.Test;

import com.javaspider.extractor.SelectorExtractor;

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
    void htmlXPathUsesRealXPathEvaluation() {
        Html html = new Html("<html><body><div><span>One</span><span>Two</span></div></body></html>");

        assertEquals("Two", html.xpath("//div/span[2]/text()").get());
    }

    @Test
    void selectorExtractorSupportsComplexCssAndXpathRules() {
        String html = """
            <html><body>
              <article class="product" data-sku="A1"><h2><span>Alpha</span></h2><a class="buy" href="/alpha">Buy</a></article>
              <article class="product featured" data-sku="B2"><h2><span>Beta</span></h2><a class="buy" href="/beta">Buy</a></article>
            </body></html>
            """;

        Map<String, Object> extracted = new SelectorExtractor().extract(html, List.of(
            SelectorExtractor.Rule.cssAll("names", "article.product > h2 span::text"),
            SelectorExtractor.Rule.xpath("featured_sku", "//article[contains(@class, 'featured')]/@data-sku"),
            new SelectorExtractor.Rule("links", "css", "article.product a.buy::attr(href)", null, true, false)
        ));

        assertEquals(List.of("Alpha", "Beta"), extracted.get("names"));
        assertEquals("B2", extracted.get("featured_sku"));
        assertEquals(List.of("/alpha", "/beta"), extracted.get("links"));
    }

    @Test
    void locatorAnalyzerBuildsCssAndXpathCandidates() {
        String html = """
            <html><body><form>
              <input id="search-box" name="q" placeholder="Search products">
              <button data-testid="submit-search">Search</button>
            </form></body></html>
            """;

        LocatorAnalyzer.LocatorPlan plan = new LocatorAnalyzer().analyze(
            html,
            LocatorAnalyzer.LocatorTarget.forField("q")
        );

        java.util.Set<String> expressions = plan.candidates().stream()
            .map(candidate -> candidate.kind() + " " + candidate.expr())
            .collect(java.util.stream.Collectors.toSet());

        assertEquals(true, expressions.contains("css #search-box"));
        assertEquals(true, expressions.contains("xpath //input[@name='q']"));
    }

    @Test
    void devToolsAnalyzerSnapshotsElementsAndSelectsNodeReverseRoute() {
        String html = """
            <html><body>
              <input id="kw" name="q">
              <script src="/static/app.js"></script>
              <script>const token = CryptoJS.MD5(window.navigator.userAgent).toString();</script>
            </body></html>
            """;

        DevToolsAnalyzer.DevToolsReport report = new DevToolsAnalyzer().analyze(
            html,
            List.of(new DevToolsAnalyzer.DevToolsNetworkArtifact(
                "https://example.com/api/search?sign=abc",
                "GET",
                200,
                "xhr"
            )),
            List.of()
        );

        assertEquals(true, report.elements().size() >= 3);
        assertEquals("analyze_crypto", report.bestReverseRoute().kind());
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
