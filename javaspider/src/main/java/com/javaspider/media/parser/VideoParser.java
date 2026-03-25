package com.javaspider.media.parser;

/**
 * 视频解析器接口
 */
public interface VideoParser {
    
    /**
     * 是否支持该 URL
     */
    boolean supports(String url);
    
    /**
     * 解析视频信息
     */
    VideoInfo parse(String url) throws Exception;
}
