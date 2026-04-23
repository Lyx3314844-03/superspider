import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.jsoup.nodes.Element;
import org.jsoup.select.Elements;

import java.io.*;
import java.net.HttpURLConnection;
import java.net.URI;
import java.net.URL;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.concurrent.TimeUnit;

/**
 * 京东 iPhone 17 价格爬虫 - 独立版本
 * 
 * 不依赖 javaspider 框架，使用 Jsoup + Gson 独立运行
 * 
 * 编译: javac -cp "lib/*" JDiPhone17SpiderStandalone.java
 * 运行: java -cp ".;lib/*" JDiPhone17SpiderStandalone
 * 
 * @author Qoder
 * @version 1.0.0
 */
public class JDiPhone17SpiderStandalone {

    private static final String[] KEYWORDS = {"iPhone 15"};
    private static final String SEARCH_URL = "https://search.jd.com/Search";
    // 使用移动端 API，反爬较弱
    private static final String MOBILE_SEARCH_URL = "https://search.m.jd.com/search";
    private static final String PRICE_API_URL = "https://p.3.cn/prices/mgets";
    // 商品推荐 API
    private static final String RECOMMEND_API = "https://re.m.jd.com/recommend";
    private static final String USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36";
    private static final String MOBILE_USER_AGENT = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1";
    
    private final List<Product> allProducts = Collections.synchronizedList(new ArrayList<>());
    private final Random random = new Random();
    private int totalPages = 5;
    private long delayMs = 2000;
    private String proxyHost = null;
    private int proxyPort = 0;

    /**
     * 商品数据模型
     */
    public static class Product {
        public String productId;
        public String name;
        public double price;
        public double originalPrice;
        public String shopName;
        public int commentCount;
        public String url;
        public String imageUrl;
        public String crawlTime;

        public Product() {
            this.crawlTime = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"));
        }
    }

    public JDiPhone17SpiderStandalone setTotalPages(int pages) {
        this.totalPages = pages;
        return this;
    }

    public JDiPhone17SpiderStandalone setDelayMs(long delayMs) {
        this.delayMs = delayMs;
        return this;
    }

    public JDiPhone17SpiderStandalone setProxy(String host, int port) {
        this.proxyHost = host;
        this.proxyPort = port;
        return this;
    }

    /**
     * 开始爬取
     */
    public void start() {
        System.out.println("========================================");
        System.out.println("京东 iPhone 17 价格爬虫启动");
        System.out.println("========================================");
        System.out.println("搜索关键词: " + Arrays.toString(KEYWORDS));
        System.out.println("爬取页数: " + totalPages);
        System.out.println("请求延迟: " + delayMs + "ms");
        if (proxyHost != null) {
            System.out.println("代理: " + proxyHost + ":" + proxyPort);
        }
        System.out.println("========================================\n");

        for (String keyword : KEYWORDS) {
            System.out.println("\n[搜索] 关键词: " + keyword);
            searchKeyword(keyword);
        }

        System.out.println("\n========================================");
        System.out.println("爬取完成! 共获取 " + allProducts.size() + " 个商品");
        System.out.println("========================================");
    }

    /**
     * 搜索关键词
     */
    private void searchKeyword(String keyword) {
        for (int page = 1; page <= totalPages; page++) {
            int skip = (page - 1) * 30;
            
            // 尝试多种搜索方式
            boolean success = false;
            
            // 方式1: 尝试移动端搜索
            if (!success) {
                String mobileUrl = buildMobileSearchUrl(keyword, page);
                System.out.println("  [移动端页面 " + page + "/" + totalPages + "] " + mobileUrl);
                
                try {
                    Document doc = fetchPage(mobileUrl, true);
                    if (doc != null && doc.body() != null) {
                        String bodyText = doc.body().text();
                        // 检查是否包含商品信息或验证码页面
                        if (bodyText.contains("验证码") || bodyText.contains("verify") || bodyText.length() < 500) {
                            System.out.println("    触发验证码，跳过");
                        } else {
                            List<Product> products = parseMobileProducts(doc);
                            System.out.println("    发现 " + products.size() + " 个商品");
                            if (!products.isEmpty()) {
                                success = true;
                                processProducts(products);
                            }
                        }
                    }
                } catch (Exception e) {
                    System.err.println("    移动端搜索失败: " + e.getMessage());
                }
            }
            
            // 方式2: 尝试 PC 端搜索
            if (!success) {
                String pcUrl = buildSearchUrl(keyword, skip);
                System.out.println("  [PC页面 " + page + "/" + totalPages + "] " + pcUrl);
                
                try {
                    Document doc = fetchPage(pcUrl, false);
                    if (doc != null) {
                        List<Product> products = parseProducts(doc);
                        System.out.println("    发现 " + products.size() + " 个商品");
                        if (!products.isEmpty()) {
                            success = true;
                            processProducts(products);
                        }
                    }
                } catch (Exception e) {
                    System.err.println("    PC端搜索失败: " + e.getMessage());
                }
            }
            
            if (!success) {
                System.out.println("    所有方式都未获取到商品，停止翻页");
                break;
            }

            // 延迟
            if (page < totalPages) {
                sleep(delayMs + random.nextInt(1000));
            }
        }
    }

    /**
     * 处理商品数据
     */
    private void processProducts(List<Product> products) {
        // 批量获取价格
        List<String> skIds = new ArrayList<>();
        for (Product p : products) {
            if (p.productId != null && !p.productId.isEmpty()) {
                skIds.add(p.productId);
            }
        }
        
        if (!skIds.isEmpty()) {
            Map<String, Double> prices = getPrices(skIds);
            for (Product p : products) {
                if (p.productId != null && prices.containsKey(p.productId)) {
                    p.price = prices.get(p.productId);
                }
            }
        }

        // 去重后添加
        for (Product p : products) {
            boolean exists = allProducts.stream()
                .anyMatch(existing -> existing.productId.equals(p.productId));
            if (!exists) {
                allProducts.add(p);
            }
        }
    }

    /**
     * 构建搜索 URL
     */
    private String buildSearchUrl(String keyword, int skip) {
        try {
            String encodedKeyword = URLEncoder.encode(keyword, StandardCharsets.UTF_8.name());
            return SEARCH_URL + "?keyword=" + encodedKeyword 
                + "&enc=utf-8"
                + "&wq=" + encodedKeyword
                + "&s=" + skip;
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    /**
     * 构建移动端搜索 URL
     */
    private String buildMobileSearchUrl(String keyword, int page) {
        try {
            String encodedKeyword = URLEncoder.encode(keyword, StandardCharsets.UTF_8.name());
            int skip = (page - 1) * 30;
            return MOBILE_SEARCH_URL + "?keyword=" + encodedKeyword 
                + "&enc=utf-8"
                + "&wq=" + encodedKeyword
                + "&page=" + page
                + "&s=" + skip;
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    /**
     * 解析移动端商品列表
     */
    private List<Product> parseMobileProducts(Document doc) {
        List<Product> products = new ArrayList<>();
        
        // 尝试多种选择器
        String[] selectors = {
            ".list-item",
            ".goods-item", 
            ".product-item",
            "[class*='item']",
            ".gl-item"
        };
        
        Elements items = null;
        for (String selector : selectors) {
            items = doc.select(selector);
            if (!items.isEmpty()) {
                System.out.println("    使用选择器: " + selector + ", 找到 " + items.size() + " 个元素");
                break;
            }
        }
        
        if (items == null || items.isEmpty()) {
            // 如果选择器都失败，尝试从页面中提取 JSON 数据
            return parseProductsFromJson(doc);
        }
        
        for (Element item : items) {
            try {
                Product product = new Product();
                
                // 提取商品 ID
                String dataSku = item.attr("data-sku");
                if (dataSku.isEmpty()) {
                    Element link = item.selectFirst("a[href*='item.jd.com']");
                    if (link != null) {
                        String href = link.attr("href");
                        dataSku = extractSkuFromUrl(href);
                    }
                }
                product.productId = dataSku;

                // 提取商品名称
                Element nameElem = item.selectFirst("[class*='name'], .p-name em, em");
                if (nameElem != null) {
                    product.name = nameElem.text().trim();
                }

                // 提取价格
                Element priceElem = item.selectFirst("[class*='price'], .p-price strong");
                if (priceElem != null) {
                    String priceText = priceElem.attr("data-price");
                    if (priceText.isEmpty()) {
                        priceText = priceElem.text().replaceAll("[^0-9.]", "");
                    }
                    if (!priceText.isEmpty()) {
                        try {
                            product.originalPrice = Double.parseDouble(priceText);
                        } catch (NumberFormatException e) {
                            // ignore
                        }
                    }
                }

                // 提取链接
                Element linkElem = item.selectFirst("a[href*='item.jd.com']");
                if (linkElem != null) {
                    String href = linkElem.attr("href");
                    if (href.startsWith("//")) {
                        href = "https:" + href;
                    }
                    product.url = href;
                }

                if (product.productId != null && !product.productId.isEmpty()) {
                    products.add(product);
                }

            } catch (Exception e) {
                // 忽略单个商品解析错误
            }
        }

        return products;
    }

    /**
     * 从页面 JSON 数据中解析商品
     */
    private List<Product> parseProductsFromJson(Document doc) {
        List<Product> products = new ArrayList<>();
        
        // 查找包含商品数据的 script 标签
        Elements scripts = doc.select("script");
        for (Element script : scripts) {
            String text = script.html();
            if (text.contains("skuId") && (text.contains("price") || text.contains("name"))) {
                try {
                    // 尝试提取 JSON
                    int start = text.indexOf("{");
                    int end = text.lastIndexOf("}") + 1;
                    if (start >= 0 && end > start) {
                        String json = text.substring(start, end);
                        // 这里可以尝试解析 JSON，但由于格式不确定，先返回空
                        System.out.println("    发现可能的商品 JSON 数据");
                    }
                } catch (Exception e) {
                    // ignore
                }
            }
        }
        
        return products;
    }

    /**
     * 从 URL 中提取 SKU ID
     */
    private String extractSkuFromUrl(String url) {
        if (url == null || url.isEmpty()) return "";
        
        // 京东商品 URL 格式: https://item.jd.com/10074539475692.html
        int start = url.indexOf("/");
        if (start >= 0) {
            url = url.substring(start + 1);
        }
        int end = url.indexOf(".");
        if (end > 0) {
            return url.substring(0, end);
        }
        return url;
    }

    /**
     * 获取页面内容
     */
    private Document fetchPage(String url) throws Exception {
        return fetchPage(url, false);
    }

    /**
     * 获取页面内容（支持移动端）
     */
    private Document fetchPage(String url, boolean mobile) throws Exception {
        try {
            String ua = mobile ? MOBILE_USER_AGENT : USER_AGENT;
            org.jsoup.Connection conn = Jsoup.connect(url)
                .userAgent(ua)
                .header("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8")
                .header("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8,en-US;q=0.7")
                .header("Accept-Encoding", "gzip, deflate, br")
                .header("Connection", "keep-alive")
                .header("Upgrade-Insecure-Requests", "1")
                .header("Sec-Fetch-Dest", "document")
                .header("Sec-Fetch-Mode", "navigate")
                .header("Sec-Fetch-Site", "none")
                .header("Sec-Ch-Ua", "\"Not_A Brand\";v=\"8\", \"Chromium\";v=\"120\", \"Google Chrome\";v=\"120\"")
                .header("Sec-Ch-Ua-Mobile", mobile ? "?1" : "?0")
                .header("Sec-Ch-Ua-Platform", mobile ? "\"iPhone\"" : "\"Windows\"")
                .cookie("thor", "random_token_" + System.currentTimeMillis())
                .timeout(30000)
                .followRedirects(true)
                .maxBodySize(0);

            if (proxyHost != null && proxyPort > 0) {
                conn = conn.proxy(proxyHost, proxyPort);
            }

            return conn.get();
        } catch (Exception e) {
            System.err.println("    请求失败: " + e.getMessage());
            return null;
        }
    }

    /**
     * 解析商品列表
     */
    private List<Product> parseProducts(Document doc) {
        List<Product> products = new ArrayList<>();
        
        Elements items = doc.select("#J_goodsList .gl-item");
        
        for (Element item : items) {
            try {
                Product product = new Product();
                
                // 提取商品 ID
                String dataSku = item.attr("data-sku");
                if (dataSku.isEmpty()) {
                    dataSku = item.selectFirst(".j-sku-item").attr("data-sku");
                }
                product.productId = dataSku;

                // 提取商品名称
                Element nameElem = item.selectFirst(".p-name a em");
                if (nameElem != null) {
                    product.name = nameElem.text().trim();
                }

                // 提取价格占位符 (实际价格通过 API 获取)
                Element priceElem = item.selectFirst(".p-price strong");
                if (priceElem != null) {
                    String priceText = priceElem.attr("data-price");
                    if (!priceText.isEmpty()) {
                        try {
                            product.originalPrice = Double.parseDouble(priceText);
                        } catch (NumberFormatException e) {
                            // ignore
                        }
                    }
                }

                // 提取店铺名称
                Element shopElem = item.selectFirst(".p-shop a");
                if (shopElem != null) {
                    product.shopName = shopElem.text().trim();
                }

                // 提取评价数
                Element commentElem = item.selectFirst(".p-commit strong a");
                if (commentElem != null) {
                    String commentText = commentElem.text().trim();
                    product.commentCount = parseCommentCount(commentText);
                }

                // 提取商品链接
                Element linkElem = item.selectFirst(".p-name a");
                if (linkElem != null) {
                    String href = linkElem.attr("href");
                    if (href.startsWith("//")) {
                        href = "https:" + href;
                    }
                    product.url = href;
                }

                // 提取图片链接
                Element imgElem = item.selectFirst(".p-img img");
                if (imgElem != null) {
                    String src = imgElem.attr("data-lazy-img")
                        .isEmpty() ? imgElem.attr("src") : imgElem.attr("data-lazy-img");
                    if (src.startsWith("//")) {
                        src = "https:" + src;
                    }
                    product.imageUrl = src;
                }

                if (product.productId != null && !product.productId.isEmpty()) {
                    products.add(product);
                }

            } catch (Exception e) {
                // 忽略单个商品解析错误
            }
        }

        return products;
    }

    /**
     * 解析评价数量
     */
    private int parseCommentCount(String text) {
        if (text == null || text.isEmpty()) return 0;
        
        text = text.replaceAll("[+万]", "").trim();
        try {
            double num = Double.parseDouble(text);
            if (text.contains("万")) {
                return (int) (num * 10000);
            }
            return (int) num;
        } catch (NumberFormatException e) {
            return 0;
        }
    }

    /**
     * 批量获取价格
     */
    private Map<String, Double> getPrices(List<String> skIds) {
        Map<String, Double> result = new HashMap<>();
        
        if (skIds.isEmpty()) return result;

        // 分批获取，每批最多 50 个 SKU
        int batchSize = 50;
        for (int i = 0; i < skIds.size(); i += batchSize) {
            int end = Math.min(i + batchSize, skIds.size());
            List<String> batch = skIds.subList(i, end);
            
            String skuIdsParam = String.join(",", batch);
            String url = PRICE_API_URL + "?type=1&area=1_72_4137_0&skuIds=" + skuIdsParam;

            try {
                String json = fetchJson(url);
                if (json != null) {
                    JsonArray array = JsonParser.parseString(json).getAsJsonArray();
                    for (JsonElement elem : array) {
                        JsonObject obj = elem.getAsJsonObject();
                        String id = obj.get("id").getAsString();
                        double price = obj.has("p") ? obj.get("p").getAsDouble() : 0;
                        result.put(id, price);
                    }
                }
            } catch (Exception e) {
                System.err.println("    获取价格失败: " + e.getMessage());
            }

            sleep(500 + random.nextInt(500));
        }

        return result;
    }

    /**
     * 获取 JSON 数据
     */
    private String fetchJson(String url) throws Exception {
        try {
            org.jsoup.Connection conn = Jsoup.connect(url)
                .userAgent(USER_AGENT)
                .header("Referer", "https://search.jd.com/")
                .ignoreContentType(true)
                .timeout(20000);

            if (proxyHost != null && proxyPort > 0) {
                conn = conn.proxy(proxyHost, proxyPort);
            }

            return conn.execute().body();
        } catch (Exception e) {
            System.err.println("    请求 JSON 失败: " + e.getMessage());
            return null;
        }
    }

    /**
     * 保存结果为 JSON
     */
    public void saveAsJson(String filename) throws IOException {
        Gson gson = new GsonBuilder()
            .setPrettyPrinting()
            .setDateFormat("yyyy-MM-dd HH:mm:ss")
            .create();

        Map<String, Object> output = new LinkedHashMap<>();
        output.put("total", allProducts.size());
        output.put("crawlTime", LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")));
        output.put("products", allProducts);

        String json = gson.toJson(output);
        Files.writeString(Path.of(filename), json, StandardCharsets.UTF_8);
        System.out.println("结果已保存到: " + filename);
    }

    /**
     * 保存结果为 CSV
     */
    public void saveAsCsv(String filename) throws IOException {
        try (BufferedWriter writer = Files.newBufferedWriter(Path.of(filename), StandardCharsets.UTF_8)) {
            // 写入表头
            writer.write("商品ID,商品名称,价格,原价,店铺,评价数,商品链接,图片链接,爬取时间\n");

            // 写入数据
            for (Product p : allProducts) {
                writer.write(String.format("%s,%s,%.2f,%.2f,%s,%d,%s,%s,%s\n",
                    escapeCsv(p.productId),
                    escapeCsv(p.name),
                    p.price,
                    p.originalPrice,
                    escapeCsv(p.shopName),
                    p.commentCount,
                    escapeCsv(p.url),
                    escapeCsv(p.imageUrl),
                    p.crawlTime
                ));
            }
        }
        System.out.println("结果已保存到: " + filename);
    }

    private String escapeCsv(String value) {
        if (value == null) return "";
        if (value.contains(",") || value.contains("\"") || value.contains("\n")) {
            return "\"" + value.replace("\"", "\"\"") + "\"";
        }
        return value;
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
        // 解析命令行参数
        int pages = 5;
        long delay = 2000;
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
                        String proxyStr = args[++i];
                        String[] parts = proxyStr.split(":");
                        if (parts.length == 2) {
                            proxy = parts[0];
                            proxyPort = Integer.parseInt(parts[1]);
                        }
                    }
                    break;
            }
        }

        // 创建并运行爬虫
        JDiPhone17SpiderStandalone spider = new JDiPhone17SpiderStandalone()
            .setTotalPages(pages)
            .setDelayMs(delay);

        if (proxy != null) {
            spider.setProxy(proxy, proxyPort);
        }

        spider.start();

        // 保存结果
        String timestamp = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss"));
        try {
            spider.saveAsJson("jd_iphone17_" + timestamp + ".json");
            spider.saveAsCsv("jd_iphone17_" + timestamp + ".csv");
        } catch (IOException e) {
            System.err.println("保存结果失败: " + e.getMessage());
        }

        System.out.println("\n所有任务完成!");
    }
}
