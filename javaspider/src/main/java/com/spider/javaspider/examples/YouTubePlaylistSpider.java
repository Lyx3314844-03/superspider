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
 * Java YouTube 播放列表爬虫 - 增强版
 * 使用统一的爬虫基类，支持多种输出格式
 * 
 * 目标播放列表：{@code https://www.youtube.com/watch?v=tr5yZ2TzXaY&amp;list=PLRuPQZBVD6vV89UKIzUwZFUhDx9DjXLxc}
 */
public class YouTubePlaylistSpider extends YouTubeSpiderBase {
    
    private WebDriver driver;
    private boolean headless;
    private String html;
    
    public YouTubePlaylistSpider(String playlistUrl) {
        super(playlistUrl);
        this.platform = "Java/javaspider";
        this.headless = true;
    }
    
    public YouTubePlaylistSpider(String playlistUrl, boolean headless) {
        super(playlistUrl);
        this.platform = "Java/javaspider";
        this.headless = headless;
    }
    
    @Override
    protected void initialize() {
        System.out.println("🚀 启动浏览器 (Selenium)...");
        
        ChromeOptions options = new ChromeOptions();
        if (headless) {
            options.addArguments("--headless");
        }
        options.addArguments("--no-sandbox");
        options.addArguments("--disable-dev-shm-usage");
        options.addArguments("--disable-gpu");
        
        driver = new ChromeDriver(options);
        driver.manage().timeouts().pageLoadTimeout(Duration.ofSeconds(30));
        System.out.println("   ✓ 浏览器已启动");
    }
    
    @Override
    protected void navigate() {
        System.out.println("🌐 正在加载播放列表页面...");
        driver.get(playlistUrl);
        
        System.out.println("   ⏳ 等待页面加载...");
        sleep(5000);
        
        // 检查是否需要验证
        String pageSource = driver.getPageSource();
        if (pageSource.toLowerCase().contains("just a moment")) {
            System.out.println("   ⚠️  检测到验证页面，等待绕过...");
            sleep(10000);
        }
        
        System.out.println("   ✓ 页面已加载");
    }
    
    @Override
    protected void waitAndScroll() {
        System.out.println("📜 滚动加载所有视频...");
        
        JavascriptExecutor js = (JavascriptExecutor) driver;
        
        for (int i = 0; i < 10; i++) {
            // 滚动到底部
            js.executeScript("window.scrollTo(0, document.body.scrollHeight)");
            sleep(1000);
            
            // 滚动回顶部
            js.executeScript("window.scrollTo(0, 0)");
            sleep(500);
            
            System.out.println("   滚动 " + (i + 1) + "/10");
        }
        
        sleep(2000);
        System.out.println("   ✓ 滚动完成");
    }
    
    @Override
    protected void extractContent() throws IOException {
        System.out.println("📄 获取页面内容...");
        html = driver.getPageSource();
        
        // 保存 HTML 用于调试
        Files.writeString(Path.of("youtube_playlist_source.html"), html, java.nio.charset.StandardCharsets.UTF_8);
        System.out.println("   ✓ HTML 已保存到：youtube_playlist_source.html");
    }
    
    @Override
    protected void parseVideos() {
        System.out.println("🔍 解析视频信息...");
        
        // 方法 1: 正则解析
        videos = parseWithRegex();
        
        // 方法 2: 如果正则失败，尝试 JavaScript
        if (videos.isEmpty()) {
            System.out.println("   尝试使用 JavaScript 提取...");
            videos = extractWithJs();
        }
        
        System.out.println("   ✓ 共解析 " + videos.size() + " 个视频");
    }
    
    private List<VideoItem> parseWithRegex() {
        List<VideoItem> videos = new ArrayList<>();
        Set<String> seenTitles = new HashSet<>();
        
        // 查找所有视频项
        Pattern pattern = Pattern.compile("<ytd-playlist-panel-video-renderer[^>]*>.*?</ytd-playlist-panel-video-renderer>", Pattern.DOTALL);
        Matcher matcher = pattern.matcher(html);
        
        int count = 0;
        while (matcher.find()) {
            count++;
        }
        System.out.println("   找到 " + count + " 个视频元素");
        
        matcher.reset();
        while (matcher.find()) {
            try {
                String videoElem = matcher.group();
                VideoItem video = new VideoItem();
                
                // 提取标题
                Pattern titlePattern = Pattern.compile("id=\"video-title\"[^>]*>([^<]+)</span>");
                Matcher titleMatcher = titlePattern.matcher(videoElem);
                if (titleMatcher.find()) {
                    video.setTitle(titleMatcher.group(1).trim());
                }
                
                // 提取 URL
                Pattern urlPattern = Pattern.compile("href=\"([^\"]*watch\\?v=[^\"]*)\"");
                Matcher urlMatcher = urlPattern.matcher(videoElem);
                if (urlMatcher.find()) {
                    video.setUrl(urlMatcher.group(1).replace("&amp;", "&"));
                }
                
                // 提取频道
                Pattern channelPattern = Pattern.compile("id=\"byline\"[^>]*>([^<]+)</span>");
                Matcher channelMatcher = channelPattern.matcher(videoElem);
                if (channelMatcher.find()) {
                    video.setChannel(channelMatcher.group(1).trim());
                }
                
                // 跳过重复或空标题
                if (video.getTitle() == null || video.getTitle().isEmpty() || seenTitles.contains(video.getTitle())) {
                    continue;
                }
                seenTitles.add(video.getTitle());
                
                video.setIndex(videos.size() + 1);
                videos.add(video);
                
            } catch (Exception e) {
                continue;
            }
        }
        
        return videos;
    }
    
    @SuppressWarnings("unchecked")
    private List<VideoItem> extractWithJs() {
        List<VideoItem> videos = new ArrayList<>();
        
        try {
            JavascriptExecutor js = (JavascriptExecutor) driver;
            
            String script = 
                "const videos = [];" +
                "const videoElements = document.querySelectorAll('ytd-playlist-panel-video-renderer');" +
                "videoElements.forEach((elem, index) => {" +
                "  const titleElem = elem.querySelector('#video-title');" +
                "  const urlElem = elem.querySelector('a#wc-endpoint');" +
                "  const durationElem = elem.querySelector('span.ytd-thumbnail-overlay-time-status-renderer');" +
                "  const channelElem = elem.querySelector('#byline');" +
                "  if (titleElem || urlElem) {" +
                "    videos.push({" +
                "      index: index + 1," +
                "      title: titleElem ? titleElem.textContent.trim() : ''," +
                "      url: urlElem ? urlElem.href : ''," +
                "      duration: durationElem ? durationElem.textContent.trim() : ''," +
                "      channel: channelElem ? channelElem.textContent.trim() : ''" +
                "    });" +
                "  }" +
                "});" +
                "return videos;";
            
            List<Map<String, Object>> videoData = (List<Map<String, Object>>) js.executeScript(script);
            
            if (videoData != null) {
                for (Map<String, Object> data : videoData) {
                    VideoItem video = new VideoItem();
                    video.setIndex(((Number) data.get("index")).intValue());
                    video.setTitle(data.get("title").toString());
                    video.setUrl(data.get("url").toString());
                    video.setDuration(data.get("duration") != null ? data.get("duration").toString() : "");
                    video.setChannel(data.get("channel") != null ? data.get("channel").toString() : "");
                    
                    if (!video.getTitle().isEmpty()) {
                        videos.add(video);
                    }
                }
            }
        } catch (Exception e) {
            System.out.println("   JavaScript 提取失败：" + e.getMessage());
        }
        
        return videos;
    }
    
    @Override
    protected void cleanup() {
        if (driver != null) {
            System.out.println("\n🔒 关闭浏览器...");
            driver.quit();
            System.out.println("   ✓ 浏览器已关闭");
        }
    }
    
    private void sleep(long millis) {
        try {
            Thread.sleep(millis);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }
    
    public static void main(String[] args) {
        String playlistUrl = "https://www.youtube.com/watch?v=tr5yZ2TzXaY&list=PLRuPQZBVD6vV89UKIzUwZFUhDx9DjXLxc";
        
        // 创建爬虫
        YouTubePlaylistSpider spider = new YouTubePlaylistSpider(playlistUrl, true);
        
        // 启动爬虫
        List<VideoItem> videos = spider.start();
        
        if (!videos.isEmpty()) {
            System.out.println("\n✅ 爬取完成!");
            
            try {
                // 保存结果
                spider.saveToFile(null, "json");
                spider.saveToFile(null, "txt");
                spider.saveToFile(null, "csv");
            } catch (IOException e) {
                System.out.println("❌ 保存文件失败：" + e.getMessage());
            }
        } else {
            System.out.println("\n⚠️  未找到视频");
        }
    }
}
