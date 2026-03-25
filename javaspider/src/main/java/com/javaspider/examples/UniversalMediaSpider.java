package com.javaspider.examples;

import com.javaspider.core.Page;
import com.javaspider.core.Spider;
import com.javaspider.core.Site;
import com.javaspider.media.MediaDownloader;
import com.javaspider.media.MediaItem;
import com.javaspider.media.MediaType;
import com.javaspider.pipeline.ConsolePipeline;
import com.javaspider.pipeline.FilePipeline;
import com.javaspider.processor.BasePageProcessor;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * 通用媒体爬虫
 * 支持爬取任何网站的视频、图片、音乐
 */
public class UniversalMediaSpider {
    
    public static void main(String[] args) {
        if (args.length == 0) {
            System.out.println("用法：UniversalMediaSpider <URL> [outputDir]");
            System.out.println("示例：UniversalMediaSpider https://www.example.com/video ./downloads");
            return;
        }
        
        String url = args[0];
        String outputDir = args.length > 1 ? args[1] : "./media_downloads";
        
        System.out.println("========== 通用媒体爬虫 ==========");
        System.out.println("目标 URL: " + url);
        System.out.println("保存目录：" + outputDir);
        System.out.println();
        
        Spider.create(new UniversalMediaProcessor(url))
            .name("UniversalMediaSpider")
            .thread(1)
            .addUrl(url)
            .addPipeline(new ConsolePipeline())
            .addPipeline(new FilePipeline(outputDir + "/media_info.json"))
            .start();
        
        // 等待爬虫完成
        try {
            Thread.sleep(15000);
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
        
        System.out.println("\n爬取完成！媒体信息已保存到 " + outputDir + "/media_info.json");
    }
    
    static class UniversalMediaProcessor extends BasePageProcessor {
        
        private final String targetUrl;
        private Map<String, Object> mediaInfo;
        
        public UniversalMediaProcessor(String targetUrl) {
            this.targetUrl = targetUrl;
            this.mediaInfo = new HashMap<>();
        }
        
        @Override
        public void process(Page page) {
            System.out.println("\n正在处理页面：" + page.getUrl());
            
            // 提取页面标题
            String title = page.$("title");
            if (title == null || title.isEmpty()) {
                title = page.xpath("//title/text()");
            }
            mediaInfo.put("pageTitle", title != null ? title : "Unknown");
            
            // 提取所有视频
            List<String> videos = page.$$("video source");
            System.out.println("找到视频源：" + videos.size() + " 个");
            
            // 提取所有图片
            List<String> images = page.$$("img");
            System.out.println("找到图片：" + images.size() + " 个");
            
            // 提取所有音频
            List<String> audios = page.$$("audio source");
            System.out.println("找到音频源：" + audios.size() + " 个");
            
            // 提取 meta 信息
            String ogVideo = page.$("meta[property=og:video]");
            String ogImage = page.$("meta[property=og:image]");
            String ogTitle = page.$("meta[property=og:title]");
            String ogDesc = page.$("meta[property=og:description]");
            
            mediaInfo.put("ogVideo", ogVideo);
            mediaInfo.put("ogImage", ogImage);
            mediaInfo.put("ogTitle", ogTitle);
            mediaInfo.put("ogDescription", ogDesc);
            
            // 提取视频信息（针对优酷等网站）
            extractVideoInfo(page);
            
            // 保存媒体列表
            Map<String, Object> mediaList = new HashMap<>();
            mediaList.put("videos", videos);
            mediaList.put("images", images);
            mediaList.put("audios", audios);
            mediaList.put("meta", mediaInfo);
            
            page.getResultItems().put("mediaList", mediaList);
            
            // 输出结果
            System.out.println("\n========== 页面信息 ==========");
            System.out.println("页面标题：" + mediaInfo.get("pageTitle"));
            System.out.println("OG 标题：" + mediaInfo.get("ogTitle"));
            System.out.println("OG 描述：" + mediaInfo.get("ogDescription"));
            System.out.println("OG 视频：" + mediaInfo.get("ogVideo"));
            System.out.println("OG 图片：" + mediaInfo.get("ogImage"));
            System.out.println("==============================\n");
        }
        
        /**
         * 提取视频网站特定信息
         */
        private void extractVideoInfo(Page page) {
            String url = page.getUrl();
            
            if (url.contains("youku")) {
                // 优酷
                mediaInfo.put("site", "Youku");
                mediaInfo.put("videoTitle", page.$("h1.title"));
                mediaInfo.put("videoDesc", page.$(".video-intro"));
            } else if (url.contains("qq")) {
                // 腾讯
                mediaInfo.put("site", "Tencent");
                mediaInfo.put("videoTitle", page.$(".video-title"));
                mediaInfo.put("videoDesc", page.$(".video-desc"));
            } else if (url.contains("iqiyi")) {
                // 爱奇艺
                mediaInfo.put("site", "iQiyi");
                mediaInfo.put("videoTitle", page.$(".video-title"));
                mediaInfo.put("videoDesc", page.$(".video-intro"));
            } else if (url.contains("bilibili")) {
                // B 站
                mediaInfo.put("site", "Bilibili");
                mediaInfo.put("videoTitle", page.$("h1.video-title"));
                mediaInfo.put("videoDesc", page.$(".video-desc"));
            }
        }
        
        @Override
        public Site getSite() {
            return Site.of("*")
                .setUserAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
                .addCookie("locale", "zh_CN")
                .setRetryTimes(3)
                .setRetrySleep(1000)
                .addHeader("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8")
                .addHeader("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8")
                .addHeader("Connection", "keep-alive")
                .addHeader("Upgrade-Insecure-Requests", "1");
        }
    }
}
