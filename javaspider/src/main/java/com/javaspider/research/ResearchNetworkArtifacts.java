package com.javaspider.research;

import com.fasterxml.jackson.databind.ObjectMapper;

import java.net.URI;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class ResearchNetworkArtifacts {
    private static final ObjectMapper MAPPER = new ObjectMapper();

    private ResearchNetworkArtifacts() {}

    public static List<Map<String, Object>> normalizeNetworkEntries(Object artifact, int limit) {
        List<RawEntry> rawEntries = rawNetworkEntries(artifact, Math.max(limit, 1) * 4);
        List<Map<String, Object>> values = new ArrayList<>();
        Set<String> seen = new LinkedHashSet<>();
        for (RawEntry raw : rawEntries) {
            Map<String, Object> entry = normalizeNetworkEntry(raw.entry(), raw.source());
            if (entry.isEmpty()) {
                continue;
            }
            String fingerprint = String.join(
                "|",
                String.valueOf(entry.getOrDefault("method", "GET")),
                String.valueOf(entry.getOrDefault("url", "")),
                String.valueOf(entry.getOrDefault("post_data", ""))
            );
            if (!seen.add(fingerprint)) {
                continue;
            }
            values.add(entry);
            if (values.size() >= limit) {
                break;
            }
        }
        return values;
    }

    public static List<String> extractNetworkApiCandidates(Object artifact, int limit) {
        List<String> values = new ArrayList<>();
        for (Map<String, Object> entry : normalizeNetworkEntries(artifact, Math.max(limit, 1) * 4)) {
            if (!isReplayableNetworkEntry(entry)) {
                continue;
            }
            String url = stringValue(entry.get("url"));
            if (!url.isBlank() && !values.contains(url)) {
                values.add(url);
            }
            if (values.size() >= limit) {
                break;
            }
        }
        return values;
    }

    public static List<Map<String, Object>> buildNetworkReplayJobTemplates(
        String baseUrl,
        String siteFamily,
        Object artifact,
        int limit
    ) {
        String family = siteFamily == null || siteFamily.isBlank() ? "generic" : siteFamily.trim();
        List<Map<String, Object>> templates = new ArrayList<>();
        Set<String> seen = new LinkedHashSet<>();
        for (Map<String, Object> entry : normalizeNetworkEntries(artifact, Math.max(limit, 1) * 4)) {
            if (!isReplayableNetworkEntry(entry)) {
                continue;
            }
            String method = stringValue(entry.getOrDefault("method", "GET")).toUpperCase();
            String url = stringValue(entry.get("url"));
            String body = stringValue(entry.get("post_data"));
            String fingerprint = String.join("|", method, url, body);
            if (url.isBlank() || !seen.add(fingerprint)) {
                continue;
            }

            Map<String, Object> target = new LinkedHashMap<>();
            target.put("url", url);
            target.put("method", method);
            target.put("headers", safeReplayHeaders(entry.get("request_headers"), baseUrl));
            if (!List.of("GET", "HEAD").contains(method) && !body.isBlank()) {
                target.put("body", body);
            }

            Map<String, Object> template = new LinkedHashMap<>();
            template.put("name", family + "-network-api-" + (templates.size() + 1));
            template.put("runtime", "http");
            template.put("target", target);
            template.put("output", Map.of("format", "json"));

            Map<String, Object> metadata = new LinkedHashMap<>();
            metadata.put("site_family", family);
            metadata.put("source_url", baseUrl);
            metadata.put("source", entry.getOrDefault("source", "network_artifact"));
            metadata.put("status", entry.get("status"));
            metadata.put("resource_type", entry.getOrDefault("resource_type", ""));
            metadata.put("content_type", entry.getOrDefault("content_type", ""));
            template.put("metadata", metadata);

            templates.add(template);
            if (templates.size() >= limit) {
                break;
            }
        }
        return templates;
    }

    private static List<RawEntry> rawNetworkEntries(Object artifact, int limit) {
        Object payload = networkPayloadFromArtifact(artifact);
        List<RawEntry> values = new ArrayList<>();
        if (payload instanceof String text) {
            Matcher matcher = Pattern.compile("https?://[^\\s\"'<>]+").matcher(text);
            while (matcher.find()) {
                values.add(new RawEntry(Map.of("url", matcher.group(), "method", "GET"), "network_text"));
                if (values.size() >= limit) {
                    return values;
                }
            }
            return values;
        }
        collectNetworkEntries(payload, values, "network_artifact", limit);
        return values;
    }

    private static Object networkPayloadFromArtifact(Object artifact) {
        if (artifact == null) {
            return null;
        }
        if (artifact instanceof String text) {
            String trimmed = text.trim();
            if (trimmed.isEmpty()) {
                return null;
            }
            try {
                return MAPPER.readValue(trimmed, Object.class);
            } catch (Exception ignored) {
                return trimmed;
            }
        }
        return artifact;
    }

    @SuppressWarnings("unchecked")
    private static void collectNetworkEntries(Object payload, List<RawEntry> values, String source, int limit) {
        if (payload == null || values.size() >= limit) {
            return;
        }
        if (payload instanceof List<?> items) {
            for (Object item : items) {
                collectNetworkEntries(item, values, source, limit);
                if (values.size() >= limit) {
                    return;
                }
            }
            return;
        }
        if (!(payload instanceof Map<?, ?> map)) {
            return;
        }
        Map<String, Object> current = (Map<String, Object>) map;
        if (looksLikeNetworkEntry(current)) {
            values.add(new RawEntry(current, source));
            return;
        }
        if (current.get("log") instanceof Map<?, ?> log && log.get("entries") instanceof List<?> entries) {
            for (Object entry : entries) {
                if (entry instanceof Map<?, ?> entryMap) {
                    values.add(new RawEntry((Map<String, Object>) entryMap, "har"));
                }
                if (values.size() >= limit) {
                    return;
                }
            }
        }
        for (Map.Entry<String, String> descriptor : Map.of(
            "network_events", "network_events",
            "networkEntries", "network_entries",
            "network_entries", "network_entries",
            "requests", "requests",
            "entries", "entries",
            "events", "events"
        ).entrySet()) {
            if (current.get(descriptor.getKey()) instanceof List<?> items) {
                for (Object item : items) {
                    if (item instanceof Map<?, ?> entryMap) {
                        values.add(new RawEntry((Map<String, Object>) entryMap, descriptor.getValue()));
                    }
                    if (values.size() >= limit) {
                        return;
                    }
                }
            }
        }
        if (current.get("extract") instanceof Map<?, ?> extract) {
            for (Object value : extract.values()) {
                if (value instanceof List<?>) {
                    collectNetworkEntries(value, values, "listen_network", limit);
                    if (values.size() >= limit) {
                        return;
                    }
                }
            }
        }
        if (current.get("fetched") instanceof Map<?, ?> fetched && fetched.get("final_url") != null) {
            Map<String, Object> entry = new LinkedHashMap<>();
            entry.put("url", fetched.get("final_url"));
            entry.put("method", "GET");
            entry.put("status", fetched.get("status"));
            values.add(new RawEntry(entry, "trace"));
        }
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> normalizeNetworkEntry(Map<String, Object> raw, String source) {
        Map<String, Object> request = raw.get("request") instanceof Map<?, ?> requestMap
            ? (Map<String, Object>) requestMap
            : Map.of();
        Map<String, Object> response = raw.get("response") instanceof Map<?, ?> responseMap
            ? (Map<String, Object>) responseMap
            : Map.of();
        String url = firstNonBlank(
            stringValue(raw.get("url")),
            stringValue(raw.get("name")),
            stringValue(raw.get("request_url")),
            stringValue(request.get("url"))
        );
        if (url.isBlank()) {
            return Map.of();
        }

        Map<String, String> requestHeaders = headerMap(
            raw.containsKey("request_headers") ? raw.get("request_headers")
                : raw.containsKey("requestHeaders") ? raw.get("requestHeaders")
                : request.get("headers")
        );
        Map<String, String> responseHeaders = headerMap(
            raw.containsKey("response_headers") ? raw.get("response_headers")
                : raw.containsKey("responseHeaders") ? raw.get("responseHeaders")
                : response.get("headers")
        );
        Map<String, Object> responseContent = response.get("content") instanceof Map<?, ?> contentMap
            ? (Map<String, Object>) contentMap
            : Map.of();

        Map<String, Object> entry = new LinkedHashMap<>();
        entry.put("url", url);
        entry.put("method", firstNonBlank(stringValue(raw.get("method")), stringValue(request.get("method")), "GET").toUpperCase());
        entry.put("status", raw.containsKey("status") ? raw.get("status") : response.get("status"));
        entry.put("resource_type", firstNonBlank(
            stringValue(raw.get("resource_type")),
            stringValue(raw.get("resourceType")),
            stringValue(raw.get("type"))
        ));
        entry.put("content_type", firstNonBlank(
            stringValue(raw.get("content_type")),
            stringValue(raw.get("mimeType")),
            stringValue(responseContent.get("mimeType")),
            headerLookup(responseHeaders, "content-type")
        ));
        entry.put("source", source);
        entry.put("request_headers", requestHeaders);
        entry.put("response_headers", responseHeaders);
        entry.put("post_data", postDataFromEntry(raw, request));
        return entry;
    }

    private static boolean looksLikeNetworkEntry(Map<String, Object> map) {
        return !firstNonBlank(
            stringValue(map.get("url")),
            stringValue(map.get("name")),
            stringValue(map.get("request_url")),
            map.get("request") instanceof Map<?, ?> request ? stringValue(request.get("url")) : ""
        ).isBlank();
    }

    private static boolean isReplayableNetworkEntry(Map<String, Object> entry) {
        String url = stringValue(entry.get("url"));
        String method = stringValue(entry.getOrDefault("method", "GET")).toUpperCase();
        if (url.isBlank() || "OPTIONS".equals(method) || !(url.startsWith("http://") || url.startsWith("https://"))) {
            return false;
        }
        String path = url.toLowerCase();
        try {
            path = URI.create(url).getPath().toLowerCase();
        } catch (Exception ignored) {
        }
        if (List.of(".css", ".js", ".mjs", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico", ".woff", ".woff2", ".ttf", ".eot", ".mp4", ".webm", ".m3u8", ".ts", ".map")
            .stream()
            .anyMatch(path::endsWith)) {
            return false;
        }
        String contentType = stringValue(entry.get("content_type")).toLowerCase();
        String resourceType = stringValue(entry.get("resource_type")).toLowerCase();
        String lowered = url.toLowerCase();
        return !List.of("GET", "HEAD").contains(method)
            || contentType.contains("json")
            || contentType.contains("graphql")
            || contentType.contains("event-stream")
            || List.of("fetch", "xhr", "eventsource").contains(resourceType)
            || List.of("api", "graphql", "comment", "comments", "review", "reviews", "detail", "item", "items", "sku", "price", "search", "product", "goods", "inventory")
                .stream()
                .anyMatch(lowered::contains);
    }

    @SuppressWarnings("unchecked")
    private static Map<String, String> headerMap(Object value) {
        Map<String, String> headers = new LinkedHashMap<>();
        if (value instanceof Map<?, ?> map) {
            for (Map.Entry<?, ?> entry : map.entrySet()) {
                String key = stringValue(entry.getKey());
                String text = stringValue(entry.getValue());
                if (!key.isBlank() && !text.isBlank()) {
                    headers.put(key, text);
                }
            }
            return headers;
        }
        if (value instanceof List<?> items) {
            for (Object item : items) {
                if (!(item instanceof Map<?, ?> map)) {
                    continue;
                }
                String key = firstNonBlank(stringValue(map.get("name")), stringValue(map.get("key")));
                String text = stringValue(map.get("value"));
                if (!key.isBlank() && !text.isBlank()) {
                    headers.put(key, text);
                }
            }
        }
        return headers;
    }

    private static Map<String, Object> safeReplayHeaders(Object headers, String baseUrl) {
        Map<String, Object> values = new LinkedHashMap<>();
        for (Map.Entry<String, String> entry : headerMap(headers).entrySet()) {
            String lowered = entry.getKey().toLowerCase();
            if (List.of("authorization", "cookie", "proxy-authorization", "set-cookie").contains(lowered)) {
                continue;
            }
            values.put(entry.getKey(), entry.getValue());
        }
        if (baseUrl != null && !baseUrl.isBlank() && values.keySet().stream().noneMatch(key -> key.equalsIgnoreCase("referer"))) {
            values.put("Referer", baseUrl);
        }
        return values;
    }

    private static String headerLookup(Map<String, String> headers, String key) {
        return headers.entrySet().stream()
            .filter(entry -> entry.getKey().equalsIgnoreCase(key))
            .map(Map.Entry::getValue)
            .findFirst()
            .orElse("");
    }

    @SuppressWarnings("unchecked")
    private static String postDataFromEntry(Map<String, Object> raw, Map<String, Object> request) {
        for (Object value : new Object[] {
            raw.get("post_data"),
            raw.get("postData"),
            raw.get("body"),
            request.get("postData"),
            request.get("body")
        }) {
            if (value instanceof Map<?, ?> map && map.get("text") != null) {
                String text = stringValue(map.get("text"));
                if (!text.isBlank()) {
                    return text;
                }
            }
            String text = stringValue(value);
            if (!text.isBlank()) {
                return text;
            }
        }
        return "";
    }

    private static String firstNonBlank(String... values) {
        for (String value : values) {
            if (value != null && !value.isBlank()) {
                return value;
            }
        }
        return "";
    }

    private static String stringValue(Object value) {
        if (value == null) {
            return "";
        }
        String text = String.valueOf(value).trim();
        return "null".equalsIgnoreCase(text) ? "" : text;
    }

    private record RawEntry(Map<String, Object> entry, String source) {}
}
