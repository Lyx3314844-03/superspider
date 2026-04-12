package com.javaspider.parser;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

class HtmlParserXPathContractTest {

    @Test
    void xpathFirstSupportsFullXPath() {
        HtmlParser parser = new HtmlParser("<html><div><span>One</span><span>Two</span></div></html>");
        assertEquals("Two", parser.xpathFirst("//div/span[2]/text()"));
    }

    @Test
    void xpathFirstRejectsInvalidExpressions() {
        HtmlParser parser = new HtmlParser("<html><div><span>Demo</span></div></html>");
        assertThrows(IllegalArgumentException.class, () -> parser.xpathFirst("//*["));
    }
}
