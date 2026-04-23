package com.javaspider.examples.jd;

import com.javaspider.core.Request;
import com.javaspider.core.Page;
import com.javaspider.core.Site;
import com.javaspider.core.Spider;
import com.javaspider.pipeline.Pipeline;
import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import java.io.BufferedWriter;
import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.TimeUnit;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * 京东 iPhone 17 价格爬虫 - JavaSpider 框架版本
 *
 * 编译: javac -cp "../target/classes:lib/*" -encoding UTF-8 -d ../target/examples JDiPhone17FrameworkSpider.java
 * 运行: java -cp "../target/examples:../target/classes:lib/*" com.javaspider.examples.jd.JDiPhone17FrameworkSpider --pages 5 --delay 3000
 */
public class JDiPhone17FrameworkSpider extends Spider {

    private static final String[] KEYWORDS = {"iPhone 17", "苹果17"};
    private static final String SEARCH_URL = "https://search.jd.com/Search";
    private static final String PRICE_API_URL = "https://p.3.cn/prices/mgets";
    private static final String USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36";

    private final ConcurrentLinkedQueue<Product> allProducts = new ConcurrentLinkedQueue<>();
    private final Set<String> seenIds = Collections.synchronizedSet(new HashSet<>());
    private final Gson gson = new GsonBuilder().setPrettyPrinting().create();
    private int maxPages = 5;
    private long delayMs = 3000;

    /**
     * 商品数据模型
     */
    public static class Product {
        public String productId;
        public String name;
        public double price;
        public double originalPrice;
        public String currency = "¥";
        public String url;
        public String imageUrl;
        public String shopName = "";
        public String shopType = "";
        public int commentCount = 0;
        public String crawlTime;

        public Product() {
            this.crawlTime = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"));
        }
    }

    public JDiPhone17FrameworkSpider() {
        super();
        this.spiderName = "JDiPhone17FrameworkSpider";
        this.threadCount = 1; // 京东反爬严格，单线程

        // 配置站点
        this.site = new Site()
            .setUserAgent(USER_AGENT)
            .setSleepTime(3000)
            .setRetryTimes(3)
            .setTimeOut(30000)
            .addHeader("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
            .addHeader("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8")
            .addHeader("Referer", "https://www.jd.com/");

        // 添加管道用于保存结果
        this.addPipeline(new Pipeline() {
            @Override
            public void process(Map<String, Object> result) {
                if (result != null && result.containsKey("product")) {
                    @SuppressWarnings("unchecked")
                    Map<String, Object> productData = (Map<String, Object>) result.get("product");
                    System.out.println("  [管道] 收到商品: " + productData.get("name"));
                }
            }
        });

        System.out.println("============================================================");
        System.out.println("JavaSpider - 京东 iPhone 17 价格爬虫");
        System.out.println("============================================================");
        System.out.println("爬取页数: " + maxPages);
        System.out.println("请求延迟: " + delayMs + "ms");
        System.out.println("线程数: " + this.threadCount);
        System.out.println("============================================================");
    }

    public JDiPhone17FrameworkSpider setMaxPages(int pages) {
        this.maxPages = pages;
        return this;
    }

    public JDiPhone17FrameworkSpider setDelayMs(long delayMs) {
        this.delayMs = delayMs;
        this.site.setSleepTime((int) delayMs);
        return this;
    }

    public JDiPhone17FrameworkSpider setProxy(String host, int port) {
        this.site.proxy(host, port);
        System.out.println("代理: " + host + ":" + port);
        return this;
    }

    /**
     * 开始爬取
     */
    public void startCrawl() {
        for (String keyword : KEYWORDS) {
            System.out.println("\n[搜索] 关键词: " + keyword);
            for (int page = 1; page <= maxPages; page++) {
                int skip = (page - 1) * 30;
                String url = buildSearchUrl(keyword, skip);
                System.out.println("  [页面 " + page + "/" + maxPages + "] " + url);

                this.addRequest(new Request(url)
                    .putExtra("keyword", keyword)
                    .putExtra("page", page));

                if (page < maxPages) {
                    sleep(delayMs);
                }
            }
        }
    }

    @Override
    public void process(Page page) {
        String url = page.getRequest().getUrl();
        Integer currentPage = page.getRequest().getExtra("page") != null ?
            (Integer) page.getRequest().getExtra("page") : 1;

        System.out.println("  解析第 " + currentPage + " 页...");

        String html = page.getHtml();
        if (html == null || html.isEmpty()) {
            System.out.println("  页面内容为空");
            return;
        }

        // 提取商品SKU
        Pattern skuPattern = Pattern.compile("data-sku=\"(\\d+)\"");
        Matcher skuMatcher = skuPattern.matcher(html);
        List<String> skuids = new ArrayList<>();

        while (skuMatcher.find()) {
            String skuId = skuMatcher.group(1);
            if (!seenIds.contains(skuId)) {
                seenIds.add(skuId);
                skuids.add(skuId);
            }
        }

        System.out.println("  找到 " + skuids.size() + " 个商品");

        if (skuids.isEmpty()) {
            System.out.println("  未找到商品，停止翻页");
            return;
        }

        // 提取商品信息
        List<Product> products = new ArrayList<>();
        for (String skuId : skuids) {
            Product product = new Product();
            product.productId = skuId;
            product.url = "https://item.jd.com/" + skuId + ".html";

            // 提取名称
            String namePattern = "data-sku=\"" + skuId + "\"[\\s\\S]*?<em[^>]*>(.*?)</em>";
            Matcher nameMatcher = Pattern.compile(namePattern).matcher(html);
            if (nameMatcher.find()) {
                String rawName = nameMatcher.group(1);
                product.name = rawName.replaceAll("<[^>]+>", "").trim();
            }
            if (product.name == null || product.name.isEmpty()) {
                product.name = "Apple iPhone 17 (SKU: " + skuId + ")";
            }

            // 提取图片
            String imgPattern = "data-sku=\"" + skuId + "\"[\\s\\S]*?data-lazy-img=\"//([^\"]+)\"";
            Matcher imgMatcher = Pattern.compile(imgPattern).matcher(html);
            if (imgMatcher.find()) {
                product.imageUrl = "https://" + imgMatcher.group(1);
            }

            products.add(product);
        }

        // 批量获取价格
        fetchPrices(products);

        System.out.println("  累计商品数: " + allProducts.size());
    }

    /**
     * 批量获取价格
     */
    private void fetchPrices(List<Product> products) {
        if (products.isEmpty()) return;

        // 分批获取
        int batchSize = 50;
        for (int i = 0; i < products.size(); i += batchSize) {
            int end = Math.min(i + batchSize, products.size());
            List<Product> batch = products.subList(i, end);

            List<String> skuIds = new ArrayList<>();
            for (Product p : batch) {
                skuIds.add(p.productId);
            }

            String skuIdsParam = String.join(",", skuIds);
            String url = PRICE_API_URL + "?type=1&area=1_72_4137_0&skuIds=" + skuIdsParam;

            try {
                String json = fetchJson(url);
                if (json != null) {
                    JsonArray array = JsonParser.parseString(json).getAsJsonArray();
                    Map<String, Double> priceMap = new HashMap<>();
                    Map<String, Double> opriceMap = new HashMap<>();

                    for (JsonElement elem : array) {
                        JsonObject obj = elem.getAsJsonObject();
                        String id = obj.get("id").getAsString();
                        if (obj.has("p")) {
                            priceMap.put(id, obj.get("p").getAsDouble());
                        }
                        if (obj.has("op")) {
                            opriceMap.put(id, obj.get("op").getAsDouble());
                        }
                    }

                    for (Product p : batch) {
                        if (priceMap.containsKey(p.productId)) {
                            p.price = priceMap.get(p.productId);
                        }
                        if (opriceMap.containsKey(p.productId)) {
                            p.originalPrice = opriceMap.get(p.productId);
                        }
                        allProducts.add(p);
                        System.out.println("    [价格] " + truncate(p.name, 30) + "... ¥" + String.format("%.2f", p.price));
                    }
                }
            } catch (Exception e) {
                System.err.println("    获取价格失败: " + e.getMessage());
            }

            sleep(500 + (long) (Math.random() * 500));
        }
    }

    /**
     * 构建搜索URL
     */
    private String buildSearchUrl(String keyword, int skip) {
        try {
            String encoded = java.net.URLEncoder.encode(keyword, StandardCharsets.UTF_8.name());
            return SEARCH_URL + "?keyword=" + encoded + "&enc=utf-8&wq=" + encoded + "&s=" + skip;
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    /**
     * 获取JSON数据
     */
    private String fetchJson(String url) throws Exception {
        org.jsoup.Connection conn = org.jsoup.Jsoup.connect(url)
            .userAgent(USER_AGENT)
            .header("Referer", "https://search.jd.com/")
            .ignoreContentType(true)
            .timeout(20000);

        // 检查是否有代理
        if (this.site.getProxyHost() != null && !this.site.getProxyHost().isEmpty()) {
            conn = conn.proxy(this.site.getProxyHost(), this.site.getProxyPort());
        }

        return conn.execute().body();
    }

    /**
     * 保存JSON结果
     */
    public void saveAsJson(String filename) throws IOException {
        Map<String, Object> output = new LinkedHashMap<>();
        output.put("framework", "JavaSpider (Java)");
        output.put("total", allProducts.size());
        output.put("crawl_time", LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")));
        output.put("products", new ArrayList<>(allProducts));

        String json = gson.toJson(output);
        Files.writeString(Paths.get(filename), json, StandardCharsets.UTF_8);
        System.out.println("JSON 已保存: " + filename);
    }

    /**
     * 保存CSV结果
     */
    public void saveAsCsv(String filename) throws IOException {
        try (BufferedWriter writer = Files.newBufferedWriter(Paths.get(filename), StandardCharsets.UTF_8)) {
            // UTF-8 BOM
            writer.write("\uFEFF");
            writer.write("商品ID,商品名称,价格,原价,货币,商品链接,图片链接,店铺,店铺类型,评论数,爬取时间\n");

            for (Product p : allProducts) {
                writer.write(String.format("%s,%s,%.2f,%.2f,%s,%s,%s,%s,%s,%d,%s\n",
                    escapeCsv(p.productId),
                    escapeCsv(p.name),
                    p.price,
                    p.originalPrice,
                    p.currency,
                    escapeCsv(p.url),
                    escapeCsv(p.imageUrl),
                    escapeCsv(p.shopName),
                    escapeCsv(p.shopType),
                    p.commentCount,
                    p.crawlTime
                ));
            }
        }
        System.out.println("CSV 已保存: " + filename);
    }

    private String escapeCsv(String value) {
        if (value == null) return "";
        if (value.contains(",") || value.contains("\"") || value.contains("\n")) {
            return "\"" + value.replace("\"", "\"\"") + "\"";
        }
        return value;
    }

    /**
     * 打印统计
     */
    public void printStats() {
        System.out.println("\n============================================================");
        System.out.println("JavaSpider 爬取统计");
        System.out.println("============================================================");
        System.out.println("商品总数: " + allProducts.size());

        double minPrice = Double.MAX_VALUE;
        double maxPrice = 0;
        double totalPrice = 0;
        int count = 0;

        for (Product p : allProducts) {
            if (p.price > 0) {
                if (p.price < minPrice) minPrice = p.price;
                if (p.price > maxPrice) maxPrice = p.price;
                totalPrice += p.price;
                count++;
            }
        }

        if (count > 0) {
            System.out.printf("价格区间: ¥%.2f - ¥%.2f%n", minPrice, maxPrice);
            System.out.printf("平均价格: ¥%.2f%n", totalPrice / count);
        }
        System.out.println("============================================================");
    }

    private String truncate(String s, int maxLen) {
        if (s.length() <= maxLen) return s;
        return s.substring(0, maxLen) + "...";
    }

    private void sleep(long ms) {
        try {
            TimeUnit.MILLISECONDS.sleep(ms);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }

    /**
     * 主函数
     */
    public static void main(String[] args) {
        int pages = 5;
        long delay = 3000;
        String proxy = null;
        int proxyPort = 0;

        for (int i = 0; i < args.length; i++) {
            switch (args[i]) {
                case "--pages":
                    if (i + 1 < args.length) pages = Integer.parseInt(args[++i]);
                    break;
                case "--delay":
                    if (i + 1 < args.length) delay = Long.parseLong(args[++i]);
                    break;
                case "--proxy":
                    if (i + 1 < args.length) {
                        String[] parts = args[++i].split(":");
                        if (parts.length == 2) {
                            proxy = parts[0];
                            proxyPort = Integer.parseInt(parts[1]);
                        }
                    }
                    break;
            }
        }

        JDiPhone17FrameworkSpider spider = new JDiPhone17FrameworkSpider()
            .setMaxPages(pages)
            .setDelayMs(delay);

        if (proxy != null) {
            spider.setProxy(proxy, proxyPort);
        }

        // 启动爬取
        spider.startCrawl();

        // 运行Spider处理队列
        Thread spiderThread = new Thread(spider);
        spiderThread.start();

        // 等待队列处理完成
        try {
            spiderThread.join(60000); // 最多等待60秒
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }

        // 保存结果
        String timestamp = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss"));
        String outputDir = ".." + File.separator + "output";
        try {
            Files.createDirectories(Paths.get(outputDir));
        } catch (IOException e) {
            System.err.println("创建输出目录失败: " + e.getMessage());
        }

        String jsonPath = outputDir + File.separator + "javaspider_jd_iphone17_" + timestamp + ".json";
        String csvPath = outputDir + File.separator + "javaspider_jd_iphone17_" + timestamp + ".csv";

        try {
            spider.saveAsJson(jsonPath);
            spider.saveAsCsv(csvPath);
        } catch (IOException e) {
            System.err.println("保存结果失败: " + e.getMessage());
        }

        spider.printStats();
    }
}
