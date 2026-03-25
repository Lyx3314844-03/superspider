package com.javaspider.media;

import java.io.*;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;
import java.util.regex.*;

/**
 * HLS 流媒体下载器
 * 支持 m3u8 播放列表解析和 TS 分段下载
 */
public class HLSDownloader {
    
    private String outputDir;
    private int concurrent;
    private int timeout;
    private int retryTimes;
    private String userAgent;
    private String referer;
    private volatile boolean cancelled;
    
    /**
     * 默认构造函数
     */
    public HLSDownloader() {
        this("./downloads");
    }
    
    /**
     * 指定输出目录
     * @param outputDir 输出目录
     */
    public HLSDownloader(String outputDir) {
        this.outputDir = outputDir;
        this.concurrent = 5;
        this.timeout = 30000;
        this.retryTimes = 3;
        this.userAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36";
        this.cancelled = false;
    }
    
    /**
     * 设置并发数
     * @param concurrent 并发数
     */
    public void setConcurrent(int concurrent) {
        this.concurrent = concurrent;
    }
    
    /**
     * 设置超时时间
     * @param timeout 超时时间（毫秒）
     */
    public void setTimeout(int timeout) {
        this.timeout = timeout;
    }
    
    /**
     * 设置重试次数
     * @param retryTimes 重试次数
     */
    public void setRetryTimes(int retryTimes) {
        this.retryTimes = retryTimes;
    }
    
    /**
     * 设置 User-Agent
     * @param userAgent User-Agent
     */
    public void setUserAgent(String userAgent) {
        this.userAgent = userAgent;
    }
    
    /**
     * 设置 Referer
     * @param referer Referer
     */
    public void setReferer(String referer) {
        this.referer = referer;
    }
    
    /**
     * 取消下载
     */
    public void cancel() {
        this.cancelled = true;
    }
    
    /**
     * 下载 HLS 流
     * @param m3u8Url m3u8 URL
     * @param outputFile 输出文件路径
     * @return 下载结果
     */
    public DownloadResult download(String m3u8Url, String outputFile) {
        long startTime = System.currentTimeMillis();
        
        try {
            // 创建输出目录
            Paths.get(outputDir).toAbsolutePath().normalize();
            Files.createDirectories(Paths.get(outputDir));
            
            // 下载 m3u8 文件
            String m3u8Content = downloadM3U8(m3u8Url);
            if (m3u8Content == null) {
                return new DownloadResult(false, "下载 m3u8 文件失败");
            }
            
            // 解析播放列表
            List<String> segmentUrls = parseM3U8(m3u8Content, m3u8Url);
            if (segmentUrls.isEmpty()) {
                return new DownloadResult(false, "未找到媒体分段");
            }
            
            System.out.println("找到 " + segmentUrls.size() + " 个媒体分段");
            
            // 下载目录
            String downloadDir = outputDir + "/temp_segments";
            Files.createDirectories(Paths.get(downloadDir));
            
            // 并发下载分段
            List<String> segmentFiles = downloadSegments(segmentUrls, downloadDir);
            
            if (segmentFiles == null || segmentFiles.isEmpty()) {
                return new DownloadResult(false, "分段下载失败");
            }
            
            // 合并分段
            mergeSegments(segmentFiles, outputFile);
            
            // 清理临时文件
            cleanupTempFiles(downloadDir);
            
            long duration = System.currentTimeMillis() - startTime;
            return new DownloadResult(true, "下载完成", outputFile, duration);
            
        } catch (Exception e) {
            e.printStackTrace();
            return new DownloadResult(false, "下载失败：" + e.getMessage());
        }
    }
    
    /**
     * 下载 m3u8 文件
     */
    private String downloadM3U8(String url) throws IOException {
        for (int i = 0; i < retryTimes; i++) {
            try {
                HttpURLConnection conn = (HttpURLConnection) new URL(url).openConnection();
                conn.setRequestProperty("User-Agent", userAgent);
                if (referer != null && !referer.isEmpty()) {
                    conn.setRequestProperty("Referer", referer);
                }
                conn.setConnectTimeout(timeout);
                conn.setReadTimeout(timeout);
                
                if (conn.getResponseCode() != 200) {
                    conn.disconnect();
                    continue;
                }
                
                BufferedReader reader = new BufferedReader(new InputStreamReader(conn.getInputStream()));
                StringBuilder content = new StringBuilder();
                String line;
                
                while ((line = reader.readLine()) != null) {
                    content.append(line).append("\n");
                }
                
                reader.close();
                conn.disconnect();
                return content.toString();
                
            } catch (Exception e) {
                if (i == retryTimes - 1) {
                    throw new IOException("下载 m3u8 失败：" + e.getMessage());
                }
            }
        }
        return null;
    }
    
    /**
     * 解析 m3u8 播放列表
     */
    private List<String> parseM3U8(String content, String baseUrl) {
        List<String> urls = new ArrayList<>();
        String[] lines = content.split("\n");
        
        String basePath = baseUrl.substring(0, baseUrl.lastIndexOf('/') + 1);
        
        for (String line : lines) {
            line = line.trim();
            
            // 跳过空行、注释和标签
            if (line.isEmpty() || line.startsWith("#")) {
                continue;
            }
            
            // 处理 URL
            String url = line;
            if (!url.startsWith("http://") && !url.startsWith("https://")) {
                if (url.startsWith("/")) {
                    // 绝对路径
                    URL base = null;
                    try {
                        base = new URL(baseUrl);
                        url = base.getProtocol() + "://" + base.getHost() + url;
                    } catch (Exception e) {
                        url = basePath + url;
                    }
                } else {
                    // 相对路径
                    url = basePath + url;
                }
            }
            
            urls.add(url);
        }
        
        return urls;
    }
    
    /**
     * 并发下载分段
     */
    private List<String> downloadSegments(List<String> urls, String downloadDir) {
        List<String> files = new CopyOnWriteArrayList<>();
        ExecutorService executor = Executors.newFixedThreadPool(concurrent);
        CountDownLatch latch = new CountDownLatch(urls.size());
        AtomicInteger successCount = new AtomicInteger(0);
        AtomicInteger failCount = new AtomicInteger(0);
        
        for (int i = 0; i < urls.size(); i++) {
            final int index = i;
            final String url = urls.get(i);
            
            executor.submit(() -> {
                try {
                    if (cancelled) {
                        return;
                    }
                    
                    String filename = String.format("seg_%04d.ts", index);
                    String filepath = downloadDir + "/" + filename;
                    
                    if (downloadSegment(url, filepath)) {
                        files.add(filepath);
                        successCount.incrementAndGet();
                        System.out.printf("\r进度：%d/%d (成功：%d, 失败：%d)", 
                            index + 1, urls.size(), successCount.get(), failCount.get());
                    } else {
                        failCount.incrementAndGet();
                    }
                    
                } finally {
                    latch.countDown();
                }
            });
        }
        
        try {
            latch.await();
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
        
        executor.shutdown();
        System.out.println();
        
        return files;
    }
    
    /**
     * 下载单个分段
     */
    private boolean downloadSegment(String url, String filepath) {
        for (int i = 0; i < retryTimes; i++) {
            try {
                HttpURLConnection conn = (HttpURLConnection) new URL(url).openConnection();
                conn.setRequestProperty("User-Agent", userAgent);
                if (referer != null && !referer.isEmpty()) {
                    conn.setRequestProperty("Referer", referer);
                }
                conn.setConnectTimeout(timeout);
                conn.setReadTimeout(timeout);
                
                if (conn.getResponseCode() != 200) {
                    conn.disconnect();
                    continue;
                }
                
                try (InputStream in = conn.getInputStream();
                     FileOutputStream out = new FileOutputStream(filepath)) {
                    
                    byte[] buffer = new byte[8192];
                    int len;
                    
                    while ((len = in.read(buffer)) != -1) {
                        out.write(buffer, 0, len);
                    }
                }
                
                conn.disconnect();
                return true;
                
            } catch (Exception e) {
                if (i == retryTimes - 1) {
                    System.err.println("下载分段失败：" + url + " - " + e.getMessage());
                }
            }
        }
        return false;
    }
    
    /**
     * 合并分段
     */
    private void mergeSegments(List<String> segmentFiles, String outputFile) throws IOException {
        // 排序文件
        Collections.sort(segmentFiles);
        
        try (FileOutputStream out = new FileOutputStream(outputFile)) {
            for (String file : segmentFiles) {
                byte[] data = Files.readAllBytes(Paths.get(file));
                out.write(data);
            }
        }
        
        System.out.println("合并完成：" + outputFile);
    }
    
    /**
     * 清理临时文件
     */
    private void cleanupTempFiles(String dir) {
        try {
            Files.walk(Paths.get(dir))
                .sorted(Comparator.reverseOrder())
                .forEach(path -> {
                    try {
                        Files.delete(path);
                    } catch (IOException e) {
                        e.printStackTrace();
                    }
                });
            Files.delete(Paths.get(dir));
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
    
    /**
     * 下载结果
     */
    public static class DownloadResult {
        public boolean success;
        public String message;
        public String outputFile;
        public long duration;
        
        public DownloadResult(boolean success, String message) {
            this.success = success;
            this.message = message;
        }
        
        public DownloadResult(boolean success, String message, String outputFile, long duration) {
            this.success = success;
            this.message = message;
            this.outputFile = outputFile;
            this.duration = duration;
        }
    }
}
