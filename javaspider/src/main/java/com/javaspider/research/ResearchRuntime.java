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
import java.util.LinkedHashSet;
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
        String compact = lower.replace(" ", "");
        String urlLower = url.toLowerCase(Locale.ROOT);
        String siteFamily = resolveSiteFamily(urlLower);
        boolean hasSearchQuery = urlLower.contains("/search")
            || urlLower.contains("search?")
            || urlLower.contains("keyword=")
            || urlLower.contains("q=")
            || urlLower.contains("query=")
            || urlLower.contains("wd=");
        Map<String, Boolean> signals = new LinkedHashMap<>();
        signals.put("has_form", lower.contains("<form"));
        signals.put("has_pagination", lower.contains("next") || lower.contains("page=") || lower.contains("pagination") || content.contains("下一页"));
        signals.put("has_list", lower.contains("<li") || lower.contains("<ul") || lower.contains("<ol") || lower.contains("product-list") || lower.contains("goods-list") || lower.contains("sku-item"));
        signals.put("has_detail", lower.contains("<article") || lower.contains("<h1"));
        signals.put("has_captcha", lower.contains("captcha") || lower.contains("verify") || lower.contains("human verification") || content.contains("滑块") || content.contains("验证码"));
        signals.put("has_price", lower.contains("price") || lower.contains("\"price\"") || content.contains("￥") || content.contains("¥") || content.contains("价格"));
        signals.put("has_search", hasSearchQuery || lower.contains("type=\"search\"") || content.contains("搜索") || lower.contains("search-input"));
        signals.put("has_login", lower.contains("type=\"password\"") || lower.contains("sign in") || lower.contains("signin") || content.contains("登录"));
        signals.put("has_hydration", lower.contains("__next_data__") || lower.contains("__next_f") || lower.contains("__nuxt__") || lower.contains("__apollo_state__") || lower.contains("__initial_state__") || lower.contains("__preloaded_state__") || lower.contains("window.__initial_data__"));
        signals.put("has_api_bootstrap", lower.contains("__initial_state__") || lower.contains("__preloaded_state__") || lower.contains("__next_data__") || lower.contains("__apollo_state__") || lower.contains("application/json") || lower.contains("window.__initial_data__"));
        signals.put("has_infinite_scroll", lower.contains("load more") || lower.contains("infinite") || lower.contains("intersectionobserver") || lower.contains("onscroll") || lower.contains("virtual-list") || content.contains("加载更多"));
        signals.put("has_graphql", lower.contains("graphql"));
        signals.put("has_reviews", lower.contains("review") || content.contains("评价") || lower.contains("comments"));
        signals.put("has_product_schema", compact.contains("\"@type\":\"product\"") || compact.contains("\"@type\":\"offer\""));
        signals.put("has_cart", lower.contains("add to cart") || content.contains("购物车") || lower.contains("buy-now") || content.contains("立即购买"));
        signals.put("has_sku", lower.contains("sku") || content.contains("商品编号") || urlLower.contains("item.jd.com") || urlLower.contains("/item.htm"));
        signals.put("has_image", lower.contains("<img") || lower.contains("og:image"));

        String crawlerType = resolveCrawlerType(signals, urlLower);
        String pageType = switch (crawlerType) {
            case "static_listing", "search_results", "ecommerce_search", "infinite_scroll_listing" -> "list";
            case "static_detail", "ecommerce_detail" -> "detail";
            default -> signals.get("has_list") && !signals.get("has_detail")
                ? "list"
                : (signals.get("has_detail") ? "detail" : "generic");
        };

        List<String> candidateFields = new ArrayList<>();
        if (lower.contains("<title")) candidateFields.add("title");
        if (signals.get("has_price")) candidateFields.add("price");
        if (lower.contains("author") || content.contains("作者")) candidateFields.add("author");
        if (signals.get("has_sku")) candidateFields.add("sku");
        if (signals.get("has_reviews")) candidateFields.add("rating");
        if (signals.get("has_search")) candidateFields.add("keyword");
        if (signals.get("has_image")) candidateFields.add("image");
        if (lower.contains("shop") || lower.contains("seller") || content.contains("店铺")) candidateFields.add("shop");
        if (lower.contains("description") || content.contains("详情")) candidateFields.add("description");
        candidateFields = new ArrayList<>(new LinkedHashSet<>(candidateFields));

        String riskLevel = signals.get("has_captcha")
            ? "high"
            : (url.startsWith("https://") && (signals.get("has_form") || signals.get("has_login") || signals.get("has_hydration") || signals.get("has_graphql")) ? "medium" : "low");
        List<String> runnerOrder = resolveRunnerOrder(crawlerType, signals);

        return new SiteProfile(
            url,
            pageType,
            siteFamily,
            signals,
            candidateFields,
            riskLevel,
            crawlerType,
            runnerOrder,
            resolveStrategyHints(crawlerType),
            resolveJobTemplates(crawlerType, siteFamily)
        );
    }

    private String resolveSiteFamily(String urlLower) {
        if (urlLower.contains("jd.com") || urlLower.contains("3.cn")) return "jd";
        if (urlLower.contains("taobao.com")) return "taobao";
        if (urlLower.contains("tmall.com")) return "tmall";
        if (urlLower.contains("pinduoduo.com") || urlLower.contains("yangkeduo.com")) return "pinduoduo";
        if (urlLower.contains("xiaohongshu.com") || urlLower.contains("xhslink.com")) return "xiaohongshu";
        if (urlLower.contains("douyin.com") || urlLower.contains("jinritemai.com")) return "douyin-shop";
        return "generic";
    }

    private String resolveCrawlerType(Map<String, Boolean> signals, String urlLower) {
        if (Boolean.TRUE.equals(signals.get("has_login")) && !Boolean.TRUE.equals(signals.get("has_detail"))) {
            return "login_session";
        }
        if (Boolean.TRUE.equals(signals.get("has_infinite_scroll")) && (Boolean.TRUE.equals(signals.get("has_list")) || Boolean.TRUE.equals(signals.get("has_search")))) {
            return "infinite_scroll_listing";
        }
        if (Boolean.TRUE.equals(signals.get("has_price"))
            && (Boolean.TRUE.equals(signals.get("has_cart")) || Boolean.TRUE.equals(signals.get("has_sku")) || Boolean.TRUE.equals(signals.get("has_product_schema")))
            && (Boolean.TRUE.equals(signals.get("has_search")) || (Boolean.TRUE.equals(signals.get("has_list")) && urlLower.contains("search")))) {
            return "ecommerce_search";
        }
        if (Boolean.TRUE.equals(signals.get("has_price"))
            && (Boolean.TRUE.equals(signals.get("has_cart")) || Boolean.TRUE.equals(signals.get("has_sku")) || Boolean.TRUE.equals(signals.get("has_product_schema")))
            && Boolean.TRUE.equals(signals.get("has_list"))
            && !Boolean.TRUE.equals(signals.get("has_detail"))) {
            return "ecommerce_search";
        }
        if (Boolean.TRUE.equals(signals.get("has_price"))
            && (Boolean.TRUE.equals(signals.get("has_cart")) || Boolean.TRUE.equals(signals.get("has_sku")) || Boolean.TRUE.equals(signals.get("has_product_schema")))) {
            return "ecommerce_detail";
        }
        if (Boolean.TRUE.equals(signals.get("has_hydration"))
            && (Boolean.TRUE.equals(signals.get("has_list")) || Boolean.TRUE.equals(signals.get("has_detail")) || Boolean.TRUE.equals(signals.get("has_search")))) {
            return "hydrated_spa";
        }
        if (Boolean.TRUE.equals(signals.get("has_api_bootstrap")) || Boolean.TRUE.equals(signals.get("has_graphql"))) {
            return "api_bootstrap";
        }
        if (Boolean.TRUE.equals(signals.get("has_search"))
            && (Boolean.TRUE.equals(signals.get("has_list")) || Boolean.TRUE.equals(signals.get("has_pagination")))) {
            return "search_results";
        }
        if (Boolean.TRUE.equals(signals.get("has_list")) && !Boolean.TRUE.equals(signals.get("has_detail"))) {
            return "static_listing";
        }
        if (Boolean.TRUE.equals(signals.get("has_detail"))) {
            return "static_detail";
        }
        return "generic_http";
    }

    private List<String> resolveRunnerOrder(String crawlerType, Map<String, Boolean> signals) {
        return switch (crawlerType) {
            case "hydrated_spa", "infinite_scroll_listing", "login_session", "ecommerce_search" -> List.of("browser", "http");
            case "ecommerce_detail" -> Boolean.TRUE.equals(signals.get("has_hydration"))
                ? List.of("browser", "http")
                : List.of("http", "browser");
            default -> List.of("http", "browser");
        };
    }

    private List<String> resolveStrategyHints(String crawlerType) {
        return switch (crawlerType) {
            case "ecommerce_search" -> List.of(
                "start with browser rendering, capture HTML and network payloads, then promote stable fields into HTTP follow-up jobs",
                "split listing fields from detail fields so sku and price can be validated independently"
            );
            case "hydrated_spa" -> List.of(
                "render the page in browser mode and inspect embedded hydration data before DOM scraping",
                "capture network responses and promote repeatable JSON endpoints into secondary HTTP jobs"
            );
            case "infinite_scroll_listing" -> List.of(
                "drive a bounded scroll loop and stop when repeated snapshots stop changing",
                "persist network and DOM artifacts so load-more behavior can be replayed without guessing"
            );
            case "login_session" -> List.of(
                "bootstrap an authenticated session once, then reuse cookies or storage state for follow-up jobs",
                "validate the post-login page shape before starting extraction"
            );
            case "ecommerce_detail" -> List.of(
                "extract embedded product JSON and schema blocks before relying on brittle selectors",
                "keep screenshot and HTML artifacts together for price and title regression checks"
            );
            case "api_bootstrap" -> List.of(
                "inspect script tags and bootstrap JSON before adding browser interactions",
                "extract stable JSON blobs into dedicated parsing rules so DOM churn matters less"
            );
            default -> List.of(
                "start with plain HTTP fetch and fall back to browser only if selectors are empty",
                "prefer stable title, meta, schema, and bootstrap data before brittle DOM selectors"
            );
        };
    }

    private List<String> resolveJobTemplates(String crawlerType, String siteFamily) {
        List<String> templates = new ArrayList<>(switch (crawlerType) {
            case "hydrated_spa" -> List.of("examples/crawler-types/hydrated-spa-browser.json");
            case "infinite_scroll_listing" -> List.of("examples/crawler-types/infinite-scroll-browser.json");
            case "ecommerce_search" -> List.of("examples/crawler-types/ecommerce-search-browser.json");
            case "ecommerce_detail" -> List.of(
                "examples/crawler-types/ecommerce-search-browser.json",
                "examples/crawler-types/api-bootstrap-http.json"
            );
            case "login_session" -> List.of("examples/crawler-types/login-session-browser.json");
            default -> List.of("examples/crawler-types/api-bootstrap-http.json");
        });
        switch (siteFamily) {
            case "jd" -> templates.add("ecommerce_detail".equals(crawlerType)
                ? "examples/site-presets/jd-detail-browser.json"
                : "examples/site-presets/jd-search-browser.json");
            case "taobao" -> templates.add("ecommerce_detail".equals(crawlerType)
                ? "examples/site-presets/taobao-detail-browser.json"
                : "examples/site-presets/taobao-search-browser.json");
            case "tmall" -> templates.add("examples/site-presets/tmall-search-browser.json");
            case "pinduoduo" -> templates.add("examples/site-presets/pinduoduo-search-browser.json");
            case "xiaohongshu" -> templates.add("examples/site-presets/xiaohongshu-feed-browser.json");
            case "douyin-shop" -> templates.add("examples/site-presets/douyin-shop-browser.json");
            default -> {
            }
        }
        return new ArrayList<>(new LinkedHashSet<>(templates));
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
