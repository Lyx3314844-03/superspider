package com.javaspider.extractor;

import com.javaspider.parser.HtmlParser;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class SelectorExtractor {

    public Map<String, Object> extract(String html, List<Rule> rules) {
        HtmlParser parser = new HtmlParser(html == null ? "" : html);
        Map<String, Object> result = new LinkedHashMap<>();
        for (Rule rule : rules == null ? List.<Rule>of() : rules) {
            if (rule == null || rule.field() == null || rule.field().isBlank()) {
                continue;
            }
            List<String> values = extractValues(parser, html == null ? "" : html, rule);
            if (values.isEmpty()) {
                if (rule.required()) {
                    throw new IllegalArgumentException("required extract field \"" + rule.field() + "\" could not be resolved");
                }
                continue;
            }
            result.put(rule.field(), rule.all() ? values : values.get(0));
        }
        return result;
    }

    private List<String> extractValues(HtmlParser parser, String html, Rule rule) {
        String type = rule.type() == null ? "" : rule.type().trim().toLowerCase(java.util.Locale.ROOT);
        String expr = rule.expr() == null ? "" : rule.expr().trim();
        return switch (type) {
            case "css" -> parser.css(expr);
            case "css_attr" -> parser.cssAttr(expr, rule.attr());
            case "xpath" -> parser.xpath(expr);
            case "regex" -> regex(html, expr);
            default -> throw new IllegalArgumentException("unsupported extract rule type: " + rule.type());
        };
    }

    private List<String> regex(String html, String expr) {
        List<String> values = new ArrayList<>();
        Matcher matcher = Pattern.compile(expr, Pattern.MULTILINE | Pattern.DOTALL).matcher(html);
        while (matcher.find()) {
            String value = matcher.groupCount() > 0 ? matcher.group(1) : matcher.group();
            if (value != null && !value.isBlank()) {
                values.add(value.trim());
            }
        }
        return values;
    }

    public record Rule(String field, String type, String expr, String attr, boolean all, boolean required) {
        public static Rule css(String field, String expr) {
            return new Rule(field, "css", expr, null, false, false);
        }

        public static Rule cssAll(String field, String expr) {
            return new Rule(field, "css", expr, null, true, false);
        }

        public static Rule cssAttr(String field, String expr, String attr) {
            return new Rule(field, "css_attr", expr, attr, false, false);
        }

        public static Rule xpath(String field, String expr) {
            return new Rule(field, "xpath", expr, null, false, false);
        }
    }
}
