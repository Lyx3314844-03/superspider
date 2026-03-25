package com.spider.javaspider.enhanced;

import java.util.*;

/**
 * 视频数据项
 */
public class VideoItem {
    private int index;
    private String title;
    private String duration;
    private String channel;
    private String url;
    private String thumbnail;
    private String views;
    private String published;
    private String description;
    
    public VideoItem() {}
    
    public VideoItem(String title) {
        this.title = title;
    }
    
    public VideoItem(String title, String duration, String channel, String url) {
        this.title = title;
        this.duration = duration;
        this.channel = channel;
        this.url = url;
    }
    
    /**
     * 转换为 JSON 字符串
     */
    public String toJson() {
        StringBuilder json = new StringBuilder();
        json.append("{");
        json.append("\"index\":").append(index).append(",");
        json.append("\"title\":\"").append(escapeJson(title)).append("\",");
        json.append("\"duration\":\"").append(escapeJson(duration != null ? duration : "")).append("\",");
        json.append("\"channel\":\"").append(escapeJson(channel != null ? channel : "")).append("\",");
        json.append("\"url\":\"").append(escapeJson(url != null ? url : "")).append("\",");
        json.append("\"thumbnail\":\"").append(escapeJson(thumbnail != null ? thumbnail : "")).append("\",");
        json.append("\"views\":\"").append(escapeJson(views != null ? views : "")).append("\",");
        json.append("\"published\":\"").append(escapeJson(published != null ? published : "")).append("\"");
        json.append("}");
        return json.toString();
    }
    
    private String escapeJson(String value) {
        if (value == null) return "";
        return value
            .replace("\\", "\\\\")
            .replace("\"", "\\\"")
            .replace("\n", "\\n")
            .replace("\r", "\\r")
            .replace("\t", "\\t");
    }
    
    /**
     * 转换为 Map
     */
    public Map<String, Object> toMap() {
        Map<String, Object> map = new HashMap<>();
        map.put("index", index);
        map.put("title", title);
        map.put("duration", duration);
        map.put("channel", channel);
        map.put("url", url);
        map.put("thumbnail", thumbnail);
        map.put("views", views);
        map.put("published", published);
        map.put("description", description);
        return map;
    }
    
    // Getters and Setters
    public int getIndex() { return index; }
    public void setIndex(int index) { this.index = index; }
    
    public String getTitle() { return title; }
    public void setTitle(String title) { this.title = title; }
    
    public String getDuration() { return duration; }
    public void setDuration(String duration) { this.duration = duration; }
    
    public String getChannel() { return channel; }
    public void setChannel(String channel) { this.channel = channel; }
    
    public String getUrl() { return url; }
    public void setUrl(String url) { this.url = url; }
    
    public String getThumbnail() { return thumbnail; }
    public void setThumbnail(String thumbnail) { this.thumbnail = thumbnail; }
    
    public String getViews() { return views; }
    public void setViews(String views) { this.views = views; }
    
    public String getPublished() { return published; }
    public void setPublished(String published) { this.published = published; }
    
    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }
    
    @Override
    public String toString() {
        return "VideoItem{" +
            "index=" + index +
            ", title='" + title + '\'' +
            ", duration='" + duration + '\'' +
            ", channel='" + channel + '\'' +
            ", url='" + url + '\'' +
            '}';
    }
}
