package com.spider.javaspider.media;

import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.*;
import java.time.*;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.concurrent.*;

/**
 * Java 多媒体下载模块
 * 支持视频、图片、音乐批量下载
 */

// 媒体项基类
abstract class MediaItem {
    public String id;
    public String title;
    public String url;
    public String thumbnail;
    public String duration;
    public long size;
    public String format;
    public String quality;
    public boolean downloaded;
    public String downloadPath;
    public String error;
    
    public Map<String, Object> toMap() {
        Map<String, Object> map = new HashMap<>();
        map.put("id", id);
        map.put("title", title);
        map.put("url", url);
        map.put("thumbnail", thumbnail);
        map.put("duration", duration);
        map.put("size", size);
        map.put("format", format);
        map.put("quality", quality);
        map.put("downloaded", downloaded);
        map.put("downloadPath", downloadPath);
        map.put("error", error);
        return map;
    }
}

// 视频项
class VideoItem extends MediaItem {
    public String channel;
    public String views;
    public String published;
    public String description;
    public int index;
    
    @Override
    public Map<String, Object> toMap() {
        Map<String, Object> map = super.toMap();
        map.put("channel", channel);
        map.put("views", views);
        map.put("published", published);
        map.put("description", description);
        map.put("index", index);
        return map;
    }
}

// 图片项
class ImageItem extends MediaItem {
    public int width;
    public int height;
    public String alt;
    public String source;
}

// 音频项
class AudioItem extends MediaItem {
    public String artist;
    public String album;
    public int track;
    public String lyrics;
}

// 下载统计
class DownloadStats {
    public int total;
    public int success;
    public int failed;
    public int skipped;
    public String startTime;
    public String endTime;
    public List<Map<String, Object>> items = new ArrayList<>();
    
    public Map<String, Object> toMap() {
        Map<String, Object> map = new HashMap<>();
        map.put("total", total);
        map.put("success", success);
        map.put("failed", failed);
        map.put("skipped", skipped);
        map.put("startTime", startTime);
        map.put("endTime", endTime);
        map.put("items", items);
        return map;
    }
}

/**
 * 媒体下载器
 */
public class MediaDownloader {
    private Path outputDir;
    private String userAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36";
    
    public MediaDownloader(String outputDir) {
        this.outputDir = Paths.get(outputDir);
        try {
            Files.createDirectories(this.outputDir);
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
    
    /**
     * 下载文件
     */
    public boolean downloadFile(String urlStr, Path savePath) {
        try {
            System.out.println("   📥 下载：" + urlStr);
            
            URL url = new URL(urlStr);
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestProperty("User-Agent", userAgent);
            conn.setConnectTimeout(30000);
            conn.setReadTimeout(300000);
            
            int responseCode = conn.getResponseCode();
            if (responseCode != HttpURLConnection.HTTP_OK) {
                System.out.println("   ❌ HTTP 错误：" + responseCode);
                return false;
            }
            
            long totalSize = conn.getContentLengthLong();
            long downloaded = 0;
            
            try (InputStream is = conn.getInputStream();
                 FileOutputStream os = new FileOutputStream(savePath.toFile())) {
                
                byte[] buffer = new byte[8192];
                int bytesRead;
                int progressInterval = 10;
                int nextProgress = progressInterval;
                
                while ((bytesRead = is.read(buffer)) != -1) {
                    os.write(buffer, 0, bytesRead);
                    downloaded += bytesRead;
                    
                    if (totalSize > 0) {
                        int progress = (int) ((downloaded * 100) / totalSize);
                        if (progress >= nextProgress) {
                            System.out.print("\r   进度：" + progress + "%");
                            nextProgress += progressInterval;
                        }
                    }
                }
            }
            
            System.out.println("\r   ✓ 下载完成：" + savePath.getFileName());
            return true;
            
        } catch (Exception e) {
            System.out.println("\n   ❌ 下载失败：" + e.getMessage());
            return false;
        }
    }
    
    /**
     * 下载视频
     */
    public boolean downloadVideo(VideoItem video, String quality) {
        try {
            Path videoDir = outputDir.resolve("videos");
            Files.createDirectories(videoDir);
            
            String safeTitle = sanitizeFilename(video.title);
            String filename = safeTitle + ".mp4";
            Path savePath = videoDir.resolve(filename);
            
            // YouTube 视频
            if (video.url.contains("youtube.com") || video.url.contains("youtu.be")) {
                return downloadYouTubeVideo(video.url, savePath, quality);
            }
            
            return downloadFile(video.url, savePath);
            
        } catch (Exception e) {
            video.error = e.getMessage();
            return false;
        }
    }
    
    /**
     * 下载音频
     */
    public boolean downloadAudio(AudioItem audio, String format) {
        try {
            Path audioDir = outputDir.resolve("audios");
            Files.createDirectories(audioDir);
            
            String safeTitle = sanitizeFilename(audio.title);
            String filename = safeTitle + "." + format;
            Path savePath = audioDir.resolve(filename);
            
            return downloadFile(audio.url, savePath);
            
        } catch (Exception e) {
            audio.error = e.getMessage();
            return false;
        }
    }
    
    /**
     * 下载图片
     */
    public boolean downloadImage(ImageItem image) {
        try {
            Path imageDir = outputDir.resolve("images");
            Files.createDirectories(imageDir);
            
            String safeTitle = sanitizeFilename(image.title != null ? image.title : image.alt);
            String ext = getImageExtension(image.url);
            String filename = safeTitle + "." + ext;
            Path savePath = imageDir.resolve(filename);
            
            return downloadFile(image.url, savePath);
            
        } catch (Exception e) {
            image.error = e.getMessage();
            return false;
        }
    }
    
    /**
     * 批量下载
     */
    public DownloadStats downloadBatch(List<MediaItem> items, int maxWorkers) {
        DownloadStats stats = new DownloadStats();
        stats.total = items.size();
        stats.startTime = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"));
        
        System.out.println("\n📦 开始批量下载 " + items.size() + " 个文件...");
        System.out.println("   并发数：" + maxWorkers);
        System.out.println("   输出目录：" + outputDir);
        System.out.println();
        
        ExecutorService executor = Executors.newFixedThreadPool(maxWorkers);
        List<Future<Boolean>> futures = new ArrayList<>();
        
        for (int i = 0; i < items.size(); i++) {
            final int index = i;
            final MediaItem item = items.get(i);
            
            Future<Boolean> future = executor.submit(() -> {
                System.out.print("[" + (index + 1) + "/" + items.size() + "] ");
                
                if (isAlreadyDownloaded(item)) {
                    System.out.println("⏭️  跳过（已存在）");
                    stats.skipped++;
                    return true;
                }
                
                boolean success = false;
                
                if (item instanceof VideoItem) {
                    success = downloadVideo((VideoItem) item, "best");
                } else if (item instanceof AudioItem) {
                    success = downloadAudio((AudioItem) item, "mp3");
                } else if (item instanceof ImageItem) {
                    success = downloadImage((ImageItem) item);
                }
                
                if (success) {
                    stats.success++;
                    item.downloaded = true;
                    item.downloadPath = outputDir.toString();
                } else {
                    stats.failed++;
                }
                
                stats.items.add(item.toMap());
                
                try {
                    Thread.sleep(500); // 礼貌延迟
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
                
                return success;
            });
            
            futures.add(future);
        }
        
        executor.shutdown();
        try {
            executor.awaitTermination(1, TimeUnit.HOURS);
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
        
        stats.endTime = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"));
        saveDownloadLog(stats);
        
        return stats;
    }
    
    /**
     * 下载 YouTube 视频
     */
    private boolean downloadYouTubeVideo(String url, Path savePath, String quality) {
        try {
            // 检查 yt-dlp
            ProcessBuilder pb = new ProcessBuilder("yt-dlp", "--version");
            Process process = pb.start();
            int exitCode = process.waitFor();
            
            if (exitCode != 0) {
                System.out.println("   ⚠️  yt-dlp 未安装");
                return false;
            }
            
            // 构建命令
            List<String> cmd = new ArrayList<>();
            cmd.add("yt-dlp");
            cmd.add("-o");
            cmd.add(savePath.toString());
            cmd.add("--no-playlist");
            
            if ("best".equals(quality)) {
                cmd.add("-f");
                cmd.add("bestvideo+bestaudio/best");
            } else if ("audio".equals(quality)) {
                cmd.add("-x");
                cmd.add("--audio-format");
                cmd.add("mp3");
            }
            
            cmd.add(url);
            
            pb = new ProcessBuilder(cmd);
            pb.inheritIO();
            process = pb.start();
            exitCode = process.waitFor();
            
            if (exitCode == 0) {
                System.out.println("   ✓ YouTube 视频下载完成");
                return true;
            } else {
                System.out.println("   ❌ YouTube 下载失败");
                return false;
            }
            
        } catch (Exception e) {
            e.printStackTrace();
            return false;
        }
    }
    
    /**
     * 清理文件名
     */
    private String sanitizeFilename(String filename) {
        if (filename == null || filename.isEmpty()) {
            return "untitled";
        }
        
        String illegalChars = "<>:\"/\\|？*";
        for (char c : illegalChars.toCharArray()) {
            filename = filename.replace(c, '_');
        }
        
        if (filename.length() > 100) {
            filename = filename.substring(0, 100);
        }
        
        return filename.trim();
    }
    
    /**
     * 获取图片扩展名
     */
    private String getImageExtension(String url) {
        String urlLower = url.toLowerCase();
        
        if (urlLower.contains(".jpg") || urlLower.contains(".jpeg")) return "jpg";
        if (urlLower.contains(".png")) return "png";
        if (urlLower.contains(".gif")) return "gif";
        if (urlLower.contains(".webp")) return "webp";
        if (urlLower.contains(".bmp")) return "bmp";
        if (urlLower.contains(".svg")) return "svg";
        
        return "jpg";
    }
    
    /**
     * 检查是否已下载
     */
    private boolean isAlreadyDownloaded(MediaItem item) {
        if (item.title == null || item.title.isEmpty()) {
            return false;
        }
        
        String safeTitle = sanitizeFilename(item.title);
        Path checkDir;
        
        if (item instanceof VideoItem) {
            checkDir = outputDir.resolve("videos");
        } else if (item instanceof AudioItem) {
            checkDir = outputDir.resolve("audios");
        } else if (item instanceof ImageItem) {
            checkDir = outputDir.resolve("images");
        } else {
            return false;
        }
        
        String[] extensions = {"mp4", "mkv", "webm", "mp3", "wav", "flac", "jpg", "png", "gif"};
        
        for (String ext : extensions) {
            if (Files.exists(checkDir.resolve(safeTitle + "." + ext))) {
                return true;
            }
        }
        
        return false;
    }
    
    /**
     * 保存下载日志
     */
    private void saveDownloadLog(DownloadStats stats) {
        Path logFile = outputDir.resolve("download_log.json");
        
        try (BufferedWriter writer = Files.newBufferedWriter(logFile, StandardCharsets.UTF_8)) {
            writer.write("{\n");
            writer.write("  \"total\": " + stats.total + ",\n");
            writer.write("  \"success\": " + stats.success + ",\n");
            writer.write("  \"failed\": " + stats.failed + ",\n");
            writer.write("  \"skipped\": " + stats.skipped + ",\n");
            writer.write("  \"startTime\": \"" + stats.startTime + "\",\n");
            writer.write("  \"endTime\": \"" + stats.endTime + "\",\n");
            writer.write("  \"items\": [\n");
            
            for (int i = 0; i < stats.items.size(); i++) {
                Map<String, Object> item = stats.items.get(i);
                writer.write("    " + mapToJson(item));
                if (i < stats.items.size() - 1) {
                    writer.write(",");
                }
                writer.write("\n");
            }
            
            writer.write("  ]\n");
            writer.write("}\n");
            
            System.out.println("\n📝 下载日志已保存到：" + logFile);
            
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
    
    /**
     * Map 转 JSON（简化版）
     */
    private String mapToJson(Map<String, Object> map) {
        StringBuilder sb = new StringBuilder("{");
        boolean first = true;
        
        for (Map.Entry<String, Object> entry : map.entrySet()) {
            if (!first) sb.append(",");
            first = false;
            
            sb.append("\"").append(entry.getKey()).append("\":");
            
            Object value = entry.getValue();
            if (value instanceof String) {
                sb.append("\"").append(value.toString().replace("\"", "\\\"")).append("\"");
            } else if (value instanceof Boolean) {
                sb.append(value.toString());
            } else if (value instanceof Number) {
                sb.append(value.toString());
            } else {
                sb.append("null");
            }
        }
        
        sb.append("}");
        return sb.toString();
    }
}
