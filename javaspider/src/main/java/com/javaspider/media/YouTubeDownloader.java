package com.javaspider.media;

import com.javaspider.media.parser.VideoInfo;
import com.javaspider.media.parser.YouTubeParser;

import java.io.*;
import java.net.*;
import java.nio.file.*;
import java.util.*;

/**
 * YouTube 视频下载器
 * 支持下载 YouTube 视频到本地
 */
public class YouTubeDownloader {
    
    private final String outputDir;
    private final YouTubeParser parser;
    private final Map<String, String> headers;
    private final int timeout;
    
    /**
     * 创建 YouTube 下载器
     * @param outputDir 输出目录
     */
    public YouTubeDownloader(String outputDir) {
        this.outputDir = outputDir;
        this.parser = new YouTubeParser();
        this.headers = new HashMap<>();
        this.headers.put("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36");
        this.headers.put("Referer", "https://www.youtube.com/");
        this.timeout = 120000;
    }
    
    /**
     * 下载 YouTube 视频
     * @param url YouTube 视频 URL
     * @return 下载的文件路径，失败返回 null
     */
    public String download(String url) {
        return download(url, "best");
    }
    
    /**
     * 下载 YouTube 视频
     * @param url YouTube 视频 URL
     * @param quality 清晰度 (best, 1080p, 720p, 480p)
     * @return 下载的文件路径，失败返回 null
     */
    public String download(String url, String quality) {
        try {
            System.out.println("\n📺 YouTube 视频下载");
            System.out.println("═══════════════════════════════════════════════════");
            System.out.println("URL: " + url);
            
            // 解析视频
            System.out.println("\n正在解析视频...");
            VideoInfo videoInfo = parser.parse(url);
            
            if (videoInfo == null) {
                System.err.println("解析视频失败");
                return null;
            }
            
            // 显示视频信息
            System.out.println("\n视频信息:");
            System.out.println("  标题：" + videoInfo.getTitle());
            System.out.println("  作者：" + videoInfo.getAuthor());
            System.out.println("  时长：" + formatDuration(videoInfo.getDuration()));
            System.out.println("  可用格式：" + (videoInfo.getFormats() != null ? videoInfo.getFormats().size() : 0));
            
            // 选择格式
            Map<String, Object> format;
            if ("best".equals(quality)) {
                format = parser.getBestFormat(videoInfo);
            } else {
                format = parser.selectFormatByQuality(videoInfo, quality);
            }
            
            if (format == null) {
                System.err.println("未找到合适的视频格式");
                return null;
            }
            
            System.out.println("\n选择格式:");
            System.out.println("  质量：" + format.get("quality"));
            System.out.println("  分辨率：" + format.get("width") + "x" + format.get("height"));
            System.out.println("  编码：" + format.get("codecs"));
            
            // 创建输出目录
            Path outputDirPath = Paths.get(outputDir);
            if (!Files.exists(outputDirPath)) {
                Files.createDirectories(outputDirPath);
            }
            
            // 生成文件名
            String safeTitle = sanitizeFileName(videoInfo.getTitle());
            String videoId = videoInfo.getVideoId();
            String fileName = safeTitle + "_" + videoId + ".mp4";
            Path outputFile = outputDirPath.resolve(fileName);
            
            // 下载视频
            System.out.println("\n⬇️  正在下载...");
            String videoUrl = (String) format.get("url");
            boolean success = downloadFile(videoUrl, outputFile.toString());
            
            if (success) {
                System.out.println("\n═══════════════════════════════════════════════════");
                System.out.println("✅ 下载完成：" + outputFile.toString());
                return outputFile.toString();
            } else {
                System.err.println("\n下载失败");
                return null;
            }
            
        } catch (Exception e) {
            System.err.println("下载失败：" + e.getMessage());
            e.printStackTrace();
            return null;
        }
    }
    
    /**
     * 下载文件
     */
    private boolean downloadFile(String urlString, String outputPath) throws Exception {
        URL url = new URL(urlString);
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        
        conn.setRequestMethod("GET");
        conn.setConnectTimeout(timeout);
        conn.setReadTimeout(timeout);
        
        for (Map.Entry<String, String> entry : headers.entrySet()) {
            conn.setRequestProperty(entry.getKey(), entry.getValue());
        }
        
        int responseCode = conn.getResponseCode();
        if (responseCode != HttpURLConnection.HTTP_OK) {
            System.err.println("HTTP 错误：" + responseCode);
            return false;
        }
        
        long contentLength = conn.getContentLengthLong();
        
        try (InputStream in = conn.getInputStream();
             FileOutputStream out = new FileOutputStream(outputPath)) {
            
            byte[] buffer = new byte[8192];
            int bytesRead;
            long totalBytes = 0;
            
            while ((bytesRead = in.read(buffer)) != -1) {
                out.write(buffer, 0, bytesRead);
                totalBytes += bytesRead;
                
                // 显示进度
                if (contentLength > 0) {
                    int percent = (int) (totalBytes * 100 / contentLength);
                    System.out.print("\r进度：" + percent + "%");
                }
            }
        }
        
        System.out.println("\r进度：100%");
        return true;
    }
    
    /**
     * 清理文件名
     */
    private String sanitizeFileName(String fileName) {
        String invalidChars = "<>:\"/\\|？*";
        for (char c : invalidChars.toCharArray()) {
            fileName = fileName.replace(c, '_');
        }
        fileName = fileName.trim();
        if (fileName.length() > 100) {
            fileName = fileName.substring(0, 100);
        }
        return fileName;
    }
    
    /**
     * 格式化时长
     */
    private String formatDuration(int seconds) {
        int hours = seconds / 3600;
        int minutes = (seconds % 3600) / 60;
        int secs = seconds % 60;
        
        if (hours > 0) {
            return String.format("%02d:%02d:%02d", hours, minutes, secs);
        } else {
            return String.format("%02d:%02d", minutes, secs);
        }
    }
    
    /**
     * 获取解析器
     */
    public YouTubeParser getParser() {
        return parser;
    }
    
    /**
     * 主函数 - 命令行入口
     */
    public static void main(String[] args) {
        if (args.length < 1) {
            System.out.println("用法：java YouTubeDownloader <YouTube URL> [quality]");
            System.out.println("\n示例:");
            System.out.println("  java YouTubeDownloader https://www.youtube.com/watch?v=xxx");
            System.out.println("  java YouTubeDownloader https://www.youtube.com/watch?v=xxx 1080p");
            System.out.println("\n质量选项：best, 1080p, 720p, 480p");
            System.exit(1);
        }
        
        String url = args[0];
        String quality = args.length > 1 ? args[1] : "best";
        String outputDir = args.length > 2 ? args[2] : "./downloads";
        
        YouTubeDownloader downloader = new YouTubeDownloader(outputDir);
        String result = downloader.download(url, quality);
        
        if (result != null) {
            System.out.println("\n✓ 下载成功：" + result);
            System.exit(0);
        } else {
            System.err.println("\n✗ 下载失败");
            System.exit(1);
        }
    }
}
