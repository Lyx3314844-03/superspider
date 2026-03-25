import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.jsoup.nodes.Element;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;

/**
 * 简单的 YouTube 视频信息爬虫
 * 无需编译整个项目，独立运行
 */
public class SimpleYouTubeSpider {

    public static void main(String[] args) {
        String videoUrl = "https://www.youtube.com/watch?v=59JONAFPv9g&list=PLRuPQZBVD6vV89UKIzUwZFUhDx9DjXLxc&index=3";
        
        System.out.println("🕷️  YouTube 视频爬虫启动");
        System.out.println("═══════════════════════════════════════════════════════════");
        System.out.println("目标 URL: " + videoUrl);
        System.out.println();
        
        try {
            // 使用 HttpClient 获取页面
            HttpClient client = HttpClient.newBuilder()
                    .followRedirects(HttpClient.Redirect.NORMAL)
                    .build();
            
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(videoUrl))
                    .header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
                    .header("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8")
                    .header("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8")
                    .GET()
                    .build();
            
            System.out.println("正在请求 YouTube 页面...");
            HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
            
            if (response.statusCode() == 200) {
                System.out.println("页面获取成功!");
                System.out.println();
                
                // 解析 HTML
                parseYouTubePage(response.body());
            } else {
                System.err.println("请求失败，状态码：" + response.statusCode());
                System.err.println("YouTube 可能需要 JavaScript 渲染，建议使用浏览器方式访问");
            }
            
        } catch (Exception e) {
            System.err.println("爬取失败：" + e.getMessage());
            e.printStackTrace();
        }
    }

    /**
     * 解析 YouTube 页面 HTML
     */
    private static void parseYouTubePage(String html) {
        Document doc = Jsoup.parse(html);
        
        // 提取视频标题 - 从多个可能的选择器中查找
        String title = extractText(doc, "h1.ytd-video-primary-renderer");
        if (title == null) title = extractText(doc, "#title h1");
        if (title == null) title = extractText(doc, "title");
        
        // 提取视频 ID
        String videoId = extractVideoId(html);
        
        // 提取频道名称
        String channelName = extractText(doc, "#owner-name a");
        if (channelName == null) channelName = extractText(doc, "#channel-name #text-container");
        if (channelName == null) channelName = extractText(doc, "ytd-video-owner-renderer");
        
        // 提取观看次数
        String viewCount = extractText(doc, ".video-view-count");
        if (viewCount == null) viewCount = extractText(doc, "#count ytd-video-view-count-renderer");
        if (viewCount == null) viewCount = extractText(doc, "span.short-view-count");
        
        // 提取发布日期
        String publishDate = extractText(doc, "#info #info-text");
        if (publishDate == null) publishDate = extractText(doc, ".date");
        
        // 提取视频描述
        String description = extractText(doc, "#description #content-text");
        if (description == null) description = extractText(doc, "#eow-description");
        
        // 提取缩略图 URL
        String thumbnailUrl = extractAttr(doc, "meta[property=\"og:image\"]", "content");
        if (thumbnailUrl == null) {
            thumbnailUrl = extractAttr(doc, "link[itemprop=\"thumbnailUrl\"]", "href");
        }
        
        // 提取播放列表信息
        String playlistTitle = extractText(doc, "#playlist-title");
        if (playlistTitle == null) playlistTitle = extractText(doc, "h1#title");
        
        // 输出结果
        System.out.println("═══════════════════════════════════════════════════════════");
        System.out.println("                      YouTube 视频信息                      ");
        System.out.println("═══════════════════════════════════════════════════════════");
        System.out.println("✅ 视频标题：" + (title != null ? title : "未找到 (可能需要 JavaScript 渲染)"));
        System.out.println("🆔 视频 ID: " + (videoId != null ? videoId : "未找到"));
        System.out.println("📺 频道名称：" + (channelName != null ? channelName : "未找到"));
        System.out.println("👁️ 观看次数：" + (viewCount != null ? viewCount : "未找到"));
        System.out.println("📅 发布日期：" + (publishDate != null ? publishDate : "未找到"));
        System.out.println("🖼️ 缩略图：" + (thumbnailUrl != null ? thumbnailUrl : "未找到"));
        System.out.println("📋 播放列表：" + (playlistTitle != null ? playlistTitle : "未找到"));
        System.out.println();
        System.out.println("📝 视频描述:");
        System.out.println("───────────────────────────────────────────────────────────");
        System.out.println(description != null ? description : "未找到");
        System.out.println("───────────────────────────────────────────────────────────");
        System.out.println();
        
        // 提示
        System.out.println("💡 提示：");
        System.out.println("   YouTube 是动态网站，内容需要 JavaScript 渲染。");
        System.out.println("   如果以上信息不完整，建议使用以下方式:");
        System.out.println("   1. 使用 Selenium/Playwright 等浏览器自动化工具");
        System.out.println("   2. 使用 YouTube Data API 获取结构化数据");
        System.out.println();
        
        // 提取推荐视频
        extractRelatedVideos(doc);
    }

    /**
     * 从 HTML 中提取视频 ID
     */
    private static String extractVideoId(String html) {
        // 尝试从 URL 中提取
        int videoIndex = html.indexOf("\"videoId\"");
        if (videoIndex != -1) {
            int start = html.indexOf("\"", videoIndex + 10) + 1;
            int end = html.indexOf("\"", start);
            if (start > 0 && end > start) {
                return html.substring(start, end);
            }
        }
        return null;
    }

    /**
     * 提取相关推荐视频
     */
    private static void extractRelatedVideos(Document doc) {
        System.out.println("═══════════════════════════════════════════════════════════");
        System.out.println("                      推荐视频 (如有)                       ");
        System.out.println("═══════════════════════════════════════════════════════════");
        
        int count = 0;
        for (Element video : doc.select("ytd-compact-video-renderer")) {
            String videoTitle = extractText(video, "#video-title");
            String videoChannel = extractText(video, "#channel-name a, #channel-name #text");
            
            if (videoTitle != null && count < 10) {
                count++;
                System.out.println(count + ". " + videoTitle);
                System.out.println("   频道：" + (videoChannel != null ? videoChannel : "未知"));
                System.out.println();
            }
        }
        
        if (count == 0) {
            System.out.println("未找到推荐视频 (页面可能需要 JavaScript 渲染)");
        }
        System.out.println();
    }

    /**
     * 提取文本内容
     */
    private static String extractText(Document doc, String selector) {
        Element element = doc.selectFirst(selector);
        return element != null ? element.text().trim() : null;
    }

    /**
     * 提取元素文本
     */
    private static String extractText(Element element, String selector) {
        Element found = element.selectFirst(selector);
        return found != null ? found.text().trim() : null;
    }

    /**
     * 提取属性值
     */
    private static String extractAttr(Document doc, String selector, String attr) {
        Element element = doc.selectFirst(selector);
        return element != null ? element.attr(attr) : null;
    }
}
