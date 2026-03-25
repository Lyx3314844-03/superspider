package com.javaspider.media;

import java.util.HashMap;
import java.util.Map;

/**
 * 媒体类型枚举
 */
public enum MediaType {
    VIDEO("video"),
    IMAGE("image"),
    AUDIO("audio"),
    UNKNOWN("unknown");
    
    private final String type;
    
    MediaType(String type) {
        this.type = type;
    }
    
    public String getType() {
        return type;
    }
    
    public static MediaType fromUrl(String url) {
        if (url == null) return UNKNOWN;
        String lower = url.toLowerCase();
        if (lower.matches(".*\\.(mp4|avi|mkv|mov|wmv|flv|webm).*")) {
            return VIDEO;
        } else if (lower.matches(".*\\.(jpg|jpeg|png|gif|bmp|webp).*")) {
            return IMAGE;
        } else if (lower.matches(".*\\.(mp3|wav|flac|aac|ogg).*")) {
            return AUDIO;
        }
        return UNKNOWN;
    }
}
