package com.javaspider.selector;

import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.jsoup.nodes.Element;
import org.jsoup.select.Elements;

import java.util.ArrayList;
import java.util.List;

/**
 * HTML 包装类
 */
public class Html {
    private Document document;
    private String url;
    
    public Html(String html, String url) {
        this.document = Jsoup.parse(html);
        this.url = url;
    }
    
    public Html(String html) {
        this(html, null);
    }
    
    public Selectable $(String cssSelector) {
        Elements elements = document.select(cssSelector);
        if (elements.isEmpty()) {
            return new Selectable(null);
        }
        return new Selectable(elements.first().text());
    }
    
    public List<Selectable> $$(String cssSelector) {
        Elements elements = document.select(cssSelector);
        List<Selectable> result = new ArrayList<>();
        for (Element element : elements) {
            result.add(new Selectable(element.text()));
        }
        return result;
    }
    
    public Selectable xpath(String xpath) {
        // 简单实现，实际应该用 XPath
        return new Selectable(document.text());
    }
    
    public Selectable jsonPath(String jsonPath) {
        // TODO: 实现 JSONPath
        return new Selectable(document.text());
    }
    
    public Selectable aiExtract(String prompt) {
        // TODO: 实现 AI 提取
        return new Selectable(document.text());
    }
    
    public Selectable regex(String regex) {
        java.util.regex.Matcher matcher = java.util.regex.Pattern.compile(regex).matcher(document.text());
        if (matcher.find()) {
            return new Selectable(matcher.group());
        }
        return new Selectable(null);
    }
    
    public String getDocumentHtml() {
        return document.html();
    }
    
    public String getDocumentText() {
        return document.text();
    }
}
