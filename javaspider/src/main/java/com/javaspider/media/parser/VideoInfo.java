package com.javaspider.media.parser;

import lombok.Data;

import java.util.*;

/**
 * 视频信息类
 */
@Data
public class VideoInfo {
    private String url;
    private String videoId;
    private String platform;
    private String title;
    private String description;
    private String coverUrl;
    private int duration;
    private int viewCount;
    private int likeCount;
    private String uploadDate;
    private String author;
    private List<String> videoUrls;
    private List<String> audioUrls;
    private List<Quality> qualities;
    private List<Map<String, Object>> formats;
    private String videoUrl;
    private boolean isDRMProtected;

    public VideoInfo() {
        this.videoUrls = new ArrayList<>();
        this.audioUrls = new ArrayList<>();
        this.qualities = new ArrayList<>();
        this.formats = new ArrayList<>();
        this.isDRMProtected = false;
    }

    // Manual Getters and Setters to bypass Lombok issues in some environments
    public String getUrl() { return url; }
    public void setUrl(String url) { this.url = url; }
    public String getVideoId() { return videoId; }
    public void setVideoId(String videoId) { this.videoId = videoId; }
    public String getPlatform() { return platform; }
    public void setPlatform(String platform) { this.platform = platform; }
    public String getTitle() { return title; }
    public void setTitle(String title) { this.title = title; }
    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }
    public String getCoverUrl() { return coverUrl; }
    public void setCoverUrl(String coverUrl) { this.coverUrl = coverUrl; }
    public int getDuration() { return duration; }
    public void setDuration(int duration) { this.duration = duration; }
    public int getViewCount() { return viewCount; }
    public void setViewCount(int viewCount) { this.viewCount = viewCount; }
    public int getLikeCount() { return likeCount; }
    public void setLikeCount(int likeCount) { this.likeCount = likeCount; }
    public String getUploadDate() { return uploadDate; }
    public void setUploadDate(String uploadDate) { this.uploadDate = uploadDate; }
    public String getAuthor() { return author; }
    public void setAuthor(String author) { this.author = author; }
    public List<String> getVideoUrls() { return videoUrls; }
    public void setVideoUrls(List<String> videoUrls) { this.videoUrls = videoUrls; }
    public List<String> getAudioUrls() { return audioUrls; }
    public void setAudioUrls(List<String> audioUrls) { this.audioUrls = audioUrls; }
    public List<Quality> getQualities() { return qualities; }
    public void setQualities(List<Quality> qualities) { this.qualities = qualities; }
    public List<Map<String, Object>> getFormats() { return formats; }
    public void setFormats(List<Map<String, Object>> formats) { this.formats = formats; }
    public String getVideoUrl() { return videoUrl; }
    public void setVideoUrl(String videoUrl) { this.videoUrl = videoUrl; }
    public boolean isDRMProtected() { return isDRMProtected; }
    public void setDRMProtected(boolean DRMProtected) { isDRMProtected = DRMProtected; }

    /**
     * 清晰度类
     */
    @Data
    public static class Quality {
        private String name;
        private String format;
        private int width;
        private int height;
        private String url;
        private long size;

        public String getName() { return name; }
        public void setName(String name) { this.name = name; }
        public String getFormat() { return format; }
        public void setFormat(String format) { this.format = format; }
        public int getWidth() { return width; }
        public void setWidth(int width) { this.width = width; }
        public int getHeight() { return height; }
        public void setHeight(int height) { this.height = height; }
        public String getUrl() { return url; }
        public void setUrl(String url) { this.url = url; }
        public long getSize() { return size; }
        public void setSize(long size) { this.size = size; }
    }
}
