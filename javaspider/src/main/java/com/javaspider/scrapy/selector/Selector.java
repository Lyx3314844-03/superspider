package com.javaspider.scrapy.selector;

import org.jsoup.Jsoup;
import org.jsoup.helper.W3CDom;
import org.jsoup.nodes.Document;
import org.jsoup.nodes.Element;
import org.jsoup.select.Elements;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;

import javax.xml.xpath.XPath;
import javax.xml.xpath.XPathConstants;
import javax.xml.xpath.XPathFactory;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class Selector {
    private final String html;
    private final Document document;

    private Selector(String html) {
        this.html = html == null ? "" : html;
        this.document = Jsoup.parse(this.html);
    }

    public static Selector select(String html) {
        return new Selector(html);
    }

    public Document getDocument() {
        return document;
    }

    public SelectorList css(String cssQuery) {
        if (cssQuery == null || cssQuery.isBlank()) {
            return new SelectorList(Collections.emptyList());
        }
        return new SelectorList(document.select(cssQuery));
    }

    public SelectorList xpath(String xpathExpression) {
        if (xpathExpression == null || xpathExpression.isBlank()) {
            return new SelectorList(Collections.emptyList());
        }

        String cssQuery = translateSimpleXPath(xpathExpression);
        if (cssQuery != null) {
            return new SelectorList(document.select(cssQuery));
        }

        try {
            XPath xpath = XPathFactory.newInstance().newXPath();
            NodeList nodes = (NodeList) xpath.evaluate(
                xpathExpression,
                new W3CDom().fromJsoup(document),
                XPathConstants.NODESET
            );

            List<String> values = new ArrayList<>();
            for (int i = 0; i < nodes.getLength(); i++) {
                Node node = nodes.item(i);
                values.add(node.getTextContent());
            }
            return SelectorList.fromValues(values);
        } catch (Exception e) {
            throw new RuntimeException("XPath evaluation error", e);
        }
    }

    private String translateSimpleXPath(String xpathExpression) {
        Matcher classMatcher = Pattern.compile("^//([a-zA-Z0-9_-]+)\\[@class='([^']+)'\\]$").matcher(xpathExpression);
        if (classMatcher.matches()) {
            return classMatcher.group(1) + "." + classMatcher.group(2).replace(" ", ".");
        }

        Matcher attrMatcher = Pattern.compile("^//([a-zA-Z0-9_-]+)\\[@([a-zA-Z0-9_-]+)='([^']+)'\\]$").matcher(xpathExpression);
        if (attrMatcher.matches()) {
            return attrMatcher.group(1) + "[" + attrMatcher.group(2) + "=" + attrMatcher.group(3) + "]";
        }

        Matcher tagMatcher = Pattern.compile("^//([a-zA-Z0-9_-]+)$").matcher(xpathExpression);
        if (tagMatcher.matches()) {
            return tagMatcher.group(1);
        }

        return null;
    }

    public List<String> re(String regex) {
        if (regex == null || regex.isBlank()) {
            return Collections.emptyList();
        }

        Pattern pattern = Pattern.compile(regex, Pattern.DOTALL | Pattern.MULTILINE);
        Matcher matcher = pattern.matcher(html);
        List<String> matches = new ArrayList<>();
        while (matcher.find()) {
            matches.add(matcher.groupCount() >= 1 ? matcher.group(1) : matcher.group());
        }
        return matches;
    }

    public String reFirst(String regex) {
        List<String> matches = re(regex);
        return matches.isEmpty() ? null : matches.get(0);
    }

    public String getHtml() {
        return document.outerHtml();
    }

    public String getText() {
        return document.text();
    }

    public static final class SelectorList {
        private final List<Element> elements;
        private final List<String> values;

        SelectorList(List<Element> elements) {
            this(elements, null);
        }

        private SelectorList(List<Element> elements, List<String> values) {
            this.elements = elements == null ? Collections.emptyList() : List.copyOf(elements);
            if (values == null) {
                List<String> extracted = new ArrayList<>();
                for (Element element : this.elements) {
                    extracted.add(element.text());
                }
                this.values = List.copyOf(extracted);
            } else {
                this.values = List.copyOf(values);
            }
        }

        static SelectorList fromValues(List<String> values) {
            return new SelectorList(Collections.emptyList(), values == null ? Collections.emptyList() : values);
        }

        public SelectorList css(String cssQuery) {
            if (cssQuery == null || cssQuery.isBlank()) {
                return new SelectorList(Collections.emptyList());
            }

            List<Element> selected = new ArrayList<>();
            for (Element element : elements) {
                selected.addAll(element.select(cssQuery));
            }
            return new SelectorList(selected);
        }

        public List<String> all() {
            return new ArrayList<>(values);
        }

        public String firstText() {
            return values.isEmpty() ? null : values.get(0);
        }

        public List<String> attrs(String attribute) {
            List<String> values = new ArrayList<>();
            if (attribute == null || attribute.isBlank()) {
                return values;
            }
            for (Element element : elements) {
                values.add(element.attr(attribute));
            }
            return values;
        }

        public String attr(String attribute) {
            if (elements.isEmpty() || attribute == null || attribute.isBlank()) {
                return null;
            }
            return elements.get(0).attr(attribute);
        }

        public int size() {
            return values.size();
        }

        public boolean isEmpty() {
            return values.isEmpty();
        }

        public SelectorNode get(int index) {
            if (!elements.isEmpty()) {
                return new SelectorNode(elements.get(index), values.get(index));
            }
            return new SelectorNode(null, values.get(index));
        }

        public SelectorNode first() {
            return values.isEmpty() ? new SelectorNode(null, null) : get(0);
        }

        public SelectorNode last() {
            return values.isEmpty() ? new SelectorNode(null, null) : get(values.size() - 1);
        }
    }

    public static final class SelectorNode {
        private final Element element;
        private final String text;

        SelectorNode(Element element, String text) {
            this.element = element;
            this.text = text;
        }

        public String getText() {
            return element == null ? text : element.text();
        }
    }
}
