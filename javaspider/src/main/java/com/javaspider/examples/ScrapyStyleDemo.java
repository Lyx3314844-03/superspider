package com.javaspider.examples;

import com.javaspider.scrapy.CrawlerProcess;
import com.javaspider.scrapy.Spider;
import com.javaspider.scrapy.feed.FeedExporter;
import com.javaspider.scrapy.item.Item;

import java.util.List;

public final class ScrapyStyleDemo {
    private ScrapyStyleDemo() {
    }

    public static void main(String[] args) {
        Spider spider = new Spider() {
            {
                setName("demo");
                addStartUrl("https://example.com");
            }

            @Override
            public List<Object> parse(Response response) {
                return List.of(
                    new Item()
                        .set("title", response.selector().css("title").firstText())
                        .set("url", response.getUrl())
                );
            }
        };

        List<Item> items = new CrawlerProcess(spider).crawl();

        try (FeedExporter exporter = FeedExporter.json("artifacts/exports/javaspider-scrapy-demo.json")) {
            exporter.exportItems(items);
        }

        System.out.println("exported items: " + items.size());
    }
}
