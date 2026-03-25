package com.javaspider.media;

import java.io.*;
import java.net.*;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;

/**
 * 批量下载器
 * 支持从文件列表批量下载
 */
public class BatchDownloader {
    
    private String outputDir;
    private int concurrent;
    private int timeout;
    private int retryTimes;
    private String userAgent;
    private volatile boolean cancelled;
    private ProgressCallback progressCallback;
    private CompleteCallback completeCallback;
    
    /**
     * 进度回调接口
     */
    public interface ProgressCallback {
        void onProgress(String url, long downloaded, long total);
    }
    
    /**
     * 完成回调接口
     */
    public interface CompleteCallback {
        void onComplete(String url, boolean success, String outputFile);
    }
    
    /**
     * 默认构造函数
     */
    public BatchDownloader() {
        this("./downloads");
    }
    
    /**
     * 指定输出目录
     * @param outputDir 输出目录
     */
    public BatchDownloader(String outputDir) {
        this.outputDir = outputDir;
        this.concurrent = 5;
        this.timeout = 30000;
        this.retryTimes = 3;
        this.userAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36";
        this.cancelled = false;
    }
    
    /**
     * 设置并发数
     */
    public void setConcurrent(int concurrent) {
        this.concurrent = concurrent;
    }
    
    /**
     * 设置超时
     */
    public void setTimeout(int timeout) {
        this.timeout = timeout;
    }
    
    /**
     * 设置重试次数
     */
    public void setRetryTimes(int retryTimes) {
        this.retryTimes = retryTimes;
    }
    
    /**
     * 设置 User-Agent
     */
    public void setUserAgent(String userAgent) {
        this.userAgent = userAgent;
    }
    
    /**
     * 设置进度回调
     */
    public void setProgressCallback(ProgressCallback callback) {
        this.progressCallback = callback;
    }
    
    /**
     * 设置完成回调
     */
    public void setCompleteCallback(CompleteCallback callback) {
        this.completeCallback = callback;
    }
    
    /**
     * 取消下载
     */
    public void cancel() {
        this.cancelled = true;
    }
    
    /**
     * 批量下载
     * @param urls URL 列表
     * @return 下载结果
     */
    public BatchResult download(List<String> urls) {
        long startTime = System.currentTimeMillis();
        
        try {
            // 创建输出目录
            Files.createDirectories(Paths.get(outputDir));
            
            // 并发下载
            List<DownloadResult> results = downloadConcurrent(urls);
            
            // 统计结果
            int success = 0;
            int failed = 0;
            long totalSize = 0;
            
            for (DownloadResult result : results) {
                if (result.success) {
                    success++;
                    totalSize += result.size;
                } else {
                    failed++;
                }
            }
            
            long duration = System.currentTimeMillis() - startTime;
            
            return new BatchResult(success, failed, totalSize, duration, results);
            
        } catch (Exception e) {
            e.printStackTrace();
            return new BatchResult(0, urls.size(), 0, 0, new ArrayList<>());
        }
    }
    
    /**
     * 从文件列表批量下载
     * @param listFile URL 列表文件
     * @return 下载结果
     */
    public BatchResult downloadFromList(String listFile) {
        try {
            List<String> urls = new ArrayList<>();
            
            try (BufferedReader reader = new BufferedReader(new FileReader(listFile))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    line = line.trim();
                    // 跳过空行和注释
                    if (line.isEmpty() || line.startsWith("#")) {
                        continue;
                    }
                    urls.add(line);
                }
            }
            
            if (urls.isEmpty()) {
                return new BatchResult(0, 0, 0, 0, new ArrayList<>());
            }
            
            System.out.println("从文件读取到 " + urls.size() + " 个 URL");
            return download(urls);
            
        } catch (Exception e) {
            e.printStackTrace();
            return new BatchResult(0, 0, 0, 0, new ArrayList<>());
        }
    }
    
    /**
     * 并发下载
     */
    private List<DownloadResult> downloadConcurrent(List<String> urls) {
        List<DownloadResult> results = new CopyOnWriteArrayList<>();
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
                    
                    // 生成文件名
                    String filename = generateFilename(url);
                    String outputFile = outputDir + "/" + filename;
                    
                    // 检查是否已存在
                    if (Files.exists(Paths.get(outputFile))) {
                        System.out.println("[" + (index + 1) + "/" + urls.size() + "] 已存在：" + filename);
                        results.add(new DownloadResult(url, true, outputFile, 0, "已存在"));
                        successCount.incrementAndGet();
                        return;
                    }
                    
                    // 下载
                    long size = downloadFile(url, outputFile, index, urls.size());
                    
                    if (size > 0) {
                        results.add(new DownloadResult(url, true, outputFile, size, "成功"));
                        successCount.incrementAndGet();
                        
                        if (completeCallback != null) {
                            completeCallback.onComplete(url, true, outputFile);
                        }
                    } else {
                        results.add(new DownloadResult(url, false, outputFile, 0, "下载失败"));
                        failCount.incrementAndGet();
                        
                        if (completeCallback != null) {
                            completeCallback.onComplete(url, false, outputFile);
                        }
                    }
                    
                    System.out.printf("\r总进度：%d/%d (成功：%d, 失败：%d)", 
                        index + 1, urls.size(), successCount.get(), failCount.get());
                    
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
        
        return results;
    }
    
    /**
     * 下载文件
     */
    private long downloadFile(String url, String outputFile, int index, int total) {
        for (int i = 0; i < retryTimes; i++) {
            try {
                HttpURLConnection conn = (HttpURLConnection) new URL(url).openConnection();
                conn.setRequestProperty("User-Agent", userAgent);
                conn.setConnectTimeout(timeout);
                conn.setReadTimeout(timeout);
                
                if (conn.getResponseCode() != 200) {
                    conn.disconnect();
                    continue;
                }
                
                long totalSize = conn.getContentLengthLong();
                long downloaded = 0;
                
                try (InputStream in = conn.getInputStream();
                     FileOutputStream out = new FileOutputStream(outputFile)) {
                    
                    byte[] buffer = new byte[8192];
                    int len;
                    
                    while ((len = in.read(buffer)) != -1) {
                        out.write(buffer, 0, len);
                        downloaded += len;
                        
                        // 进度回调
                        if (progressCallback != null && totalSize > 0) {
                            progressCallback.onProgress(url, downloaded, totalSize);
                        }
                    }
                }
                
                conn.disconnect();
                return downloaded;
                
            } catch (Exception e) {
                if (i == retryTimes - 1) {
                    System.err.println("[" + (index + 1) + "/" + total + "] 下载失败：" + url + " - " + e.getMessage());
                }
            }
        }
        return 0;
    }
    
    /**
     * 生成文件名
     */
    private String generateFilename(String url) {
        try {
            URL u = new URL(url);
            String path = u.getPath();
            String filename = path.substring(path.lastIndexOf('/') + 1);
            
            if (filename.isEmpty() || filename.equals("/")) {
                filename = "download_" + System.currentTimeMillis();
            }
            
            // 清理文件名
            filename = filename.replaceAll("[^a-zA-Z0-9._-]", "_");
            
            return filename;
            
        } catch (Exception e) {
            return "download_" + System.currentTimeMillis();
        }
    }
    
    /**
     * 批量下载结果
     */
    public static class BatchResult {
        public int success;
        public int failed;
        public long totalSize;
        public long duration;
        public List<DownloadResult> results;
        
        public BatchResult(int success, int failed, long totalSize, long duration, List<DownloadResult> results) {
            this.success = success;
            this.failed = failed;
            this.totalSize = totalSize;
            this.duration = duration;
            this.results = results;
        }
        
        public void printSummary() {
            System.out.println("=== 批量下载完成 ===");
            System.out.println("成功：" + success);
            System.out.println("失败：" + failed);
            System.out.println("总大小：" + formatSize(totalSize));
            System.out.println("耗时：" + formatDuration(duration));
        }
        
        private String formatSize(long size) {
            if (size < 1024) {
                return size + " B";
            } else if (size < 1024 * 1024) {
                return String.format("%.2f KB", size / 1024.0);
            } else if (size < 1024 * 1024 * 1024) {
                return String.format("%.2f MB", size / (1024.0 * 1024.0));
            } else {
                return String.format("%.2f GB", size / (1024.0 * 1024.0 * 1024.0));
            }
        }
        
        private String formatDuration(long ms) {
            long seconds = ms / 1000;
            long minutes = seconds / 60;
            long hours = minutes / 60;
            
            if (hours > 0) {
                return String.format("%d小时%d分钟", hours, minutes % 60);
            } else if (minutes > 0) {
                return String.format("%d分钟%d秒", minutes, seconds % 60);
            } else {
                return String.format("%d秒", seconds);
            }
        }
    }
    
    /**
     * 单个下载结果
     */
    public static class DownloadResult {
        public String url;
        public boolean success;
        public String outputFile;
        public long size;
        public String message;
        
        public DownloadResult(String url, boolean success, String outputFile, long size, String message) {
            this.url = url;
            this.success = success;
            this.outputFile = outputFile;
            this.size = size;
            this.message = message;
        }
    }
}
