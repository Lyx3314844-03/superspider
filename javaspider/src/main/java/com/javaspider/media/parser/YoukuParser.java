package com.javaspider.media.parser;

import java.io.*;
import java.net.*;
import java.util.*;
import java.util.regex.*;

/**
 * 优酷视频解析器
 * 解析优酷视频的真实下载地址
 */
public class YoukuParser implements VideoParser {
    
    private static final String[] USER_AGENTS = {
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15"
    };
    
    @Override
    public boolean supports(String url) {
        return url.contains("youku") || url.contains("yk");
    }
    
    @Override
    public VideoInfo parse(String url) throws Exception {
        System.out.println("Parsing Youku video: " + url);
        
        // 1. 提取视频 ID
        String videoId = extractVideoId(url);
        if (videoId == null) {
            throw new Exception("Cannot extract video ID from URL");
        }
        
        System.out.println("Video ID: " + videoId);
        
        // 2. 获取视频信息
        String videoInfo = fetchVideoInfo(videoId);
        
        // 3. 解析视频信息
        return parseVideoInfo(videoInfo, url);
    }
    
    /**
     * 提取视频 ID
     */
    private String extractVideoId(String url) {
        // 格式：id_XXXXXXXX.html
        Pattern pattern = Pattern.compile("id_([A-Za-z0-9=]+)");
        Matcher matcher = pattern.matcher(url);
        
        if (matcher.find()) {
            return matcher.group(1);
        }
        
        return null;
    }
    
    /**
     * 获取视频信息
     */
    private String fetchVideoInfo(String videoId) throws Exception {
        // 构建 API URL
        String apiUrl = "https://openapi.youku.com/v2/videos/show.json?" +
                       "client_id=YOUR_CLIENT_ID&" +
                       "video_id=" + videoId;
        
        URL url = new URL(apiUrl);
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestProperty("User-Agent", USER_AGENTS[0]);
        conn.setConnectTimeout(10000);
        conn.setReadTimeout(10000);
        
        BufferedReader reader = new BufferedReader(
            new InputStreamReader(conn.getInputStream()));
        StringBuilder content = new StringBuilder();
        String line;
        
        while ((line = reader.readLine()) != null) {
            content.append(line);
        }
        
        reader.close();
        conn.disconnect();
        
        return content.toString();
    }
    
    /**
     * 解析视频信息
     */
    private VideoInfo parseVideoInfo(String json, String originalUrl) {
        VideoInfo info = new VideoInfo();
        info.setUrl(originalUrl);
        info.setPlatform("Youku");
        
        try {
            // 简单 JSON 解析（实际应该使用 JSON 库）
            info.setTitle(extractJsonString(json, "title"));
            info.setDescription(extractJsonString(json, "description"));
            
            // 提取播放次数
            String playCount = extractJsonString(json, "plays");
            if (playCount != null) {
                info.setViewCount(Integer.parseInt(playCount));
            }
            
            // 提取时长
            String duration = extractJsonString(json, "seconds");
            if (duration != null) {
                info.setDuration(Integer.parseInt(duration));
            }
            
            // 提取封面
            String cover = extractJsonString(json, "logo");
            info.setCoverUrl(cover);
            
            // 提取视频 URL（需要解密，这里简化处理）
            List<String> videoUrls = extractVideoUrls(json);
            info.setVideoUrls(videoUrls);
            
        } catch (Exception e) {
            System.err.println("Error parsing video info: " + e.getMessage());
        }
        
        return info;
    }
    
    /**
     * 提取视频 URL 列表
     */
    private List<String> extractVideoUrls(String json) {
        List<String> urls = new ArrayList<>();
        
        // 提取 stream_types
        // 实际实现需要解析 JSON 结构
        // 这里简化处理
        
        return urls;
    }
    
    /**
     * 提取 JSON 字符串
     */
    private String extractJsonString(String json, String key) {
        Pattern pattern = Pattern.compile("\"" + key + "\"\\s*:\\s*\"([^\"]+)\"");
        Matcher matcher = pattern.matcher(json);
        
        if (matcher.find()) {
            return matcher.group(1);
        }
        
        return null;
    }
    
    /**
     * 获取所有清晰度
     */
    public List<QualityOption> getQualityOptions(String url) throws Exception {
        List<QualityOption> options = new ArrayList<>();
        
        options.add(new QualityOption("流畅", "3gp", 270));
        options.add(new QualityOption("标清", "mp4", 480));
        options.add(new QualityOption("高清", "hd2", 720));
        options.add(new QualityOption("超清", "hd3", 1080));
        options.add(new QualityOption("蓝光", "hd4", 2160));
        
        return options;
    }
    
    /**
     * 清晰度选项类
     */
    public static class QualityOption {
        private String name;
        private String format;
        private int height;
        
        public QualityOption(String name, String format, int height) {
            this.name = name;
            this.format = format;
            this.height = height;
        }
        
        public String getName() { return name; }
        public String getFormat() { return format; }
        public int getHeight() { return height; }
        
        @Override
        public String toString() {
            return name + " (" + height + "p, " + format + ")";
        }
    }
}
