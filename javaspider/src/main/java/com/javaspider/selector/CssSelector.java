package com.javaspider.selector;

import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.jsoup.nodes.Element;
import org.jsoup.select.Elements;

import java.util.ArrayList;
import java.util.List;

/**
 * CssSelector - CSS 选择器
 * 
 * @author Lan
 * @version 2.0.0
 * @since 2026-03-20
 */
public class CssSelector implements Selector {
    
    /**
     * CSS 选择器表达式
     */
    private final String cssExpression;
    
    /**
     * 属性名 (可选)
     */
    private final String attributeName;
    
    /**
     * 构造函数
     * @param cssExpression CSS 选择器表达式
     */
    public CssSelector(String cssExpression) {
        this(cssExpression, null);
    }
    
    /**
     * 构造函数
     * @param cssExpression CSS 选择器表达式
     * @param attributeName 属性名
     */
    public CssSelector(String cssExpression, String attributeName) {
        this.cssExpression = cssExpression;
        this.attributeName = attributeName;
    }
    
    @Override
    public String select(String text) {
        if (text == null || text.isEmpty()) {
            return null;
        }
        
        Document document = Jsoup.parse(text);
        CssQuery query = parseCssQuery(cssExpression);
        Elements elements = document.select(query.selector());
        
        if (elements.isEmpty()) {
            return null;
        }
        
        Element element = elements.first();
        return valueFor(element, query);
    }
    
    @Override
    public List<String> selectAll(String text) {
        List<String> results = new ArrayList<>();
        
        if (text == null || text.isEmpty()) {
            return results;
        }
        
        Document document = Jsoup.parse(text);
        CssQuery query = parseCssQuery(cssExpression);
        Elements elements = document.select(query.selector());
        
        for (Element element : elements) {
            String value = valueFor(element, query);
            if (value != null && !value.isEmpty()) {
                results.add(value);
            }
        }
        
        return results;
    }
    
    /**
     * 创建 CssSelector 实例
     * @param css CSS 选择器
     * @return CssSelector 实例
     */
    public static CssSelector of(String css) {
        return new CssSelector(css);
    }
    
    /**
     * 创建 CssSelector 实例 (带属性)
     * @param css CSS 选择器
     * @param attr 属性名
     * @return CssSelector 实例
     */
    public static CssSelector of(String css, String attr) {
        return new CssSelector(css, attr);
    }

    private CssQuery parseCssQuery(String selector) {
        String query = selector == null ? "" : selector.trim();
        java.util.regex.Matcher attrMatcher = java.util.regex.Pattern
            .compile("(?i)::attr\\(([^)]+)\\)\\s*$")
            .matcher(query);
        if (attrMatcher.find()) {
            return new CssQuery(query.substring(0, attrMatcher.start()).trim(), "attr", attrMatcher.group(1).trim());
        }
        if (query.toLowerCase(java.util.Locale.ROOT).endsWith("::html")) {
            return new CssQuery(query.substring(0, query.length() - "::html".length()).trim(), "html", null);
        }
        if (query.toLowerCase(java.util.Locale.ROOT).endsWith("::text")) {
            return new CssQuery(query.substring(0, query.length() - "::text".length()).trim(), "text", null);
        }
        return new CssQuery(query, "text", attributeName);
    }

    private String valueFor(Element element, CssQuery query) {
        if ("attr".equals(query.mode()) || query.attribute() != null) {
            return element.attr(query.attribute()).trim();
        }
        if ("html".equals(query.mode())) {
            return element.html().trim();
        }
        return element.text().trim();
    }

    private record CssQuery(String selector, String mode, String attribute) {
    }
}
