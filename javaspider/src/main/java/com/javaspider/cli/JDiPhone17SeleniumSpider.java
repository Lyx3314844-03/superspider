package com.javaspider.cli;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.javaspider.core.Page;
import com.javaspider.core.Request;
import com.javaspider.core.Site;
import com.javaspider.downloader.SeleniumDownloader;
import com.javaspider.processor.PageProcessor;
import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.jsoup.nodes.Element;
import org.jsoup.select.Elements;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * 京东 iPhone 17 价格爬虫 (Selenium 强化版)
 *
 * 使用 javaspider 框架的 SeleniumDownloader 功能，模拟真实浏览器行为
 */
public class JDiPhone17SeleniumSpider implements PageProcessor {

    private static final String[] KEYWORDS = {"iPhone 17", "苹果17"};
    private static final String SEARCH_URL_TEMPLATE = "https://search.jd.com/Search?keyword=%s&enc=utf-8&wq=%s&s=%d";
    private static final String OUTPUT_DIR = "artifacts/exports/jd_iphone17_selenium";

    private List<Map<String, Object>> products = new ArrayList<>();
    private Set<String> seenIds = new HashSet<>();
    private int maxPages = 2;
    private Site site;
    private SeleniumDownloader downloader;

    public JDiPhone17SeleniumSpider() {
        this.site = Site.create()
                .setUserAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
                .setRetryTimes(3)
                .setDownloadDelay(5000);

        // 初始化 Selenium 下载器 (无头模式)
        this.downloader = new SeleniumDownloader("chrome", true);
    }

    @Override
    public void process(Page page) {
        String rawHtml = page.getRawText();
        if (rawHtml == null || rawHtml.isEmpty()) {
            System.out.println("  [错误] 页面内容为空");
            return;
        }

        Document document = Jsoup.parse(rawHtml);
        // 京东商品列表选择器
        Elements goodsItems = document.select(".gl-item");

        System.out.println("  [解析] 发现 " + goodsItems.size() + " 个潜在商品元素");

        for (Element item : goodsItems) {
            String skId = item.attr("data-sku");
            if (skId == null || skId.isEmpty()) {
                skId = item.attr("data-pid");
            }

            if (skId == null || skId.isEmpty() || seenIds.contains(skId)) continue;
            seenIds.add(skId);

            String name = item.select(".p-name em").text();
            if (name == null || name.isEmpty()) name = item.select(".p-name a").text();

            // 简单价格提取（Selenium 版通常能直接获取到渲染后的价格）
            String priceText = item.select(".p-price i").text();
            double price = 0;
            try {
                if (priceText != null && !priceText.isEmpty()) {
                    price = Double.parseDouble(priceText.replaceAll("[^0-9.]", ""));
                }
            } catch (Exception e) { /* ignore */ }

            String shopName = item.select(".p-shop a").text();
            String link = "https://item.jd.com/" + skId + ".html";

            Map<String, Object> product = new LinkedHashMap<>();
            product.put("product_id", skId);
            product.put("name", name);
            product.put("price", price);
            product.put("url", link);
            product.put("shop_name", shopName);
            product.put("crawl_time", LocalDateTime.now().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME));

            products.add(product);
            System.out.println("    [发现] " + (name.length() > 30 ? name.substring(0, 30) : name) + " | 价格: ¥" + price);
        }
    }

    @Override
    public Site getSite() {
        return site;
    }

    public void run() {
        System.out.println("\n[启动] Selenium 爬虫开始工作...");
        try {
            for (String keyword : KEYWORDS) {
                for (int page = 1; page <= maxPages; page++) {
                    int skip = (page - 1) * 30 + 1;
                    String url = String.format(SEARCH_URL_TEMPLATE, keyword, keyword, skip);
                    System.out.println("\n[正在爬取] 关键词: " + keyword + " | 第 " + page + " 页");

                    Request request = new Request(url);
                    Page pageObj = downloader.download(request, site);

                    if (pageObj != null && !pageObj.isSkip()) {
                        process(pageObj);
                    } else {
                        System.out.println("  [失败] 无法下载页面");
                    }

                    Thread.sleep(site.getDownloadDelay());
                }
            }
        } catch (Exception e) {
            System.err.println("[严重错误] " + e.getMessage());
        } finally {
            downloader.close();
            saveResults();
        }
    }

    private void saveResults() {
        try {
            Files.createDirectories(Paths.get(OUTPUT_DIR));
            String ts = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss"));
            Path path = Paths.get(OUTPUT_DIR, "iphone17_results_" + ts + ".json");

            ObjectMapper mapper = new ObjectMapper();
            String json = mapper.writerWithDefaultPrettyPrinter().writeValueAsString(products);
            Files.write(path, json.getBytes(StandardCharsets.UTF_8));

            System.out.println("\n[完成] 共获取 " + products.size() + " 个商品数据");
            System.out.println("[保存] 结果已导出至: " + path.toAbsolutePath());
        } catch (Exception e) {
            System.err.println("[错误] 保存结果失败: " + e.getMessage());
        }
    }

    public static void main(String[] args) {
        new JDiPhone17SeleniumSpider().run();
    }
}
