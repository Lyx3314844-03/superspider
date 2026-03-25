package com.javaspider.media;

import lombok.Data;

import java.util.HashMap;
import java.util.Map;

/**
 * 媒体项数据类
 */
@Data
public class MediaItem {
    private String title;
    private String description;
    private MediaType type;
    private String url;
    private String downloadUrl;
    private String coverImage;
    private String duration;
    private String size;
    private String quality;
    private String author;
    private String uploadTime;
    private String viewCount;
    private String likeCount;
    private String[] tags;
    private Map<String, String> metadata;
    
    public MediaItem() {
        this.metadata = new HashMap<>();
        this.type = MediaType.UNKNOWN;
    }
    
    public MediaItem(String title, String url, MediaType type) {
        this();
        this.title = title;
        this.url = url;
        this.type = type;
    }
    
    public void addMetadata(String key, String value) {
        metadata.put(key, value);
    }
    
    public String getMetadata(String key) {
        return metadata.get(key);
    }
    
    @Override
    public String toString() {
        return "MediaItem{" +
                "title='" + title + '\'' +
                ", type=" + type +
                ", url='" + url + '\'' +
                '}';
    }
}
