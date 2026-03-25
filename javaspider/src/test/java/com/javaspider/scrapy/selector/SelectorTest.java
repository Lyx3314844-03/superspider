package com.javaspider.scrapy.selector;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.DisplayName;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Selector 类单元测试
 */
class SelectorTest {

    private static final String SAMPLE_HTML = """
        <html>
            <head>
                <title>Test Page</title>
            </head>
            <body>
                <h1 class="title">Hello World</h1>
                <div class="content">
                    <p class="para1">Paragraph 1</p>
                    <p class="para2">Paragraph 2</p>
                    <a href="/link1">Link 1</a>
                    <a href="/link2">Link 2</a>
                    <a href="https://external.com">External</a>
                </div>
                <ul id="list">
                    <li>Item 1</li>
                    <li>Item 2</li>
                    <li>Item 3</li>
                </ul>
            </body>
        </html>
        """;

    @Test
    @DisplayName("创建 Selector")
    void testCreateSelector() {
        Selector selector = Selector.select(SAMPLE_HTML);
        
        assertNotNull(selector);
        assertNotNull(selector.getDocument());
    }

    @Test
    @DisplayName("CSS 选择器 - 单个元素")
    void testCssFirst() {
        Selector selector = Selector.select(SAMPLE_HTML);
        
        String title = selector.css("h1.title").firstText();
        
        assertEquals("Hello World", title);
    }

    @Test
    @DisplayName("CSS 选择器 - 多个元素")
    void testCssAll() {
        Selector selector = Selector.select(SAMPLE_HTML);
        
        List<String> paragraphs = selector.css("p").all();
        
        assertEquals(2, paragraphs.size());
        assertEquals("Paragraph 1", paragraphs.get(0));
        assertEquals("Paragraph 2", paragraphs.get(1));
    }

    @Test
    @DisplayName("CSS 选择器 - 获取属性")
    void testCssAttr() {
        Selector selector = Selector.select(SAMPLE_HTML);
        
        List<String> hrefs = selector.css("a").attrs("href");
        
        assertEquals(3, hrefs.size());
        assertTrue(hrefs.contains("/link1"));
        assertTrue(hrefs.contains("/link2"));
        assertTrue(hrefs.contains("https://external.com"));
    }

    @Test
    @DisplayName("CSS 选择器 - 第一个属性")
    void testCssAttrFirst() {
        Selector selector = Selector.select(SAMPLE_HTML);
        
        String firstHref = selector.css("a").attr("href");
        
        assertEquals("/link1", firstHref);
    }

    @Test
    @DisplayName("XPath 选择器 - 基本查询")
    void testXpath() {
        Selector selector = Selector.select(SAMPLE_HTML);
        
        // 简单的 XPath 转换测试
        List<String> items = selector.xpath("//li").all();
        
        assertEquals(3, items.size());
    }

    @Test
    @DisplayName("XPath 选择器 - 属性查询")
    void testXpathWithAttribute() {
        Selector selector = Selector.select(SAMPLE_HTML);
        
        List<String> titles = selector.xpath("//h1[@class='title']").all();
        
        assertEquals(1, titles.size());
        assertEquals("Hello World", titles.get(0));
    }

    @Test
    @DisplayName("正则表达式匹配")
    void testRegex() {
        Selector selector = Selector.select(SAMPLE_HTML);
        
        List<String> hrefs = selector.re("href=\"([^\"]+)\"");
        
        assertEquals(3, hrefs.size());
        assertTrue(hrefs.contains("/link1"));
    }

    @Test
    @DisplayName("正则表达式 - 第一个匹配")
    void testRegexFirst() {
        Selector selector = Selector.select(SAMPLE_HTML);
        
        String title = selector.reFirst("<title>([^<]+)</title>");
        
        assertEquals("Test Page", title);
    }

    @Test
    @DisplayName("获取 HTML")
    void testGetHtml() {
        Selector selector = Selector.select(SAMPLE_HTML);
        
        String html = selector.getHtml();
        
        assertNotNull(html);
        assertTrue(html.contains("<html>"));
        assertTrue(html.contains("</html>"));
    }

    @Test
    @DisplayName("获取文本")
    void testGetText() {
        Selector selector = Selector.select(SAMPLE_HTML);
        
        String text = selector.getText();
        
        assertNotNull(text);
        assertTrue(text.contains("Hello World"));
        assertTrue(text.contains("Paragraph 1"));
    }

    @Test
    @DisplayName("SelectorList - 链式 CSS")
    void testSelectorListChainedCss() {
        Selector selector = Selector.select(SAMPLE_HTML);
        
        List<String> texts = selector.css("div.content")
                                     .css("p")
                                     .all();
        
        assertEquals(2, texts.size());
    }

    @Test
    @DisplayName("SelectorList - 大小")
    void testSelectorListSize() {
        Selector selector = Selector.select(SAMPLE_HTML);
        
        int count = selector.css("li").size();
        
        assertEquals(3, count);
    }

    @Test
    @DisplayName("SelectorList - isEmpty")
    void testSelectorListIsEmpty() {
        Selector selector = Selector.select(SAMPLE_HTML);
        
        assertFalse(selector.css("li").isEmpty());
        assertTrue(selector.css("nonexistent").isEmpty());
    }

    @Test
    @DisplayName("SelectorList - 获取指定索引")
    void testSelectorListGet() {
        Selector selector = Selector.select(SAMPLE_HTML);
        
        String secondItem = selector.css("li").get(1).getText();
        
        assertEquals("Item 2", secondItem);
    }

    @Test
    @DisplayName("SelectorList - first 和 last")
    void testSelectorListFirstAndLast() {
        Selector selector = Selector.select(SAMPLE_HTML);
        
        String first = selector.css("li").first().getText();
        String last = selector.css("li").last().getText();
        
        assertEquals("Item 1", first);
        assertEquals("Item 3", last);
    }

    @Test
    @DisplayName("空 HTML 处理")
    void testEmptyHtml() {
        Selector selector = Selector.select("");
        
        List<String> results = selector.css("div").all();
        
        assertTrue(results.isEmpty());
    }

    @Test
    @DisplayName("null 选择器处理")
    void testNullSelector() {
        Selector selector = Selector.select(SAMPLE_HTML);
        
        List<String> results = selector.css(null).all();
        
        assertNotNull(results);
    }
}
