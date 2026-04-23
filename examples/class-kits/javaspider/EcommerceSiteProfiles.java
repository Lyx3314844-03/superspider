package project.spiders.classkit;

import com.javaspider.scrapy.Spider;

import java.net.URI;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

final class EcommerceSiteProfiles {
    static final String DEFAULT_SITE_FAMILY = "jd";

    private static final Profile JD = new Profile(
        "jd",
        "https://search.jd.com/Search?keyword=iphone",
        "https://item.jd.com/100000000000.html",
        "https://club.jd.com/comment/productPageComments.action?productId=100000000000",
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
        return DEFAULT_SITE_FAMILY;
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
