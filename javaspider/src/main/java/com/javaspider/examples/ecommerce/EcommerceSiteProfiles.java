package com.javaspider.examples.ecommerce;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.javaspider.scrapy.Spider;

import java.net.URI;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

final class EcommerceSiteProfiles {
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

    private EcommerceSiteProfiles() {
    }

    static Profile profileFor(String siteFamily) {
        return switch ((siteFamily == null ? DEFAULT_SITE_FAMILY : siteFamily).toLowerCase()) {
            case "generic" -> GENERIC;
            case "taobao" -> TAOBAO;
            case "tmall" -> TMALL;
            case "pinduoduo" -> PINDUODUO;
            case "amazon" -> AMAZON;
            default -> JD;
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
        if (lowered.contains("taobao.com")) {
            return "taobao";
        }
        if (lowered.contains("tmall.com")) {
            return "tmall";
        }
        if (lowered.contains("yangkeduo.com") || lowered.contains("pinduoduo.com")) {
            return "pinduoduo";
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
        return values;
    }

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

    static final class Profile {
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
}
