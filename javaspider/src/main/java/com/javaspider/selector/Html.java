package com.javaspider.selector;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.javaspider.ai.AIExtractor;
import com.javaspider.ai.SchemaNormalizer;
import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.jsoup.nodes.Element;
import org.jsoup.select.Elements;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;
import java.util.Locale;

/**
 * HTML 包装类
 */
public class Html {
    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();
    private static AiResponder AI_RESPONDER = Html::callDefaultAiResponder;
    private static boolean AI_RESPONDER_USES_DEFAULT = true;
    private static StructuredAiResponder STRUCTURED_AI_RESPONDER = Html::callDefaultStructuredAiResponder;
    private static boolean STRUCTURED_AI_RESPONDER_USES_DEFAULT = true;

    private Document document;
    private String url;
    private String rawContent;
    
    public Html(String html, String url) {
        this.document = url == null || url.isBlank() ? Jsoup.parse(html) : Jsoup.parse(html, url);
        this.url = url;
        this.rawContent = html;
    }
    
    public Html(String html) {
        this(html, null);
    }
    
    public Selectable $(String cssSelector) {
        Elements elements = document.select(cssSelector);
        if (elements.isEmpty()) {
            return new Selectable((String) null);
        }
        return new Selectable(elements.first().text());
    }

    public Selectable css(String cssSelector) {
        return $(cssSelector);
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
        if (jsonPath == null || jsonPath.isBlank()) {
            return new Selectable((String) null);
        }

        try {
            JsonNode root = OBJECT_MAPPER.readTree(extractJsonSource());
            List<JsonNode> matches = evaluateJsonPath(root, jsonPath.trim());
            List<String> values = new ArrayList<>();
            for (JsonNode node : matches) {
                values.add(jsonNodeToString(node));
            }
            return new Selectable(values);
        } catch (Exception ignored) {
            return new Selectable((String) null);
        }
    }
    
    public Selectable aiExtract(String prompt) {
        if (prompt == null || prompt.isBlank()) {
            return new Selectable(fallbackText());
        }

        Selectable aiSelectable = tryAiExtract(prompt);
        if (aiSelectable != null && !aiSelectable.all().isEmpty()) {
            return aiSelectable;
        }

        String normalized = prompt.toLowerCase(Locale.ROOT);
        if (normalized.startsWith("$")) {
            return jsonPath(prompt);
        }
        if (normalized.contains("title") || normalized.contains("标题")) {
            String title = document.title();
            if (!title.isBlank()) {
                return new Selectable(title);
            }
            Element h1 = document.selectFirst("h1");
            if (h1 != null) {
                return new Selectable(h1.text());
            }
        }
        if (normalized.contains("description") || normalized.contains("summary")
            || normalized.contains("描述") || normalized.contains("简介")) {
            Element meta = document.selectFirst("meta[name=description], meta[property='og:description']");
            if (meta != null) {
                String content = meta.attr("content");
                if (!content.isBlank()) {
                    return new Selectable(content);
                }
            }
            Element paragraph = document.selectFirst("p");
            if (paragraph != null) {
                return new Selectable(paragraph.text());
            }
        }
        if (normalized.contains("link") || normalized.contains("url") || normalized.contains("链接")) {
            List<String> links = new ArrayList<>();
            for (Element link : document.select("a[href]")) {
                String href = link.absUrl("href");
                if (href.isBlank()) {
                    href = link.attr("href");
                }
                if (!href.isBlank()) {
                    links.add(href);
                }
            }
            if (!links.isEmpty()) {
                return new Selectable(links);
            }
        }
        return new Selectable(fallbackText());
    }

    public java.util.Map<String, Object> aiExtractStructured(String instructions, java.util.Map<String, Object> schema) {
        if (schema == null || schema.isEmpty()) {
            return java.util.Map.of();
        }

        java.util.Map<String, Object> heuristics = heuristicStructuredExtraction(schema);
        java.util.Map<String, Object> structured = tryAiExtractStructured(instructions, schema);
        if (structured != null) {
            java.util.Map<String, Object> normalized = SchemaNormalizer.normalizeObject(schema, structured, heuristics);
            if (!normalized.isEmpty()) {
                return normalized;
            }
        }
        return SchemaNormalizer.normalizeObject(schema, java.util.Map.of(), heuristics);
    }
    
    public Selectable regex(String regex) {
        java.util.regex.Matcher matcher = java.util.regex.Pattern.compile(regex).matcher(document.text());
        if (matcher.find()) {
            return new Selectable(matcher.group());
        }
        return new Selectable((String) null);
    }
    
    public String getDocumentHtml() {
        return document.html();
    }
    
    public String getDocumentText() {
        return document.text();
    }

    private String extractJsonSource() {
        String source = rawContent == null ? "" : rawContent.trim();
        if (source.startsWith("{") || source.startsWith("[")) {
            return source;
        }

        String text = document.text().trim();
        if (text.startsWith("{") || text.startsWith("[")) {
            return text;
        }

        throw new IllegalArgumentException("document does not contain JSON content");
    }

    private List<JsonNode> evaluateJsonPath(JsonNode root, String jsonPath) {
        if ("$".equals(jsonPath)) {
            return List.of(root);
        }
        if (!jsonPath.startsWith("$")) {
            throw new IllegalArgumentException("jsonPath must start with $");
        }

        List<PathToken> tokens = parseJsonPath(jsonPath);
        List<JsonNode> current = new ArrayList<>();
        current.add(root);

        for (PathToken token : tokens) {
            List<JsonNode> next = new ArrayList<>();
            for (JsonNode node : current) {
                switch (token.kind) {
                    case FIELD -> {
                        if (node.isObject() && node.has(token.value)) {
                            next.add(node.get(token.value));
                        }
                    }
                    case INDEX -> {
                        if (node.isArray()) {
                            int index = Integer.parseInt(token.value);
                            if (index >= 0 && index < node.size()) {
                                next.add(node.get(index));
                            }
                        }
                    }
                    case WILDCARD -> {
                        if (node.isArray()) {
                            node.forEach(next::add);
                        } else if (node.isObject()) {
                            Iterator<JsonNode> iterator = node.elements();
                            iterator.forEachRemaining(next::add);
                        }
                    }
                }
            }
            current = next;
        }

        return current;
    }

    private List<PathToken> parseJsonPath(String jsonPath) {
        List<PathToken> tokens = new ArrayList<>();
        int index = 1;
        while (index < jsonPath.length()) {
            char ch = jsonPath.charAt(index);
            if (ch == '.') {
                index++;
                if (index < jsonPath.length() && jsonPath.charAt(index) == '*') {
                    tokens.add(PathToken.wildcard());
                    index++;
                    continue;
                }
                int start = index;
                while (index < jsonPath.length()) {
                    char current = jsonPath.charAt(index);
                    if (current == '.' || current == '[') {
                        break;
                    }
                    index++;
                }
                if (start < index) {
                    tokens.add(PathToken.field(jsonPath.substring(start, index)));
                }
                continue;
            }
            if (ch == '[') {
                int end = jsonPath.indexOf(']', index);
                if (end < 0) {
                    throw new IllegalArgumentException("unterminated bracket expression");
                }
                String content = jsonPath.substring(index + 1, end).trim();
                if ("*".equals(content)) {
                    tokens.add(PathToken.wildcard());
                } else if ((content.startsWith("'") && content.endsWith("'"))
                    || (content.startsWith("\"") && content.endsWith("\""))) {
                    tokens.add(PathToken.field(content.substring(1, content.length() - 1)));
                } else {
                    tokens.add(PathToken.index(content));
                }
                index = end + 1;
                continue;
            }
            index++;
        }
        return tokens;
    }

    private String jsonNodeToString(JsonNode node) {
        if (node == null || node.isNull()) {
            return "";
        }
        if (node.isTextual() || node.isNumber() || node.isBoolean()) {
            return node.asText();
        }
        return node.toString();
    }

    private String fallbackText() {
        String title = document.title();
        if (!title.isBlank()) {
            return title;
        }
        Element paragraph = document.selectFirst("p");
        if (paragraph != null) {
            return paragraph.text();
        }
        return document.text();
    }

    private Selectable tryAiExtract(String prompt) {
        if (AI_RESPONDER_USES_DEFAULT) {
            String apiKey = firstConfiguredApiKey();
            if (apiKey == null || apiKey.isBlank()) {
                return null;
            }
        }

        try {
            String response = AI_RESPONDER.respond(rawContent == null ? "" : rawContent, prompt);
            if (response == null || response.isBlank()) {
                return null;
            }
            return selectableFromAiResponse(response);
        } catch (Exception ignored) {
            return null;
        }
    }

    private static String callDefaultAiResponder(String content, String prompt) throws IOException {
        AIExtractor extractor = AIExtractor.fromEnv();
        String aiPrompt = String.format(
            "根据用户提示从以下 HTML 或文本中提取答案。%n" +
                "用户提示：%s%n%n" +
                "如果答案是多个值，请直接返回 JSON 数组。%n" +
                "如果答案是单个值，请直接返回该值，不要附加解释。%n%n" +
                "内容：%s",
            prompt,
            content.length() > 12000 ? content.substring(0, 12000) : content
        );
        return extractor.understandPage(content, aiPrompt);
    }

    private static java.util.Map<String, Object> callDefaultStructuredAiResponder(
        String content,
        String instructions,
        java.util.Map<String, Object> schema
    ) throws IOException {
        AIExtractor extractor = AIExtractor.fromEnv();
        return extractor.extractStructured(content, instructions == null ? "" : instructions, schema);
    }

    private Selectable selectableFromAiResponse(String response) {
        String trimmed = response.trim();
        try {
            JsonNode node = OBJECT_MAPPER.readTree(trimmed);
            if (node.isArray()) {
                List<String> values = new ArrayList<>();
                for (JsonNode item : node) {
                    values.add(jsonNodeToString(item));
                }
                return new Selectable(values);
            }
            if (node.isObject()) {
                if (node.has("result")) {
                    return new Selectable(jsonNodeToString(node.get("result")));
                }
                if (node.has("value")) {
                    return new Selectable(jsonNodeToString(node.get("value")));
                }
                return new Selectable(trimmed);
            }
            return new Selectable(jsonNodeToString(node));
        } catch (Exception ignored) {
            return new Selectable(trimmed);
        }
    }

    private static String firstConfiguredApiKey() {
        String apiKey = System.getenv("OPENAI_API_KEY");
        if (apiKey == null || apiKey.isBlank()) {
            apiKey = System.getenv("AI_API_KEY");
        }
        return apiKey;
    }

    private java.util.Map<String, Object> tryAiExtractStructured(
        String instructions,
        java.util.Map<String, Object> schema
    ) {
        if (STRUCTURED_AI_RESPONDER_USES_DEFAULT) {
            String apiKey = firstConfiguredApiKey();
            if (apiKey == null || apiKey.isBlank()) {
                return null;
            }
        }

        try {
            java.util.Map<String, Object> result = STRUCTURED_AI_RESPONDER.respond(
                rawContent == null ? "" : rawContent,
                instructions,
                schema
            );
            return result == null || result.isEmpty() ? null : result;
        } catch (Exception ignored) {
            return null;
        }
    }

    private java.util.Map<String, Object> heuristicStructuredExtraction(java.util.Map<String, Object> schema) {
        java.util.Map<String, Object> result = new java.util.LinkedHashMap<>();
        Object propertiesNode = schema.get("properties");
        if (!(propertiesNode instanceof java.util.Map<?, ?> rawProperties)) {
            return result;
        }

        for (Object rawKey : rawProperties.keySet()) {
            if (!(rawKey instanceof String key)) {
                continue;
            }
            String normalized = key.toLowerCase(Locale.ROOT);
            if (normalized.contains("title") || normalized.contains("headline") || normalized.contains("标题")) {
                result.put(key, document.title().isBlank() ? fallbackText() : document.title());
                continue;
            }
            if (normalized.contains("description") || normalized.contains("summary")
                || normalized.contains("desc") || normalized.contains("简介")) {
                Element meta = document.selectFirst("meta[name=description], meta[property='og:description']");
                if (meta != null && !meta.attr("content").isBlank()) {
                    result.put(key, meta.attr("content"));
                } else {
                    Element paragraph = document.selectFirst("p");
                    result.put(key, paragraph != null ? paragraph.text() : fallbackText());
                }
                continue;
            }
            if (normalized.contains("link") || normalized.contains("url") || normalized.contains("链接")) {
                java.util.List<String> links = new java.util.ArrayList<>();
                for (Element link : document.select("a[href]")) {
                    String href = link.absUrl("href");
                    if (href.isBlank()) {
                        href = link.attr("href");
                    }
                    if (!href.isBlank()) {
                        links.add(href);
                    }
                }
                result.put(key, links);
                continue;
            }
            if (normalized.contains("image") || normalized.contains("cover") || normalized.contains("thumbnail")) {
                java.util.List<String> images = new java.util.ArrayList<>();
                for (Element image : document.select("img[src]")) {
                    String src = image.absUrl("src");
                    if (src.isBlank()) {
                        src = image.attr("src");
                    }
                    if (!src.isBlank()) {
                        images.add(src);
                    }
                }
                result.put(key, images);
                continue;
            }
            if (normalized.contains("content") || normalized.contains("body") || normalized.contains("text")) {
                result.put(key, document.text());
                continue;
            }
            result.put(key, null);
        }
        return result;
    }

    static void setAiResponderForTests(AiResponder responder) {
        if (responder == null) {
            AI_RESPONDER = Html::callDefaultAiResponder;
            AI_RESPONDER_USES_DEFAULT = true;
            return;
        }
        AI_RESPONDER = responder;
        AI_RESPONDER_USES_DEFAULT = false;
    }

    static void resetAiResponderForTests() {
        AI_RESPONDER = Html::callDefaultAiResponder;
        AI_RESPONDER_USES_DEFAULT = true;
    }

    static void setStructuredAiResponderForTests(StructuredAiResponder responder) {
        if (responder == null) {
            STRUCTURED_AI_RESPONDER = Html::callDefaultStructuredAiResponder;
            STRUCTURED_AI_RESPONDER_USES_DEFAULT = true;
            return;
        }
        STRUCTURED_AI_RESPONDER = responder;
        STRUCTURED_AI_RESPONDER_USES_DEFAULT = false;
    }

    static void resetStructuredAiResponderForTests() {
        STRUCTURED_AI_RESPONDER = Html::callDefaultStructuredAiResponder;
        STRUCTURED_AI_RESPONDER_USES_DEFAULT = true;
    }

    private record PathToken(PathTokenKind kind, String value) {
        static PathToken field(String value) {
            return new PathToken(PathTokenKind.FIELD, value);
        }

        static PathToken index(String value) {
            return new PathToken(PathTokenKind.INDEX, value);
        }

        static PathToken wildcard() {
            return new PathToken(PathTokenKind.WILDCARD, "*");
        }
    }

    private enum PathTokenKind {
        FIELD,
        INDEX,
        WILDCARD,
    }

    @FunctionalInterface
    interface AiResponder {
        String respond(String content, String prompt) throws IOException;
    }

    @FunctionalInterface
    interface StructuredAiResponder {
        java.util.Map<String, Object> respond(
            String content,
            String instructions,
            java.util.Map<String, Object> schema
        ) throws IOException;
    }
}
