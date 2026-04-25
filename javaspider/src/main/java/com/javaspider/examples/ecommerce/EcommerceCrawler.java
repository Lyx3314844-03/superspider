package com.javaspider.examples.ecommerce;

import com.javaspider.scrapy.CrawlerProcess;
import com.javaspider.scrapy.Spider;
import com.javaspider.scrapy.feed.FeedExporter;
import com.javaspider.scrapy.item.Item;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;

public final class EcommerceCrawler {
    private final String siteFamily;
    private final Path outputDir;

    public EcommerceCrawler() {
        this(EcommerceSiteProfiles.DEFAULT_SITE_FAMILY, Path.of("artifacts", "exports"));
    }

    public EcommerceCrawler(String siteFamily) {
        this(siteFamily, Path.of("artifacts", "exports"));
    }

    public EcommerceCrawler(String siteFamily, Path outputDir) {
        this.siteFamily = siteFamily;
        this.outputDir = outputDir;
    }

    public Spider buildSpider(String mode) {
        return switch (normalizeMode(mode)) {
            case "detail" -> new EcommerceDetailSpider(siteFamily);
            case "review" -> new EcommerceReviewSpider(siteFamily);
            default -> new EcommerceCatalogSpider(siteFamily);
        };
    }

    public CrawlResult run(String mode) throws Exception {
        String normalizedMode = normalizeMode(mode);
        List<Item> items = new CrawlerProcess(buildSpider(normalizedMode)).crawl();
        Files.createDirectories(outputDir);
        Path outputPath = outputDir.resolve("javaspider-" + siteFamily + "-" + normalizedMode + ".json");
        try (FeedExporter exporter = FeedExporter.json(outputPath.toString())) {
            exporter.exportItems(items);
        }
        return new CrawlResult(normalizedMode, items.size(), outputPath.toString(), Map.of());
    }

    public CrawlResult runBrowser(String mode) throws Exception {
        String normalizedMode = normalizeMode(mode);
        Map<String, Object> payload = EcommerceSeleniumCrawler.capture(
            siteFamily,
            normalizedMode,
            Path.of("artifacts", "browser")
        );
        @SuppressWarnings("unchecked")
        Map<String, String> artifacts = payload.get("artifacts") instanceof Map<?, ?> raw
            ? (Map<String, String>) raw
            : Map.of();
        int productCount = listSize(payload.get("json_ld_products")) + listSize(payload.get("bootstrap_products"));
        return new CrawlResult(
            normalizedMode,
            productCount,
            artifacts.getOrDefault("json", ""),
            payload
        );
    }

    private static int listSize(Object value) {
        return value instanceof List<?> list ? list.size() : 0;
    }

    private static String normalizeMode(String mode) {
        return switch (mode == null ? "" : mode) {
            case "detail" -> "detail";
            case "review" -> "review";
            default -> "catalog";
        };
    }

    public record CrawlResult(String mode, int itemCount, String outputPath, Map<String, Object> payload) {
    }

    public static void main(String[] args) throws Exception {
        String mode = args.length > 0 ? args[0] : "catalog";
        String siteFamily = args.length > 1 ? args[1] : EcommerceSiteProfiles.DEFAULT_SITE_FAMILY;
        EcommerceCrawler crawler = new EcommerceCrawler(siteFamily);
        CrawlResult result;
        if ("browser".equals(mode) || "selenium".equals(mode)) {
            String browserMode = args.length > 2 ? args[2] : "catalog";
            result = crawler.runBrowser(browserMode);
        } else {
            result = crawler.run(mode);
        }
        System.out.println("exported " + result.itemCount() + " items to " + result.outputPath());
    }
}
