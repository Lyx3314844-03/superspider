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
    private boolean isDRMProtected;
    
    public VideoInfo() {
        this.videoUrls = new ArrayList<>();
        this.audioUrls = new ArrayList<>();
        this.qualities = new ArrayList<>();
        this.isDRMProtected = false;
    }
    
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
    }
}
