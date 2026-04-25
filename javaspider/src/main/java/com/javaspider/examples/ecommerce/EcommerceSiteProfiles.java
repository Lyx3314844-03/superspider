package com.javaspider.examples.ecommerce;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.Gson;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.javaspider.scrapy.Spider;

import java.net.URI;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class EcommerceSiteProfiles {
    static final String DEFAULT_SITE_FAMILY = "jd";

    private static final Profile JD = new Profile(
        "jd",
        "https://search.jd.com/Search?keyword=iphone",
        "https://item.jd.com/100000000000.html",
        "https://club.jd.com/comment/productPageComments.action?productId=100000000000&score=0&sortType=5&page=0&pageSize=10&isShadowSku=0&fold=1",
        "browser",
        List.of("item.jd.com", "sku=", "wareId=", "item.htm", "detail"),
        List.of("page=", "pn-next", "next"),
        List.of("comment", "review", "club.jd.com"),
        List.of(
            "\"p\"\\s*:\\s*\"([0-9]+(?:\\.[0-9]{1,2})?)\"",
            "(?:price|jdPrice|promotionPrice)[\"'=:\\s]+([0-9]+(?:\\.[0-9]{1,2})?)",
            "(?:￥|¥)\\s*([0-9]+(?:\\.[0-9]{1,2})?)"
        ),
        List.of("(?:skuId|sku|wareId|productId)[\"'=:\\s]+([A-Za-z0-9_-]+)"),
        List.of("(?:shopName|venderName|storeName)[\"'=:\\s]+([^\"'\\n<,}]+)"),
        List.of("(?:commentCount|comment_num|reviewCount)[\"'=:\\s]+([0-9]+)"),
        List.of("(?:score|rating)[\"'=:\\s]+([0-9]+(?:\\.[0-9])?)")
    );

    private static final Profile GENERIC = new Profile(
        "generic",
        "https://shop.example.com/search?q=demo",
        "https://shop.example.com/product/demo-item",
        "https://shop.example.com/product/demo-item/reviews",
        "browser",
        List.of("/product", "/item", "/goods", "/sku", "detail", "productId", "itemId"),
        List.of("page=", "next", "pagination", "load-more"),
        List.of("review", "reviews", "comment", "comments", "rating"),
        List.of(
            "(?:price|salePrice|currentPrice|finalPrice|minPrice|maxPrice|offerPrice)[\"'=:\\s]+([0-9]+(?:\\.[0-9]{1,2})?)",
            "(?:￥|¥|\\$|€|£)\\s*([0-9]+(?:\\.[0-9]{1,2})?)"
        ),
        List.of("(?:skuId|sku|wareId|productId|itemId|goods_id|goodsId|asin)[\"'=:\\s]+([A-Za-z0-9_-]+)"),
        List.of("(?:shopName|seller|sellerNick|storeName|merchantName|vendor|brand)[\"'=:\\s]+([^\"'\\n<,}]+)"),
        List.of("(?:reviewCount|commentCount|comments|ratingsTotal|totalReviewCount)[\"'=:\\s]+([0-9]+)"),
        List.of("(?:rating|score|ratingValue|averageRating)[\"'=:\\s]+([0-9]+(?:\\.[0-9])?)")
    );

    private static final Profile TAOBAO = new Profile(
        "taobao",
        "https://s.taobao.com/search?q=iphone",
        "https://item.taobao.com/item.htm?id=100000000000",
        "https://rate.taobao.com/detailCommon.htm?id=100000000000",
        "browser",
        List.of("item.taobao.com", "item.htm", "id=", "detail"),
        List.of("page=", "next"),
        List.of("review", "rate.taobao.com", "comment"),
        List.of(
            "(?:price|promotionPrice|minPrice)[\"'=:\\s]+([0-9]+(?:\\.[0-9]{1,2})?)",
            "(?:￥|¥)\\s*([0-9]+(?:\\.[0-9]{1,2})?)"
        ),
        List.of("(?:itemId|item_id|id)[\"'=:\\s]+([A-Za-z0-9_-]+)"),
        List.of("(?:shopName|sellerNick|nick)[\"'=:\\s]+([^\"'\\n<,}]+)"),
        List.of("(?:reviewCount|commentCount|rateTotal)[\"'=:\\s]+([0-9]+)"),
        List.of("(?:score|rating)[\"'=:\\s]+([0-9]+(?:\\.[0-9])?)")
    );

    private static final Profile TMALL = new Profile(
        "tmall",
        "https://list.tmall.com/search_product.htm?q=iphone",
        "https://detail.tmall.com/item.htm?id=100000000000",
        "https://rate.tmall.com/list_detail_rate.htm?itemId=100000000000",
        "browser",
        List.of("detail.tmall.com", "item.htm", "id=", "detail"),
        List.of("page=", "next"),
        List.of("review", "rate.tmall.com", "comment"),
        List.of(
            "(?:price|promotionPrice|minPrice)[\"'=:\\s]+([0-9]+(?:\\.[0-9]{1,2})?)",
            "(?:￥|¥)\\s*([0-9]+(?:\\.[0-9]{1,2})?)"
        ),
        List.of("(?:itemId|item_id|id)[\"'=:\\s]+([A-Za-z0-9_-]+)"),
        List.of("(?:shopName|sellerNick|shop)[\"'=:\\s]+([^\"'\\n<,}]+)"),
        List.of("(?:reviewCount|commentCount|rateTotal)[\"'=:\\s]+([0-9]+)"),
        List.of("(?:score|rating)[\"'=:\\s]+([0-9]+(?:\\.[0-9])?)")
    );

    private static final Profile PINDUODUO = new Profile(
        "pinduoduo",
        "https://mobile.yangkeduo.com/search_result.html?search_key=iphone",
        "https://mobile.yangkeduo.com/goods.html?goods_id=100000000000",
        "https://mobile.yangkeduo.com/proxy/api/reviews/100000000000",
        "browser",
        List.of("goods.html", "goods_id=", "product", "detail"),
        List.of("page=", "next"),
        List.of("review", "comment"),
        List.of(
            "(?:minPrice|price|groupPrice)[\"'=:\\s]+([0-9]+(?:\\.[0-9]{1,2})?)",
            "(?:￥|¥)\\s*([0-9]+(?:\\.[0-9]{1,2})?)"
        ),
        List.of("(?:goods_id|goodsId|skuId)[\"'=:\\s]+([A-Za-z0-9_-]+)"),
        List.of("(?:mall_name|storeName|shopName)[\"'=:\\s]+([^\"'\\n<,}]+)"),
        List.of("(?:reviewCount|commentCount)[\"'=:\\s]+([0-9]+)"),
        List.of("(?:score|rating)[\"'=:\\s]+([0-9]+(?:\\.[0-9])?)")
    );

    private static final Profile AMAZON = new Profile(
        "amazon",
        "https://www.amazon.com/s?k=iphone",
        "https://www.amazon.com/dp/B0EXAMPLE00",
        "https://www.amazon.com/product-reviews/B0EXAMPLE00",
        "browser",
        List.of("/dp/", "/gp/product/", "/product/", "asin"),
        List.of("page=", "next"),
        List.of("review", "product-reviews"),
        List.of(
            "(?:priceToPay|displayPrice|priceAmount)[\"'=:\\s]+([0-9]+(?:\\.[0-9]{1,2})?)",
            "\\$\\s*([0-9]+(?:\\.[0-9]{1,2})?)"
        ),
        List.of("(?:asin|parentAsin|sku)[\"'=:\\s]+([A-Za-z0-9_-]+)"),
        List.of("(?:seller|merchantName|bylineInfo)[\"'=:\\s]+([^\"'\\n<,}]+)"),
        List.of("(?:reviewCount|totalReviewCount)[\"'=:\\s]+([0-9]+)"),
        List.of("(?:averageRating|rating)[\"'=:\\s]+([0-9]+(?:\\.[0-9])?)")
    );

    private static final Profile XIAOHONGSHU = new Profile(
        "xiaohongshu",
        "https://www.xiaohongshu.com/search_result?keyword=iphone",
        "https://www.xiaohongshu.com/explore/660000000000000000000000",
        "https://edith.xiaohongshu.com/api/sns/web/v2/comment/page",
        "browser",
        List.of("/explore/", "/discovery/item/", "note_id=", "goods_id=", "item/"),
        List.of("page=", "cursor=", "note_id=", "load-more"),
        List.of("comment", "comments", "edith.xiaohongshu.com", "note_id="),
        List.of(
            "(?:price|salePrice|currentPrice|minPrice|maxPrice)[\"'=:\\s]+([0-9]+(?:\\.[0-9]{1,2})?)",
            "(?:￥|¥)\\s*([0-9]+(?:\\.[0-9]{1,2})?)"
        ),
        List.of("(?:noteId|note_id|itemId|item_id|goodsId|goods_id|skuId|sku)[\"'=:\\s]+([A-Za-z0-9_-]+)"),
        List.of("(?:shopName|seller|sellerNick|storeName|merchantName|brand)[\"'=:\\s]+([^\"'\\n<,}]+)"),
        List.of("(?:commentCount|comments|reviewCount|interactCount)[\"'=:\\s]+([0-9]+)"),
        List.of("(?:rating|score|ratingValue|averageRating)[\"'=:\\s]+([0-9]+(?:\\.[0-9])?)")
    );

    private static final Profile DOUYIN_SHOP = new Profile(
        "douyin-shop",
        "https://www.douyin.com/search/iphone?type=commodity",
        "https://haohuo.jinritemai.com/views/product/item2?id=100000000000",
        "https://www.jinritemai.com/ecommerce/trade/comment/list?id=100000000000",
        "browser",
        List.of("/product/", "/item", "item2", "product_id=", "detail", "commodity"),
        List.of("page=", "cursor=", "offset=", "load-more"),
        List.of("comment", "comments", "review", "jinritemai.com"),
        List.of(
            "(?:price|salePrice|currentPrice|minPrice|maxPrice|promotionPrice)[\"'=:\\s]+([0-9]+(?:\\.[0-9]{1,2})?)",
            "(?:￥|¥)\\s*([0-9]+(?:\\.[0-9]{1,2})?)"
        ),
        List.of("(?:productId|product_id|itemId|item_id|goodsId|goods_id|skuId|sku)[\"'=:\\s]+([A-Za-z0-9_-]+)"),
        List.of("(?:shopName|seller|sellerNick|storeName|merchantName|authorName|brand)[\"'=:\\s]+([^\"'\\n<,}]+)"),
        List.of("(?:commentCount|comments|reviewCount|soldCount|sales)[\"'=:\\s]+([0-9]+)"),
        List.of("(?:rating|score|ratingValue|averageRating)[\"'=:\\s]+([0-9]+(?:\\.[0-9])?)")
    );

    private EcommerceSiteProfiles() {
    }

    static Profile profileFor(String siteFamily) {
        return switch ((siteFamily == null ? DEFAULT_SITE_FAMILY : siteFamily).toLowerCase()) {
            case "jd" -> JD;
            case "generic" -> GENERIC;
            case "taobao" -> TAOBAO;
            case "tmall" -> TMALL;
            case "pinduoduo" -> PINDUODUO;
            case "amazon" -> AMAZON;
            case "xiaohongshu" -> XIAOHONGSHU;
            case "douyin-shop" -> DOUYIN_SHOP;
            default -> GENERIC;
        };
    }

    static String siteFamilyFrom(Spider.Response response) {
        Spider.Request request = response.getRequest();
        if (request != null) {
            Object metaValue = request.getMeta().get("site_family");
            if (metaValue instanceof String family && !family.isBlank()) {
                return family;
            }
        }

        String lowered = response.getUrl().toLowerCase();
        if (lowered.contains("jd.com") || lowered.contains("3.cn")) {
            return "jd";
        }
        if (lowered.contains("taobao.com")) {
            return "taobao";
        }
        if (lowered.contains("tmall.com")) {
            return "tmall";
        }
        if (lowered.contains("yangkeduo.com") || lowered.contains("pinduoduo.com")) {
            return "pinduoduo";
        }
        if (lowered.contains("xiaohongshu.com") || lowered.contains("xhslink.com")) {
            return "xiaohongshu";
        }
        if (lowered.contains("douyin.com") || lowered.contains("jinritemai.com")) {
            return "douyin-shop";
        }
        if (lowered.contains("amazon.com")) {
            return "amazon";
        }
        return "generic";
    }

    static String bestTitle(Spider.Response response) {
        String title = response.selector().css("title").firstText();
        if (title != null && !title.isBlank()) {
            return title.trim();
        }
        String h1 = response.selector().css("h1").firstText();
        return h1 == null ? "" : h1.trim();
    }

    static String firstMatch(String text, List<String> patterns) {
        for (String pattern : patterns) {
            Matcher matcher = Pattern.compile(pattern, Pattern.CASE_INSENSITIVE | Pattern.DOTALL).matcher(text);
            if (matcher.find()) {
                return matcher.group(1).trim();
            }
        }
        return "";
    }

    static List<String> collectMatches(String text, List<String> patterns, int limit) {
        Set<String> values = new LinkedHashSet<>();
        for (String pattern : patterns) {
            Matcher matcher = Pattern.compile(pattern, Pattern.CASE_INSENSITIVE | Pattern.DOTALL).matcher(text);
            while (matcher.find()) {
                values.add(matcher.group(1).trim());
                if (values.size() >= limit) {
                    return new ArrayList<>(values);
                }
            }
        }
        return new ArrayList<>(values);
    }

    static List<String> normalizeLinks(String baseUrl, List<String> rawLinks) {
        Set<String> values = new LinkedHashSet<>();
        URI base = URI.create(baseUrl);
        for (String rawLink : rawLinks) {
            if (rawLink == null || rawLink.isBlank()) {
                continue;
            }
            String absolute = base.resolve(rawLink.trim()).toString();
            if (absolute.startsWith("http://") || absolute.startsWith("https://")) {
                values.add(absolute);
            }
        }
        return new ArrayList<>(values);
    }

    static List<String> collectProductLinks(String baseUrl, List<String> rawLinks, Profile profile, int limit) {
        List<String> values = new ArrayList<>();
        for (String link : normalizeLinks(baseUrl, rawLinks)) {
            String lowered = link.toLowerCase();
            boolean matched = profile.detailLinkKeywords.stream().anyMatch(keyword -> lowered.contains(keyword.toLowerCase()));
            if (matched) {
                values.add(link);
            }
            if (values.size() >= limit) {
                return values;
            }
        }
        return values;
    }

    static List<String> collectImageLinks(String baseUrl, List<String> rawLinks, int limit) {
        List<String> values = new ArrayList<>();
        for (String link : normalizeLinks(baseUrl, rawLinks)) {
            String lowered = link.toLowerCase();
            if (lowered.contains("image")
                || lowered.endsWith(".jpg")
                || lowered.endsWith(".jpeg")
                || lowered.endsWith(".png")
                || lowered.endsWith(".webp")
                || lowered.endsWith(".gif")) {
                values.add(link);
            }
            if (values.size() >= limit) {
                return values;
            }
        }
        return values;
    }

    static String firstLinkWithKeywords(String baseUrl, List<String> rawLinks, List<String> keywords) {
        for (String link : normalizeLinks(baseUrl, rawLinks)) {
            String lowered = link.toLowerCase();
            boolean matched = keywords.stream().anyMatch(keyword -> lowered.contains(keyword.toLowerCase()));
            if (matched) {
                return link;
            }
        }
        return "";
    }

    static String textExcerpt(String text, int limit) {
        String normalized = text.replaceAll("\\s+", " ").trim();
        return normalized.length() <= limit ? normalized : normalized.substring(0, limit);
    }

    static String buildJDPriceApiUrl(List<String> skuIds) {
        return "https://p.3.cn/prices/mgets?skuIds=" + String.join(",", skuIds) + "&type=1&area=1_72_4137_0";
    }

    static String extractJDItemId(String url, String html) {
        Matcher matcher = Pattern.compile("/(\\d+)\\.html").matcher(url);
        if (matcher.find()) {
            return matcher.group(1);
        }
        return firstMatch(
            html,
            List.of(
                "(?:skuId|sku|wareId|productId)[\"'=:\\s]+([A-Za-z0-9_-]+)",
                "\"sku\"\\s*:\\s*\"(\\d+)\""
            )
        );
    }

    static List<Map<String, Object>> extractJDCatalogProducts(String html) {
        List<Map<String, Object>> values = new ArrayList<>();
        Set<String> seen = new LinkedHashSet<>();
        Matcher matcher = Pattern.compile("data-sku=\"(\\d+)\"").matcher(html);
        while (matcher.find()) {
            String skuId = matcher.group(1);
            if (!seen.add(skuId)) {
                continue;
            }

            Matcher nameMatcher = Pattern.compile(
                "(?is)data-sku=\"" + Pattern.quote(skuId) + "\"[\\s\\S]*?<em[^>]*>(.*?)</em>"
            ).matcher(html);
            Matcher imageMatcher = Pattern.compile(
                "(?is)data-sku=\"" + Pattern.quote(skuId) + "\"[\\s\\S]*?(?:data-lazy-img|src)=\"//([^\"]+)\""
            ).matcher(html);
            Matcher commentMatcher = Pattern.compile(
                "(?is)data-sku=\"" + Pattern.quote(skuId) + "\"[\\s\\S]*?(?:comment-count|J_comment).*?(\\d+)"
            ).matcher(html);

            String name = "JD Product " + skuId;
            if (nameMatcher.find()) {
                name = nameMatcher.group(1).replaceAll("<[^>]+>", "").trim();
            }
            String imageUrl = imageMatcher.find() ? "https://" + imageMatcher.group(1) : "";
            int commentCount = commentMatcher.find() ? Integer.parseInt(commentMatcher.group(1)) : 0;

            Map<String, Object> product = new LinkedHashMap<>();
            product.put("product_id", skuId);
            product.put("name", name);
            product.put("url", "https://item.jd.com/" + skuId + ".html");
            product.put("image_url", imageUrl);
            product.put("comment_count", commentCount);
            values.add(product);
        }
        return values;
    }

    static JsonArray parseJsonArray(String text) {
        try {
            return JsonParser.parseString(text).getAsJsonArray();
        } catch (Exception ignored) {
            return new JsonArray();
        }
    }

    static JsonObject parseJsonObject(String text) {
        try {
            return JsonParser.parseString(text).getAsJsonObject();
        } catch (Exception ignored) {
            return new JsonObject();
        }
    }

    static List<String> collectVideoLinks(String baseUrl, List<String> rawLinks, int limit) {
        List<String> values = new ArrayList<>();
        for (String link : normalizeLinks(baseUrl, rawLinks)) {
            String lowered = link.toLowerCase();
            if (lowered.contains("video")
                || lowered.endsWith(".mp4")
                || lowered.endsWith(".m3u8")
                || lowered.endsWith(".webm")
                || lowered.endsWith(".mov")) {
                values.add(link);
            }
            if (values.size() >= limit) {
                return values;
            }
        }
        return values;
    }

    static List<String> extractEmbeddedJsonBlocks(String text, int limit, int maxChars) {
        List<String> values = new ArrayList<>();
        List<String> patterns = List.of(
            "(?is)<script[^>]+type=[\"']application/ld\\+json[\"'][^>]*>(.*?)</script>",
            "(?is)<script[^>]+type=[\"']application/json[\"'][^>]*>(.*?)</script>",
            "(?is)__NEXT_DATA__\\s*=\\s*(\\{.*?\\})\\s*;</script>",
            "(?is)__NUXT__\\s*=\\s*(\\{.*?\\})\\s*;",
            "(?is)__INITIAL_STATE__\\s*=\\s*(\\{.*?\\})\\s*;",
            "(?is)__PRELOADED_STATE__\\s*=\\s*(\\{.*?\\})\\s*;"
        );
        for (String pattern : patterns) {
            Matcher matcher = Pattern.compile(pattern).matcher(text);
            while (matcher.find()) {
                String block = textExcerpt(matcher.group(1), maxChars);
                if (!block.isBlank() && !values.contains(block)) {
                    values.add(block);
                }
                if (values.size() >= limit) {
                    return values;
                }
            }
        }
        return values;
    }

    static List<String> extractApiCandidates(String text, int limit) {
        List<String> values = new ArrayList<>();
        List<String> patterns = List.of(
            "https?://[^\"'\\s<>]+",
            "/(?:api|comment|comments|review|reviews|detail|item|items|sku|price|search)[^\"'\\s<>]+"
        );
        List<String> keywords = List.of("api", "comment", "review", "detail", "item", "sku", "price", "search");
        for (String pattern : patterns) {
            Matcher matcher = Pattern.compile(pattern, Pattern.CASE_INSENSITIVE).matcher(text);
            while (matcher.find()) {
                String candidate = matcher.group().trim();
                String lowered = candidate.toLowerCase();
                boolean matched = keywords.stream().anyMatch(lowered::contains);
                if (matched && !values.contains(candidate)) {
                    values.add(candidate);
                }
                if (values.size() >= limit) {
                    return values;
                }
            }
        }
        for (String rawPayload : rawEmbeddedJsonPayloads(text)) {
            try {
                walkApiCandidates(JsonParser.parseString(rawPayload), values, limit);
            } catch (Exception ignored) {
            }
            if (values.size() >= limit) {
                return values;
            }
        }
        return values;
    }

    public static List<Map<String, Object>> normalizeNetworkEntries(Object artifact, int limit) {
        List<NetworkArtifactEntry> rawEntries = rawNetworkEntries(artifact, Math.max(limit, 1) * 4);
        List<Map<String, Object>> values = new ArrayList<>();
        Set<String> seen = new LinkedHashSet<>();
        for (NetworkArtifactEntry raw : rawEntries) {
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
            String url = String.valueOf(entry.getOrDefault("url", "")).trim();
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
            String method = String.valueOf(entry.getOrDefault("method", "GET")).trim().toUpperCase();
            String url = String.valueOf(entry.getOrDefault("url", "")).trim();
            String body = String.valueOf(entry.getOrDefault("post_data", "")).trim();
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

    private static List<NetworkArtifactEntry> rawNetworkEntries(Object artifact, int limit) {
        Object payload = networkPayloadFromArtifact(artifact);
        List<NetworkArtifactEntry> values = new ArrayList<>();
        if (payload instanceof String text) {
            Matcher matcher = Pattern.compile("https?://[^\\s\"'<>]+").matcher(text);
            while (matcher.find()) {
                values.add(new NetworkArtifactEntry(Map.of("url", matcher.group(), "method", "GET"), "network_text"));
                if (values.size() >= limit) {
                    return values;
                }
            }
            return values;
        }
        collectNetworkEntries((JsonElement) payload, values, "network_artifact", limit);
        return values;
    }

    private static Object networkPayloadFromArtifact(Object artifact) {
        if (artifact == null) {
            return JsonParser.parseString("null");
        }
        if (artifact instanceof String text) {
            String trimmed = text.trim();
            if (trimmed.isEmpty()) {
                return JsonParser.parseString("null");
            }
            try {
                return JsonParser.parseString(trimmed);
            } catch (Exception ignored) {
                return trimmed;
            }
        }
        return new Gson().toJsonTree(artifact);
    }

    private static void collectNetworkEntries(
        JsonElement payload,
        List<NetworkArtifactEntry> values,
        String source,
        int limit
    ) {
        if (payload == null || payload.isJsonNull() || values.size() >= limit) {
            return;
        }
        if (payload.isJsonArray()) {
            for (JsonElement element : payload.getAsJsonArray()) {
                collectNetworkEntries(element, values, source, limit);
                if (values.size() >= limit) {
                    return;
                }
            }
            return;
        }
        if (!payload.isJsonObject()) {
            return;
        }
        JsonObject map = payload.getAsJsonObject();
        if (looksLikeNetworkEntry(map)) {
            values.add(new NetworkArtifactEntry(toJavaMap(map), source));
            return;
        }
        if (map.has("log") && map.get("log").isJsonObject()) {
            JsonObject log = map.getAsJsonObject("log");
            if (log.has("entries") && log.get("entries").isJsonArray()) {
                for (JsonElement element : log.getAsJsonArray("entries")) {
                    if (element.isJsonObject()) {
                        values.add(new NetworkArtifactEntry(toJavaMap(element.getAsJsonObject()), "har"));
                    }
                    if (values.size() >= limit) {
                        return;
                    }
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
            if (map.has(descriptor.getKey()) && map.get(descriptor.getKey()).isJsonArray()) {
                for (JsonElement element : map.getAsJsonArray(descriptor.getKey())) {
                    if (element.isJsonObject()) {
                        values.add(new NetworkArtifactEntry(toJavaMap(element.getAsJsonObject()), descriptor.getValue()));
                    }
                    if (values.size() >= limit) {
                        return;
                    }
                }
            }
        }
        if (map.has("extract") && map.get("extract").isJsonObject()) {
            for (Map.Entry<String, JsonElement> entry : map.getAsJsonObject("extract").entrySet()) {
                if (entry.getValue().isJsonArray()) {
                    collectNetworkEntries(entry.getValue(), values, "listen_network", limit);
                    if (values.size() >= limit) {
                        return;
                    }
                }
            }
        }
        if (map.has("fetched") && map.get("fetched").isJsonObject()) {
            JsonObject fetched = map.getAsJsonObject("fetched");
            if (fetched.has("final_url")) {
                Map<String, Object> entry = new LinkedHashMap<>();
                entry.put("url", fetched.get("final_url").getAsString());
                entry.put("method", "GET");
                if (fetched.has("status") && fetched.get("status").isJsonPrimitive()) {
                    entry.put("status", fetched.get("status").getAsInt());
                }
                values.add(new NetworkArtifactEntry(entry, "trace"));
            }
        }
    }

    private static boolean looksLikeNetworkEntry(JsonObject map) {
        return !firstNonBlank(
            valueOrEmpty(map.get("url")),
            valueOrEmpty(map.get("name")),
            valueOrEmpty(map.get("request_url")),
            map.has("request") && map.get("request").isJsonObject()
                ? valueOrEmpty(map.getAsJsonObject("request").get("url"))
                : ""
        ).isBlank();
    }

    private static Map<String, Object> normalizeNetworkEntry(Map<String, Object> raw, String source) {
        @SuppressWarnings("unchecked")
        Map<String, Object> request = raw.get("request") instanceof Map<?, ?> requestMap
            ? (Map<String, Object>) requestMap
            : Map.of();
        @SuppressWarnings("unchecked")
        Map<String, Object> response = raw.get("response") instanceof Map<?, ?> responseMap
            ? (Map<String, Object>) responseMap
            : Map.of();
        String url = firstNonBlank(
            String.valueOf(raw.getOrDefault("url", "")).trim(),
            String.valueOf(raw.getOrDefault("name", "")).trim(),
            String.valueOf(raw.getOrDefault("request_url", "")).trim(),
            String.valueOf(request.getOrDefault("url", "")).trim()
        );
        if (url.isBlank()) {
            return Map.of();
        }
        String method = firstNonBlank(
            String.valueOf(raw.getOrDefault("method", "")).trim(),
            String.valueOf(request.getOrDefault("method", "")).trim(),
            "GET"
        ).toUpperCase();
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
        @SuppressWarnings("unchecked")
        Map<String, Object> responseContent = response.get("content") instanceof Map<?, ?> contentMap
            ? (Map<String, Object>) contentMap
            : Map.of();
        String contentType = firstNonBlank(
            String.valueOf(raw.getOrDefault("content_type", "")).trim(),
            String.valueOf(raw.getOrDefault("mimeType", "")).trim(),
            String.valueOf(responseContent.getOrDefault("mimeType", "")).trim(),
            headerLookup(responseHeaders, "content-type")
        );
        Map<String, Object> entry = new LinkedHashMap<>();
        entry.put("url", url);
        entry.put("method", method);
        entry.put("status", raw.containsKey("status") ? raw.get("status") : response.get("status"));
        entry.put("resource_type", firstNonBlank(
            String.valueOf(raw.getOrDefault("resource_type", "")).trim(),
            String.valueOf(raw.getOrDefault("resourceType", "")).trim(),
            String.valueOf(raw.getOrDefault("type", "")).trim()
        ));
        entry.put("content_type", contentType);
        entry.put("source", source);
        entry.put("request_headers", requestHeaders);
        entry.put("response_headers", responseHeaders);
        entry.put("post_data", postDataFromEntry(raw, request));
        return entry;
    }

    private static boolean isReplayableNetworkEntry(Map<String, Object> entry) {
        String url = String.valueOf(entry.getOrDefault("url", "")).trim();
        String method = String.valueOf(entry.getOrDefault("method", "GET")).trim().toUpperCase();
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
        String contentType = String.valueOf(entry.getOrDefault("content_type", "")).toLowerCase();
        String resourceType = String.valueOf(entry.getOrDefault("resource_type", "")).toLowerCase();
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

    private static Map<String, Object> safeReplayHeaders(Object headers, String baseUrl) {
        Map<String, Object> values = new LinkedHashMap<>();
        for (Map.Entry<String, String> entry : headerMap(headers).entrySet()) {
            String lowered = entry.getKey().toLowerCase();
            if (List.of("authorization", "cookie", "proxy-authorization", "set-cookie").contains(lowered)) {
                continue;
            }
            values.put(entry.getKey(), entry.getValue());
        }
        boolean hasReferer = values.keySet().stream().anyMatch(key -> key.equalsIgnoreCase("referer"));
        if (!baseUrl.isBlank() && !hasReferer) {
            values.put("Referer", baseUrl);
        }
        return values;
    }

    private static Map<String, String> headerMap(Object value) {
        Map<String, String> headers = new LinkedHashMap<>();
        if (value instanceof Map<?, ?> map) {
            for (Map.Entry<?, ?> entry : map.entrySet()) {
                String key = String.valueOf(entry.getKey()).trim();
                String text = String.valueOf(entry.getValue()).trim();
                if (!key.isBlank() && !text.isBlank() && !"null".equalsIgnoreCase(text)) {
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
                String key = firstNonBlank(
                    String.valueOf(mapValue(map, "name")).trim(),
                    String.valueOf(mapValue(map, "key")).trim()
                );
                String text = String.valueOf(mapValue(map, "value")).trim();
                if (!key.isBlank() && !text.isBlank() && !"null".equalsIgnoreCase(text)) {
                    headers.put(key, text);
                }
            }
        }
        return headers;
    }

    private static String headerLookup(Map<String, String> headers, String key) {
        return headers.entrySet().stream()
            .filter(entry -> entry.getKey().equalsIgnoreCase(key))
            .map(Map.Entry::getValue)
            .findFirst()
            .orElse("");
    }

    private static String postDataFromEntry(Map<String, Object> raw, Map<String, Object> request) {
        for (Object value : new Object[] {
            raw.get("post_data"),
            raw.get("postData"),
            raw.get("body"),
            request.get("postData"),
            request.get("body")
        }) {
            if (value instanceof Map<?, ?> map && map.get("text") != null) {
                String text = String.valueOf(map.get("text")).trim();
                if (!text.isBlank() && !"null".equalsIgnoreCase(text)) {
                    return text;
                }
            }
            if (value != null) {
                String text = String.valueOf(value).trim();
                if (!text.isBlank() && !"null".equalsIgnoreCase(text)) {
                    return text;
                }
            }
        }
        return "";
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> toJavaMap(JsonObject object) {
        return new Gson().fromJson(object, Map.class);
    }

    private static Object mapValue(Map<?, ?> map, String key) {
        Object value = map.get(key);
        return value == null ? "" : value;
    }

    private record NetworkArtifactEntry(Map<String, Object> entry, String source) {}

    static List<Map<String, Object>> extractJsonLdProducts(String text, int limit) {
        List<Map<String, Object>> values = new ArrayList<>();
        Matcher matcher = Pattern.compile(
            "(?is)<script[^>]+type=[\"']application/ld\\+json[\"'][^>]*>(.*?)</script>"
        ).matcher(text);
        while (matcher.find()) {
            try {
                walkJsonLdProducts(JsonParser.parseString(matcher.group(1)), values, limit);
            } catch (Exception ignored) {
            }
            if (values.size() >= limit) {
                return values;
            }
        }
        return values;
    }

    static List<Map<String, Object>> extractBootstrapProducts(String text, int limit) {
        List<Map<String, Object>> values = new ArrayList<>();
        Set<String> seen = new LinkedHashSet<>();
        for (String rawPayload : rawEmbeddedJsonPayloads(text)) {
            try {
                walkBootstrapProducts(JsonParser.parseString(rawPayload), values, seen, limit);
            } catch (Exception ignored) {
            }
            if (values.size() >= limit) {
                return values;
            }
        }
        return values;
    }

    private static List<String> rawEmbeddedJsonPayloads(String text) {
        List<String> values = new ArrayList<>();
        List<String> patterns = List.of(
            "(?is)<script[^>]+type=[\"']application/ld\\+json[\"'][^>]*>(.*?)</script>",
            "(?is)<script[^>]+type=[\"']application/json[\"'][^>]*>(.*?)</script>",
            "(?is)__NEXT_DATA__\\s*=\\s*(\\{.*?\\})\\s*;</script>",
            "(?is)__NUXT__\\s*=\\s*(\\{.*?\\})\\s*;",
            "(?is)__INITIAL_STATE__\\s*=\\s*(\\{.*?\\})\\s*;",
            "(?is)__PRELOADED_STATE__\\s*=\\s*(\\{.*?\\})\\s*;",
            "(?is)__APOLLO_STATE__\\s*=\\s*(\\{.*?\\})\\s*;"
        );
        for (String pattern : patterns) {
            Matcher matcher = Pattern.compile(pattern).matcher(text);
            while (matcher.find()) {
                values.add(matcher.group(1).trim());
            }
        }
        return values;
    }

    private static void walkJsonLdProducts(JsonElement payload, List<Map<String, Object>> values, int limit) {
        if (values.size() >= limit || payload == null || payload.isJsonNull()) {
            return;
        }
        if (payload.isJsonObject()) {
            JsonObject map = payload.getAsJsonObject();
            boolean isProduct = false;
            if (map.has("@type")) {
                JsonElement type = map.get("@type");
                if (type.isJsonPrimitive()) {
                    isProduct = "Product".equalsIgnoreCase(type.getAsString());
                } else if (type.isJsonArray()) {
                    for (JsonElement element : type.getAsJsonArray()) {
                        if (element.isJsonPrimitive() && "Product".equalsIgnoreCase(element.getAsString())) {
                            isProduct = true;
                            break;
                        }
                    }
                }
            }
            if (isProduct) {
                Map<String, Object> item = new LinkedHashMap<>();
                item.put("name", map.has("name") ? map.get("name").getAsString() : "");
                item.put("sku", map.has("sku") ? map.get("sku").getAsString() : "");
                item.put("brand", map.has("brand") && map.get("brand").isJsonObject() && map.getAsJsonObject("brand").has("name")
                    ? map.getAsJsonObject("brand").get("name").getAsString()
                    : map.has("brand") && map.get("brand").isJsonPrimitive() ? map.get("brand").getAsString() : "");
                item.put("category", map.has("category") ? map.get("category").getAsString() : "");
                item.put("url", map.has("url") ? map.get("url").getAsString() : "");
                if (map.has("image")) {
                    JsonElement image = map.get("image");
                    if (image.isJsonArray() && !image.getAsJsonArray().isEmpty()) {
                        item.put("image", image.getAsJsonArray().get(0).getAsString());
                    } else if (image.isJsonPrimitive()) {
                        item.put("image", image.getAsString());
                    }
                } else {
                    item.put("image", "");
                }
                if (map.has("offers") && map.get("offers").isJsonObject()) {
                    JsonObject offers = map.getAsJsonObject("offers");
                    item.put("price", offers.has("price") ? offers.get("price").getAsString() : "");
                    item.put("currency", offers.has("priceCurrency") ? offers.get("priceCurrency").getAsString() : "");
                } else {
                    item.put("price", "");
                    item.put("currency", "");
                }
                if (map.has("aggregateRating") && map.get("aggregateRating").isJsonObject()) {
                    JsonObject rating = map.getAsJsonObject("aggregateRating");
                    item.put("rating", rating.has("ratingValue") ? rating.get("ratingValue").getAsString() : "");
                    item.put("review_count", rating.has("reviewCount") ? rating.get("reviewCount").getAsString() : "");
                } else {
                    item.put("rating", "");
                    item.put("review_count", "");
                }
                values.add(item);
                if (values.size() >= limit) {
                    return;
                }
            }
            for (Map.Entry<String, JsonElement> entry : map.entrySet()) {
                walkJsonLdProducts(entry.getValue(), values, limit);
                if (values.size() >= limit) {
                    return;
                }
            }
            return;
        }
        if (payload.isJsonArray()) {
            for (JsonElement element : payload.getAsJsonArray()) {
                walkJsonLdProducts(element, values, limit);
                if (values.size() >= limit) {
                    return;
                }
            }
        }
    }

    private static void walkBootstrapProducts(
        JsonElement payload,
        List<Map<String, Object>> values,
        Set<String> seen,
        int limit
    ) {
        if (values.size() >= limit || payload == null || payload.isJsonNull()) {
            return;
        }
        if (payload.isJsonObject()) {
            JsonObject map = payload.getAsJsonObject();
            Map<String, Object> product = normalizeBootstrapProduct(map);
            if (!product.isEmpty()) {
                String fingerprint = String.join(
                    "|",
                    String.valueOf(product.getOrDefault("sku", "")),
                    String.valueOf(product.getOrDefault("url", "")),
                    String.valueOf(product.getOrDefault("name", "")),
                    String.valueOf(product.getOrDefault("price", ""))
                );
                if (seen.add(fingerprint)) {
                    values.add(product);
                    if (values.size() >= limit) {
                        return;
                    }
                }
            }
            for (Map.Entry<String, JsonElement> entry : map.entrySet()) {
                walkBootstrapProducts(entry.getValue(), values, seen, limit);
                if (values.size() >= limit) {
                    return;
                }
            }
            return;
        }
        if (payload.isJsonArray()) {
            for (JsonElement element : payload.getAsJsonArray()) {
                walkBootstrapProducts(element, values, seen, limit);
                if (values.size() >= limit) {
                    return;
                }
            }
        }
    }

    private static void walkApiCandidates(JsonElement payload, List<String> values, int limit) {
        if (values.size() >= limit || payload == null || payload.isJsonNull()) {
            return;
        }
        if (payload.isJsonObject()) {
            JsonObject map = payload.getAsJsonObject();
            for (Map.Entry<String, JsonElement> entry : map.entrySet()) {
                String candidate = apiCandidateFromValue(entry.getValue());
                if (!candidate.isBlank() && !values.contains(candidate)) {
                    values.add(candidate);
                }
                if (values.size() >= limit) {
                    return;
                }
                walkApiCandidates(entry.getValue(), values, limit);
                if (values.size() >= limit) {
                    return;
                }
            }
            return;
        }
        if (payload.isJsonArray()) {
            for (JsonElement element : payload.getAsJsonArray()) {
                String candidate = apiCandidateFromValue(element);
                if (!candidate.isBlank() && !values.contains(candidate)) {
                    values.add(candidate);
                }
                if (values.size() >= limit) {
                    return;
                }
                walkApiCandidates(element, values, limit);
                if (values.size() >= limit) {
                    return;
                }
            }
        }
    }

    private static Map<String, Object> normalizeBootstrapProduct(JsonObject map) {
        String name = valueOrEmpty(firstPresent(
            map,
            List.of("name", "title", "itemName", "productName", "goodsName", "noteTitle", "note_title")
        ));
        String sku = valueOrEmpty(firstPresent(
            map,
            List.of("sku", "skuId", "itemId", "item_id", "productId", "product_id", "goodsId", "goods_id", "noteId", "note_id", "asin", "id")
        ));
        String url = valueOrEmpty(firstPresent(
            map,
            List.of("url", "detailUrl", "itemUrl", "shareUrl", "jumpUrl", "link")
        ));
        String image = imageOrEmpty(firstPresent(
            map,
            List.of("image", "imageUrl", "imageURL", "pic", "picUrl", "cover", "coverUrl", "mainImage", "img")
        ));
        String price = firstNonBlank(
            valueOrEmpty(firstPresent(
                map,
                List.of("price", "salePrice", "currentPrice", "finalPrice", "minPrice", "maxPrice", "promotionPrice", "groupPrice", "jdPrice", "priceToPay", "displayPrice", "priceAmount")
            )),
            valueOrEmpty(nestedFirst(map, List.of(
                List.of("offers", "price"),
                List.of("offers", "lowPrice"),
                List.of("priceInfo", "price"),
                List.of("currentSku", "price"),
                List.of("product", "price")
            )))
        );
        String currency = firstNonBlank(
            valueOrEmpty(firstPresent(map, List.of("currency", "priceCurrency"))),
            valueOrEmpty(nestedFirst(map, List.of(
                List.of("offers", "priceCurrency"),
                List.of("priceInfo", "currency")
            )))
        );
        String brand = firstNonBlank(
            valueOrEmpty(firstPresent(map, List.of("brand", "brandName"))),
            valueOrEmpty(nestedFirst(map, List.of(
                List.of("brand", "name"),
                List.of("brandInfo", "name")
            )))
        );
        String category = valueOrEmpty(firstPresent(map, List.of("category", "categoryName")));
        String rating = firstNonBlank(
            valueOrEmpty(firstPresent(map, List.of("rating", "score", "ratingValue", "averageRating"))),
            valueOrEmpty(nestedFirst(map, List.of(
                List.of("aggregateRating", "ratingValue"),
                List.of("ratings", "average")
            )))
        );
        String reviewCount = firstNonBlank(
            valueOrEmpty(firstPresent(map, List.of("reviewCount", "commentCount", "comments", "ratingsTotal", "totalReviewCount", "soldCount", "sales", "interactCount"))),
            valueOrEmpty(nestedFirst(map, List.of(
                List.of("aggregateRating", "reviewCount"),
                List.of("aggregateRating", "ratingCount")
            )))
        );
        String shop = valueOrEmpty(firstPresent(
            map,
            List.of("shopName", "seller", "sellerNick", "storeName", "merchantName", "vendor", "authorName", "mall_name")
        ));

        int score = 0;
        if (!name.isBlank() || !sku.isBlank()) score++;
        if (!price.isBlank()) score++;
        if (!image.isBlank() || !url.isBlank()) score++;
        if (!shop.isBlank() || !rating.isBlank() || !reviewCount.isBlank()) score++;
        if (score < 2) {
            return Map.of();
        }

        Map<String, Object> item = new LinkedHashMap<>();
        item.put("name", name);
        item.put("sku", sku);
        item.put("brand", brand);
        item.put("category", category);
        item.put("url", url);
        item.put("image", image);
        item.put("price", price);
        item.put("currency", currency);
        item.put("rating", rating);
        item.put("review_count", reviewCount);
        item.put("shop", shop);
        return item;
    }

    private static JsonElement firstPresent(JsonObject map, List<String> keys) {
        for (String key : keys) {
            if (map.has(key) && !map.get(key).isJsonNull() && !valueOrEmpty(map.get(key)).isBlank()) {
                return map.get(key);
            }
        }
        return null;
    }

    private static JsonElement nestedFirst(JsonObject map, List<List<String>> paths) {
        for (List<String> path : paths) {
            JsonElement current = map;
            boolean valid = true;
            for (String key : path) {
                if (!current.isJsonObject() || !current.getAsJsonObject().has(key)) {
                    valid = false;
                    break;
                }
                current = current.getAsJsonObject().get(key);
            }
            if (valid && !valueOrEmpty(current).isBlank()) {
                return current;
            }
        }
        return null;
    }

    private static String firstNonBlank(String... values) {
        for (String value : values) {
            if (value != null && !value.isBlank()) {
                return value;
            }
        }
        return "";
    }

    private static String imageOrEmpty(JsonElement value) {
        if (value == null || value.isJsonNull()) {
            return "";
        }
        if (value.isJsonArray() && !value.getAsJsonArray().isEmpty()) {
            return valueOrEmpty(value.getAsJsonArray().get(0));
        }
        return valueOrEmpty(value);
    }

    private static String valueOrEmpty(JsonElement value) {
        if (value == null || value.isJsonNull()) {
            return "";
        }
        if (value.isJsonPrimitive()) {
            return value.getAsString().trim();
        }
        return "";
    }

    private static String apiCandidateFromValue(JsonElement value) {
        String candidate = valueOrEmpty(value);
        if (candidate.isBlank()) {
            return "";
        }
        String lowered = candidate.toLowerCase();
        List<String> keywords = List.of("api", "comment", "comments", "review", "reviews", "detail", "item", "items", "sku", "price", "search");
        boolean matched = keywords.stream().anyMatch(lowered::contains);
        if (!matched) {
            return "";
        }
        if (candidate.startsWith("http://") || candidate.startsWith("https://") || candidate.startsWith("/")) {
            return candidate;
        }
        for (String prefix : List.of("api/", "comment", "review", "detail", "item/", "items/", "search", "price")) {
            if (lowered.startsWith(prefix)) {
                return candidate;
            }
        }
        return "";
    }

    static List<String> normalizeApiCandidates(String baseUrl, List<String> candidates, int limit) {
        List<String> values = new ArrayList<>();
        for (String rawCandidate : candidates) {
            String candidate = rawCandidate == null ? "" : rawCandidate.trim();
            if (candidate.isBlank()) {
                continue;
            }
            String absolute = candidate;
            if (!candidate.startsWith("http://") && !candidate.startsWith("https://")) {
                List<String> resolved = normalizeLinks(baseUrl, List.of(candidate));
                if (resolved.isEmpty()) {
                    continue;
                }
                absolute = resolved.get(0);
            }
            if (!values.contains(absolute)) {
                values.add(absolute);
            }
            if (values.size() >= limit) {
                break;
            }
        }
        return values;
    }

    static List<Map<String, Object>> buildApiJobTemplates(
        String baseUrl,
        String siteFamily,
        List<String> apiCandidates,
        List<String> itemIds,
        int limit
    ) {
        String family = siteFamily == null || siteFamily.isBlank() ? "generic" : siteFamily.trim();
        List<String> urls = new ArrayList<>();
        if ("jd".equals(family)) {
            List<String> cleanItemIds = itemIds == null
                ? List.of()
                : itemIds.stream().map(value -> value == null ? "" : value.trim()).filter(value -> !value.isBlank()).toList();
            if (!cleanItemIds.isEmpty()) {
                urls.add(buildJDPriceApiUrl(cleanItemIds.subList(0, Math.min(3, cleanItemIds.size()))));
                urls.add("https://club.jd.com/comment/productPageComments.action?productId=" + cleanItemIds.get(0) + "&score=0&sortType=5&page=0&pageSize=10&isShadowSku=0&fold=1");
            }
        }
        urls.addAll(normalizeApiCandidates(baseUrl, apiCandidates, limit * 2));

        List<Map<String, Object>> templates = new ArrayList<>();
        for (String url : urls) {
            boolean exists = templates.stream().anyMatch(template -> {
                Object target = template.get("target");
                return target instanceof Map<?, ?> targetMap && url.equals(String.valueOf(targetMap.get("url")));
            });
            if (exists) {
                continue;
            }
            Map<String, Object> template = new LinkedHashMap<>();
            template.put("name", family + "-api-" + (templates.size() + 1));
            template.put("runtime", "http");
            template.put("target", Map.of("url", url, "method", "GET", "headers", Map.of("Referer", baseUrl)));
            template.put("output", Map.of("format", "json"));
            template.put("metadata", Map.of("site_family", family, "source_url", baseUrl));
            templates.add(template);
            if (templates.size() >= limit) {
                break;
            }
        }
        return templates;
    }

    public static final class Profile {
        final String family;
        final String catalogUrl;
        final String detailUrl;
        final String reviewUrl;
        final String runner;
        final List<String> detailLinkKeywords;
        final List<String> nextLinkKeywords;
        final List<String> reviewLinkKeywords;
        final List<String> pricePatterns;
        final List<String> itemIdPatterns;
        final List<String> shopPatterns;
        final List<String> reviewCountPatterns;
        final List<String> ratingPatterns;

        Profile(
            String family,
            String catalogUrl,
            String detailUrl,
            String reviewUrl,
            String runner,
            List<String> detailLinkKeywords,
            List<String> nextLinkKeywords,
            List<String> reviewLinkKeywords,
            List<String> pricePatterns,
            List<String> itemIdPatterns,
            List<String> shopPatterns,
            List<String> reviewCountPatterns,
            List<String> ratingPatterns
        ) {
            this.family = family;
            this.catalogUrl = catalogUrl;
            this.detailUrl = detailUrl;
            this.reviewUrl = reviewUrl;
            this.runner = runner;
            this.detailLinkKeywords = detailLinkKeywords;
            this.nextLinkKeywords = nextLinkKeywords;
            this.reviewLinkKeywords = reviewLinkKeywords;
            this.pricePatterns = pricePatterns;
            this.itemIdPatterns = itemIdPatterns;
            this.shopPatterns = shopPatterns;
            this.reviewCountPatterns = reviewCountPatterns;
            this.ratingPatterns = ratingPatterns;
        }
    }

    // ═══════════════════════════════════════════════════════════════════
    // Enhanced Data Extraction Functions (v2.0 upgrade)
    // - SKU/Variant extraction
    // - Image gallery extraction
    // - Parameter/spec table extraction
    // - Coupon/promotion detection
    // - Stock/availability monitoring
    // ═══════════════════════════════════════════════════════════════════

    // ── SKU Variant Extraction ────────────────────────────────────────

    /**
     * Extract SKU variant/specification options from product page.
     * Returns list of maps with keys: name, values (List<String>), sku_id
     */
    public static List<Map<String, Object>> extractSkuVariants(String html) {
        List<Map<String, Object>> variants = new ArrayList<>();

        // Strategy 1: Extract from embedded JSON blocks
        List<Map<String, Object>> bootstrapVariants = extractVariantsFromBootstrap(html);
        variants.addAll(bootstrapVariants);

        // Strategy 2: Regex-based extraction
        if (variants.isEmpty()) {
            List<Map<String, Object>> regexVariants = extractVariantsByRegex(html);
            variants.addAll(regexVariants);
        }

        if (variants.size() > 20) {
            return variants.subList(0, 20);
        }
        return variants;
    }

    private static final String[] VARIANT_JSON_KEYS = {
        "skus", "variants", "specs", "sale_attrs", "attr_list",
        "spec_items", "variant_list", "skulist", "product_options", "attributes"
    };

    private static final String[] VARIANT_VALUE_KEYS = {
        "values", "options", "list", "value_list", "attr_values", "spec_values"
    };

    private static List<Map<String, Object>> extractVariantsFromBootstrap(String html) {
        List<Map<String, Object>> variants = new ArrayList<>();
        List<String> blocks = extractEmbeddedJsonBlocks(html, 10, 8000);
        for (String raw : blocks) {
            Object payload = safeJSONParse(raw);
            if (payload instanceof Map) {
                walkForVariants((Map<String, Object>) payload, variants, 0, 6);
            }
        }
        return variants;
    }

    private static Object safeJSONParse(String raw) {
        try {
            return new Gson().fromJson(raw, Object.class);
        } catch (Exception ignored) {
            return Map.of();
        }
    }

    private static String stringValue(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
    }

    @SuppressWarnings("unchecked")
    private static void walkForVariants(Map<String, Object> node, List<Map<String, Object>> variants, int depth, int maxDepth) {
        if (depth > maxDepth || variants.size() >= 20) return;

        for (Map.Entry<String, Object> entry : node.entrySet()) {
            String keyLower = entry.getKey().toLowerCase();
            for (String vk : VARIANT_JSON_KEYS) {
                if (keyLower.equals(vk)) {
                    if (entry.getValue() instanceof List) {
                        for (Object item : (List<?>) entry.getValue()) {
                            if (item instanceof Map) {
                                Map<String, Object> m = (Map<String, Object>) item;
                                String name = stringValue(m.getOrDefault("name", ""));
                                if (name.isEmpty()) name = stringValue(m.getOrDefault("attr_name", ""));
                                if (name.isEmpty()) name = stringValue(m.getOrDefault("spec_name", ""));
                                String skuId = stringValue(m.getOrDefault("sku_id", ""));
                                if (skuId.isEmpty()) skuId = stringValue(m.getOrDefault("skuId", ""));
                                if (skuId.isEmpty()) skuId = stringValue(m.getOrDefault("id", ""));
                                List<String> values = extractVariantValues(m);
                                Map<String, Object> variant = new LinkedHashMap<>();
                                variant.put("name", name);
                                variant.put("values", values);
                                variant.put("sku_id", skuId);
                                variants.add(variant);
                            }
                        }
                    }
                    break;
                }
            }
            Object val = entry.getValue();
            if (val instanceof Map) walkForVariants((Map<String, Object>) val, variants, depth + 1, maxDepth);
            else if (val instanceof List) {
                List<?> list = (List<?>) val;
                for (int i = 0; i < Math.min(list.size(), 10); i++) {
                    if (list.get(i) instanceof Map) {
                        walkForVariants((Map<String, Object>) list.get(i), variants, depth + 1, maxDepth);
                    }
                }
            }
        }
    }

    @SuppressWarnings("unchecked")
    private static List<String> extractVariantValues(Map<String, Object> item) {
        List<String> values = new ArrayList<>();
        for (String vkey : VARIANT_VALUE_KEYS) {
            Object v = item.get(vkey);
            if (v instanceof List) {
                for (Object entry : (List<?>) v) {
                    String val;
                    if (entry instanceof Map) {
                        Map<String, Object> m = (Map<String, Object>) entry;
                        val = stringValue(m.getOrDefault("name", ""));
                        if (val.isEmpty()) val = stringValue(m.getOrDefault("value", ""));
                        if (val.isEmpty()) val = stringValue(m.getOrDefault("text", ""));
                    } else if (entry instanceof String) {
                        val = (String) entry;
                    } else {
                        val = String.valueOf(entry);
                    }
                    if (!val.isEmpty()) values.add(val);
                }
                break; // Use first matching key
            }
        }
        return values;
    }

    private static List<Map<String, Object>> extractVariantsByRegex(String html) {
        List<Map<String, Object>> variants = new ArrayList<>();
        Set<String> seen = new HashSet<>();
        String[] patterns = {
            "\"(color|colour)\s*:\s*\\\"([^\\\"]+)\\\"",
            "\"(size)\s*:\s*\\\"([^\\\"]+)\\\"",
            "\"(storage)\s*:\s*\\\"([^\\\"]+)\\\"",
            "\"(style)\s*:\s*\\\"([^\\\"]+)\\\"",
            "\"(version)\s*:\s*\\\"([^\\\"]+)\\\"",
        };
        for (String pat : patterns) {
            try {
                java.util.regex.Matcher m = Pattern.compile(pat).matcher(html);
                while (m.find()) {
                    String name = m.group(1);
                    String val = m.group(2);
                    String key = name + ":" + val;
                    if (seen.add(key)) {
                        Map<String, Object> variant = new LinkedHashMap<>();
                        variant.put("name", name);
                        variant.put("values", List.of(val));
                        variants.add(variant);
                    }
                }
            } catch (Exception ignored) {}
        }
        return variants.size() > 10 ? variants.subList(0, 10) : variants;
    }

    // ── Image Gallery Extraction ───────────────────────────────────────

    /**
     * Extract full product image gallery from detail page.
     * Returns list of maps with: url, alt, kind (main/gallery/thumbnail)
     */
    public static List<Map<String, String>> extractImageGallery(String pageUrl, List<String> imgSrcs) {
        List<Map<String, String>> gallery = new ArrayList<>();
        Set<String> seen = new HashSet<>();
        String[] skipPatterns = {"1x1", "spacer", "pixel", "tracker", "icon", "logo", "banner", "arrow", "blank"};

        for (int i = 0; i < imgSrcs.size(); i++) {
            String src = imgSrcs.get(i);
            if (src.isEmpty() || seen.contains(src)) continue;
            String srcLower = src.toLowerCase();
            boolean skip = false;
            for (String pat : skipPatterns) {
                if (srcLower.contains(pat)) { skip = true; break; }
            }
            if (skip) continue;
            seen.add(src);
            String absUrl = src.startsWith("http://") || src.startsWith("https://")
                ? src
                : pageUrl.substring(0, pageUrl.lastIndexOf("/") + 1) + src;

            String kind = "gallery";
            if (i == 0) kind = "main";
            else if (srcLower.contains("thumb") || srcLower.contains("60x60") || srcLower.contains("50x50")) kind = "thumbnail";

            Map<String, String> entry = new HashMap<>();
            entry.put("url", absUrl);
            entry.put("alt", "");
            entry.put("kind", kind);
            gallery.add(entry);
        }
        return gallery;
    }

    // -- Parameter/Spec Table Extraction -----------------------------------

    public static List<Map<String, String>> extractParameterTable(String html) {
        List<Map<String, String>> params = new ArrayList<>();
        Pattern trPattern = Pattern.compile(
            "<tr[^>]*>\\s*<t[dh][^>]*>(.*?)</t[dh]>\\s*<t[dh][^>]*>(.*?)</t[dh]>",
            Pattern.CASE_INSENSITIVE | Pattern.DOTALL);
        Matcher trMatcher = trPattern.matcher(html);
        while (trMatcher.find() && params.size() < 30) {
            String key = cleanHtmlText(trMatcher.group(1)).trim();
            String value = cleanHtmlText(trMatcher.group(2)).trim();
            if (!key.isEmpty() && !value.isEmpty() && key.length() < 50) {
                Map<String, String> entry = new HashMap<>();
                entry.put("key", key);
                entry.put("value", value);
                params.add(entry);
            }
        }
        if (params.isEmpty()) {
            params = extractParamsFromJSON(html);
        }
        return params.size() > 30 ? params.subList(0, 30) : params;
    }

    private static List<Map<String, String>> extractParamsFromJSON(String html) {
        List<Map<String, String>> params = new ArrayList<>();
        List<String> jsonBlocks = extractEmbeddedJsonBlocks(html, 5, 2000);
        for (String block : jsonBlocks) {
            try {
                Pattern paramPattern = Pattern.compile("\"([\\w\\u4e00-\\u9fa5]{2,20})\"\\s*:\\s*\"([^\"]{1,100})\"");
                Matcher matcher = paramPattern.matcher(block);
                while (matcher.find() && params.size() < 30) {
                    Map<String, String> entry = new HashMap<>();
                    entry.put("key", matcher.group(1));
                    entry.put("value", matcher.group(2));
                    params.add(entry);
                }
            } catch (Exception ignored) {}
        }
        return params;
    }

    // -- Coupon/Promotion Detection ---------------------------------------

    public static List<Map<String, String>> detectCouponsPromotions(String html) {
        List<Map<String, String>> coupons = new ArrayList<>();
        String[] couponSelectors = {
            "class=\"[^\"]*coupon[^\"]*\"",
            "class=\"[^\"]*promo[^\"]*\"",
            "class=\"[^\"]*discount[^\"]*\"",
            "data-coupon", "data-promo", "data-discount",
        };
        for (String selector : couponSelectors) {
            try {
                Pattern p = Pattern.compile(selector, Pattern.CASE_INSENSITIVE);
                Matcher m = p.matcher(html);
                if (m.find() && coupons.size() < 10) {
                    Map<String, String> coupon = new HashMap<>();
                    coupon.put("type", "promotion");
                    coupon.put("description", m.group());
                    coupons.add(coupon);
                }
            } catch (Exception ignored) {}
        }
        // Detect coupon codes in Chinese text
        try {
            String[] codeKeywords = {"\u4fc3\u9500\u5238", "\u4f18\u60e0\u5238", "\u4e13\u5c5e\u5238"};
            for (String kw : codeKeywords) {
                if (html.contains(kw)) {
                    Map<String, String> coupon = new HashMap<>();
                    coupon.put("type", "coupon_code");
                    coupon.put("description", kw);
                    coupons.add(coupon);
                }
            }
        } catch (Exception ignored) {}
        return coupons;
    }

    // -- Stock/Availability Extraction ------------------------------------

    public static Map<String, String> extractStockStatus(String html) {
        Map<String, String> stock = new HashMap<>();
        stock.put("status", "unknown");
        String htmlLower = html.toLowerCase();

        String[] outOfStockSignals = {
            "\u552e\u7f44", "\u65e0\u8d27", "sold out", "out of stock",
            "currently unavailable", "\u6682\u65e0\u5e93\u5b58",
        };
        for (String signal : outOfStockSignals) {
            if (htmlLower.contains(signal.toLowerCase())) {
                stock.put("status", "out_of_stock");
                return stock;
            }
        }

        String[] inStockSignals = {
            "\u6709\u8d27", "\u5f00\u653e\u8d2d\u4e70", "in stock", "add to cart",
            "\u7acb\u5373\u8d2d\u4e70", "\u9884\u552e",
        };
        for (String signal : inStockSignals) {
            if (htmlLower.contains(signal.toLowerCase())) {
                stock.put("status", "in_stock");
                return stock;
            }
        }

        String[] limitedSignals = {"\u4ec5\u9650", "limited", "\u5373\u5c06\u552e\u7f44"};
        for (String signal : limitedSignals) {
            if (htmlLower.contains(signal.toLowerCase())) {
                stock.put("status", "limited");
                return stock;
            }
        }
        return stock;
    }

    // -- Clean HTML Text Helper -------------------------------------------

    private static String cleanHtmlText(String html) {
        return html.replaceAll("<[^>]+>", "").replaceAll("&[a-zA-Z]+;", " ").trim();
    }
}
