package com.javaspider.media;

import java.io.*;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.channels.Channels;
import java.nio.channels.ReadableByteChannel;
import java.util.concurrent.*;

/**
 * 高级媒体下载器
 * 支持断点续传、多线程下载、进度监控
 */
public class AdvancedMediaDownloader {

    private final String outputDir;
    private final boolean overwrite;
    private final int threadCount;
    private final long timeout;

    public AdvancedMediaDownloader(String outputDir) {
        this(outputDir, false, 3);
    }

    public AdvancedMediaDownloader(String outputDir, boolean overwrite, int threadCount) {
        this.outputDir = outputDir;
        this.overwrite = overwrite;
        this.threadCount = threadCount;
        this.timeout = 30000;

        // 创建输出目录
        File dir = new File(outputDir);
        if (!dir.exists()) {
            dir.mkdirs();
        }
    }

    /**
     * 下载媒体文件（支持断点续传和重试）
     */
    public String downloadWithResume(MediaItem media) throws IOException {
        int maxRetries = 3;
        IOException lastException = null;

        for (int attempt = 1; attempt <= maxRetries; attempt++) {
            try {
                return downloadWithResumeInternal(media, attempt);
            } catch (IOException e) {
                lastException = e;
                System.err.println("下载失败 (尝试 " + attempt + "/" + maxRetries + "): " + e.getMessage());

                if (attempt < maxRetries) {
                    // 删除可能损坏的部分文件
                    String fileName = generateFileName(media);
                    String filePath = outputDir + File.separator + fileName;
                    File file = new File(filePath);
                    if (file.exists()) {
                        file.delete();
                    }

                    // 等待后重试
                    try {
                        Thread.sleep(3000);
                    } catch (InterruptedException ie) {
                        Thread.currentThread().interrupt();
                        break;
                    }
                }
            }
        }

        throw new IOException("下载失败，已重试 " + maxRetries + " 次", lastException);
    }

    private String downloadWithResumeInternal(MediaItem media, int attempt) throws IOException {
        if (media.getDownloadUrl() == null || media.getDownloadUrl().isEmpty()) {
            throw new IOException("No download URL available");
        }

        String fileName = generateFileName(media);
        String filePath = outputDir + File.separator + fileName;

        File file = new File(filePath);
        long downloadedSize = file.exists() && !overwrite ? file.length() : 0;

        System.out.println("Downloading: " + media.getDownloadUrl());
        System.out.println("Saving to: " + filePath);
        if (downloadedSize > 0) {
            System.out.println("Resuming from: " + downloadedSize + " bytes");
        }

        URL url = new URL(media.getDownloadUrl());
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setConnectTimeout((int) timeout);
        conn.setReadTimeout((int) timeout);

        // 设置必要的请求头绕过Bilibili防盗链
        conn.setRequestProperty("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36");
        conn.setRequestProperty("Referer", "https://www.bilibili.com");
        conn.setRequestProperty("Origin", "https://www.bilibili.com");
        conn.setRequestProperty("Accept", "*/*");
        conn.setRequestProperty("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8");
        conn.setRequestProperty("Accept-Encoding", "gzip, deflate, br");

        // 设置 Range 头实现断点续传
        if (downloadedSize > 0) {
            conn.setRequestProperty("Range", "bytes=" + downloadedSize + "-");
        }

        int responseCode = conn.getResponseCode();
        if (responseCode == 416) {
            // Range不匹配，从头开始下载
            System.out.println("Range不匹配，从头开始下载");
            conn.disconnect();
            conn = (HttpURLConnection) url.openConnection();
            conn.setConnectTimeout((int) timeout);
            conn.setReadTimeout((int) timeout);
            conn.setRequestProperty("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36");
            conn.setRequestProperty("Referer", "https://www.bilibili.com");
            conn.setRequestProperty("Origin", "https://www.bilibili.com");
            conn.setRequestProperty("Accept", "*/*");
            conn.setRequestProperty("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8");
            conn.setRequestProperty("Accept-Encoding", "gzip, deflate, br");
            downloadedSize = 0;
        } else if (responseCode == 403 || responseCode == 404) {
            throw new IOException("HTTP " + responseCode + " - URL可能已过期");
        }

        long fileSize = conn.getContentLengthLong();
        if (fileSize > 0) {
            System.out.println("File size: " + (fileSize / 1024 / 1024.0) + " MB");
        }

        try (InputStream is = conn.getInputStream();
             FileOutputStream fos = new FileOutputStream(filePath, downloadedSize > 0);
             ReadableByteChannel rbc = Channels.newChannel(is)) {

            byte[] buffer = new byte[8192];
            long totalDownloaded = downloadedSize;
            int lastProgress = 0;

            int bytesRead;
            while ((bytesRead = is.read(buffer)) != -1) {
                fos.write(buffer, 0, bytesRead);
                totalDownloaded += bytesRead;

                // 显示进度
                if (fileSize > 0) {
                    int progress = (int) (totalDownloaded * 100 / fileSize);
                    if (progress > lastProgress && progress % 10 == 0) {
                        System.out.printf("Progress: %d%% (%.2f MB / %.2f MB)%n",
                            progress,
                            totalDownloaded / 1024.0 / 1024.0,
                            fileSize / 1024.0 / 1024.0);
                        lastProgress = progress;
                    }
                }
            }
        }

        System.out.println("Download completed: " + filePath);
        return filePath;
    }

    /**
     * 多线程下载（分片下载）
     */
    public String downloadMultiThread(MediaItem media) throws Exception {
        String fileName = generateFileName(media);
        String filePath = outputDir + File.separator + fileName;

        URL url = new URL(media.getDownloadUrl());
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setConnectTimeout((int) timeout);
        conn.setRequestMethod("HEAD");

        long fileSize = conn.getContentLengthLong();
        if (fileSize <= 0) {
            System.out.println("File size unknown, using single thread download");
            return downloadWithResume(media);
        }

        System.out.println("Multi-thread download: " + fileSize / 1024 / 1024.0 + " MB");
        System.out.println("Thread count: " + threadCount);

        // 计算每个线程的下载范围
        long chunkSize = fileSize / threadCount;
        ExecutorService executor = Executors.newFixedThreadPool(threadCount);
        CountDownLatch latch = new CountDownLatch(threadCount);

        // 创建临时文件
        RandomAccessFile raf = new RandomAccessFile(filePath, "rw");
        raf.setLength(fileSize);
        raf.close();

        // 启动下载线程
        for (int i = 0; i < threadCount; i++) {
            final int threadIndex = i;
            final long start = threadIndex * chunkSize;
            final long end = (threadIndex == threadCount - 1) ? fileSize : (threadIndex + 1) * chunkSize;

            executor.submit(() -> {
                try {
                    downloadChunk(media.getDownloadUrl(), filePath, start, end, latch);
                } catch (Exception e) {
                    System.err.println("Thread " + threadIndex + " failed: " + e.getMessage());
                    e.printStackTrace();
                }
            });
        }

        // 等待所有线程完成
        latch.await(5, TimeUnit.MINUTES);
        executor.shutdown();

        System.out.println("Multi-thread download completed: " + filePath);
        return filePath;
    }

    /**
     * 下载文件分片
     */
    private void downloadChunk(String urlStr, String filePath, long start, long end, CountDownLatch latch) throws Exception {
        URL url = new URL(urlStr);
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setConnectTimeout((int) timeout);
        conn.setRequestProperty("Range", "bytes=" + start + "-" + (end - 1));

        // 设置必要的请求头绕过Bilibili防盗链
        conn.setRequestProperty("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36");
        conn.setRequestProperty("Referer", "https://www.bilibili.com");
        conn.setRequestProperty("Origin", "https://www.bilibili.com");

        try (InputStream is = conn.getInputStream();
             RandomAccessFile raf = new RandomAccessFile(filePath, "rw")) {

            raf.seek(start);
            byte[] buffer = new byte[8192];
            int bytesRead;

            while ((bytesRead = is.read(buffer)) != -1) {
                raf.write(buffer, 0, bytesRead);
            }

            System.out.printf("Chunk downloaded: %d-%d (%.2f MB)%n",
                start, end, (end - start) / 1024.0 / 1024.0);
        } finally {
            latch.countDown();
        }
    }

    /**
     * 批量下载
     */
    public void downloadBatch(java.util.List<MediaItem> items) {
        System.out.println("Batch download: " + items.size() + " files");

        ExecutorService executor = Executors.newFixedThreadPool(3);

        for (MediaItem item : items) {
            executor.submit(() -> {
                try {
                    downloadWithResume(item);
                } catch (Exception e) {
                    System.err.println("Failed to download: " + item.getUrl());
                    e.printStackTrace();
                }
            });
        }

        executor.shutdown();
        try {
            executor.awaitTermination(30, TimeUnit.MINUTES);
        } catch (InterruptedException e) {
            e.printStackTrace();
        }

        System.out.println("Batch download completed");
    }

    /**
     * 生成文件名
     */
    private String generateFileName(MediaItem media) {
        StringBuilder sb = new StringBuilder();

        if (media.getTitle() != null && !media.getTitle().isEmpty()) {
            String safeTitle = media.getTitle()
                .replaceAll("[^a-zA-Z0-9\\u4e00-\\u9fa5]", "_")
                .replaceAll("_+", "_");
            sb.append(safeTitle, 0, Math.min(safeTitle.length(), 50));
        } else {
            sb.append("media_").append(System.currentTimeMillis());
        }

        String ext = getFileExtension(media.getDownloadUrl());
        if (!ext.isEmpty()) {
            sb.append(".").append(ext);
        }

        return sb.toString();
    }

    /**
     * 获取文件扩展名
     */
    private String getFileExtension(String url) {
        if (url == null) return "";
        String path = url.split("\\?")[0];
        int lastDot = path.lastIndexOf('.');
        return lastDot >= 0 ? path.substring(lastDot + 1) : "";
    }
}
