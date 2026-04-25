package com.javaspider.examples.ecommerce;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.regex.Pattern;

public final class UniversalEcommerceDetector {
    private UniversalEcommerceDetector() {
    }

    public static final class DetectionResult {
        public boolean isEcommerce = false;
        public double confidence = 0.0;
        public String siteFamily = "generic";
        public String platform = "";
        public List<String> detectedFeatures = new ArrayList<>();
        public String currency = "";
        public boolean hasJsonLd = false;
        public boolean hasNextData = false;
        public boolean hasInitialState = false;
        public boolean priceApiDetected = false;
        public String cartUrl = "";
        public List<String> categoryUrls = new ArrayList<>();

        public Map<String, Object> toMap() {
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("is_ecommerce", isEcommerce);
            result.put("confidence", confidence);
            result.put("site_family", siteFamily);
            result.put("platform", platform);
            result.put("detected_features", detectedFeatures);
            result.put("currency", currency);
            result.put("has_jsonld", hasJsonLd);
            result.put("has_next_data", hasNextData);
            result.put("has_initial_state", hasInitialState);
            result.put("price_api_detected", priceApiDetected);
            result.put("cart_url", cartUrl);
            result.put("category_urls", categoryUrls);
            return result;
        }
    }

    private record UrlSignature(List<String> patterns, double confidence, String currency) {
    }

    private record PlatformSignature(List<String> needles, double confidence) {
    }

    private static final Map<String, UrlSignature> URL_SIGNATURES = new LinkedHashMap<>();
    private static final Map<String, PlatformSignature> PLATFORM_SIGNATURES = new LinkedHashMap<>();
    private static final String[] HTML_SIGNALS = {
        "\"@type\"\\s*:\\s*\"Product\"",
        "\"@type\"\\s*:\\s*\"Offer\"",
        "\"@type\"\\s*:\\s*\"AggregateOffer\"",
        "class=[\"'][^\"']*price[^\"']*[\"']",
        "class=[\"'][^\"']*product[^\"']*[\"']",
        "class=[\"'][^\"']*add-to-cart[^\"']*[\"']",
        "shopping[\\-]?cart",
        "data-product-id",
        "data-sku",
        "data-variant-id",
        "itemtype=[\"']https?://schema\\.org/Product[\"']",
        "[\\$€£¥₹₩₽][\\d,]+\\.?\\d*"
    };

    static {
        putUrl("jd", 0.95, "CNY", "jd\\.com", "jd\\.hk");
        putUrl("taobao", 0.95, "CNY", "taobao\\.com");
        putUrl("tmall", 0.95, "CNY", "tmall\\.com");
        putUrl("pinduoduo", 0.95, "CNY", "pinduoduo\\.com", "yangkeduo\\.com", "pdd\\.com");
        putUrl("1688", 0.95, "CNY", "1688\\.com");
        putUrl("suning", 0.90, "CNY", "suning\\.com");
        putUrl("vip", 0.95, "CNY", "vip\\.com", "vipshop\\.com");
        putUrl("xiaohongshu", 0.95, "CNY", "xiaohongshu\\.com", "xhscdn\\.com");
        putUrl("douyin-shop", 0.90, "CNY", "douyin\\.com", "jinritemai\\.com", "life\\.douyin");
        putUrl("kuaishou-shop", 0.90, "CNY", "kuaishou\\.com", "kwai\\.com");
        putUrl("amazon", 0.95, "USD", "amazon\\.(com|co\\.uk|de|fr|it|es|co\\.jp|com\\.au|ca|in|com\\.br|com\\.mx|nl|pl|se|ae|sa|sg)");
        putUrl("ebay", 0.95, "USD", "ebay\\.(com|co\\.uk|de|fr|it|es|com\\.au|ca|ch|at|be|nl|ie|pl|ph|in|my|sg)");
        putUrl("aliexpress", 0.95, "USD", "aliexpress\\.(com|us|es|ru|pt|fr|de|it|nl|ja|ko|ar|th|vi|id|he|pl|tr)");
        putUrl("lazada", 0.95, "USD", "lazada\\.(com|com\\.my|com\\.ph|co\\.id|co\\.th|vn)");
        putUrl("shopee", 0.95, "USD", "shopee\\.(com|co\\.th|co\\.id|com\\.my|com\\.ph|vn|tw|br|cl|pl)");
        putUrl("walmart", 0.95, "USD", "walmart\\.(com|ca)");
        putUrl("target", 0.95, "USD", "target\\.com");
        putUrl("temu", 0.95, "USD", "temu\\.(com|co\\.uk|co\\.jp|de|fr|es|it|nl|be|at|se|pl|pt|ch|dk|fi|gr|cz|hu|ro|bg)");
        putUrl("shein", 0.95, "USD", "shein\\.(com|co\\.uk|co\\.jp|de|fr|es|it|nl|se|at|pl|pt|ch|dk|fi|gr|cz|hu|ro|bg)");
        putUrl("mercadolibre", 0.95, "USD", "mercadolibre\\.(com\\.ar|com\\.mx|com\\.br|com\\.co|com\\.pe|cl|com\\.uy)");
        putUrl("ozon", 0.95, "RUB", "ozon\\.ru");
        putUrl("wildberries", 0.95, "RUB", "wildberries\\.ru");
        putUrl("allegro", 0.95, "PLN", "allegro\\.(pl|cz|sk|hu|ro|bg)");

        putPlatform("shopify", 0.90, "shopify.com", "cdn.shopify", "Shopify.theme");
        putPlatform("magento", 0.90, "Magento_", "mage-cache", "mage/cookies");
        putPlatform("woocommerce", 0.85, "woocommerce", "wp-content/plugins/woocommerce");
        putPlatform("bigcommerce", 0.90, "bigcommerce", "bc.js");
        putPlatform("prestashop", 0.90, "prestashop", "ps-shoppingcart");
        putPlatform("wix", 0.80, "wix.com", "wixstores");
        putPlatform("salesforce", 0.85, "demandware", "sfcc", "commercecloud");
    }

    public static DetectionResult detect(String url, String html) {
        DetectionResult result = new DetectionResult();
        if (url == null || url.isBlank()) {
            return result;
        }
        merge(result, detectByUrl(url));
        merge(result, detectByPlatform(html));
        merge(result, detectByHtmlSignals(html));
        merge(result, detectByStructuredData(html));
        merge(result, detectByPriceApi(html));
        applyFamilyUrls(result);
        return result;
    }

    private static void putUrl(String family, double confidence, String currency, String... patterns) {
        URL_SIGNATURES.put(family, new UrlSignature(List.of(patterns), confidence, currency));
    }

    private static void putPlatform(String platform, double confidence, String... needles) {
        PLATFORM_SIGNATURES.put(platform, new PlatformSignature(List.of(needles), confidence));
    }

    private static void merge(DetectionResult result, DetectionResult candidate) {
        if (candidate == null) {
            return;
        }
        result.isEcommerce = result.isEcommerce || candidate.isEcommerce;
        result.confidence = Math.max(result.confidence, candidate.confidence);
        if ("generic".equals(result.siteFamily) && !"generic".equals(candidate.siteFamily)) {
            result.siteFamily = candidate.siteFamily;
        }
        if (result.platform.isBlank() && !candidate.platform.isBlank()) {
            result.platform = candidate.platform;
        }
        if (result.currency.isBlank() && !candidate.currency.isBlank()) {
            result.currency = candidate.currency;
        }
        result.hasJsonLd = result.hasJsonLd || candidate.hasJsonLd;
        result.hasNextData = result.hasNextData || candidate.hasNextData;
        result.hasInitialState = result.hasInitialState || candidate.hasInitialState;
        result.priceApiDetected = result.priceApiDetected || candidate.priceApiDetected;
        for (String feature : candidate.detectedFeatures) {
            if (!result.detectedFeatures.contains(feature)) {
                result.detectedFeatures.add(feature);
            }
        }
    }

    private static DetectionResult detectByUrl(String url) {
        for (Map.Entry<String, UrlSignature> entry : URL_SIGNATURES.entrySet()) {
            for (String pattern : entry.getValue().patterns()) {
                if (Pattern.compile(pattern, Pattern.CASE_INSENSITIVE).matcher(url).find()) {
                    DetectionResult result = new DetectionResult();
                    result.isEcommerce = true;
                    result.confidence = entry.getValue().confidence();
                    result.siteFamily = entry.getKey();
                    result.platform = entry.getKey();
                    result.currency = entry.getValue().currency();
                    result.detectedFeatures.add("url_pattern");
                    return result;
                }
            }
        }
        return null;
    }

    private static DetectionResult detectByPlatform(String html) {
        if (html == null || html.isBlank()) {
            return null;
        }
        String lowered = html.toLowerCase(Locale.ROOT);
        for (Map.Entry<String, PlatformSignature> entry : PLATFORM_SIGNATURES.entrySet()) {
            for (String needle : entry.getValue().needles()) {
                if (lowered.contains(needle.toLowerCase(Locale.ROOT))) {
                    DetectionResult result = new DetectionResult();
                    result.isEcommerce = true;
                    result.confidence = entry.getValue().confidence();
                    result.platform = entry.getKey();
                    result.detectedFeatures.add("platform_signature");
                    return result;
                }
            }
        }
        return null;
    }

    private static DetectionResult detectByHtmlSignals(String html) {
        if (html == null || html.isBlank()) {
            return null;
        }
        int signals = 0;
        for (String pattern : HTML_SIGNALS) {
            if (Pattern.compile(pattern, Pattern.CASE_INSENSITIVE).matcher(html).find()) {
                signals++;
            }
        }
        boolean hasJsonLd = html.contains("application/ld+json");
        boolean hasNextData = html.contains("__NEXT_DATA__") || html.contains("__NUXT__");
        boolean hasInitialState = html.contains("__INITIAL_STATE__") || html.contains("__PRELOADED_STATE__");
        if (hasJsonLd) {
            signals += 2;
        }
        if (hasNextData || hasInitialState) {
            signals++;
        }
        if (signals < 2) {
            return null;
        }
        DetectionResult result = new DetectionResult();
        result.isEcommerce = true;
        result.confidence = Math.min(0.85, signals * 0.15);
        result.hasJsonLd = hasJsonLd;
        result.hasNextData = hasNextData;
        result.hasInitialState = hasInitialState;
        result.detectedFeatures.add("html_structure");
        return result;
    }

    private static DetectionResult detectByStructuredData(String html) {
        if (html == null || html.isBlank()) {
            return null;
        }
        if (Pattern.compile("\"@type\"\\s*:\\s*\"(Product|Offer|AggregateOffer|ItemList)\"", Pattern.CASE_INSENSITIVE).matcher(html).find()
            || (html.contains("\"offers\"") && (html.contains("\"price\"") || html.contains("\"priceCurrency\"")))) {
            DetectionResult result = new DetectionResult();
            result.isEcommerce = true;
            result.confidence = 0.75;
            result.hasJsonLd = html.contains("application/ld+json");
            result.detectedFeatures.add("structured_product_data");
            return result;
        }
        return null;
    }

    private static DetectionResult detectByPriceApi(String html) {
        if (html == null || html.isBlank()) {
            return null;
        }
        String lowered = html.toLowerCase(Locale.ROOT);
        int hits = 0;
        for (String needle : List.of("price", "amount", "currency", "discount", "saleprice", "stock")) {
            if (lowered.contains(needle)) {
                hits++;
            }
        }
        if (hits < 3) {
            return null;
        }
        DetectionResult result = new DetectionResult();
        result.isEcommerce = true;
        result.confidence = 0.50;
        result.priceApiDetected = true;
        result.detectedFeatures.add("price_api");
        return result;
    }

    private static void applyFamilyUrls(DetectionResult result) {
        switch (result.siteFamily) {
            case "jd" -> {
                result.cartUrl = "https://cart.jd.com/";
                result.categoryUrls = List.of("https://channel.jd.com/");
            }
            case "taobao" -> {
                result.cartUrl = "https://cart.taobao.com/";
                result.categoryUrls = List.of("https://www.taobao.com/tbhome/");
            }
            case "tmall" -> {
                result.cartUrl = "https://cart.tmall.com/";
                result.categoryUrls = List.of("https://www.tmall.com/");
            }
            case "amazon" -> {
                result.cartUrl = "https://www.amazon.com/gp/cart/";
                result.categoryUrls = List.of("https://www.amazon.com/best-sellers/");
            }
            default -> {
            }
        }
    }
}
