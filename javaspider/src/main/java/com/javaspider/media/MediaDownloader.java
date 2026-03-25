package com.javaspider.media;

import java.io.*;
import java.net.URL;
import java.nio.channels.Channels;
import java.nio.channels.ReadableByteChannel;

/**
 * 媒体下载器
 */
public class MediaDownloader {
    
    private final String outputDir;
    private final boolean overwrite;
    
    public MediaDownloader(String outputDir) {
        this(outputDir, false);
    }
    
    public MediaDownloader(String outputDir, boolean overwrite) {
        this.outputDir = outputDir;
        this.overwrite = overwrite;
        
        // 创建输出目录
        File dir = new File(outputDir);
        if (!dir.exists()) {
            dir.mkdirs();
        }
    }
    
    /**
     * 下载媒体文件
     */
    public String download(MediaItem media) throws IOException {
        if (media.getDownloadUrl() == null || media.getDownloadUrl().isEmpty()) {
            throw new IOException("No download URL available");
        }
        
        String fileName = generateFileName(media);
        String filePath = outputDir + File.separator + fileName;
        
        File file = new File(filePath);
        if (file.exists() && !overwrite) {
            System.out.println("File already exists: " + filePath);
            return filePath;
        }
        
        System.out.println("Downloading: " + media.getDownloadUrl());
        System.out.println("Saving to: " + filePath);
        
        URL url = new URL(media.getDownloadUrl());
        try (ReadableByteChannel rbc = Channels.newChannel(url.openStream());
             FileOutputStream fos = new FileOutputStream(filePath)) {
            
            fos.getChannel().transferFrom(rbc, 0, Long.MAX_VALUE);
        }
        
        System.out.println("Download completed: " + filePath);
        return filePath;
    }
    
    /**
     * 下载文件到指定路径
     */
    public String download(String url, String filePath) throws IOException {
        File file = new File(filePath);
        if (file.exists() && !overwrite) {
            System.out.println("File already exists: " + filePath);
            return filePath;
        }
        
        // 创建目录
        File parent = file.getParentFile();
        if (parent != null && !parent.exists()) {
            parent.mkdirs();
        }
        
        System.out.println("Downloading: " + url);
        System.out.println("Saving to: " + filePath);
        
        URL urlObj = new URL(url);
        try (ReadableByteChannel rbc = Channels.newChannel(urlObj.openStream());
             FileOutputStream fos = new FileOutputStream(filePath)) {
            
            fos.getChannel().transferFrom(rbc, 0, Long.MAX_VALUE);
        }
        
        System.out.println("Download completed: " + filePath);
        return filePath;
    }
    
    /**
     * 生成文件名
     */
    private String generateFileName(MediaItem media) {
        StringBuilder sb = new StringBuilder();
        
        // 添加标题
        if (media.getTitle() != null && !media.getTitle().isEmpty()) {
            String safeTitle = media.getTitle()
                .replaceAll("[^a-zA-Z0-9\\u4e00-\\u9fa5]", "_")
                .replaceAll("_+", "_");
            sb.append(safeTitle, 0, Math.min(safeTitle.length(), 50));
        } else {
            sb.append("media");
        }
        
        // 添加扩展名
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
        if (lastDot >= 0) {
            return path.substring(lastDot + 1);
        }
        return "";
    }
}
