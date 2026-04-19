package com.javaspider.ai;

import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.jsoup.nodes.Element;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.regex.Pattern;

public final class EntityExtractor {
    private static final Map<String, Pattern> PATTERNS = Map.of(
        "email", Pattern.compile("\\b[A-Za-z0-9._%+\\-]+@[A-Za-z0-9.\\-]+\\.[A-Za-z]{2,}\\b"),
        "phone", Pattern.compile("(?:\\+?\\d[\\d\\s()./\\-]{6,}\\d)"),
        "url", Pattern.compile("https?://[^\\s<>\"{}|\\\\^`\\[\\]]+"),
        "date", Pattern.compile("\\b\\d{4}[-/]\\d{1,2}[-/]\\d{1,2}\\b|\\b\\d{1,2}[-/]\\d{1,2}[-/]\\d{2,4}\\b"),
        "time", Pattern.compile("\\b\\d{1,2}:\\d{2}(?::\\d{2})?\\s*(?:AM|PM)?\\b"),
        "money", Pattern.compile("[\\$€£￥¥]\\s*\\d+[,.]?\\d*"),
        "percentage", Pattern.compile("\\d+\\.?\\d*\\s*%")
    );

    public Map<String, List<String>> extract(String html) {
        Document document = Jsoup.parse(html == null ? "" : html);
        String text = document.text();
        Map<String, List<String>> result = new LinkedHashMap<>();
        for (Map.Entry<String, Pattern> entry : PATTERNS.entrySet()) {
            List<String> values = unique(entry.getValue().matcher(text).results().map(match -> match.group()).toList());
            if (!values.isEmpty()) {
                result.put(entry.getKey(), values);
            }
        }
        putIfPresent(result, "persons", unique(extractTexts(document, "meta[name=author], .author, .byline, [itemprop=author]", true)));
        putIfPresent(result, "organizations", unique(extractTexts(document, "meta[name=application-name], meta[name=copyright], .organization, .org", true)));
        putIfPresent(result, "locations", unique(extractTexts(document, "[itemprop=location], .location, .address", false)));
        putIfPresent(result, "products", unique(extractTexts(document, ".product-name, .product-title, [itemprop=name], meta[property='product:name'], h1.product-title", true)));
        return result;
    }

    private List<String> extractTexts(Document document, String selector, boolean includeMetaContent) {
        List<String> values = new ArrayList<>();
        for (Element element : document.select(selector)) {
            if (includeMetaContent) {
                String content = element.attr("content").trim();
                if (!content.isBlank()) {
                    values.add(content);
                    continue;
                }
            }
            String text = element.text().trim();
            if (!text.isBlank() && text.length() < 200) {
                values.add(text);
            }
        }
        return values;
    }

    private List<String> unique(List<String> values) {
        return new ArrayList<>(new LinkedHashSet<>(values.stream().map(String::trim).filter(value -> !value.isBlank()).toList()));
    }

    private void putIfPresent(Map<String, List<String>> result, String key, List<String> values) {
        if (!values.isEmpty()) {
            result.put(key, values);
        }
    }
}
