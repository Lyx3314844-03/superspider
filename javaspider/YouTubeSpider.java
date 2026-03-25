package com.javaspider;

import com.javaspider.browser.BrowserManager;
import com.javaspider.core.Spider;
import com.javaspider.model.Page;
import com.javaspider.model.Site;
import com.javaspider.pipeline.ConsolePipeline;
import com.javaspider.pipeline.JsonFilePipeline;
import com.javaspider.processor.PageProcessor;
import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.jsoup.nodes.Element;

/**
 * YouTube 视频爬虫
 * 爬取视频标题、描述、观看次数、点赞数、评论等信息
 */
public class YouTubeSpider {

    public static void main(String[] args) {
        String targetUrl = "https://www.youtube.com/watch?v=59JONAFPv9g&list=PLRuPQZBVD6vV89UKIzUwZFUhDx9DjXLxc&index=3";
        
        System.out.println("🕷️  启动 YouTube 视频爬虫...");
        System.out.println("目标 URL: " + targetUrl);
        System.out.println();

        // 使用浏览器管理器获取渲染后的页面
        BrowserManager browser = BrowserManager.headless();
        
        try {
            System.out.println("正在加载页面...");
            browser.navigate(targetUrl);
            browser.waitForPageLoad(5000);
            
            // 等待视频信息加载
            Thread.sleep(3000);
            
            // 获取渲染后的 HTML
            String html = browser.getPageSource();
            
            System.out.println("页面加载完成，开始解析...");
            System.out.println();
            
            // 解析 HTML
            parseYouTubePage(html);
            
        } catch (Exception e) {
            System.err.println("爬取失败：" + e.getMessage());
            e.printStackTrace();
        } finally {
            browser.close();
        }
    }

    /**
     * 解析 YouTube 页面
     */
    private static void parseYouTubePage(String html) {
        Document doc = Jsoup.parse(html);
        
        // 提取视频标题
        String title = extractText(doc, "h1.ytd-video-primary-renderer");
        if (title == null) {
            title = extractText(doc, "#title h1");
        }
        if (title == null) {
            title = extractText(doc, "title"); // 备用：从页面标题获取
        }
        
        // 提取视频描述
        String description = extractText(doc, "#description #content-text");
        if (description == null) {
            description = extractText(doc, "#eow-description");
        }
        
        // 提取观看次数
        String viewCount = extractText(doc, ".video-view-count");
        if (viewCount == null) {
            viewCount = extractText(doc, "#count ytd-video-view-count-renderer");
        }
        
        // 提取频道名称
        String channelName = extractText(doc, "#owner-name a");
        if (channelName == null) {
            channelName = extractText(doc, "#channel-name #text-container");
        }
        
        // 提取点赞数
        String likeCount = extractText(doc, "#segmented-like-button button");
        
        // 提取发布日期
        String publishDate = extractText(doc, "#info #info-text");
        
        // 提取播放列表信息
        String playlistInfo = extractText(doc, "#playlist-title");
        
        // 提取视频缩略图
        String thumbnailUrl = extractAttr(doc, "meta[property=\"og:image\"]", "content");
        
        // 提取视频 ID
        String videoId = extractAttr(doc, "meta[itemprop=\"videoId\"]", "content");
        if (videoId == null) {
            videoId = extractAttr(doc, "link[itemprop=\"identifier\"]", "href");
            if (videoId != null && videoId.contains("v=")) {
                videoId = videoId.substring(videoId.indexOf("v=") + 2);
                if (videoId.contains("&")) {
                    videoId = videoId.substring(0, videoId.indexOf("&"));
                }
            }
        }
        
        // 提取相关推荐视频
        System.out.println("═══════════════════════════════════════════════════════════");
        System.out.println("                      YouTube 视频信息                      ");
        System.out.println("═══════════════════════════════════════════════════════════");
        System.out.println("视频标题：" + (title != null ? title : "未找到"));
        System.out.println("视频 ID: " + (videoId != null ? videoId : "未找到"));
        System.out.println("频道名称：" + (channelName != null ? channelName : "未找到"));
        System.out.println("观看次数：" + (viewCount != null ? viewCount : "未找到"));
        System.out.println("点赞数：" + (likeCount != null ? likeCount : "未找到"));
        System.out.println("发布日期：" + (publishDate != null ? publishDate : "未找到"));
        System.out.println("播放列表：" + (playlistInfo != null ? playlistInfo : "未找到"));
        System.out.println("缩略图：" + (thumbnailUrl != null ? thumbnailUrl : "未找到"));
        System.out.println();
        System.out.println("视频描述:");
        System.out.println("----------------------------------------");
        System.out.println(description != null ? description : "未找到");
        System.out.println("----------------------------------------");
        System.out.println();
        
        // 提取推荐视频列表
        extractRelatedVideos(doc);
        
        // 提取评论（如果可见）
        extractComments(doc);
    }

    /**
     * 提取相关推荐视频
     */
    private static void extractRelatedVideos(Document doc) {
        System.out.println("═══════════════════════════════════════════════════════════");
        System.out.println("                      推荐视频列表                          ");
        System.out.println("═══════════════════════════════════════════════════════════");
        
        int count = 0;
        for (Element video : doc.select("ytd-compact-video-renderer")) {
            String videoTitle = extractText(video, "#video-title");
            String videoChannel = extractText(video, "#channel-name a, #channel-name #text");
            String videoViews = extractText(video, "#metadata-line span");
            String videoUrl = extractAttr(video, "a#video-title", "href");
            
            if (videoTitle != null && count < 10) {
                count++;
                System.out.println(count + ". " + videoTitle);
                System.out.println("   频道：" + (videoChannel != null ? videoChannel : "未知"));
                System.out.println("   观看：" + (videoViews != null ? videoViews : "未知"));
                System.out.println("   链接：" + (videoUrl != null ? "https://youtube.com" + videoUrl : "未知"));
                System.out.println();
            }
        }
        
        if (count == 0) {
            System.out.println("未找到推荐视频（可能是页面结构变化）");
        }
        System.out.println();
    }

    /**
     * 提取评论
     */
    private static void extractComments(Document doc) {
        System.out.println("═══════════════════════════════════════════════════════════");
        System.out.println("                      热门评论                              ");
        System.out.println("═══════════════════════════════════════════════════════════");
        
        int count = 0;
        for (Element comment : doc.select("ytd-comment-thread-renderer")) {
            String author = extractText(comment, "#author-text span");
            String text = extractText(comment, "#content-text");
            String likeCount = extractText(comment, "#vote-count-middle");
            
            if (text != null && count < 5) {
                count++;
                System.out.println(count + ". " + author);
                System.out.println("   " + text);
                System.out.println("   点赞：" + (likeCount != null ? likeCount : "0"));
                System.out.println();
            }
        }
        
        if (count == 0) {
            System.out.println("未找到评论（评论可能需要额外加载）");
        }
        System.out.println();
    }

    /**
     * 提取文本内容
     */
    private static String extractText(Document doc, String selector) {
        Element element = doc.selectFirst(selector);
        return element != null ? element.text().trim() : null;
    }

    /**
     * 提取元素文本
     */
    private static String extractText(Element element, String selector) {
        Element found = element.selectFirst(selector);
        return found != null ? found.text().trim() : null;
    }

    /**
     * 提取属性值
     */
    private static String extractAttr(Document doc, String selector, String attr) {
        Element element = doc.selectFirst(selector);
        return element != null ? element.attr(attr) : null;
    }
}
