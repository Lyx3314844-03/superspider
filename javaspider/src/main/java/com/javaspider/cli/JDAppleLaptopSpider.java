package com.javaspider.cli;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.javaspider.core.Page;
import com.javaspider.core.Request;
import com.javaspider.core.Site;
import com.javaspider.downloader.HttpClientDownloader;
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
 * 京东 iPhone 17 价格爬虫
 *
 * 使用 javaspider 框架爬取京东平台上所有 iPhone 17 相关商品信息
 * 包括：商品名称、价格、店铺、评价数、商品链接等
 *
 * 编译: mvn compile
 * 运行: mvn exec:java -Dexec.mainClass="com.javaspider.cli.JDiPhone17Spider"
 * 或者: java -cp target/classes:target/dependency/* com.javaspider.cli.JDiPhone17Spider
 */
public class JDAppleLaptopSpider implements PageProcessor {

    // 搜索关键词列表
    private static final String[] KEYWORDS = {"苹果笔记本", "MacBook Air", "MacBook Pro"};

    // 京东搜索 URL 模板 (加入 psort=1 参数，按价格从低到高排序)
    private static final String SEARCH_URL_TEMPLATE = "https://search.jd.com/Search?keyword=%s&enc=utf-8&wq=%s&s=%d&psort=1";

    // 价格 API
    private static final String PRICE_API_URL = "https://p.3.cn/prices/mgets?type=1&area=1_72_4137_0&skuIds=%s";

    // 配置
    private int maxPages = 3;           // 每个关键词爬取的最大页数
    private int delayMs = 2000;         // 请求延迟（毫秒）
    private String proxyServer = null;  // 代理服务器地址

    // 结果存储
    private List<Map<String, Object>> products = new ArrayList<>();
    private Set<String> seenIds = new HashSet<>();  // 去重

    // 统计信息
    private int totalPages = 0;
    private int totalErrors = 0;

    // 输出目录
    private static final String OUTPUT_DIR = "output/jd_apple_laptop";

    private Site site;

    public JDAppleLaptopSpider() {
        this.site = Site.create()
                .setUserAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
                .setRetryTimes(3)
                .setTimeout(30000)
                .setDownloadDelay(delayMs);

        // 添加更多请求头
        site.addHeader("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8");
        site.addHeader("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8");
        site.addHeader("Accept-Encoding", "gzip, deflate, br");
        site.addHeader("Connection", "keep-alive");
        site.addHeader("Referer", "https://www.jd.com/");
    }

    @Override
    public void process(Page page) {
        String rawHtml = page.getRawText();
        if (rawHtml == null || rawHtml.isEmpty()) {
            System.out.println("  无法解析页面内容");
            totalErrors++;
            return;
        }

        try {
            Document document = page.getUrl() == null || page.getUrl().isBlank()
                ? Jsoup.parse(rawHtml)
                : Jsoup.parse(rawHtml, page.getUrl());

            Elements goodsItems = document.select("#J_goodsList .gl-item");
            if (goodsItems.isEmpty()) {
                goodsItems = document.select(".gl-item");
            }

            if (goodsItems.isEmpty()) {
                System.out.println("  未找到商品列表");
                return;
            }

            System.out.println("  找到 " + goodsItems.size() + " 个商品");

            // 收集商品ID用于批量获取价格
            List<String> skIds = new ArrayList<>();
            List<Element> productElements = new ArrayList<>();

            for (Element item : goodsItems) {
                String dataPid = item.attr("data-pid");
                if (dataPid == null || dataPid.isEmpty()) {
                    dataPid = item.attr("data-sku");
                }
                if (dataPid == null || dataPid.isEmpty()) {
                    // 从链接提取
                    Element linkElement = item.selectFirst(".p-name a[href], .p-img a[href], a[href]");
                    String href = linkElement != null ? linkElement.absUrl("href") : "";
                    if (href.isEmpty() && linkElement != null) {
                        href = linkElement.attr("href");
                    }
                    if (href != null) {
                        Pattern pattern = Pattern.compile("(\\d+)\\.html");
                        Matcher matcher = pattern.matcher(href);
                        if (matcher.find()) {
                            dataPid = matcher.group(1);
                        }
                    }
                }

                if (dataPid != null && !dataPid.isEmpty()) {
                    skIds.add(dataPid);
                    productElements.add(item);
                }
            }

            // 批量获取价格
            Map<String, Double> prices = getPrices(skIds);

            // 解析每个商品
            for (int i = 0; i < productElements.size(); i++) {
                Element item = productElements.get(i);

                if (i >= skIds.size()) break;

                String skId = skIds.get(i);

                // 去重
                if (seenIds.contains(skId)) continue;
                seenIds.add(skId);

                // 提取商品名称
                String name = item.select(".p-name em").text();
                if (name == null || name.isEmpty()) {
                    name = item.select(".p-name a").text();
                }

                if (name == null) name = "";
                name = name.trim();

                // 过滤非苹果笔记本相关商品
                String nameLower = name.toLowerCase();
                if (!nameLower.contains("macbook") &&
                    !nameLower.contains("苹果笔记本") &&
                    !nameLower.contains("apple laptop") &&
                    !nameLower.contains("mac book")) {
                    continue;
                }

                // 提取价格
                double price = prices.getOrDefault(skId, 0.0);

                // 提取链接
                String link = "https://item.jd.com/" + skId + ".html";
                Element hrefElement = item.selectFirst(".p-name a[href], .p-img a[href], a[href]");
                String href = hrefElement != null ? hrefElement.absUrl("href") : "";
                if (href.isEmpty() && hrefElement != null) {
                    href = hrefElement.attr("href");
                }
                if (href != null && !href.isEmpty()) {
                    if (href.startsWith("//")) {
                        link = "https:" + href;
                    } else if (href.startsWith("http")) {
                        link = href;
                    }
                }

                // 提取店铺名称
                String shopName = item.select(".p-shop a").text();
                if (shopName == null || shopName.isEmpty()) {
                    shopName = item.select(".p-shop span").text();
                }
                if (shopName == null) shopName = "";

                // 判断是否自营
                String shopText = item.select(".p-shop").text();
                String shopType = (shopText != null && shopText.contains("自营")) ? "自营" : "第三方";

                // 提取评论数
                String commentText = item.select(".p-commit a").text();
                int commentCount = parseNumber(commentText);

                // 提取图片
                Element imageElement = item.selectFirst(".p-img img");
                String imageUrl = imageElement != null ? imageElement.attr("data-lazy-img") : "";
                if (imageUrl == null || imageUrl.isEmpty()) {
                    imageUrl = imageElement != null ? imageElement.attr("src") : "";
                }
                if (imageUrl != null && imageUrl.startsWith("//")) {
                    imageUrl = "https:" + imageUrl;
                }

                // 提取标签
                List<String> tags = new ArrayList<>();
                Elements tagElements = item.select(".p-icons i");
                for (Element tag : tagElements) {
                    String tagText = tag.text();
                    if (tagText != null && !tagText.trim().isEmpty()) {
                        tags.add(tagText.trim());
                    }
                }

                // 构建商品数据
                Map<String, Object> product = new LinkedHashMap<>();
                product.put("product_id", skId);
                product.put("name", name);
                product.put("price", price);
                product.put("original_price", 0.0);
                product.put("currency", "¥");
                product.put("url", link);
                product.put("image_url", imageUrl != null ? imageUrl : "");
                product.put("shop_name", shopName);
                product.put("shop_type", shopType);
                product.put("comment_count", commentCount);
                product.put("good_rate", 0.0);
                product.put("brand", "Apple");
                product.put("category", "笔记本电脑");
                product.put("tags", tags);
                product.put("crawl_time", LocalDateTime.now().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME));

                products.add(product);
            }

            // 保存结果到页面
            page.getResultItems().put("products_count", products.size());

        } catch (Exception e) {
            System.out.println("  解析商品失败: " + e.getMessage());
            totalErrors++;
        }
    }

    @Override
    public Site getSite() {
        return site;
    }

    /**
     * 批量获取商品价格
     */
    private Map<String, Double> getPrices(List<String> skIds) {
        Map<String, Double> prices = new HashMap<>();

        if (skIds.isEmpty()) {
            return prices;
        }

        // 分批获取（每批最多50个）
        int batchSize = 50;
        for (int i = 0; i < skIds.size(); i += batchSize) {
            int end = Math.min(i + batchSize, skIds.size());
            List<String> batch = skIds.subList(i, end);

            try {
                String skuIdsParam = String.join(",", batch);
                String url = String.format(PRICE_API_URL, skuIdsParam);

                // 使用简单的 HTTP 请求获取价格
                String response = httpGet(url);
                if (response != null) {
                    // 解析 JSON 响应
                    parsePriceResponse(response, prices);
                }

                Thread.sleep(500);  // 批次间延迟
            } catch (Exception e) {
                System.out.println("  获取价格批次失败: " + e.getMessage());
                totalErrors++;
            }
        }

        return prices;
    }

    /**
     * 解析价格响应
     */
    private void parsePriceResponse(String response, Map<String, Double> prices) {
        try {
            // 简单解析 JSON 数组
            Pattern pattern = Pattern.compile("\"id\":\"([^\"]+)\",\"p\":\"([^\"]+)\"");
            Matcher matcher = pattern.matcher(response);

            while (matcher.find()) {
                String skuId = matcher.group(1);
                String priceStr = matcher.group(2);
                try {
                    double price = Double.parseDouble(priceStr);
                    prices.put(skuId, price);
                } catch (NumberFormatException e) {
                    // 忽略无效价格
                }
            }
        } catch (Exception e) {
            System.out.println("  解析价格响应失败: " + e.getMessage());
        }
    }

    /**
     * 简单的 HTTP GET 请求
     */
    private String httpGet(String url) {
        try {
            java.net.URL urlObj = new java.net.URL(url);
            java.net.HttpURLConnection conn = (java.net.HttpURLConnection) urlObj.openConnection();
            conn.setRequestMethod("GET");
            conn.setRequestProperty("User-Agent", site.getUserAgent());
            conn.setConnectTimeout(15000);
            conn.setReadTimeout(15000);

            int responseCode = conn.getResponseCode();
            if (responseCode == 200) {
                try (BufferedReader reader = new BufferedReader(
                        new InputStreamReader(conn.getInputStream(), StandardCharsets.UTF_8))) {
                    StringBuilder response = new StringBuilder();
                    String line;
                    while ((line = reader.readLine()) != null) {
                        response.append(line);
                    }
                    return response.toString();
                }
            }
        } catch (Exception e) {
            System.out.println("  HTTP 请求失败: " + e.getMessage());
        }
        return null;
    }

    /**
     * 解析数字字符串
     */
    private int parseNumber(String text) {
        if (text == null || text.isEmpty()) {
            return 0;
        }

        try {
            Pattern pattern = Pattern.compile("([\\d.]+)");
            Matcher matcher = pattern.matcher(text);
            if (matcher.find()) {
                double number = Double.parseDouble(matcher.group(1));
                if (text.contains("万")) {
                    number *= 10000;
                } else if (text.contains("亿")) {
                    number *= 100000000;
                }
                return (int) number;
            }
        } catch (Exception e) {
            // 忽略
        }
        return 0;
    }

    /**
     * 保存结果到文件
     */
    private void saveResults() throws Exception {
        System.out.println("\n============================================================");
        System.out.println("保存 " + products.size() + " 个商品数据...");
        System.out.println("============================================================");

        // 创建输出目录
        Path outputDir = Paths.get(OUTPUT_DIR);
        Files.createDirectories(outputDir);

        String timestamp = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss"));

        // 保存 JSON
        ObjectMapper mapper = new ObjectMapper();

        Path jsonPath = outputDir.resolve("jd_apple_laptop_" + timestamp + ".json");
        String jsonContent = mapper.writerWithDefaultPrettyPrinter()
                .writeValueAsString(products);
        Files.write(jsonPath, jsonContent.getBytes(StandardCharsets.UTF_8));
        System.out.println("✓ 已保存 JSON: " + jsonPath);

        // 保存 CSV
        Path csvPath = outputDir.resolve("jd_apple_laptop_" + timestamp + ".csv");
        try (BufferedWriter writer = Files.newBufferedWriter(csvPath, StandardCharsets.UTF_8)) {
            if (!products.isEmpty()) {
                // 写入表头
                Map<String, Object> first = products.get(0);
                String[] headers = first.keySet().toArray(new String[0]);
                writer.write(String.join(",", headers));
                writer.newLine();

                // 写入数据
                for (Map<String, Object> product : products) {
                    String[] values = new String[headers.length];
                    for (int i = 0; i < headers.length; i++) {
                        Object value = product.get(headers[i]);
                        if (value instanceof List) {
                            values[i] = "\"" + String.join("; ", (List<String>) value) + "\"";
                        } else if (value instanceof String) {
                            values[i] = "\"" + ((String) value).replace("\"", "\"\"") + "\"";
                        } else {
                            values[i] = String.valueOf(value);
                        }
                    }
                    writer.write(String.join(",", values));
                    writer.newLine();
                }
            }
        }
        System.out.println("✓ 已保存 CSV: " + csvPath);
    }

    /**
     * 打印统计信息
     */
    private void printStats() {
        System.out.println("\n============================================================");
        System.out.println("爬取统计信息 - 苹果笔记本");
        System.out.println("============================================================");
        System.out.println("商品总数: " + products.size());
        System.out.println("爬取页数: " + totalPages);
        System.out.println("错误次数: " + totalErrors);

        if (!products.isEmpty()) {
            // 价格统计
            List<Double> prices = new ArrayList<>();
            for (Map<String, Object> p : products) {
                double price = (double) p.getOrDefault("price", 0.0);
                if (price > 1000) { // 过滤掉一些附件或低价干扰
                    prices.add(price);
                }
            }

            if (!prices.isEmpty()) {
                double min = Collections.min(prices);
                double max = Collections.max(prices);
                double avg = prices.stream().mapToDouble(Double::doubleValue).average().orElse(0.0);

                System.out.println("\n价格统计:");
                System.out.println("  最低价: ¥" + String.format("%.2f", min));
                System.out.println("  最高价: ¥" + String.format("%.2f", max));
                System.out.println("  平均价: ¥" + String.format("%.2f", avg));
            }

            // 打印价格前10的商品
            System.out.println("\n价格最低的10个笔记本商品:");
            List<Map<String, Object>> sorted = new ArrayList<>(products);
            sorted.sort(Comparator.comparingDouble(p -> {
                double price = (double) p.getOrDefault("price", 0.0);
                return price > 1000 ? price : Double.MAX_VALUE;
            }));

            for (int i = 0; i < Math.min(10, sorted.size()); i++) {
                Map<String, Object> p = sorted.get(i);
                double price = (double) p.getOrDefault("price", 0.0);
                if (price <= 1000) continue;
                String priceStr = String.format("¥%.2f", price);
                String name = (String) p.get("name");
                String shopType = (String) p.get("shop_type");
                System.out.println("  " + (i + 1) + ". " + priceStr + " - " +
                    (name.length() > 60 ? name.substring(0, 60) : name) + " (" + shopType + ")");
            }
        }

        System.out.println("============================================================");
    }

    /**
     * 运行爬虫
     */
    public void run() {
        System.out.println("\n开始爬取苹果笔记本...");

        for (String keyword : KEYWORDS) {
            System.out.println("\n搜索关键词: " + keyword);

            for (int page = 1; page <= maxPages; page++) {
                System.out.println("  爬取第 " + page + " 页...");

                int skip = (page - 1) * 30 + 1;
                String url = String.format(SEARCH_URL_TEMPLATE, keyword, keyword, skip);

                try {
                    Request request = new Request(url);
                    HttpClientDownloader downloader = new HttpClientDownloader();
                    Page pageObj = downloader.download(request, getSite());

                    if (pageObj == null || pageObj.isSkip()) {
                        System.out.println("  第 " + page + " 页获取失败");
                        totalErrors++;
                        break;
                    }

                    process(pageObj);
                    totalPages++;

                    Thread.sleep(delayMs + (long)(Math.random() * 1000));

                } catch (Exception e) {
                    System.out.println("  第 " + page + " 页爬取失败: " + e.getMessage());
                    totalErrors++;
                    break;
                }
            }
        }
    }

    /**
     * 主方法
     */
    public static void main(String[] args) {
        JDAppleLaptopSpider spider = new JDAppleLaptopSpider();
        try {
            spider.run();
        } catch (Exception e) {
            System.err.println("爬虫运行失败: " + e.getMessage());
        } finally {
            try {
                spider.saveResults();
                spider.printStats();
            } catch (Exception e) {
                System.err.println("保存结果失败: " + e.getMessage());
            }
        }
    }
}
