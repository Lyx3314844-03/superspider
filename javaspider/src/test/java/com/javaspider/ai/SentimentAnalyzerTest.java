package com.javaspider.ai;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class SentimentAnalyzerTest {

    @Test
    void classifiesPositiveHtml() {
        SentimentAnalyzer.SentimentResult result = new SentimentAnalyzer()
            .analyze("<html><body>Excellent product, wonderful quality, great support.</body></html>");

        assertEquals("positive", result.sentiment());
        assertTrue(result.positiveCount() > 0);
    }
}
