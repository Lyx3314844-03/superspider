package com.javaspider.ai;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class ContentSummarizerTest {

    @Test
    void usesMetaDescriptionWhenAvailable() {
        ContentSummarizer.SummaryResult result = new ContentSummarizer(2)
            .summarize("<html><head><title>Demo</title><meta name=\"description\" content=\"Short summary\"></head><body></body></html>");

        assertEquals("meta_description", result.method());
        assertEquals("Short summary", result.summary());
        assertEquals("Demo", result.title());
    }
}
