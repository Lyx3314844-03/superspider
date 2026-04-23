package com.javaspider.examples.ecommerce;

import com.javaspider.scrapy.CrawlerProcess;
import com.javaspider.scrapy.Spider;
import com.javaspider.scrapy.feed.FeedExporter;
import com.javaspider.scrapy.item.Item;

import java.util.List;

public final class EcommerceExampleRunner {
    private EcommerceExampleRunner() {
    }

    public static void main(String[] args) {
        String mode = args.length > 0 ? args[0] : "catalog";
        String siteFamily = args.length > 1 ? args[1] : EcommerceSiteProfiles.DEFAULT_SITE_FAMILY;

        Spider spider = switch (mode) {
            case "detail" -> new EcommerceDetailSpider(siteFamily);
            case "review" -> new EcommerceReviewSpider(siteFamily);
            default -> new EcommerceCatalogSpider(siteFamily);
        };

        List<Item> items = new CrawlerProcess(spider).crawl();
        String outputPath = String.format("artifacts/exports/javaspider-%s-%s.json", siteFamily, mode);

        try (FeedExporter exporter = FeedExporter.json(outputPath)) {
            exporter.exportItems(items);
        }

        System.out.println("exported items: " + items.size() + " -> " + outputPath);
    }
}
