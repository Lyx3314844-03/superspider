package com.javaspider.research;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.jsoup.nodes.Element;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class ResearchRuntime {
    private static final ObjectMapper MAPPER = new ObjectMapper();

    public Map<String, Object> run(ResearchJob job, String content) {
        String seed = job.getSeedUrls().isEmpty() ? "" : job.getSeedUrls().get(0);
        if (seed.isBlank()) {
            throw new IllegalArgumentException("seed_urls[0] is required");
        }
        String resolvedContent = content == null || content.isBlank()
            ? "<title>" + seed + "</title>"
            : content;
        SiteProfile profile = profile(seed, resolvedContent);
        Map<String, Object> extracted = extract(
            resolvedContent,
            job.getExtractSchema(),
            job.getExtractSpecs()
        );

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("seed", seed);
        result.put("profile", profile);
        result.put("extract", extracted);

        String outputPath = stringValue(job.getOutput().get("path"));
        if (!outputPath.isBlank()) {
            result.put("dataset", writeDataset(outputPath, stringValue(job.getOutput().get("format")), extracted));
        }
        return result;
    }

    public SiteProfile profile(String url, String content) {
        String lower = content.toLowerCase(Locale.ROOT);
        Map<String, Boolean> signals = new LinkedHashMap<>();
        signals.put("has_form", lower.contains("<form"));
        signals.put("has_pagination", lower.contains("next") || lower.contains("page="));
        signals.put("has_list", lower.contains("<li") || lower.contains("<ul"));
        signals.put("has_detail", lower.contains("<article") || lower.contains("<h1"));
        signals.put("has_captcha", lower.contains("captcha") || lower.contains("verify"));

        String pageType = signals.get("has_list") && !signals.get("has_detail")
            ? "list"
            : (signals.get("has_detail") ? "detail" : "generic");

        List<String> candidateFields = new ArrayList<>();
        if (lower.contains("<title")) candidateFields.add("title");
        if (lower.contains("price")) candidateFields.add("price");
        if (lower.contains("author")) candidateFields.add("author");

        String riskLevel = signals.get("has_captcha")
            ? "high"
            : (url.startsWith("https://") && signals.get("has_form") ? "medium" : "low");

        return new SiteProfile(url, pageType, signals, candidateFields, riskLevel);
    }

    private Map<String, Object> extract(
        String content,
        Map<String, Object> schema,
        List<Map<String, Object>> specs
    ) {
        Map<String, Object> extracted = new LinkedHashMap<>();
        if (!specs.isEmpty()) {
            @SuppressWarnings("unchecked")
            Map<String, Object> properties = schema.get("properties") instanceof Map<?, ?> map
                ? (Map<String, Object>) map
                : Map.of();
            for (Map<String, Object> spec : specs) {
                String field = stringValue(spec.get("field"));
                if (field.isBlank()) {
                    continue;
                }
                Object value = extractWithSpec(content, field, spec);
                if (isEmpty(value)) {
                    if (Boolean.TRUE.equals(spec.get("required"))) {
                        throw new IllegalArgumentException("required extract field \"" + field + "\" could not be resolved");
                    }
                    continue;
                }
                validateSchema(field, value, schemaForField(spec, properties, field));
                extracted.put(field, value);
            }
            return extracted;
        }

        @SuppressWarnings("unchecked")
        Map<String, Object> properties = schema.get("properties") instanceof Map<?, ?> map
            ? (Map<String, Object>) map
            : Map.of();
        for (String field : properties.keySet()) {
            heuristicExtract(content, field).ifPresent(value -> extracted.put(field, value));
        }
        return extracted;
    }

    private Object extractWithSpec(String content, String field, Map<String, Object> spec) {
        String type = stringValue(spec.get("type")).toLowerCase(Locale.ROOT);
        String expr = stringValue(spec.get("expr"));
        String path = stringValue(spec.get("path"));
        switch (type) {
            case "css" -> {
                String selector = expr.isBlank() && "title".equals(field) ? "title" : expr;
                if (!selector.isBlank()) {
                    Object value = extractCssText(content, selector);
                    if (value != null) {
                        return value;
                    }
                }
            }
            case "css_attr" -> {
                String attr = stringValue(spec.get("attr"));
                if (!expr.isBlank() && !attr.isBlank()) {
                    Object value = extractCssAttr(content, expr, attr);
                    if (value != null) {
                        return value;
                    }
                }
            }
            case "xpath" -> {
                return extractXPath(content, expr);
            }
            case "regex" -> {
                if (!expr.isBlank()) {
                    Matcher matcher = Pattern.compile(expr, Pattern.CASE_INSENSITIVE | Pattern.DOTALL).matcher(content);
                    if (matcher.find()) {
                        return matcher.groupCount() >= 1 ? matcher.group(1).trim() : matcher.group().trim();
                    }
                }
            }
            case "json_path" -> {
                return extractJsonPath(content, path.isBlank() ? expr : path);
            }
            case "ai" -> {
                if ("title".equals(field)) {
                    return heuristicExtract(content, "title").orElse(null);
                }
                if ("html".equals(field) || "dom".equals(field)) {
                    return content;
                }
            }
            default -> {
                return heuristicExtract(content, field).orElse(null);
            }
        }
        return heuristicExtract(content, field).orElse(null);
    }

    private Object extractXPath(String content, String expr) {
        String normalized = stringValue(expr).trim().toLowerCase(Locale.ROOT);
        if ("//title/text()".equals(normalized)) {
            return heuristicExtract(content, "title").orElse(null);
        }
        if ("//h1/text()".equals(normalized)) {
            Matcher matcher = Pattern.compile("(?is)<h1[^>]*>(.*?)</h1>").matcher(content);
            if (matcher.find()) {
                return matcher.group(1).replaceAll("(?is)<[^>]+>", "").trim();
            }
        }
        Matcher meta = Pattern.compile("^//meta\\[@name=['\"]([^'\"]+)['\"]\\]/@content$", Pattern.CASE_INSENSITIVE)
            .matcher(normalized);
        if (meta.find()) {
            Matcher matcher = Pattern.compile(
                "(?is)<meta[^>]*name=[\"']" + Pattern.quote(meta.group(1)) + "[\"'][^>]*content=[\"']([^\"']+)[\"']"
            ).matcher(content);
            if (matcher.find()) {
                return matcher.group(1).trim();
            }
        }
        return null;
    }

    private Object extractJsonPath(String content, String path) {
        if (path == null || path.isBlank()) {
            return null;
        }
        try {
            @SuppressWarnings("unchecked")
            Map<String, Object> root = MAPPER.readValue(content, Map.class);
            String normalized = path.startsWith("$.") ? path.substring(2) : path;
            Object current = root;
            for (String segment : normalized.split("\\.")) {
                if (!(current instanceof Map<?, ?> currentMap)) {
                    return null;
                }
                current = currentMap.get(segment);
                if (current == null) {
                    return null;
                }
            }
            return current;
        } catch (IOException ignored) {
            return null;
        }
    }

    private java.util.Optional<String> heuristicExtract(String content, String field) {
        if ("title".equalsIgnoreCase(field)) {
            Matcher title = Pattern.compile("(?is)<title>(.*?)</title>").matcher(content);
            if (title.find()) {
                return java.util.Optional.of(title.group(1).trim());
            }
        }
        Matcher matcher = Pattern.compile(
            "(?im)" + Pattern.quote(field) + "\\s*[:=]\\s*([^\\n<]+)"
        ).matcher(content);
        if (matcher.find()) {
            return java.util.Optional.of(matcher.group(1).trim());
        }
        return java.util.Optional.empty();
    }

    private Object extractCssText(String content, String selector) {
        Document document = Jsoup.parse(content);
        Element element = document.selectFirst(selector);
        return element == null ? null : element.text().trim();
    }

    private Object extractCssAttr(String content, String selector, String attr) {
        Document document = Jsoup.parse(content);
        Element element = document.selectFirst(selector);
        if (element == null || !element.hasAttr(attr)) {
            return null;
        }
        return element.attr(attr).trim();
    }

    private void validateSchema(String field, Object value, Map<String, Object> schema) {
        String expectedType = stringValue(schema.get("type")).trim();
        if (expectedType.isBlank()) {
            return;
        }
        boolean valid = switch (expectedType) {
            case "string" -> value instanceof String;
            case "number" -> value instanceof Number;
            case "integer" -> value instanceof Integer || value instanceof Long;
            case "boolean" -> value instanceof Boolean;
            case "object" -> value instanceof Map<?, ?>;
            case "array" -> value instanceof List<?>;
            default -> true;
        };
        if (!valid) {
            throw new IllegalArgumentException("extract field \"" + field + "\" violates schema.type=" + expectedType);
        }
    }

    private Map<String, Object> schemaForField(
        Map<String, Object> spec,
        Map<String, Object> properties,
        String field
    ) {
        @SuppressWarnings("unchecked")
        Map<String, Object> specSchema = spec.get("schema") instanceof Map<?, ?> map
            ? (Map<String, Object>) map
            : null;
        if (specSchema != null) {
            return specSchema;
        }
        @SuppressWarnings("unchecked")
        Map<String, Object> propertySchema = properties.get(field) instanceof Map<?, ?> map
            ? (Map<String, Object>) map
            : Map.of();
        return propertySchema;
    }

    private Map<String, Object> writeDataset(String pathText, String formatText, Map<String, Object> extracted) {
        String format = formatText == null || formatText.isBlank() ? detectFormat(pathText) : formatText;
        Path path = Path.of(pathText);
        try {
            Files.createDirectories(path.getParent());
            switch (format) {
                case "jsonl" -> Files.writeString(
                    path,
                    MAPPER.writeValueAsString(extracted) + System.lineSeparator(),
                    StandardCharsets.UTF_8
                );
                case "csv" -> {
                    StringBuilder builder = new StringBuilder();
                    builder.append(String.join(",", extracted.keySet())).append(System.lineSeparator());
                    builder.append(String.join(",", extracted.values().stream().map(ResearchRuntime::stringValue).toList()))
                        .append(System.lineSeparator());
                    Files.writeString(path, builder.toString(), StandardCharsets.UTF_8);
                }
                default -> MAPPER.writerWithDefaultPrettyPrinter().writeValue(path.toFile(), List.of(extracted));
            }
        } catch (IOException e) {
            throw new RuntimeException("failed to write dataset", e);
        }
        return Map.of("path", pathText, "format", format);
    }

    private String detectFormat(String path) {
        String lower = path.toLowerCase(Locale.ROOT);
        if (lower.endsWith(".jsonl")) return "jsonl";
        if (lower.endsWith(".csv")) return "csv";
        return "json";
    }

    private static String stringValue(Object value) {
        return value == null ? "" : String.valueOf(value);
    }

    private boolean isEmpty(Object value) {
        return value == null || (value instanceof String text && text.isBlank());
    }
}
