package com.javaspider.graph;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class GraphBuilderTest {

    @Test
    void buildFromHtmlExtractsTitleLinksAndImages() {
        GraphBuilder builder = new GraphBuilder().buildFromHtml("""
            <html>
              <head><title>Java Graph Demo</title></head>
              <body>
                <h1>Headline</h1>
                <a href="https://example.com/page">Read more</a>
                <img src="https://example.com/image.png" alt="demo" />
              </body>
            </html>
            """);

        assertEquals("document", builder.rootId());
        assertEquals(1, builder.links().size());
        assertEquals(1, builder.images().size());
        assertEquals("Java Graph Demo", builder.nodes().get("title-0").text());
        assertTrue(builder.stats().getOrDefault("type_heading", 0) >= 1);
    }
}
