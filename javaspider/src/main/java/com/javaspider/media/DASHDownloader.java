package com.javaspider.media;

import org.w3c.dom.*;
import javax.xml.parsers.*;
import java.io.*;
import java.net.*;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;
import java.util.regex.*;

/**
 * DASH 流媒体下载器
 * 支持 MPD 解析和多清晰度选择
 */
public class DASHDownloader {
    
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
    public DASHDownloader() {
        this("./downloads");
    }
    
    /**
     * 指定输出目录
     * @param outputDir 输出目录
     */
    public DASHDownloader(String outputDir) {
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
     * 设置 Referer
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
     * 下载 DASH 流
     * @param mpdUrl MPD URL
     * @param quality 清晰度 (4k, 2k, 1080p, 720p, auto)
     * @return 下载结果
     */
    public DownloadResult download(String mpdUrl, String quality) {
        long startTime = System.currentTimeMillis();
        
        try {
            // 创建输出目录
            Files.createDirectories(Paths.get(outputDir));
            
            // 下载并解析 MPD
            MPDInfo mpdInfo = parseMPD(mpdUrl);
            if (mpdInfo == null) {
                return new DownloadResult(false, "解析 MPD 失败");
            }
            
            // 选择最佳格式
            FormatInfo videoFormat = selectVideoFormat(mpdInfo.videoFormats, quality);
            FormatInfo audioFormat = selectAudioFormat(mpdInfo.audioFormats);
            
            if (videoFormat == null) {
                return new DownloadResult(false, "未找到视频格式");
            }
            
            System.out.println("选择视频格式：" + videoFormat.quality + " (" + 
                videoFormat.width + "x" + videoFormat.height + ")");
            
            if (audioFormat != null) {
                System.out.println("选择音频格式：" + audioFormat.codecs);
            }
            
            // 下载目录
            String downloadDir = outputDir + "/dash_temp_" + System.currentTimeMillis();
            Files.createDirectories(Paths.get(downloadDir));
            
            // 下载视频
            String videoFile = null;
            if (videoFormat != null) {
                System.out.println("正在下载视频分段...");
                videoFile = downloadDir + "/video.mp4";
                List<String> videoFiles = downloadSegments(videoFormat.urls, downloadDir, "video");
                if (videoFiles == null || videoFiles.isEmpty()) {
                    return new DownloadResult(false, "视频下载失败");
                }
                mergeFiles(videoFiles, videoFile);
            }
            
            // 下载音频
            String audioFile = null;
            if (audioFormat != null) {
                System.out.println("正在下载音频分段...");
                audioFile = downloadDir + "/audio.mp4";
                List<String> audioFiles = downloadSegments(audioFormat.urls, downloadDir, "audio");
                if (audioFiles != null && !audioFiles.isEmpty()) {
                    mergeFiles(audioFiles, audioFile);
                }
            }
            
            // 合并音视频
            String outputFile = outputDir + "/output_" + System.currentTimeMillis() + ".mp4";
            if (videoFile != null && audioFile != null) {
                // 有 ffmpeg 则合并，没有则只保存视频
                outputFile = mergeAudioVideo(videoFile, audioFile, outputFile);
            } else if (videoFile != null) {
                outputFile = videoFile;
            } else if (audioFile != null) {
                outputFile = audioFile;
            }
            
            // 清理临时目录
            cleanupTempDir(downloadDir);
            
            long duration = System.currentTimeMillis() - startTime;
            return new DownloadResult(true, "下载完成", outputFile, duration);
            
        } catch (Exception e) {
            e.printStackTrace();
            return new DownloadResult(false, "下载失败：" + e.getMessage());
        }
    }
    
    /**
     * 下载并解析 MPD
     */
    private MPDInfo parseMPD(String mpdUrl) throws Exception {
        String content = downloadContent(mpdUrl);
        if (content == null) {
            return null;
        }
        
        // 解析 XML
        DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
        DocumentBuilder builder = factory.newDocumentBuilder();
        Document doc = builder.parse(new ByteArrayInputStream(content.getBytes()));
        
        MPDInfo info = new MPDInfo();
        String basePath = mpdUrl.substring(0, mpdUrl.lastIndexOf('/') + 1);
        
        // 提取 AdaptationSet
        NodeList adaptationSets = doc.getElementsByTagName("AdaptationSet");
        
        for (int i = 0; i < adaptationSets.getLength(); i++) {
            Element adaptationSet = (Element) adaptationSets.item(i);
            String mimeType = adaptationSet.getAttribute("mimeType");
            
            NodeList representations = adaptationSet.getElementsByTagName("Representation");
            
            for (int j = 0; j < representations.getLength(); j++) {
                Element rep = (Element) representations.item(j);
                
                FormatInfo format = new FormatInfo();
                format.id = rep.getAttribute("id");
                format.mimeType = mimeType;
                
                String width = rep.getAttribute("width");
                String height = rep.getAttribute("height");
                String bandwidth = rep.getAttribute("bandwidth");
                String codecs = rep.getAttribute("codecs");
                
                format.width = width.isEmpty() ? 0 : Integer.parseInt(width);
                format.height = height.isEmpty() ? 0 : Integer.parseInt(height);
                format.bandwidth = bandwidth.isEmpty() ? 0 : Integer.parseInt(bandwidth);
                format.codecs = codecs;
                
                // 确定质量
                format.quality = determineQuality(format.height);
                
                // 确定类型
                format.isVideo = mimeType.contains("video") || format.width > 0;
                format.isAudio = mimeType.contains("audio") || codecs.contains("mp4a");
                
                // 提取分段 URL
                List<String> urls = extractSegmentUrls(rep, basePath);
                format.urls = urls;
                
                if (!urls.isEmpty()) {
                    if (format.isVideo) {
                        info.videoFormats.add(format);
                    } else if (format.isAudio) {
                        info.audioFormats.add(format);
                    }
                }
            }
        }
        
        return info;
    }
    
    /**
     * 提取分段 URL
     */
    private List<String> extractSegmentUrls(Element rep, String basePath) {
        List<String> urls = new ArrayList<>();
        
        // SegmentList
        NodeList segmentLists = rep.getElementsByTagName("SegmentList");
        if (segmentLists.getLength() > 0) {
            Element segmentList = (Element) segmentLists.item(0);
            NodeList segmentUrls = segmentList.getElementsByTagName("SegmentURL");
            
            for (int i = 0; i < segmentUrls.getLength(); i++) {
                Element segUrl = (Element) segmentUrls.item(i);
                String media = segUrl.getAttribute("media");
                if (!media.isEmpty()) {
                    urls.add(absoluteUrl(media, basePath));
                }
            }
        }
        
        // SegmentTemplate
        NodeList segmentTemplates = rep.getElementsByTagName("SegmentTemplate");
        if (segmentTemplates.getLength() > 0) {
            Element segmentTemplate = (Element) segmentTemplates.item(0);
            String media = segmentTemplate.getAttribute("media");
            String startNumber = segmentTemplate.getAttribute("startNumber");
            String duration = segmentTemplate.getAttribute("duration");
            String timescale = segmentTemplate.getAttribute("timescale");
            
            if (!media.isEmpty()) {
                int start = startNumber.isEmpty() ? 1 : Integer.parseInt(startNumber);
                int count = 100; // 默认分段数
                
                for (int i = 0; i < count; i++) {
                    String url = media
                        .replace("$Number$", String.format("%04d", start + i))
                        .replace("$RepresentationID$", rep.getAttribute("id"));
                    urls.add(absoluteUrl(url, basePath));
                }
            }
        }
        
        return urls;
    }
    
    /**
     * 下载内容
     */
    private String downloadContent(String url) throws IOException {
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
                    throw new IOException("下载失败：" + e.getMessage());
                }
            }
        }
        return null;
    }
    
    /**
     * 下载分段
     */
    private List<String> downloadSegments(List<String> urls, String dir, String prefix) {
        List<String> files = new CopyOnWriteArrayList<>();
        ExecutorService executor = Executors.newFixedThreadPool(concurrent);
        CountDownLatch latch = new CountDownLatch(urls.size());
        AtomicInteger successCount = new AtomicInteger(0);
        
        for (int i = 0; i < urls.size(); i++) {
            final int index = i;
            final String url = urls.get(i);
            
            executor.submit(() -> {
                try {
                    if (cancelled) return;
                    
                    String filename = String.format("%s_%04d.tmp", prefix, index);
                    String filepath = dir + "/" + filename;
                    
                    if (downloadFile(url, filepath)) {
                        files.add(filepath);
                        successCount.incrementAndGet();
                        System.out.printf("\r进度：%d/%d", index + 1, urls.size());
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
     * 下载文件
     */
    private boolean downloadFile(String url, String filepath) {
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
                    return false;
                }
            }
        }
        return false;
    }
    
    /**
     * 合并文件
     */
    private void mergeFiles(List<String> files, String outputFile) throws IOException {
        Collections.sort(files);
        
        try (FileOutputStream out = new FileOutputStream(outputFile)) {
            for (String file : files) {
                byte[] data = Files.readAllBytes(Paths.get(file));
                out.write(data);
            }
        }
    }
    
    /**
     * 合并音视频
     */
    private String mergeAudioVideo(String videoFile, String audioFile, String outputFile) {
        // 尝试使用 FFmpeg
        String ffmpegPath = findFFmpeg();
        if (ffmpegPath != null) {
            try {
                ProcessBuilder pb = new ProcessBuilder(
                    ffmpegPath,
                    "-i", videoFile,
                    "-i", audioFile,
                    "-c:v", "copy",
                    "-c:a", "aac",
                    "-y",
                    outputFile
                );
                pb.inheritIO();
                Process process = pb.start();
                process.waitFor();
                
                if (process.exitValue() == 0) {
                    System.out.println("FFmpeg 合并成功");
                    return outputFile;
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        
        // 没有 FFmpeg，只返回视频
        System.out.println("未找到 FFmpeg，仅保存视频");
        return videoFile;
    }
    
    /**
     * 查找 FFmpeg
     */
    private String findFFmpeg() {
        // 检查环境变量
        String ffmpegPath = System.getenv("FFMPEG_PATH");
        if (ffmpegPath != null && !ffmpegPath.isEmpty()) {
            return ffmpegPath;
        }
        
        // 检查 PATH
        String[] paths = {"ffmpeg", "C:\\ffmpeg\\bin\\ffmpeg.exe", "/usr/bin/ffmpeg", "/usr/local/bin/ffmpeg"};
        for (String path : paths) {
            try {
                ProcessBuilder pb = new ProcessBuilder(path, "-version");
                Process process = pb.start();
                process.waitFor();
                if (process.exitValue() == 0) {
                    return path;
                }
            } catch (Exception e) {
                // 忽略
            }
        }
        
        return null;
    }
    
    /**
     * 清理临时目录
     */
    private void cleanupTempDir(String dir) {
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
     * 绝对 URL
     */
    private String absoluteUrl(String url, String basePath) {
        if (url.startsWith("http://") || url.startsWith("https://")) {
            return url;
        }
        if (url.startsWith("/")) {
            try {
                URL base = new URL(basePath);
                return base.getProtocol() + "://" + base.getHost() + url;
            } catch (Exception e) {
                return basePath + url;
            }
        }
        return basePath + url;
    }
    
    /**
     * 确定质量
     */
    private String determineQuality(int height) {
        if (height >= 2160) return "4K";
        if (height >= 1440) return "2K";
        if (height >= 1080) return "1080p";
        if (height >= 720) return "720p";
        if (height >= 480) return "480p";
        return "360p";
    }
    
    /**
     * 选择视频格式
     */
    private FormatInfo selectVideoFormat(List<FormatInfo> formats, String quality) {
        if (formats.isEmpty()) return null;
        
        if ("auto".equals(quality)) {
            // 选择最高清晰度
            FormatInfo best = formats.get(0);
            for (FormatInfo f : formats) {
                if (f.height > best.height) {
                    best = f;
                }
            }
            return best;
        }
        
        Map<String, Integer> qualityMap = new HashMap<>();
        qualityMap.put("4k", 2160);
        qualityMap.put("2k", 1440);
        qualityMap.put("1080p", 1080);
        qualityMap.put("720p", 720);
        qualityMap.put("480p", 480);
        qualityMap.put("360p", 360);
        
        int targetHeight = qualityMap.getOrDefault(quality.toLowerCase(), 1080);
        
        FormatInfo best = null;
        for (FormatInfo f : formats) {
            if (f.height <= targetHeight) {
                if (best == null || f.height > best.height) {
                    best = f;
                }
            }
        }
        
        return best != null ? best : formats.get(0);
    }
    
    /**
     * 选择音频格式
     */
    private FormatInfo selectAudioFormat(List<FormatInfo> formats) {
        if (formats.isEmpty()) return null;
        
        FormatInfo best = formats.get(0);
        for (FormatInfo f : formats) {
            if (f.bandwidth > best.bandwidth) {
                best = f;
            }
        }
        return best;
    }
    
    /**
     * MPD 信息
     */
    static class MPDInfo {
        List<FormatInfo> videoFormats = new ArrayList<>();
        List<FormatInfo> audioFormats = new ArrayList<>();
    }
    
    /**
     * 格式信息
     */
    static class FormatInfo {
        String id;
        String mimeType;
        String quality;
        int width;
        int height;
        int bandwidth;
        String codecs;
        boolean isVideo;
        boolean isAudio;
        List<String> urls = new ArrayList<>();
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
