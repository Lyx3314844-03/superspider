package com.javaspider.media.parser;

import java.util.*;

/**
 * 通用视频解析器
 */
public class GenericParser implements VideoParser {
    
    @Override
    public boolean supports(String url) {
        return true; // 支持所有 URL
    }
    
    @Override
    public VideoInfo parse(String url) throws Exception {
        VideoInfo info = new VideoInfo();
        info.setUrl(url);
        info.setPlatform("Generic");
        
        // 尝试从 URL 提取信息
        try {
            java.net.URL u = new java.net.URL(url);
            String path = u.getPath();
            
            // 提取文件名作为标题
            int lastSlash = path.lastIndexOf('/');
            if (lastSlash > 0) {
                String fileName = path.substring(lastSlash + 1);
                String title = fileName.replaceAll("\\.[^.]+$", "");
                info.setTitle(title);
            }
        } catch (Exception e) {
            info.setTitle("Unknown");
        }
        
        return info;
    }
}
