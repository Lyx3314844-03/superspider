package com.javaspider.examples.ecommerce;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.javaspider.scrapy.Spider;
import com.javaspider.scrapy.item.Item;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public final class EcommerceDetailSpider extends Spider {
    private final String siteFamily;

    public EcommerceDetailSpider() {
        this(EcommerceSiteProfiles.DEFAULT_SITE_FAMILY);
    }

    public EcommerceDetailSpider(String siteFamily) {
        this.siteFamily = siteFamily;
        EcommerceSiteProfiles.Profile profile = EcommerceSiteProfiles.profileFor(siteFamily);
        setName("ecommerce-detail");
        addStartUrl(profile.detailUrl);
        startMeta("site_family", profile.family);
        startMeta("runner", profile.runner);
        startHeader("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36");
        startHeader("Referer", "https://www.jd.com/");
    }

    @Override
    public List<Object> parse(Response response) {
        String family = EcommerceSiteProfiles.siteFamilyFrom(response);
        EcommerceSiteProfiles.Profile current = EcommerceSiteProfiles.profileFor(family);
        List<String> links = response.selector().css("a").attrs("href");
        List<Map<String, Object>> jsonLdProducts = EcommerceSiteProfiles.extractJsonLdProducts(response.getBody(), 1);
        Map<String, Object> universalFields = new LinkedHashMap<>();
        universalFields.put("embedded_json_blocks", EcommerceSiteProfiles.extractEmbeddedJsonBlocks(response.getBody(), 5, 2000));
        universalFields.put("api_candidates", EcommerceSiteProfiles.extractApiCandidates(response.getBody(), 20));
        universalFields.put("script_sources", response.selector().css("script").attrs("src"));
        universalFields.put("json_ld_products", jsonLdProducts);
        universalFields.put("video_candidates", EcommerceSiteProfiles.collectVideoLinks(response.getUrl(), merge(response.selector().css("video").attrs("src"), response.selector().css("source").attrs("src")), 10));
        universalFields.put("html_excerpt", EcommerceSiteProfiles.textExcerpt(response.getBody(), 800));

        if ("jd".equals(family)) {
            String itemId = EcommerceSiteProfiles.extractJDItemId(response.getUrl(), response.getBody());
            Map<String, Object> detail = new LinkedHashMap<>();
            detail.put("kind", "jd_detail_product");
            detail.put("site_family", family);
            detail.put("title", EcommerceSiteProfiles.bestTitle(response));
            detail.put("url", response.getUrl());
            detail.put("item_id", itemId);
            detail.put("shop", EcommerceSiteProfiles.firstMatch(response.getBody(), current.shopPatterns));
            detail.put("review_count", EcommerceSiteProfiles.firstMatch(response.getBody(), current.reviewCountPatterns));
            detail.put("image_candidates", EcommerceSiteProfiles.collectImageLinks(response.getUrl(), response.selector().css("img").attrs("src"), 10));
            detail.put("review_url", EcommerceSiteProfiles.firstLinkWithKeywords(response.getUrl(), links, current.reviewLinkKeywords));
            detail.putAll(universalFields);
            detail.put("note", "Public universal ecommerce detail extraction with JD price fast path.");

            if (!itemId.isBlank()) {
                Spider.Request request = new Spider.Request(
                    EcommerceSiteProfiles.buildJDPriceApiUrl(List.of(itemId)),
                    this::parsePrice
                )
                    .meta("detail", detail)
                    .header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
                    .header("Referer", response.getUrl());
                return List.of(request);
            }
            return List.of(Item.fromMap(detail));
        }

        if (!"jd".equals(family) && !"generic".equals(family) && !jsonLdProducts.isEmpty()) {
            Map<String, Object> product = jsonLdProducts.get(0);
            return List.of(new Item()
                .set("kind", family + "_detail_product")
                .set("site_family", family)
                .set("title", String.valueOf(product.getOrDefault("name", "")).isBlank() ? EcommerceSiteProfiles.bestTitle(response) : product.get("name"))
                .set("url", String.valueOf(product.getOrDefault("url", "")).isBlank() ? response.getUrl() : product.get("url"))
                .set("item_id", String.valueOf(product.getOrDefault("sku", "")).isBlank() ? EcommerceSiteProfiles.firstMatch(response.getBody(), current.itemIdPatterns) : product.get("sku"))
                .set("price", String.valueOf(product.getOrDefault("price", "")).isBlank() ? EcommerceSiteProfiles.firstMatch(response.getBody(), current.pricePatterns) : product.get("price"))
                .set("currency", product.get("currency"))
                .set("brand", product.get("brand"))
                .set("category", product.get("category"))
                .set("rating", String.valueOf(product.getOrDefault("rating", "")).isBlank() ? EcommerceSiteProfiles.firstMatch(response.getBody(), current.ratingPatterns) : product.get("rating"))
                .set("review_count", String.valueOf(product.getOrDefault("review_count", "")).isBlank() ? EcommerceSiteProfiles.firstMatch(response.getBody(), current.reviewCountPatterns) : product.get("review_count"))
                .set("shop", EcommerceSiteProfiles.firstMatch(response.getBody(), current.shopPatterns))
                .set("review_url", EcommerceSiteProfiles.firstLinkWithKeywords(response.getUrl(), links, current.reviewLinkKeywords))
                .set("embedded_json_blocks", universalFields.get("embedded_json_blocks"))
                .set("api_candidates", universalFields.get("api_candidates"))
                .set("script_sources", universalFields.get("script_sources"))
                .set("json_ld_products", universalFields.get("json_ld_products"))
                .set("video_candidates", universalFields.get("video_candidates"))
                .set("html_excerpt", universalFields.get("html_excerpt"))
                .set("image_candidates", EcommerceSiteProfiles.collectImageLinks(response.getUrl(), response.selector().css("img").attrs("src"), 10))
                .set("note", "Public ecommerce detail fast path via JSON-LD product extraction."));
        }

        return List.of(new Item()
            .set("kind", "ecommerce_detail")
            .set("site_family", family)
            .set("title", EcommerceSiteProfiles.bestTitle(response))
            .set("url", response.getUrl())
            .set("item_id", EcommerceSiteProfiles.firstMatch(response.getBody(), current.itemIdPatterns))
            .set("price", EcommerceSiteProfiles.firstMatch(response.getBody(), current.pricePatterns))
            .set("shop", EcommerceSiteProfiles.firstMatch(response.getBody(), current.shopPatterns))
            .set("review_count", EcommerceSiteProfiles.firstMatch(response.getBody(), current.reviewCountPatterns))
            .set("image_candidates", EcommerceSiteProfiles.collectImageLinks(response.getUrl(), response.selector().css("img").attrs("src"), 10))
            .set("review_url", EcommerceSiteProfiles.firstLinkWithKeywords(response.getUrl(), links, current.reviewLinkKeywords))
            .set("embedded_json_blocks", universalFields.get("embedded_json_blocks"))
            .set("api_candidates", universalFields.get("api_candidates"))
            .set("script_sources", universalFields.get("script_sources"))
            .set("json_ld_products", universalFields.get("json_ld_products"))
            .set("video_candidates", universalFields.get("video_candidates"))
            .set("html_excerpt", universalFields.get("html_excerpt"))
            .set("note", "Public universal ecommerce detail extraction."));
    }

    public String getSiteFamily() {
        return siteFamily;
    }

    private List<Object> parsePrice(Response response) {
        @SuppressWarnings("unchecked")
        Map<String, Object> detail = (Map<String, Object>) response.getRequest().getMeta().get("detail");
        JsonArray payload = EcommerceSiteProfiles.parseJsonArray(response.getBody());
        if (!payload.isEmpty()) {
            JsonObject first = payload.get(0).getAsJsonObject();
            detail.put("price", first.has("p") ? first.get("p").getAsString() : "");
            detail.put("original_price", first.has("op") ? first.get("op").getAsString() : "");
        }
        return List.of(Item.fromMap(detail));
    }

    private static List<String> merge(List<String> first, List<String> second) {
        List<String> values = new java.util.ArrayList<>(first);
        values.addAll(second);
        return values;
    }
}
