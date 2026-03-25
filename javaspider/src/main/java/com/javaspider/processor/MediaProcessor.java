package com.javaspider.processor;

import com.javaspider.core.Page;
import com.javaspider.core.Site;
import com.javaspider.media.MediaItem;
import com.javaspider.media.MediaType;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * 通用媒体处理器
 * 支持视频、图片、音乐爬取
 */
public class MediaProcessor extends BasePageProcessor {
    
    private static final Pattern VIDEO_PATTERN = Pattern.compile(
        "https?://[^\\s\"']+\\.(mp4|avi|mkv|mov|wmv|flv|webm)",
        Pattern.CASE_INSENSITIVE
    );
    
    private static final Pattern IMAGE_PATTERN = Pattern.compile(
        "https?://[^\\s\"']+\\.(jpg|jpeg|png|gif|bmp|webp)",
        Pattern.CASE_INSENSITIVE
    );
    
    private static final Pattern AUDIO_PATTERN = Pattern.compile(
        "https?://[^\\s\"']+\\.(mp3|wav|flac|aac|ogg)",
        Pattern.CASE_INSENSITIVE
    );
    
    private final List<MediaItem> mediaItems;
    private final boolean extractAll;
    
    public MediaProcessor() {
        this(true);
    }
    
    public MediaProcessor(boolean extractAll) {
        this.mediaItems = new ArrayList<>();
        this.extractAll = extractAll;
    }
    
    @Override
    public void process(Page page) {
        String html = page.getRawText();
        if (html == null) {
            html = page.getHtml().getDocumentHtml();
        }
        
        // 提取视频
        extractVideos(page, html);
        
        // 提取图片
        extractImages(page, html);
        
        // 提取音频
        extractAudios(page, html);
        
        // 保存结果
        page.getResultItems().put("mediaItems", mediaItems);
        page.getResultItems().put("videoCount", countByType(MediaType.VIDEO));
        page.getResultItems().put("imageCount", countByType(MediaType.IMAGE));
        page.getResultItems().put("audioCount", countByType(MediaType.AUDIO));
        
        // 输出统计
        System.out.println("\n========== 媒体统计 ==========");
        System.out.println("视频数量：" + countByType(MediaType.VIDEO));
        System.out.println("图片数量：" + countByType(MediaType.IMAGE));
        System.out.println("音频数量：" + countByType(MediaType.AUDIO));
        System.out.println("总计：" + mediaItems.size());
        System.out.println("==============================\n");
    }
    
    @Override
    public Site getSite() {
        return Site.of("*")
            .setUserAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            .addHeader("Accept", "*/*")
            .addHeader("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8")
            .setRetryTimes(3)
            .setRetrySleep(1000);
    }
    
    /**
     * 提取视频
     */
    protected void extractVideos(Page page, String html) {
        // 提取 video 标签
        List<String> videoTags = page.$$("video source");
        for (String src : videoTags) {
            if (src != null && !src.isEmpty()) {
                MediaItem item = new MediaItem("Video", src, MediaType.VIDEO);
                mediaItems.add(item);
            }
        }
        
        // 正则提取视频 URL
        if (extractAll) {
            extractByPattern(html, VIDEO_PATTERN, MediaType.VIDEO);
        }
        
        // 提取 meta 标签中的视频
        String videoUrl = page.$("meta[property=og:video:url]");
        if (videoUrl != null && !videoUrl.isEmpty()) {
            MediaItem item = new MediaItem("OG Video", videoUrl, MediaType.VIDEO);
            item.setCoverImage(page.$("meta[property=og:image]"));
            mediaItems.add(item);
        }
    }
    
    /**
     * 提取图片
     */
    protected void extractImages(Page page, String html) {
        // 提取 img 标签
        List<String> images = page.$$("img");
        for (String img : images) {
            String src = extractAttribute(img, "src");
            String dataSrc = extractAttribute(img, "data-src");
            String dataOriginal = extractAttribute(img, "data-original");
            
            String imageUrl = dataOriginal != null ? dataOriginal : 
                             (dataSrc != null ? dataSrc : src);
            
            if (imageUrl != null && !imageUrl.isEmpty() && !imageUrl.startsWith("data:")) {
                MediaItem item = new MediaItem("Image", imageUrl, MediaType.IMAGE);
                String alt = extractAttribute(img, "alt");
                if (alt != null) {
                    item.addMetadata("alt", alt);
                }
                mediaItems.add(item);
            }
        }
        
        // 正则提取图片 URL
        if (extractAll) {
            extractByPattern(html, IMAGE_PATTERN, MediaType.IMAGE);
        }
        
        // 提取 meta 标签中的图片
        String ogImage = page.$("meta[property=og:image]");
        if (ogImage != null && !ogImage.isEmpty()) {
            MediaItem item = new MediaItem("OG Image", ogImage, MediaType.IMAGE);
            mediaItems.add(item);
        }
    }
    
    /**
     * 提取音频
     */
    protected void extractAudios(Page page, String html) {
        // 提取 audio 标签
        List<String> audioTags = page.$$("audio source");
        for (String src : audioTags) {
            if (src != null && !src.isEmpty()) {
                MediaItem item = new MediaItem("Audio", src, MediaType.AUDIO);
                mediaItems.add(item);
            }
        }
        
        // 正则提取音频 URL
        if (extractAll) {
            extractByPattern(html, AUDIO_PATTERN, MediaType.AUDIO);
        }
    }
    
    /**
     * 使用正则提取媒体 URL
     */
    private void extractByPattern(String html, Pattern pattern, MediaType type) {
        Matcher matcher = pattern.matcher(html);
        while (matcher.find()) {
            String url = matcher.group();
            MediaItem item = new MediaItem(type.name(), url, type);
            mediaItems.add(item);
        }
    }
    
    /**
     * 提取属性
     */
    private String extractAttribute(String html, String attr) {
        if (html == null) return null;
        Pattern pattern = Pattern.compile(attr + "=[\"']([^\"']+)[\"']");
        Matcher matcher = pattern.matcher(html);
        if (matcher.find()) {
            return matcher.group(1);
        }
        return null;
    }
    
    /**
     * 统计指定类型的数量
     */
    private int countByType(MediaType type) {
        int count = 0;
        for (MediaItem item : mediaItems) {
            if (item.getType() == type) {
                count++;
            }
        }
        return count;
    }
    
    /**
     * 获取所有媒体项
     */
    public List<MediaItem> getMediaItems() {
        return mediaItems;
    }
    
    /**
     * 清空媒体列表
     */
    public void clear() {
        mediaItems.clear();
    }
}
