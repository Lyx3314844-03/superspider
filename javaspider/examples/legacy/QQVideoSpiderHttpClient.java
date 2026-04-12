package com.javaspider.examples;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.jsoup.nodes.Element;

/**
 * 腾讯视频爬虫示例（使用 HttpClient）
 * 爬取 URL: https://v.qq.com/x/page/l3134b6lp72.html
 * 
 * 这个版本使用纯 HTTP 请求，不需要浏览器
 */
@Deprecated(since = "2.1.0", forRemoval = false)
public class QQVideoSpiderHttpClient {

    public static void main(String[] args) {
        String targetUrl = "https://v.qq.com/x/page/l3134b6lp72.html";

        System.out.println("🕷️  腾讯视频爬虫启动（HttpClient 版本）");
        System.out.println("═══════════════════════════════════════════════════════════");
        System.out.println("目标 URL: " + targetUrl);
        System.out.println();

        try {
            // 创建 HttpClient
            HttpClient client = HttpClient.newBuilder()
                    .followRedirects(HttpClient.Redirect.NORMAL)
                    .connectTimeout(Duration.ofSeconds(30))
                    .build();

            // 创建请求
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(targetUrl))
                    .timeout(Duration.ofSeconds(60))
                    .header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
                    .header("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8")
                    .header("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8")
                    .header("Accept-Encoding", "gzip, deflate")
                    .header("Upgrade-Insecure-Requests", "1")
                    .GET()
                    .build();

            System.out.println("正在请求腾讯视频页面...");
            HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());

            int statusCode = response.statusCode();
            System.out.println("响应状态码：" + statusCode);

            if (statusCode == 200) {
                String html = response.body();
                System.out.println("页面获取成功！");
                System.out.println("页面大小：" + html.length() + " 字节");
                System.out.println();

                // 解析 HTML
                parseVideoPage(html, targetUrl);

                // 保存原始 HTML
                saveHtml(html, "./qq_video_raw.html");
            } else if (statusCode == 302 || statusCode == 301) {
                String location = response.headers().firstValue("Location").orElse("未知");
                System.out.println("重定向到：" + location);
                System.out.println("腾讯视频可能需要登录或使用 Cookie 才能访问");
            } else {
                System.err.println("请求失败，状态码：" + statusCode);
                System.out.println("\n提示：");
                System.out.println("1. 腾讯视频可能需要登录才能访问");
                System.out.println("2. 可能需要使用 Cookie");
                System.out.println("3. 可能需要使用浏览器自动化（Playwright 版本）");
            }

        } catch (Exception e) {
            System.err.println("爬取失败：" + e.getMessage());
            e.printStackTrace();
        }

        System.out.println("\n爬取完成！");
    }

    /**
     * 解析视频页面
     */
    private static void parseVideoPage(String html, String url) {
        try {
            System.out.println("\n═══════════════════════════════════════════════════════════");
            System.out.println("                      页面解析结果                          ");
            System.out.println("═══════════════════════════════════════════════════════════");

            Document doc = Jsoup.parse(html);

            // 提取页面标题
            String title = extractText(doc, "title");
            if (title == null) title = extractAttr(doc, "meta[property=\"og:title\"]", "content");

            // 提取视频描述
            String description = extractAttr(doc, "meta[name=\"description\"]", "content");
            if (description == null) description = extractAttr(doc, "meta[property=\"og:description\"]", "content");

            // 提取视频封面图
            String coverImage = extractAttr(doc, "meta[property=\"og:image\"]", "content");

            // 提取视频 ID（从 URL 中）
            String videoId = extractVideoId(url);

            // 尝试从 JSON 数据中提取信息
            String jsonInfo = extractJsonData(html);

            // 输出结果
            System.out.println("\n📺 视频信息:");
            System.out.println("───────────────────────────────────────────────────────────");
            System.out.println("✅ 视频 ID: " + (videoId != null ? videoId : "未找到"));
            System.out.println("📝 页面标题：" + (title != null ? title.substring(0, Math.min(100, title.length())) : "未找到"));
            System.out.println("📋 描述：" + (description != null ? description.substring(0, Math.min(100, description.length())) : "未找到"));
            System.out.println("🖼️  封面图：" + (coverImage != null ? coverImage : "未找到"));
            System.out.println("📄 JSON 数据：" + (jsonInfo != null ? "已找到" : "未找到"));
            System.out.println("───────────────────────────────────────────────────────────");

            // 检查是否是重定向页面或错误页面
            if (title != null && (title.contains("404") || title.contains("错误") || title.contains("不存在"))) {
                System.out.println("\n⚠️  警告：页面可能不存在或已删除");
            }

            // 保存数据到文件
            saveToFile(videoId, title, description, coverImage, url);

        } catch (Exception e) {
            System.err.println("解析页面时出错：" + e.getMessage());
            e.printStackTrace();
        }
    }

    /**
     * 从 HTML 中提取视频 ID
     */
    private static String extractVideoId(String url) {
        if (url == null) return null;
        String[] parts = url.split("/");
        String lastPart = parts[parts.length - 1];
        return lastPart.replace(".html", "");
    }

    /**
     * 从 HTML 中提取 JSON 数据
     */
    private static String extractJsonData(String html) {
        if (html == null) return null;

        // 尝试查找页面配置数据
        int configIndex = html.indexOf("\"vid\"");
        if (configIndex != -1) {
            return "视频配置数据已找到";
        }

        return null;
    }

    /**
     * 提取文本内容
     */
    private static String extractText(Document doc, String selector) {
        Element element = doc.selectFirst(selector);
        return element != null ? element.text().trim() : null;
    }

    /**
     * 提取属性值
     */
    private static String extractAttr(Document doc, String selector, String attr) {
        Element element = doc.selectFirst(selector);
        return element != null ? element.attr(attr) : null;
    }

    /**
     * 保存数据到文件
     */
    private static void saveToFile(String videoId, String title, String description, 
                                   String coverImage, String url) {
        try {
            String filename = "./qq_video_" + (videoId != null ? videoId : "unknown") + "_info.txt";
            java.io.PrintWriter writer = new java.io.PrintWriter(filename, "UTF-8");
            
            writer.println("═══════════════════════════════════════════════════════════");
            writer.println("                      腾讯视频信息                          ");
            writer.println("═══════════════════════════════════════════════════════════");
            writer.println("URL: " + url);
            writer.println("视频 ID: " + (videoId != null ? videoId : "未找到"));
            writer.println("标题：" + (title != null ? title : "未找到"));
            writer.println("描述：" + (description != null ? description : "未找到"));
            writer.println("封面图：" + (coverImage != null ? coverImage : "未找到"));
            writer.println("═══════════════════════════════════════════════════════════");
            writer.println("\n注意：");
            writer.println("- 腾讯视频是动态网站，可能需要 JavaScript 渲染才能看到完整内容");
            writer.println("- 如果需要提取视频播放地址，可能需要使用 Playwright 版本");
            writer.println("- 某些视频可能需要登录或 VIP 才能访问");
            
            writer.close();
            System.out.println("\n数据已保存到：" + filename);
        } catch (Exception e) {
            System.err.println("保存文件失败：" + e.getMessage());
        }
    }

    /**
     * 保存 HTML 到文件
     */
    private static void saveHtml(String html, String filename) {
        try {
            java.io.PrintWriter writer = new java.io.PrintWriter(filename, "UTF-8");
            writer.println(html);
            writer.close();
            System.out.println("原始 HTML 已保存到：" + filename);
        } catch (Exception e) {
            System.err.println("保存 HTML 失败：" + e.getMessage());
        }
    }
}
