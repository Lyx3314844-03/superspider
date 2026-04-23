package com.javaspider.examples.ecommerce;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.javaspider.scrapy.Spider;
import com.javaspider.scrapy.item.Item;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

public final class EcommerceReviewSpider extends Spider {
    private final String siteFamily;

    public EcommerceReviewSpider() {
        this(EcommerceSiteProfiles.DEFAULT_SITE_FAMILY);
    }

    public EcommerceReviewSpider(String siteFamily) {
        this.siteFamily = siteFamily;
        EcommerceSiteProfiles.Profile profile = EcommerceSiteProfiles.profileFor(siteFamily);
        setName("ecommerce-review");
        addStartUrl(profile.reviewUrl);
        startMeta("site_family", profile.family);
        startMeta("runner", profile.runner);
        startHeader("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36");
        startHeader("Referer", "https://item.jd.com/100000000000.html");
    }

    @Override
    public List<Object> parse(Response response) {
        String family = EcommerceSiteProfiles.siteFamilyFrom(response);
        EcommerceSiteProfiles.Profile current = EcommerceSiteProfiles.profileFor(family);
        List<Map<String, Object>> jsonLdProducts = EcommerceSiteProfiles.extractJsonLdProducts(response.getBody(), 1);
        List<String> videoCandidates = EcommerceSiteProfiles.collectVideoLinks(
            response.getUrl(),
            merge(response.selector().css("video").attrs("src"), response.selector().css("source").attrs("src")),
            10
        );

        if ("jd".equals(family)) {
            JsonObject payload = EcommerceSiteProfiles.parseJsonObject(response.getBody());
            List<Map<String, Object>> commentsPreview = new ArrayList<>();
            JsonArray comments = payload.has("comments") ? payload.getAsJsonArray("comments") : new JsonArray();
            for (JsonElement element : comments) {
                JsonObject comment = element.getAsJsonObject();
                commentsPreview.add(Map.of(
                    "id", comment.has("id") ? comment.get("id").getAsLong() : 0L,
                    "score", comment.has("score") ? comment.get("score").getAsInt() : 0,
                    "nickname", comment.has("nickname") ? comment.get("nickname").getAsString() : "",
                    "content", EcommerceSiteProfiles.textExcerpt(comment.has("content") ? comment.get("content").getAsString() : "", 120)
                ));
                if (commentsPreview.size() >= 5) {
                    break;
                }
            }

            return List.of(new Item()
                .set("kind", "jd_review_summary")
                .set("site_family", family)
                .set("url", response.getUrl())
                .set("item_id", payload.has("productId") ? payload.get("productId").getAsString() : EcommerceSiteProfiles.extractJDItemId(response.getUrl(), response.getBody()))
                .set("rating", EcommerceSiteProfiles.firstMatch(response.getBody(), current.ratingPatterns))
                .set("review_count", payload.has("maxPage") ? payload.get("maxPage").getAsInt() : 0)
                .set("max_page", payload.has("maxPage") ? payload.get("maxPage").getAsInt() : 0)
                .set("comments_preview", commentsPreview)
                .set("embedded_json_blocks", EcommerceSiteProfiles.extractEmbeddedJsonBlocks(response.getBody(), 5, 2000))
                .set("api_candidates", EcommerceSiteProfiles.extractApiCandidates(response.getBody(), 20))
                .set("script_sources", response.selector().css("script").attrs("src"))
                .set("json_ld_products", jsonLdProducts)
                .set("video_candidates", videoCandidates)
                .set("excerpt", EcommerceSiteProfiles.textExcerpt(response.getBody(), 800))
                .set("note", "Public universal ecommerce review extraction with JD review fast path."));
        }

        if (!"jd".equals(family) && !"generic".equals(family) && !jsonLdProducts.isEmpty()) {
            Map<String, Object> product = jsonLdProducts.get(0);
            return List.of(new Item()
                .set("kind", family + "_review_summary")
                .set("site_family", family)
                .set("url", response.getUrl())
                .set("item_id", String.valueOf(product.getOrDefault("sku", "")).isBlank() ? EcommerceSiteProfiles.firstMatch(response.getBody(), current.itemIdPatterns) : product.get("sku"))
                .set("rating", String.valueOf(product.getOrDefault("rating", "")).isBlank() ? EcommerceSiteProfiles.firstMatch(response.getBody(), current.ratingPatterns) : product.get("rating"))
                .set("review_count", String.valueOf(product.getOrDefault("review_count", "")).isBlank() ? EcommerceSiteProfiles.firstMatch(response.getBody(), current.reviewCountPatterns) : product.get("review_count"))
                .set("brand", product.get("brand"))
                .set("category", product.get("category"))
                .set("embedded_json_blocks", EcommerceSiteProfiles.extractEmbeddedJsonBlocks(response.getBody(), 5, 2000))
                .set("api_candidates", EcommerceSiteProfiles.extractApiCandidates(response.getBody(), 20))
                .set("script_sources", response.selector().css("script").attrs("src"))
                .set("json_ld_products", jsonLdProducts)
                .set("video_candidates", videoCandidates)
                .set("excerpt", EcommerceSiteProfiles.textExcerpt(response.getBody(), 800))
                .set("note", "Public ecommerce review fast path via JSON-LD aggregate rating extraction."));
        }

        return List.of(new Item()
            .set("kind", "ecommerce_review")
            .set("site_family", family)
            .set("url", response.getUrl())
            .set("item_id", EcommerceSiteProfiles.firstMatch(response.getBody(), current.itemIdPatterns))
            .set("rating", EcommerceSiteProfiles.firstMatch(response.getBody(), current.ratingPatterns))
            .set("review_count", EcommerceSiteProfiles.firstMatch(response.getBody(), current.reviewCountPatterns))
            .set("review_id_candidates", EcommerceSiteProfiles.collectMatches(response.getBody(), List.of("(?:commentId|reviewId|id)[\"'=:\\s]+([A-Za-z0-9_-]+)"), 10))
            .set("embedded_json_blocks", EcommerceSiteProfiles.extractEmbeddedJsonBlocks(response.getBody(), 5, 2000))
            .set("api_candidates", EcommerceSiteProfiles.extractApiCandidates(response.getBody(), 20))
            .set("script_sources", response.selector().css("script").attrs("src"))
            .set("json_ld_products", jsonLdProducts)
            .set("video_candidates", videoCandidates)
            .set("excerpt", EcommerceSiteProfiles.textExcerpt(response.getBody(), 800))
            .set("note", "Public universal ecommerce review extraction."));
    }

    public String getSiteFamily() {
        return siteFamily;
    }

    private static List<String> merge(List<String> first, List<String> second) {
        List<String> values = new java.util.ArrayList<>(first);
        values.addAll(second);
        return values;
    }
}
