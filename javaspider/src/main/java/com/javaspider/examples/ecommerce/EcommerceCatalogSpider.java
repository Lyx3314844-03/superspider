package com.javaspider.examples.ecommerce;

import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.javaspider.scrapy.Spider;
import com.javaspider.scrapy.item.Item;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public final class EcommerceCatalogSpider extends Spider {
    private final String siteFamily;

    public EcommerceCatalogSpider() {
        this(EcommerceSiteProfiles.DEFAULT_SITE_FAMILY);
    }

    public EcommerceCatalogSpider(String siteFamily) {
        this.siteFamily = siteFamily;
        EcommerceSiteProfiles.Profile profile = EcommerceSiteProfiles.profileFor(siteFamily);
        setName("ecommerce-catalog");
        addStartUrl(profile.catalogUrl);
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
        List<Map<String, Object>> jsonLdProducts = EcommerceSiteProfiles.extractJsonLdProducts(response.getBody(), 5);
        Item summary = new Item()
            .set("kind", "jd".equals(family) ? "jd_catalog_page" : "ecommerce_catalog_page")
            .set("site_family", family)
            .set("runner", current.runner)
            .set("title", EcommerceSiteProfiles.bestTitle(response))
            .set("url", response.getUrl())
            .set("product_link_candidates", EcommerceSiteProfiles.collectProductLinks(response.getUrl(), links, current, 20))
            .set("next_page", EcommerceSiteProfiles.firstLinkWithKeywords(response.getUrl(), links, current.nextLinkKeywords))
            .set("sku_candidates", EcommerceSiteProfiles.collectMatches(response.getBody(), current.itemIdPatterns, 10))
            .set("price_excerpt", EcommerceSiteProfiles.firstMatch(response.getBody(), current.pricePatterns))
            .set("image_candidates", EcommerceSiteProfiles.collectImageLinks(response.getUrl(), response.selector().css("img").attrs("src"), 10))
            .set("video_candidates", EcommerceSiteProfiles.collectVideoLinks(response.getUrl(), merge(response.selector().css("video").attrs("src"), response.selector().css("source").attrs("src")), 10))
            .set("script_sources", response.selector().css("script").attrs("src"))
            .set("api_candidates", EcommerceSiteProfiles.extractApiCandidates(response.getBody(), 20))
            .set("embedded_json_blocks", EcommerceSiteProfiles.extractEmbeddedJsonBlocks(response.getBody(), 5, 2000))
            .set("json_ld_products", jsonLdProducts)
            .set("page_excerpt", EcommerceSiteProfiles.textExcerpt(response.getBody(), 800))
            .set("note", "Public universal ecommerce catalog page extraction.");

        if ("jd".equals(family)) {
            List<Map<String, Object>> products = EcommerceSiteProfiles.extractJDCatalogProducts(response.getBody());
            if (!products.isEmpty()) {
                Spider.Request request = new Spider.Request(
                    EcommerceSiteProfiles.buildJDPriceApiUrl(
                        products.stream().map(product -> String.valueOf(product.get("product_id"))).toList()
                    ),
                    this::parsePrices
                )
                    .meta("site_family", family)
                    .meta("source_url", response.getUrl())
                    .meta("products", products)
                    .header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
                    .header("Referer", response.getUrl());
                return List.of(summary, request);
            }
        }

        if (!"jd".equals(family) && !"generic".equals(family) && !jsonLdProducts.isEmpty()) {
            List<Object> results = new java.util.ArrayList<>();
            results.add(summary);
            @SuppressWarnings("unchecked")
            List<String> productLinks = (List<String>) summary.get("product_link_candidates", java.util.List.of());
            @SuppressWarnings("unchecked")
            List<String> skuCandidates = (List<String>) summary.get("sku_candidates", java.util.List.of());
            for (int i = 0; i < jsonLdProducts.size(); i++) {
                Map<String, Object> product = jsonLdProducts.get(i);
                String url = String.valueOf(product.getOrDefault("url", ""));
                if (url.isBlank() && i < productLinks.size()) {
                    url = productLinks.get(i);
                }
                String sku = String.valueOf(product.getOrDefault("sku", ""));
                if (sku.isBlank() && !skuCandidates.isEmpty()) {
                    sku = skuCandidates.get(0);
                }
                results.add(new Item()
                    .set("kind", family + "_catalog_product")
                    .set("site_family", family)
                    .set("source_url", response.getUrl())
                    .set("product_id", sku)
                    .set("name", product.get("name"))
                    .set("url", url)
                    .set("image_url", product.get("image"))
                    .set("brand", product.get("brand"))
                    .set("category", product.get("category"))
                    .set("price", product.get("price"))
                    .set("currency", product.get("currency"))
                    .set("rating", product.get("rating"))
                    .set("review_count", product.get("review_count")));
            }
            return results;
        }
        return List.of(summary);
    }

    public String getSiteFamily() {
        return siteFamily;
    }

    private List<Object> parsePrices(Response response) {
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> products = (List<Map<String, Object>>) response.getRequest().getMeta().get("products");
        String family = String.valueOf(response.getRequest().getMeta().get("site_family"));
        String sourceUrl = String.valueOf(response.getRequest().getMeta().get("source_url"));

        Map<String, JsonObject> priceMap = new LinkedHashMap<>();
        for (JsonElement element : EcommerceSiteProfiles.parseJsonArray(response.getBody())) {
            JsonObject row = element.getAsJsonObject();
            if (row.has("id")) {
                priceMap.put(row.get("id").getAsString(), row);
            }
        }

        return products.stream().map(product -> {
            String skuId = String.valueOf(product.get("product_id"));
            JsonObject pricing = priceMap.getOrDefault(skuId, new JsonObject());
            return (Object) new Item()
                .set("kind", "jd_catalog_product")
                .set("site_family", family)
                .set("source_url", sourceUrl)
                .set("product_id", skuId)
                .set("name", product.get("name"))
                .set("url", product.get("url"))
                .set("image_url", product.get("image_url"))
                .set("comment_count", product.get("comment_count"))
                .set("price", pricing.has("p") ? pricing.get("p").getAsString() : "")
                .set("original_price", pricing.has("op") ? pricing.get("op").getAsString() : "");
        }).toList();
    }

    private static List<String> merge(List<String> first, List<String> second) {
        List<String> values = new java.util.ArrayList<>(first);
        values.addAll(second);
        return values;
    }
}
