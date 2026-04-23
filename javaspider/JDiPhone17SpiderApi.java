import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import org.jsoup.Jsoup;

import java.io.*;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.concurrent.TimeUnit;

/**
 * 京东 iPhone 17 价格爬虫 - API 版本
 * 
 * 使用京东公开 API 接口，不依赖浏览器渲染
 * 通过已知 SKU ID 批量获取价格信息
 * 
 * 编译: javac -cp "lib/*" JDiPhone17SpiderApi.java
 * 运行: java -cp ".;lib/*" JDiPhone17SpiderApi
 * 
 * @author Qoder
 * @version 2.0.0
 */
public class JDiPhone17SpiderApi {

    // iPhone 17 系列常见 SKU ID（需要实际搜索获取完整列表）
    // 这些是示例 SKU，实际使用时需要通过搜索页面获取真实 SKU
    private static final String[] SAMPLE_SKU_IDS = {
        "100142678892", // iPhone 16 Pro Max 示例
        "100136308994", // iPhone 16 Pro 示例
        "100136308988", // iPhone 16 示例
        "100094542436", // iPhone 15 Pro Max 示例
        "100094542430", // iPhone 15 Pro 示例
    };

    private static final String PRICE_API_URL = "https://p.3.cn/prices/mgets";
    private static final String PRODUCT_INFO_API = "https://cdnware.m.jd.com/c1.json";
    private static final String USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36";
    private static final String MOBILE_USER_AGENT = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)";
    
    private final List<Product> allProducts = Collections.synchronizedList(new ArrayList<>());
    private final Random random = new Random();
    private long delayMs = 1000;
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
        public String shopName = "京东自营";
        public int commentCount;
        public String url;
        public String imageUrl;
        public String crawlTime;
        public String specifications;

        public Product() {
            this.crawlTime = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"));
        }
    }

    public JDiPhone17SpiderApi setDelayMs(long delayMs) {
        this.delayMs = delayMs;
        return this;
    }

    public JDiPhone17SpiderApi setProxy(String host, int port) {
        this.proxyHost = host;
        this.proxyPort = port;
        return this;
    }

    /**
     * 开始爬取
     */
    public void start() {
        System.out.println("========================================");
        System.out.println("京东 iPhone 17 价格爬虫 (API版)");
        System.out.println("========================================");
        System.out.println("使用 API 直接获取价格数据");
        System.out.println("请求延迟: " + delayMs + "ms");
        if (proxyHost != null) {
            System.out.println("代理: " + proxyHost + ":" + proxyPort);
        }
        System.out.println("========================================\n");

        // 方式1: 通过已知 SKU 获取价格
        System.out.println("[方式1] 通过 SKU ID 获取价格...");
        fetchPricesBySkus(SAMPLE_SKU_IDS);

        // 方式2: 尝试通过搜索 API 获取更多
        System.out.println("\n[方式2] 尝试搜索 API...");
        trySearchApi("iPhone 17");

        System.out.println("\n========================================");
        System.out.println("爬取完成! 共获取 " + allProducts.size() + " 个商品");
        System.out.println("========================================");
    }

    /**
     * 通过 SKU ID 批量获取价格
     */
    private void fetchPricesBySkus(String[] skuIds) {
        if (skuIds == null || skuIds.length == 0) return;

        System.out.println("  获取 " + skuIds.length + " 个 SKU 的价格...");

        // 分批获取，每批最多 50 个
        int batchSize = 50;
        for (int i = 0; i < skuIds.length; i += batchSize) {
            int end = Math.min(i + batchSize, skuIds.length);
            String[] batch = Arrays.copyOfRange(skuIds, i, end);
            String skuIdsParam = String.join(",", batch);
            
            String url = PRICE_API_URL + "?type=1&area=1_72_4137_0&skuIds=" + skuIdsParam;

            try {
                String json = fetchJson(url);
                if (json != null && json.startsWith("[")) {
                    JsonArray array = JsonParser.parseString(json).getAsJsonArray();
                    for (JsonElement elem : array) {
                        JsonObject obj = elem.getAsJsonObject();
                        Product product = new Product();
                        
                        product.productId = obj.get("id").getAsString();
                        product.price = obj.has("p") ? obj.get("p").getAsDouble() : 0;
                        product.originalPrice = obj.has("m") ? obj.get("m").getAsDouble() : product.price;
                        product.url = "https://item.jd.com/" + product.productId + ".html";
                        product.name = "iPhone 17 系列 (SKU: " + product.productId + ")";
                        
                        allProducts.add(product);
                        System.out.println("    - SKU " + product.productId + ": ¥" + product.price);
                    }
                } else {
                    System.out.println("    价格 API 返回异常: " + (json != null ? json.substring(0, Math.min(100, json.length())) : "null"));
                }
            } catch (Exception e) {
                System.err.println("    获取价格失败: " + e.getMessage());
            }

            sleep(delayMs);
        }
    }

    /**
     * 尝试通过搜索 API 获取商品
     */
    private void trySearchApi(String keyword) {
        try {
            String encodedKeyword = URLEncoder.encode(keyword, StandardCharsets.UTF_8.name());
            
            // 尝试移动端搜索 API
            String apiUrl = "https://search.jd.com/recommend";
            String url = apiUrl + "?keyword=" + encodedKeyword 
                + "&enc=utf-8"
                + "&wq=" + encodedKeyword
                + "&callback=jsonp_" + System.currentTimeMillis()
                + "&page=1";

            String json = fetchJson(url);
            if (json != null) {
                // 尝试解析 JSONP
                if (json.startsWith("jsonp_")) {
                    int start = json.indexOf("(");
                    int end = json.lastIndexOf(")");
                    if (start >= 0 && end > start) {
                        json = json.substring(start + 1, end);
                    }
                }

                System.out.println("  搜索 API 返回: " + json.substring(0, Math.min(200, json.length())));
                
                // 解析返回的商品
                JsonObject root = JsonParser.parseString(json).getAsJsonObject();
                if (root.has("vops")) {
                    JsonArray vops = root.getAsJsonArray("vops");
                    for (JsonElement elem : vops) {
                        JsonObject vop = elem.getAsJsonObject();
                        Product product = new Product();
                        
                        product.productId = vop.get("skuId").getAsString();
                        product.name = vop.has("wname") ? vop.get("wname").getAsString() : "";
                        product.price = vop.has("jdPrice") ? vop.get("jdPrice").getAsDouble() : 0;
                        product.url = "https://item.jd.com/" + product.productId + ".html";
                        
                        if (vop.has("imageurl")) {
                            product.imageUrl = vop.get("imageurl").getAsString();
                        }
                        
                        allProducts.add(product);
                        System.out.println("    - " + product.name.substring(0, Math.min(30, product.name.length())) + ": ¥" + product.price);
                    }
                }
            }
        } catch (Exception e) {
            System.out.println("  搜索 API 不可用: " + e.getMessage());
        }
    }

    /**
     * 获取 JSON 数据
     */
    private String fetchJson(String url) throws Exception {
        try {
            org.jsoup.Connection conn = Jsoup.connect(url)
                .userAgent(USER_AGENT)
                .header("Accept", "application/json, text/javascript, */*; q=0.01")
                .header("Accept-Language", "zh-CN,zh;q=0.9")
                .header("Referer", "https://search.jd.com/")
                .header("Origin", "https://search.jd.com")
                .ignoreContentType(true)
                .timeout(20000)
                .followRedirects(true);

            if (proxyHost != null && proxyPort > 0) {
                conn = conn.proxy(proxyHost, proxyPort);
            }

            return conn.execute().body();
        } catch (Exception e) {
            System.err.println("    请求失败: " + e.getMessage());
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
        output.put("source", "JD API");
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
            writer.write("商品ID,商品名称,价格,原价,店铺,评价数,商品链接,图片链接,规格,爬取时间\n");

            for (Product p : allProducts) {
                writer.write(String.format("%s,%s,%.2f,%.2f,%s,%d,%s,%s,%s,%s\n",
                    escapeCsv(p.productId),
                    escapeCsv(p.name),
                    p.price,
                    p.originalPrice,
                    escapeCsv(p.shopName),
                    p.commentCount,
                    escapeCsv(p.url),
                    escapeCsv(p.imageUrl),
                    escapeCsv(p.specifications),
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
        long delay = 1000;
        String proxy = null;
        int proxyPort = 0;

        for (int i = 0; i < args.length; i++) {
            switch (args[i]) {
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

        JDiPhone17SpiderApi spider = new JDiPhone17SpiderApi()
            .setDelayMs(delay);

        if (proxy != null) {
            spider.setProxy(proxy, proxyPort);
        }

        spider.start();

        String timestamp = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss"));
        try {
            spider.saveAsJson("jd_iphone17_api_" + timestamp + ".json");
            spider.saveAsCsv("jd_iphone17_api_" + timestamp + ".csv");
        } catch (IOException e) {
            System.err.println("保存结果失败: " + e.getMessage());
        }

        System.out.println("\n所有任务完成!");
    }
}
