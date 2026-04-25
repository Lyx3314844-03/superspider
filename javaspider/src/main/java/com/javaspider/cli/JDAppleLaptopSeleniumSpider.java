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
public class JDAppleLaptopSeleniumSpider implements PageProcessor {

    private static final String[] KEYWORDS = {"苹果笔记本 MacBook"};
    private static final String SEARCH_URL_TEMPLATE = "https://search.jd.com/Search?keyword=%s&enc=utf-8&psort=1&s=%d";
    private static final String OUTPUT_DIR = "output/jd_apple_laptop_selenium";

    private List<Map<String, Object>> products = new ArrayList<>();
    private Set<String> seenIds = new HashSet<>();
    private int maxPages = 2;
    private Site site;
    private SeleniumDownloader downloader;

    public JDAppleLaptopSeleniumSpider() {
        this.site = Site.create()
                .setUserAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
                .setRetryTimes(3)
                .setDownloadDelay(5000);

        // 初始化 Selenium 下载器 (使用有界面模式以降低检测风险，超时增加到 60 秒)
        this.downloader = new SeleniumDownloader("chrome", false, 60000);
    }

    @Override
    public void process(Page page) {
        String rawHtml = page.getRawText();
        if (rawHtml == null || rawHtml.isEmpty()) {
            System.out.println("  [错误] 页面内容为空");
            return;
        }

        if (rawHtml.contains("京东验证") || rawHtml.contains("验证码")) {
            System.out.println("  [警告] 遇到京东验证页面！请在浏览器窗口手动处理（如有）。");
            try { Thread.sleep(10000); } catch (Exception e) {} // 给点时间手动处理
        }

        Document document = Jsoup.parse(rawHtml);
        Elements goodsItems = document.select(".gl-item");

        System.out.println("  [解析] 发现 " + goodsItems.size() + " 个潜在商品元素");

        if (goodsItems.isEmpty()) {
            try {
                Path debugPath = Paths.get(OUTPUT_DIR, "debug_page.html");
                Files.createDirectories(debugPath.getParent());
                Files.writeString(debugPath, rawHtml);
                System.out.println("  [调试] 已保存页面 HTML 到: " + debugPath.toAbsolutePath());
            } catch (Exception e) {
                System.err.println("  [错误] 保存调试 HTML 失败: " + e.getMessage());
            }
        }

        for (Element item : goodsItems) {
            String skId = item.attr("data-sku");
            if (skId == null || skId.isEmpty()) {
                skId = item.attr("data-pid");
            }

            if (skId == null || skId.isEmpty() || seenIds.contains(skId)) continue;

            String name = item.select(".p-name em").text();
            if (name == null || name.isEmpty()) name = item.select(".p-name a").text();
            if (name == null) name = "";

            // 过滤
            String nameLower = name.toLowerCase();
            if (!nameLower.contains("macbook") && !nameLower.contains("苹果笔记本")) continue;

            seenIds.add(skId);

            String priceText = item.select(".p-price i").text();
            double price = 0;
            try {
                if (priceText != null && !priceText.isEmpty()) {
                    price = Double.parseDouble(priceText.replaceAll("[^0-9.]", ""));
                }
            } catch (Exception e) { /* ignore */ }

            if (price < 1000) continue; // 过滤低价配件

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
            System.out.println("    [发现] " + (name.length() > 40 ? name.substring(0, 40) : name) + " | 价格: ¥" + price);
        }
    }

    @Override
    public Site getSite() {
        return site;
    }

    public void run() {
        System.out.println("\n[启动] Selenium 爬虫开始工作 (使用分类页获取苹果笔记本)...");
        try {
            // 直接访问京东苹果笔记本分类页
            String url = "https://list.jd.com/list.html?cat=670,671,672&ev=exbrand_Apple&psort=1&JL=3_%E5%93%81%E7%89%8C_Apple";
            System.out.println("[步骤1] 访问分类页: " + url);

            Request request = new Request(url);
            Page pageObj = downloader.download(request, site);

            if (pageObj != null && !pageObj.isSkip()) {
                process(pageObj);

                // 尝试翻页获取更多数据（按价格排序后，前几页通常是最便宜的）
                if (products.size() < 20) {
                    System.out.println("  [翻页] 尝试获取第 2 页...");
                    String nextUrl = url + "&page=2";
                    Page nextObj = downloader.download(new Request(nextUrl), site);
                    if (nextObj != null) process(nextObj);
                }
            } else {
                System.out.println("  [失败] 无法下载页面");
            }
        } catch (Exception e) {
            System.err.println("[严重错误] " + e.getMessage());
        } finally {
            downloader.close();
            saveResults();
            printCheapest();
        }
    }

    private void saveResults() {
        try {
            Files.createDirectories(Paths.get(OUTPUT_DIR));
            String ts = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss"));
            Path path = Paths.get(OUTPUT_DIR, "apple_laptop_results_" + ts + ".json");

            ObjectMapper mapper = new ObjectMapper();
            String json = mapper.writerWithDefaultPrettyPrinter().writeValueAsString(products);
            Files.write(path, json.getBytes(StandardCharsets.UTF_8));

            System.out.println("\n[完成] 共获取 " + products.size() + " 个商品数据");
            System.out.println("[保存] 结果已导出至: " + path.toAbsolutePath());
        } catch (Exception e) {
            System.err.println("[错误] 保存结果失败: " + e.getMessage());
        }
    }

    private void printCheapest() {
        if (products.isEmpty()) {
            System.out.println("\n[提醒] 未找到任何苹果笔记本商品。");
            return;
        }

        products.sort(Comparator.comparingDouble(p -> (double) p.get("price")));

        System.out.println("\n============================================================");
        System.out.println("京东苹果笔记本 - 最便宜的价格排名:");
        System.out.println("============================================================");

        for (int i = 0; i < Math.min(5, products.size()); i++) {
            Map<String, Object> p = products.get(i);
            System.out.println((i + 1) + ". ¥" + p.get("price") + " - " + p.get("name"));
            System.out.println("   链接: " + p.get("url"));
        }
        System.out.println("============================================================\n");
    }

    public static void main(String[] args) {
        new JDAppleLaptopSeleniumSpider().run();
    }
}
