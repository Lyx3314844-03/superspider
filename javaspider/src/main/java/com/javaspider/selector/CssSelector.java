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
        Elements elements = document.select(cssExpression);
        
        if (elements.isEmpty()) {
            return null;
        }
        
        Element element = elements.first();
        return attributeName != null ? element.attr(attributeName) : element.text();
    }
    
    @Override
    public List<String> selectAll(String text) {
        List<String> results = new ArrayList<>();
        
        if (text == null || text.isEmpty()) {
            return results;
        }
        
        Document document = Jsoup.parse(text);
        Elements elements = document.select(cssExpression);
        
        for (Element element : elements) {
            String value = attributeName != null ? element.attr(attributeName) : element.text();
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
}
