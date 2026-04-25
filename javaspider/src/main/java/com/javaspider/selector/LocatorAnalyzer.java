package com.javaspider.selector;

import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.jsoup.nodes.Element;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Locale;

public final class LocatorAnalyzer {

    public LocatorPlan analyze(String html, LocatorTarget target) {
        Document document = Jsoup.parse(html == null ? "" : html);
        Map<String, LocatorCandidate> candidates = new LinkedHashMap<>();
        for (Element element : document.getAllElements()) {
            int score = matchScore(element, target);
            if (score <= 0) {
                continue;
            }
            for (LocatorCandidate candidate : candidatesFor(document, element, score)) {
                String key = candidate.kind() + "\u0000" + candidate.expr();
                LocatorCandidate current = candidates.get(key);
                if (current == null || candidate.score() > current.score()) {
                    candidates.put(key, candidate);
                }
            }
        }
        List<LocatorCandidate> ordered = new ArrayList<>(candidates.values());
        ordered.sort(
            Comparator.comparingInt(LocatorCandidate::score).reversed()
                .thenComparing(LocatorCandidate::kind)
                .thenComparing(LocatorCandidate::expr)
        );
        return new LocatorPlan(ordered);
    }

    private int matchScore(Element element, LocatorTarget target) {
        int score = 0;
        if (target.tag() != null && !target.tag().isBlank()) {
            if (!element.tagName().equalsIgnoreCase(target.tag())) {
                return 0;
            }
            score += 2;
        }
        String text = element.text().trim();
        if (target.text() != null && !target.text().isBlank()) {
            if (text.equals(target.text())) {
                score += 6;
            } else if (text.toLowerCase(Locale.ROOT).contains(target.text().toLowerCase(Locale.ROOT))) {
                score += 3;
            }
        }
        score += attrContains(element, "role", target.role(), 4);
        score += attrContains(element, "name", target.name(), 4);
        score += attrContains(element, "placeholder", target.placeholder(), 4);
        if (target.name() != null && !target.name().isBlank()) {
            for (String attr : List.of("id", "aria-label", "data-testid", "data-test")) {
                score += attrContains(element, attr, target.name(), 3);
            }
        }
        if (target.attr() != null && !target.attr().isBlank()
            && target.value() != null && element.attr(target.attr()).equals(target.value())) {
            score += 6;
        }
        return score;
    }

    private int attrContains(Element element, String attr, String expected, int weight) {
        if (expected == null || expected.isBlank()) {
            return 0;
        }
        return element.attr(attr).toLowerCase(Locale.ROOT).contains(expected.toLowerCase(Locale.ROOT)) ? weight : 0;
    }

    private List<LocatorCandidate> candidatesFor(Document document, Element element, int score) {
        List<LocatorCandidate> result = new ArrayList<>();
        String tag = element.tagName();
        for (String attr : List.of("id", "data-testid", "data-test", "name", "aria-label", "placeholder", "role")) {
            String value = element.attr(attr).trim();
            if (value.isBlank()) {
                continue;
            }
            String css = "id".equals(attr) ? "#" + cssIdent(value) : tag + "[" + attr + "='" + cssQuote(value) + "']";
            String xpath = "//" + tag + "[@" + attr + "=" + xpathLiteral(value) + "]";
            int bonus = document.select(css).size() == 1 ? 8 : 3;
            result.add(new LocatorCandidate("css", css, score + bonus, attr + " attribute"));
            result.add(new LocatorCandidate("xpath", xpath, score + bonus - 1, attr + " attribute"));
        }
        String text = element.text().trim();
        if (!text.isBlank()) {
            String snippet = text.length() > 80 ? text.substring(0, 80) : text;
            result.add(new LocatorCandidate("xpath", "//" + tag + "[contains(normalize-space(.), " + xpathLiteral(snippet) + ")]", score + 2, "visible text"));
        }
        result.add(new LocatorCandidate("css", element.cssSelector(), score + 1, "structural css path"));
        result.add(new LocatorCandidate("xpath", fullXPath(element), score + 1, "structural xpath path"));
        return result;
    }

    private String fullXPath(Element element) {
        List<String> parts = new ArrayList<>();
        Element current = element;
        while (current != null && !current.tagName().equals("#root")) {
            if (!current.id().isBlank()) {
                parts.add(current.tagName() + "[@id=" + xpathLiteral(current.id()) + "]");
                break;
            }
            int index = 1;
            Element sibling = current.previousElementSibling();
            while (sibling != null) {
                if (sibling.tagName().equals(current.tagName())) {
                    index++;
                }
                sibling = sibling.previousElementSibling();
            }
            parts.add(current.tagName() + "[" + index + "]");
            current = current.parent();
        }
        java.util.Collections.reverse(parts);
        return "/" + String.join("/", parts);
    }

    private String cssIdent(String value) {
        StringBuilder builder = new StringBuilder();
        for (char ch : value.toCharArray()) {
            if (Character.isLetterOrDigit(ch) || ch == '_' || ch == '-') {
                builder.append(ch);
            } else {
                builder.append("\\").append(Integer.toHexString(ch)).append(" ");
            }
        }
        return builder.toString();
    }

    private String cssQuote(String value) {
        return value.replace("\\", "\\\\").replace("'", "\\'");
    }

    private String xpathLiteral(String value) {
        if (!value.contains("'")) {
            return "'" + value + "'";
        }
        if (!value.contains("\"")) {
            return "\"" + value + "\"";
        }
        String[] parts = value.split("'");
        return "concat(" + String.join(", \"'\", ", java.util.Arrays.stream(parts).map(part -> "'" + part + "'").toList()) + ")";
    }

    public record LocatorTarget(String tag, String text, String role, String name, String placeholder, String attr, String value) {
        public static LocatorTarget forText(String text) {
            return new LocatorTarget("", text, "", "", "", "", "");
        }

        public static LocatorTarget forField(String name) {
            return new LocatorTarget("", "", "", name, "", "", "");
        }
    }

    public record LocatorCandidate(String kind, String expr, int score, String reason) {
    }

    public record LocatorPlan(List<LocatorCandidate> candidates) {
        public LocatorCandidate best() {
            return candidates.isEmpty() ? null : candidates.get(0);
        }
    }
}
