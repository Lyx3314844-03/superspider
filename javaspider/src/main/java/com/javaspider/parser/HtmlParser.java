package com.javaspider.parser;

import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.jsoup.nodes.Element;
import org.jsoup.select.Elements;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * HTML 解析器
 * 支持 CSS 选择器、XPath、正则表达式
 */
public class HtmlParser {
    private final Document document;
    private final String html;

    public HtmlParser(String html) {
        this.html = html;
        this.document = Jsoup.parse(html);
    }

    public HtmlParser(String html, String baseUri) {
        this.html = html;
        this.document = Jsoup.parse(html, baseUri);
    }

    /**
     * 使用 CSS 选择器提取所有匹配的元素文本
     */
    public List<String> css(String selector) {
        List<String> results = new ArrayList<>();
        Elements elements = document.select(selector);
        for (Element element : elements) {
            results.add(element.text());
        }
        return results;
    }

    /**
     * 使用 CSS 选择器提取第一个匹配的元素文本
     */
    public String cssFirst(String selector) {
        Element element = document.selectFirst(selector);
        return element != null ? element.text() : null;
    }

    /**
     * 使用 CSS 选择器提取所有匹配元素的 HTML
     */
    public List<String> cssHtml(String selector) {
        List<String> results = new ArrayList<>();
        Elements elements = document.select(selector);
        for (Element element : elements) {
            results.add(element.html());
        }
        return results;
    }

    /**
     * 使用 CSS 选择器提取第一个匹配元素的 HTML
     */
    public String cssHtmlFirst(String selector) {
        Element element = document.selectFirst(selector);
        return element != null ? element.html() : null;
    }

    /**
     * 使用 CSS 选择器提取所有匹配元素的属性
     */
    public List<String> cssAttr(String selector, String attribute) {
        List<String> results = new ArrayList<>();
        Elements elements = document.select(selector);
        for (Element element : elements) {
            if (element.hasAttr(attribute)) {
                results.add(element.attr(attribute));
            }
        }
        return results;
    }

    /**
     * 使用 CSS 选择器提取第一个匹配元素的属性
     */
    public String cssAttrFirst(String selector, String attribute) {
        Element element = document.selectFirst(selector);
        return element != null && element.hasAttr(attribute) ? element.attr(attribute) : null;
    }

    /**
     * 使用 CSS 选择器提取所有匹配的 Element
     */
    public List<Element> cssElements(String selector) {
        return document.select(selector);
    }

    /**
     * 使用 CSS 选择器提取第一个匹配的 Element
     */
    public Element cssElementFirst(String selector) {
        return document.selectFirst(selector);
    }

    /**
     * 使用 XPath 提取数据（简化版，使用 CSS 选择器模拟）
     */
    public List<String> xpath(String xpath) {
        // 将简单的 XPath 转换为 CSS 选择器
        String cssSelector = convertXPathToCss(xpath);
        return css(cssSelector);
    }

    /**
     * 使用 XPath 提取单个数据
     */
    public String xpathFirst(String xpath) {
        String cssSelector = convertXPathToCss(xpath);
        return cssFirst(cssSelector);
    }

    /**
     * 简单的 XPath 转 CSS 选择器（仅支持基本语法）
     */
    private String convertXPathToCss(String xpath) {
        if (xpath == null || xpath.isEmpty()) {
            return "*";
        }

        String css = xpath;
        
        // 处理 // 后代选择器
        css = css.replaceAll("//", " ");
        
        // 处理 / 子元素选择器
        css = css.replaceAll("/", " > ");
        
        // 处理 [@id='xxx']
        css = css.replaceAll("\\[@id='([^']+)'\\]", "#$1");
        css = css.replaceAll("\\[@id=\"([^\"]+)\"\\]", "#$1");
        
        // 处理 [@class='xxx']
        css = css.replaceAll("\\[@class='([^']+)'\\]", ".$1");
        css = css.replaceAll("\\[@class=\"([^\"]+)\"\\]", ".$1");
        
        // 处理 [@xxx='yyy'] 属性选择器
        css = css.replaceAll("\\[@([\\w-]+)='([^']+)'\\]", "[$1=$2]");
        css = css.replaceAll("\\[@([\\w-]+)=\"([^\"]+)\"\\]", "[$1=$2]");
        
        // 处理 text()
        if (css.contains("text()")) {
            css = css.replace("text()", ":containsOwn(%)");
        }

        return css.trim();
    }

    /**
     * 使用正则表达式提取所有匹配
     */
    public List<String> regex(String regex) {
        List<String> results = new ArrayList<>();
        Pattern pattern = Pattern.compile(regex, Pattern.MULTILINE | Pattern.DOTALL);
        Matcher matcher = pattern.matcher(html);
        while (matcher.find()) {
            if (matcher.groupCount() > 0) {
                results.add(matcher.group(1));
            } else {
                results.add(matcher.group());
            }
        }
        return results;
    }

    /**
     * 使用正则表达式提取第一个匹配
     */
    public String regexFirst(String regex) {
        Pattern pattern = Pattern.compile(regex, Pattern.MULTILINE | Pattern.DOTALL);
        Matcher matcher = pattern.matcher(html);
        if (matcher.find()) {
            return matcher.groupCount() > 0 ? matcher.group(1) : matcher.group();
        }
        return null;
    }

    /**
     * 使用正则表达式提取所有分组
     */
    public List<List<String>> regexAll(String regex) {
        List<List<String>> results = new ArrayList<>();
        Pattern pattern = Pattern.compile(regex, Pattern.MULTILINE | Pattern.DOTALL);
        Matcher matcher = pattern.matcher(html);
        while (matcher.find()) {
            List<String> groups = new ArrayList<>();
            for (int i = 0; i <= matcher.groupCount(); i++) {
                groups.add(matcher.group(i));
            }
            results.add(groups);
        }
        return results;
    }

    /**
     * 获取所有链接
     */
    public List<String> links() {
        return cssAttr("a", "href");
    }

    /**
     * 获取指定 CSS 选择器的链接
     */
    public List<String> links(String cssQuery) {
        return cssAttr(cssQuery, "href");
    }

    /**
     * 获取所有图片链接
     */
    public List<String> images() {
        List<String> results = new ArrayList<>();
        results.addAll(cssAttr("img", "src"));
        results.addAll(cssAttr("img", "data-src"));
        results.addAll(cssAttr("img", "data-original"));
        return results;
    }

    /**
     * 获取所有表单数据
     */
    public List<FormData> forms() {
        List<FormData> results = new ArrayList<>();
        Elements formElements = document.select("form");
        for (Element form : formElements) {
            FormData formData = new FormData();
            formData.setAction(form.attr("action"));
            formData.setMethod(form.attr("method"));
            
            Elements inputs = form.select("input, textarea, select");
            for (Element input : inputs) {
                String name = input.attr("name");
                String value = input.val();
                if (name != null && !name.isEmpty()) {
                    formData.getFields().put(name, value);
                }
            }
            results.add(formData);
        }
        return results;
    }

    /**
     * 获取标题
     */
    public String title() {
        return document.title();
    }

    /**
     * 获取正文内容（移除脚本和样式）
     */
    public String text() {
        return document.body() != null ? document.body().text() : document.text();
    }

    /**
     * 获取纯文本（移除所有 HTML 标签）
     */
    public String plainText() {
        return document.text();
    }

    /**
     * 获取 meta 标签内容
     */
    public String meta(String name) {
        Element meta = document.selectFirst("meta[name=" + name + "]");
        if (meta != null) {
            return meta.attr("content");
        }
        meta = document.selectFirst("meta[property=" + name + "]");
        if (meta != null) {
            return meta.attr("content");
        }
        return null;
    }

    /**
     * 获取 description
     */
    public String description() {
        return meta("description");
    }

    /**
     * 获取 keywords
     */
    public String keywords() {
        return meta("keywords");
    }

    /**
     * 获取 author
     */
    public String author() {
        return meta("author");
    }

    /**
     * 获取 canonical URL
     */
    public String canonicalUrl() {
        Element link = document.selectFirst("link[rel=canonical]");
        if (link != null) {
            return link.attr("href");
        }
        return document.baseUri();
    }

    /**
     * 获取所有表格数据
     */
    public List<List<String>> tables() {
        List<List<String>> results = new ArrayList<>();
        Elements tables = document.select("table");
        for (Element table : tables) {
            Elements rows = table.select("tr");
            List<String> tableData = new ArrayList<>();
            for (Element row : rows) {
                Elements cells = row.select("td, th");
                StringBuilder rowData = new StringBuilder();
                for (Element cell : cells) {
                    if (rowData.length() > 0) {
                        rowData.append("\t");
                    }
                    rowData.append(cell.text());
                }
                tableData.add(rowData.toString());
            }
            if (!tableData.isEmpty()) {
                results.add(tableData);
            }
        }
        return results;
    }

    /**
     * 获取文档对象
     */
    public Document getDocument() {
        return document;
    }

    /**
     * 获取原始 HTML
     */
    public String getHtml() {
        return html;
    }

    /**
     * 检查是否匹配选择器
     */
    public boolean matches(String selector) {
        return !document.select(selector).isEmpty();
    }

    /**
     * 获取匹配的元素数量
     */
    public int count(String selector) {
        return document.select(selector).size();
    }

    /**
     * 表单数据类
     */
    public static class FormData {
        private String action;
        private String method = "GET";
        private final java.util.Map<String, String> fields = new java.util.HashMap<>();

        public String getAction() {
            return action;
        }

        public void setAction(String action) {
            this.action = action;
        }

        public String getMethod() {
            return method;
        }

        public void setMethod(String method) {
            this.method = method;
        }

        public java.util.Map<String, String> getFields() {
            return fields;
        }

        @Override
        public String toString() {
            return "FormData{" +
                    "action='" + action + '\'' +
                    ", method='" + method + '\'' +
                    ", fields=" + fields +
                    '}';
        }
    }
}
