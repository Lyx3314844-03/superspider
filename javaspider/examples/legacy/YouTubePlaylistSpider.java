package com.javaspider.examples;

import com.javaspider.browser.BrowserManager;
import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.jsoup.nodes.Element;

import java.io.FileWriter;
import java.io.PrintWriter;
import java.util.ArrayList;
import java.util.List;

/**
 * YouTube 播放列表爬虫
 * 爬取播放列表中所有视频的标题、时长、链接等信息
 * 
 * 目标播放列表：{@code https://www.youtube.com/watch?v=tr5yZ2TzXaY&amp;list=PLRuPQZBVD6vV89UKIzUwZFUhDx9DjXLxc}
 */
@Deprecated(since = "2.1.0", forRemoval = false)
public class YouTubePlaylistSpider {

    private static final String PLAYLIST_URL = "https://www.youtube.com/watch?v=tr5yZ2TzXaY&list=PLRuPQZBVD6vV89UKIzUwZFUhDx9DjXLxc";

    public static void main(String[] args) {
        System.out.println("╔═══════════════════════════════════════════════════════════╗");
        System.out.println("║           YouTube 播放列表爬虫                             ║");
        System.out.println("╚═══════════════════════════════════════════════════════════╝");
        System.out.println();
        System.out.println("播放列表 URL: " + PLAYLIST_URL);
        System.out.println();

        BrowserManager browser = new BrowserManager(BrowserManager.BrowserType.CHROME, true, false);
        browser.init();

        try {
            // 导航到播放列表
            System.out.println("正在加载播放列表页面...");
            browser.navigate(PLAYLIST_URL);
            browser.waitForPageLoad();

            // 等待视频列表加载
            System.out.println("等待视频列表加载...");
            Thread.sleep(5000);

            // 滚动加载所有视频
            System.out.println("滚动加载所有视频...");
            for (int i = 0; i < 5; i++) {
                browser.scrollToBottom();
                Thread.sleep(1000);
                browser.scrollToTop();
            }

            // 获取页面 HTML
            String html = browser.getPageSource();

            // 解析视频列表
            List<VideoInfo> videos = parsePlaylist(html);

            System.out.println();
            System.out.println("═══════════════════════════════════════════════════════════");
            System.out.println("                      爬取结果                              ");
            System.out.println("═══════════════════════════════════════════════════════════");
            System.out.println("共找到 " + videos.size() + " 个视频");
            System.out.println();

            // 打印结果
            for (int i = 0; i < videos.size(); i++) {
                VideoInfo video = videos.get(i);
                System.out.printf("%d. %s%n", i + 1, video.title);
                System.out.printf("   时长：%s%n", video.duration);
                System.out.printf("   链接：%s%n", video.url);
                System.out.println();
            }

            // 保存到文件
            saveToFile(videos, "youtube_playlist_result.txt");
            System.out.println("结果已保存到：youtube_playlist_result.txt");

        } catch (Exception e) {
            System.err.println("爬取失败：" + e.getMessage());
            e.printStackTrace();
        } finally {
            browser.close();
        }
    }

    /**
     * 解析播放列表中的视频
     */
    private static List<VideoInfo> parsePlaylist(String html) {
        List<VideoInfo> videos = new ArrayList<>();
        Document doc = Jsoup.parse(html);

        // YouTube 播放列表视频项
        for (Element video : doc.select("ytd-playlist-video-renderer")) {
            VideoInfo info = new VideoInfo();

            // 提取标题
            Element titleElem = video.selectFirst("#video-title");
            if (titleElem != null) {
                info.title = titleElem.text().trim();
                info.url = titleElem.attr("abs:href");
            }

            // 提取时长
            Element durationElem = video.selectFirst("span.ytd-thumbnail-overlay-time-status-renderer");
            if (durationElem != null) {
                info.duration = durationElem.text().trim();
            }

            // 提取频道名称
            Element channelElem = video.selectFirst("#channel-name #text");
            if (channelElem != null) {
                info.channel = channelElem.text().trim();
            }

            // 只添加有标题的视频
            if (info.title != null && !info.title.isEmpty()) {
                videos.add(info);
            }
        }

        // 如果没有找到，尝试备用选择器
        if (videos.isEmpty()) {
            System.out.println("使用备用选择器重新解析...");
            
            // 尝试从不同的结构中提取
            for (Element video : doc.select("a#video-title")) {
                VideoInfo info = new VideoInfo();
                info.title = video.text().trim();
                info.url = video.attr("abs:href");
                
                if (!info.title.isEmpty()) {
                    videos.add(info);
                }
            }
        }

        return videos;
    }

    /**
     * 保存到文件
     */
    private static void saveToFile(List<VideoInfo> videos, String filename) {
        try (PrintWriter writer = new PrintWriter(new FileWriter(filename, java.nio.charset.StandardCharsets.UTF_8))) {
            writer.println("YouTube 播放列表视频列表");
            writer.println("═══════════════════════════════════════════════════════════");
            writer.println("播放列表 URL: " + PLAYLIST_URL);
            writer.println("爬取时间：" + new java.util.Date());
            writer.println("视频总数：" + videos.size());
            writer.println();
            writer.println("═══════════════════════════════════════════════════════════");
            writer.println();

            for (int i = 0; i < videos.size(); i++) {
                VideoInfo video = videos.get(i);
                writer.printf("%d. %s%n", i + 1, video.title);
                writer.printf("   时长：%s%n", video.duration != null ? video.duration : "N/A");
                writer.printf("   频道：%s%n", video.channel != null ? video.channel : "N/A");
                writer.printf("   链接：%s%n", video.url);
                writer.println();
            }
        } catch (Exception e) {
            System.err.println("保存文件失败：" + e.getMessage());
        }
    }

    /**
     * 视频信息类
     */
    static class VideoInfo {
        String title;
        String duration;
        String channel;
        String url;

        @Override
        public String toString() {
            return String.format("VideoInfo{title='%s', duration='%s', url='%s'}", 
                title, duration, url);
        }
    }
}
