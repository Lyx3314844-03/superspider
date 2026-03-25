package com.spider.javaspider.examples;

import com.spider.javaspider.enhanced.*;
import org.openqa.selenium.*;
import org.openqa.selenium.chrome.*;
import java.io.*;
import java.nio.file.*;
import java.time.*;
import java.util.*;
import java.util.regex.*;

/**
 * Java YouTube 单视频爬虫
 * 爬取单个 YouTube 视频的详细信息
 *
 * 目标视频：https://www.youtube.com/watch?v=aZGYAc5c6gw
 */
public class YouTubeVideoSpider extends YouTubeSpiderBase {

    private WebDriver driver;
    private boolean headless;
    private String html;

    // 视频信息类
    static class VideoDetail {
        public String title = "";
        public String channel = "";
        public String views = "";
        public String publishDate = "";
        public String description = "";
        public String duration = "";
        public String likes = "";
        public String url = "";

        @Override
        public String toString() {
            return "VideoDetail{" +
                "title='" + title + '\'' +
                ", channel='" + channel + '\'' +
                ", views='" + views + '\'' +
                ", publishDate='" + publishDate + '\'' +
                ", duration='" + duration + '\'' +
                ", likes='" + likes + '\'' +
                '}';
        }

        public Map<String, Object> toMap() {
            Map<String, Object> map = new HashMap<>();
            map.put("title", title);
            map.put("channel", channel);
            map.put("views", views);
            map.put("publishDate", publishDate);
            map.put("description", description);
            map.put("duration", duration);
            map.put("likes", likes);
            map.put("url", url);
            return map;
        }

        public String toJson() {
            StringBuilder json = new StringBuilder();
            json.append("{\n");
            json.append("  \"title\": \"").append(escapeJson(title)).append("\",\n");
            json.append("  \"channel\": \"").append(escapeJson(channel)).append("\",\n");
            json.append("  \"views\": \"").append(escapeJson(views)).append("\",\n");
            json.append("  \"publishDate\": \"").append(escapeJson(publishDate)).append("\",\n");
            json.append("  \"description\": \"").append(escapeJson(description)).append("\",\n");
            json.append("  \"duration\": \"").append(escapeJson(duration)).append("\",\n");
            json.append("  \"likes\": \"").append(escapeJson(likes)).append("\",\n");
            json.append("  \"url\": \"").append(escapeJson(url)).append("\"\n");
            json.append("}");
            return json.toString();
        }

        private String escapeJson(String value) {
            if (value == null) return "";
            return value
                .replace("\\", "\\\\")
                .replace("\"", "\\\"")
                .replace("\n", "\\n")
                .replace("\r", "\\r")
                .replace("\t", "\\t");
        }
    }

    public YouTubeVideoSpider(String videoUrl) {
        super(videoUrl);
        this.platform = "Java/javaspider";
        this.headless = true;
    }

    public YouTubeVideoSpider(String videoUrl, boolean headless) {
        super(videoUrl);
        this.platform = "Java/javaspider";
        this.headless = headless;
    }

    @Override
    protected void initialize() {
        System.out.println("🚀 启动浏览器 (Selenium)...");

        ChromeOptions options = new ChromeOptions();
        if (headless) {
            options.addArguments("--headless");
            options.addArguments("--disable-gpu");
        }
        options.addArguments("--no-sandbox");
        options.addArguments("--disable-dev-shm-usage");
        options.addArguments("--window-size=1920,1080");
        options.addArguments("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36");

        driver = new ChromeDriver(options);
        driver.manage().timeouts().pageLoadTimeout(Duration.ofSeconds(30));
        System.out.println("   ✓ 浏览器已启动");
    }

    @Override
    protected void navigate() {
        System.out.println("🌐 正在加载视频页面...");
        driver.get(playlistUrl);

        System.out.println("   ⏳ 等待页面加载...");
        try {
            Thread.sleep(5000);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }

        // 检查是否需要验证
        String pageSource = driver.getPageSource();
        if (pageSource.toLowerCase().contains("just a moment")) {
            System.out.println("   ⚠️  检测到验证页面，等待绕过...");
            try {
                Thread.sleep(10000);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        }

        System.out.println("   ✓ 页面已加载");
    }

    @Override
    protected void waitAndScroll() {
        System.out.println("📜 滚动页面加载更多内容...");

        JavascriptExecutor js = (JavascriptExecutor) driver;

        // 滚动到描述区域
        for (int i = 0; i < 3; i++) {
            js.executeScript("window.scrollTo(0, document.body.scrollHeight)");
            try {
                Thread.sleep(1000);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        }

        // 滚动回顶部
        js.executeScript("window.scrollTo(0, 0)");
        try {
            Thread.sleep(500);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }

        System.out.println("   ✓ 滚动完成");
    }

    @Override
    protected void extractContent() throws IOException {
        System.out.println("📄 获取页面内容...");
        html = driver.getPageSource();

        // 保存 HTML 用于调试
        Files.writeString(Path.of("youtube_video_source.html"), html, java.nio.charset.StandardCharsets.UTF_8);
        System.out.println("   ✓ HTML 已保存到：youtube_video_source.html");
    }

    @Override
    protected void parseVideos() {
        System.out.println("🔍 解析视频信息...");

        VideoDetail video = parseVideoDetail();

        if (video != null) {
            System.out.println("   ✓ 成功解析视频信息");

            // 将视频信息添加到 results
            System.out.println("\n" + "═".repeat(60));
            System.out.println("                    视频信息");
            System.out.println("═".repeat(60));
            System.out.println("标题：" + video.title);
            System.out.println("频道：" + video.channel);
            System.out.println("观看次数：" + video.views);
            System.out.println("发布日期：" + video.publishDate);
            System.out.println("时长：" + video.duration);
            System.out.println("点赞：" + video.likes);
            System.out.println("URL: " + video.url);
            System.out.println("═".repeat(60));

            // 保存结果
            saveVideoDetail(video);
        } else {
            System.out.println("   ❌ 未找到视频信息");
        }
    }

    private VideoDetail parseVideoDetail() {
        VideoDetail video = new VideoDetail();
        video.url = playlistUrl;

        try {
            // 方法 1: 使用 JavaScript 提取
            JavascriptExecutor js = (JavascriptExecutor) driver;

            // 提取标题
            Object titleObj = js.executeScript(
                "return document.querySelector('h1.ytd-video-primary-info-renderer')?.textContent?.trim();"
            );
            if (titleObj != null) {
                video.title = titleObj.toString().trim();
            }

            // 提取频道名称
            Object channelObj = js.executeScript(
                "return document.querySelector('#channel-name #text')?.textContent?.trim();"
            );
            if (channelObj != null) {
                video.channel = channelObj.toString().trim();
            }

            // 提取观看次数
            Object viewsObj = js.executeScript(
                "return document.querySelector('.view-count-style')?.textContent?.trim() || " +
                "document.querySelector('ytd-video-view-count-renderer')?.textContent?.trim();"
            );
            if (viewsObj != null) {
                video.views = viewsObj.toString().trim();
            }

            // 提取发布日期
            Object dateObj = js.executeScript(
                "return document.querySelector('#info #info-text')?.textContent?.trim();"
            );
            if (dateObj != null) {
                String dateText = dateObj.toString().trim();
                // 提取日期部分
                if (dateText.contains("views")) {
                    String[] parts = dateText.split("•");
                    if (parts.length > 1) {
                        video.publishDate = parts[1].trim();
                    }
                } else {
                    video.publishDate = dateText;
                }
            }

            // 提取时长（从视频播放器）
            Object durationObj = js.executeScript(
                "return document.querySelector('.ytp-time-duration')?.textContent?.trim();"
            );
            if (durationObj != null) {
                video.duration = durationObj.toString().trim();
            }

            // 提取描述
            Object descObj = js.executeScript(
                "return document.querySelector('#description #text')?.textContent?.trim();"
            );
            if (descObj != null) {
                video.description = descObj.toString().trim();
            }

            // 备用方法：从 HTML 正则解析
            if (video.title.isEmpty()) {
                parseWithRegex(video);
            }

        } catch (Exception e) {
            System.out.println("   ❌ JavaScript 提取失败：" + e.getMessage());
            e.printStackTrace();
        }

        return video;
    }

    private void parseWithRegex(VideoDetail video) {
        System.out.println("   使用正则解析...");

        try {
            // 提取标题
            Pattern titlePattern = Pattern.compile("<title>([^<]+) - YouTube</title>");
            Matcher titleMatcher = titlePattern.matcher(html);
            if (titleMatcher.find()) {
                video.title = titleMatcher.group(1).trim();
            }

            // 提取频道
            Pattern channelPattern = Pattern.compile("\"channelName\":\\s*\"([^\"]+)\"");
            Matcher channelMatcher = channelPattern.matcher(html);
            if (channelMatcher.find()) {
                video.channel = channelMatcher.group(1).trim();
            }

        } catch (Exception e) {
            System.out.println("   正则解析失败：" + e.getMessage());
        }
    }

    private void saveVideoDetail(VideoDetail video) {
        try {
            // 保存为 JSON
            String jsonFilename = "youtube_video_" + System.currentTimeMillis() + ".json";
            Files.writeString(Path.of(jsonFilename), video.toJson(), java.nio.charset.StandardCharsets.UTF_8);
            System.out.println("💾 JSON 已保存到：" + jsonFilename);

            // 保存为 TXT
            String txtFilename = "youtube_video_" + System.currentTimeMillis() + ".txt";
            StringBuilder text = new StringBuilder();
            text.append("YouTube 视频信息\n");
            text.append("═".repeat(60)).append("\n\n");
            text.append("标题：").append(video.title).append("\n");
            text.append("频道：").append(video.channel).append("\n");
            text.append("观看次数：").append(video.views).append("\n");
            text.append("发布日期：").append(video.publishDate).append("\n");
            text.append("时长：").append(video.duration).append("\n");
            text.append("点赞：").append(video.likes).append("\n");
            text.append("URL: ").append(video.url).append("\n");
            if (!video.description.isEmpty()) {
                text.append("\n描述:\n").append(video.description).append("\n");
            }

            Files.writeString(Path.of(txtFilename), text.toString(), java.nio.charset.StandardCharsets.UTF_8);
            System.out.println("💾 TXT 已保存到：" + txtFilename);

        } catch (IOException e) {
            System.out.println("❌ 保存文件失败：" + e.getMessage());
        }
    }

    @Override
    protected void cleanup() {
        if (driver != null) {
            System.out.println("\n🔒 关闭浏览器...");
            driver.quit();
            System.out.println("   ✓ 浏览器已关闭");
        }
    }

    public static void main(String[] args) {
        // 目标视频 URL
        String videoUrl = "https://www.youtube.com/watch?v=aZGYAc5c6gw";

        System.out.println("\n" + "╔".repeat(30) + "╗");
        System.out.println("║".repeat(10) + " Java YouTube 视频爬虫 " + "║".repeat(10));
        System.out.println("╚".repeat(30) + "╝");
        System.out.println("\n📺 视频 URL: " + videoUrl + "\n");

        // 创建爬虫
        YouTubeVideoSpider spider = new YouTubeVideoSpider(videoUrl, true);

        try {
            // 启动爬虫
            spider.start();

            System.out.println("\n✅ 爬取完成!");

        } catch (Exception e) {
            System.out.println("\n❌ 爬取失败：" + e.getMessage());
            e.printStackTrace();
        } finally {
            spider.cleanup();
        }
    }
}
