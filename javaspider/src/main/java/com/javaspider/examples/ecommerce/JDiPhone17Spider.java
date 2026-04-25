package com.javaspider.examples.ecommerce;

import com.google.gson.JsonObject;
import com.javaspider.scrapy.CrawlerProcess;
import com.javaspider.scrapy.Spider;
import com.javaspider.scrapy.feed.FeedExporter;
import com.javaspider.scrapy.item.Item;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 京东苹果17手机爬虫
 * 专门爬取京东上关于 iPhone 17 的所有产品信息
 */
public final class JDiPhone17Spider extends Spider {

    // 默认搜索关键词
    private static final String DEFAULT_KEYWORD = "iphone17";

    private final String keyword;
    private final String searchUrl;
    private final List<String> productLinks = new ArrayList<>();
    private final List<Item> allItems = new ArrayList<>();
    private int maxPages = 1;
    private int currentPage = 0;

    public JDiPhone17Spider(String keyword) {
        this.keyword = keyword != null && !keyword.isBlank() ? keyword : DEFAULT_KEYWORD;
        this.searchUrl = "https://search.jd.com/Search?keyword=" + this.keyword + "&enc=utf-8";
        setName(getClass().getSimpleName());
        addStartUrl(searchUrl);
        startMeta.putAll(Map.of(
            "site_family", "jd",
            "keyword", this.keyword,
            "page_type", "search"
        ));
        startHeader("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36");
        startHeader("Referer", "https://www.jd.com/");
        startHeader("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8");
        startHeader("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8");
    }

    public JDiPhone17Spider() {
        this(DEFAULT_KEYWORD);
    }

    @Override
    public List<Object> parse(Response response) {
        List<Object> results = new ArrayList<>();
        String body = response.getBody();

        // 提取商品链接
        List<String> allLinks = response.selector().css("a").attrs("href");
        List<String> productUrls = new ArrayList<>();

        for (String link : allLinks) {
            if (link != null && (link.contains("item.jd.com") || link.matches(".*\\d+\\.html.*"))) {
                String fullUrl = link.startsWith("http") ? link : "https:" + link;
                if (!productUrls.contains(fullUrl) && fullUrl.contains("jd.com")) {
                    productUrls.add(fullUrl);
                    productLinks.add(fullUrl);
                }
            }
        }

        // 提取商品信息
        List<Map<String, Object>> products = EcommerceSiteProfiles.extractJDCatalogProducts(body);

        // 添加搜索结果汇总
        Item summary = new Item()
            .set("kind", "jd_iphone17_search")
            .set("keyword", keyword)
            .set("search_url", searchUrl)
            .set("page", currentPage + 1)
            .set("products_found", products.size())
            .set("product_links", productUrls)
            .set("total_links", productLinks.size())
            .set("next_page_url", getNextPageUrl(response))
            .set("title", EcommerceSiteProfiles.bestTitle(response))
            .set("note", "京东苹果17手机搜索结果");

        results.add(summary);

        // 为每个商品创建详情页爬取请求
        for (Map<String, Object> product : products) {
            String productUrl = String.valueOf(product.get("url"));
            if (!productUrl.isBlank() && productUrl.contains("jd.com")) {
                Item productItem = new Item()
                    .set("kind", "jd_iphone17_product")
                    .set("keyword", keyword)
                    .set("source", "search_result")
                    .set("product_id", product.get("product_id"))
                    .set("name", product.get("name"))
                    .set("url", productUrl)
                    .set("image_url", product.get("image_url"))
                    .set("comment_count", product.get("comment_count"));
                results.add(productItem);
                allItems.add(productItem);
            }
        }

        // 处理翻页
        String nextPage = getNextPageUrl(response);
        if (nextPage != null && currentPage < maxPages - 1) {
            currentPage++;
            Spider.Request nextRequest = new Spider.Request(nextPage, this::parse)
                .meta("page", currentPage)
                .header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
                .header("Referer", response.getUrl());
            results.add(nextRequest);
        }

        return results;
    }

    private String getNextPageUrl(Response response) {
        List<String> links = response.selector().css("a").attrs("href");
        for (String link : links) {
            if (link != null && (link.contains("page=") || link.contains("pn-next") || link.contains("keyword"))) {
                return link.startsWith("http") ? link : "https://search.jd.com" + link;
            }
        }
        return null;
    }

    public List<String> getProductLinks() {
        return productLinks;
    }

    public List<Item> getAllItems() {
        return allItems;
    }

    public static void main(String[] args) {
        String keyword = args.length > 0 ? args[0] : DEFAULT_KEYWORD;
        String outputFile = args.length > 1 ? args[1] : String.format(
            "artifacts/exports/javaspider-iphone17-%d.json",
            System.currentTimeMillis()
        );

        System.out.println("🚀 启动京东苹果17手机爬虫...");
        System.out.println("📌 搜索关键词: " + keyword);
        System.out.println("📁 输出文件: " + outputFile);

        JDiPhone17Spider spider = new JDiPhone17Spider(keyword);
        List<Item> items = new CrawlerProcess(spider).crawl();

        System.out.println("\n✅ 爬取完成!");
        System.out.println("📊 共获取 " + items.size() + " 条数据");

        try (FeedExporter exporter = FeedExporter.json(outputFile)) {
            exporter.exportItems(items);
            System.out.println("💾 数据已保存至: " + outputFile);
        } catch (Exception e) {
            System.err.println("❌ 保存失败: " + e.getMessage());
        }
    }
}
