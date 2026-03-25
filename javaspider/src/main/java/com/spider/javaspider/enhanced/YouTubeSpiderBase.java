package com.spider.javaspider.enhanced;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.time.*;
import java.time.format.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.regex.*;

/**
 * 增强型 YouTube 爬虫基类
 * 提供统一的爬虫接口和工具方法
 */
public abstract class YouTubeSpiderBase {
    
    protected String name = "youtube_spider";
    protected String platform = "Java";
    protected String playlistUrl;
    protected List<VideoItem> videos = new ArrayList<>();
    protected CrawlStats stats = new CrawlStats();
    protected Map<String, Object> settings = new HashMap<>();
    protected LocalDateTime startTime;
    protected LocalDateTime endTime;
    
    public YouTubeSpiderBase(String playlistUrl) {
        this.playlistUrl = playlistUrl;
    }
    
    public YouTubeSpiderBase(String playlistUrl, Map<String, Object> settings) {
        this.playlistUrl = playlistUrl;
        this.settings = settings;
    }
    
    /**
     * 启动爬虫（模板方法）
     */
    public List<VideoItem> start() {
        beforeStart();
        
        try {
            initialize();
            navigate();
            waitAndScroll();
            extractContent();
            parseVideos();
            afterExtract();
            
            calculateStats();
            printResults();
            
            return videos;
            
        } catch (Exception e) {
            onError(e);
            return Collections.emptyList();
            
        } finally {
            cleanup();
        }
    }
    
    protected void beforeStart() {
        startTime = LocalDateTime.now();
        stats.setStartTime(startTime.format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")));
        printHeader();
    }
    
    protected void printHeader() {
        System.out.println("\n" + "╔".repeat(30) + "╗");
        System.out.println("║".repeat(10) + " " + platform + " - YouTube 爬虫 " + "║".repeat(10));
        System.out.println("╚".repeat(30) + "╝");
        System.out.println("\n📺 播放列表：" + playlistUrl + "\n");
    }
    
    protected abstract void initialize() throws Exception;
    protected abstract void navigate() throws Exception;
    protected abstract void waitAndScroll() throws Exception;
    protected abstract void extractContent() throws Exception;
    protected abstract void parseVideos() throws Exception;
    
    protected void afterExtract() {
        endTime = LocalDateTime.now();
        stats.setEndTime(endTime.format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")));
        stats.setCrawlTime(Duration.between(startTime, endTime).getSeconds());
    }
    
    protected void calculateStats() {
        stats.setTotalVideos(videos.size());
        Set<String> channels = new HashSet<>();
        for (VideoItem video : videos) {
            if (video.getChannel() != null && !video.getChannel().isEmpty()) {
                channels.add(video.getChannel());
            }
        }
        stats.setUniqueChannels(channels.size());
    }
    
    protected void printResults() {
        System.out.println("\n" + "═".repeat(60));
        System.out.println(" " + " ".repeat(19) + "爬取结果");
        System.out.println("═".repeat(60));
        System.out.println("共找到 " + stats.getTotalVideos() + " 个视频");
        System.out.println("唯一频道数：" + stats.getUniqueChannels());
        System.out.println("爬取耗时：" + stats.getCrawlTime() + "秒");
        System.out.println("\n前 20 个视频:");
        
        for (int i = 0; i < Math.min(20, videos.size()); i++) {
            VideoItem video = videos.get(i);
            System.out.println("\n" + String.format("%2d", i+1) + ". " + video.getTitle());
            if (video.getDuration() != null && !video.getDuration().isEmpty()) {
                System.out.println("    ⏱️  时长：" + video.getDuration());
            }
            if (video.getChannel() != null && !video.getChannel().isEmpty()) {
                System.out.println("    👤  频道：" + video.getChannel());
            }
        }
        
        if (videos.size() > 20) {
            System.out.println("\n... 还有 " + (videos.size() - 20) + " 个视频");
        }
    }
    
    protected void onError(Exception error) {
        System.out.println("\n❌ 爬取失败：" + error.getMessage());
        error.printStackTrace();
    }
    
    protected void cleanup() {
        // 清理资源
    }
    
    /**
     * 保存到文件
     */
    public String saveToFile(String filename, String format) throws IOException {
        if (filename == null) {
            String timestamp = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss"));
            filename = "youtube_playlist_" + timestamp + "." + format;
        }
        
        switch (format.toLowerCase()) {
            case "json":
                saveJson(filename);
                break;
            case "txt":
                saveTxt(filename);
                break;
            case "csv":
                saveCsv(filename);
                break;
            default:
                throw new IllegalArgumentException("不支持的格式：" + format);
        }
        
        System.out.println("💾 结果已保存到：" + filename);
        return filename;
    }
    
    protected void saveJson(String filename) throws IOException {
        StringBuilder json = new StringBuilder();
        json.append("{\n");
        json.append("  \"playlist_url\": \"").append(playlistUrl).append("\",\n");
        json.append("  \"crawl_stats\": {\n");
        json.append("    \"total_videos\": ").append(stats.getTotalVideos()).append(",\n");
        json.append("    \"unique_channels\": ").append(stats.getUniqueChannels()).append(",\n");
        json.append("    \"crawl_time\": ").append(stats.getCrawlTime()).append(",\n");
        json.append("    \"start_time\": \"").append(stats.getStartTime()).append("\",\n");
        json.append("    \"end_time\": \"").append(stats.getEndTime()).append("\"\n");
        json.append("  },\n");
        json.append("  \"videos\": [\n");
        
        for (int i = 0; i < videos.size(); i++) {
            VideoItem video = videos.get(i);
            json.append("    ").append(video.toJson());
            if (i < videos.size() - 1) {
                json.append(",");
            }
            json.append("\n");
        }
        
        json.append("  ]\n");
        json.append("}\n");
        
        Files.writeString(Path.of(filename), json.toString(), StandardCharsets.UTF_8);
    }
    
    protected void saveTxt(String filename) throws IOException {
        StringBuilder text = new StringBuilder();
        text.append("YouTube 播放列表视频列表\n");
        text.append("═".repeat(60)).append("\n\n");
        text.append("播放列表 URL: ").append(playlistUrl).append("\n");
        text.append("爬取时间：").append(stats.getStartTime()).append("\n");
        text.append("视频总数：").append(stats.getTotalVideos()).append("\n");
        text.append("唯一频道数：").append(stats.getUniqueChannels()).append("\n");
        text.append("爬取耗时：").append(stats.getCrawlTime()).append("秒\n\n");
        text.append("═".repeat(60)).append("\n\n");
        
        for (int i = 0; i < videos.size(); i++) {
            VideoItem video = videos.get(i);
            text.append(i+1).append(". ").append(video.getTitle()).append("\n");
            if (video.getDuration() != null && !video.getDuration().isEmpty()) {
                text.append("   时长：").append(video.getDuration()).append("\n");
            }
            if (video.getChannel() != null && !video.getChannel().isEmpty()) {
                text.append("   频道：").append(video.getChannel()).append("\n");
            }
            if (video.getUrl() != null && !video.getUrl().isEmpty()) {
                text.append("   链接：").append(video.getUrl()).append("\n");
            }
            text.append("\n");
        }
        
        Files.writeString(Path.of(filename), text.toString(), StandardCharsets.UTF_8);
    }
    
    protected void saveCsv(String filename) throws IOException {
        StringBuilder csv = new StringBuilder();
        csv.append("index,title,duration,channel,url,thumbnail,views,published\n");
        
        for (int i = 0; i < videos.size(); i++) {
            VideoItem video = videos.get(i);
            csv.append(i+1).append(",");
            csv.append(escapeCsv(video.getTitle())).append(",");
            csv.append(escapeCsv(video.getDuration())).append(",");
            csv.append(escapeCsv(video.getChannel())).append(",");
            csv.append(escapeCsv(video.getUrl())).append(",");
            csv.append(escapeCsv(video.getThumbnail())).append(",");
            csv.append(escapeCsv(video.getViews())).append(",");
            csv.append(escapeCsv(video.getPublished())).append("\n");
        }
        
        Files.writeString(Path.of(filename), csv.toString(), StandardCharsets.UTF_8);
    }
    
    private String escapeCsv(String value) {
        if (value == null || value.isEmpty()) {
            return "";
        }
        if (value.contains(",") || value.contains("\"") || value.contains("\n")) {
            return "\"" + value.replace("\"", "\"\"") + "\"";
        }
        return value;
    }
    
    // Getters and Setters
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    
    public String getPlatform() { return platform; }
    public void setPlatform(String platform) { this.platform = platform; }
    
    public String getPlaylistUrl() { return playlistUrl; }
    public List<VideoItem> getVideos() { return Collections.unmodifiableList(videos); }
    public CrawlStats getStats() { return stats; }
}
