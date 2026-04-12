package com.javaspider.examples;

import com.javaspider.core.Page;
import com.javaspider.core.Spider;
import com.javaspider.core.Site;
import com.javaspider.pipeline.ConsolePipeline;
import com.javaspider.pipeline.FilePipeline;
import com.javaspider.processor.BasePageProcessor;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * 优酷视频爬虫
 * 爬取优酷视频信息
 */
@Deprecated(since = "2.1.0", forRemoval = false)
public class YoukuVideoSpider {
    
    public static void main(String[] args) {
        String videoUrl = "https://www.youku.tv/v/v_show/id_XNTk4Mjg1MjEzMg==.html";
        
        System.out.println("开始爬取优酷视频...");
        System.out.println("视频 URL: " + videoUrl);
        System.out.println();
        
        Spider.create(new YoukuVideoProcessor())
            .name("YoukuVideoSpider")
            .thread(1)
            .addUrl(videoUrl)
            .addPipeline(new ConsolePipeline())
            .addPipeline(new FilePipeline("results/youku_video.json"))
            .start();
        
        // 等待爬虫完成
        try {
            Thread.sleep(10000);
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
        
        System.out.println("\n爬取完成！结果已保存到 results/youku_video.json");
    }
    
    static class YoukuVideoProcessor extends BasePageProcessor {
        @Override
        public void process(Page page) {
            // 提取视频标题
            String title = page.$("h1.title");
            if (title == null || title.isEmpty()) {
                title = page.$(".video-title");
            }
            if (title == null || title.isEmpty()) {
                title = page.xpath("//title/text()");
            }
            
            // 提取视频简介
            String description = page.$(".video-intro");
            if (description == null || description.isEmpty()) {
                description = page.$(".desc");
            }
            if (description == null || description.isEmpty()) {
                description = page.$("meta[name=description]");
            }
            
            // 提取播放次数
            String playCount = page.$(".play-count");
            if (playCount == null || playCount.isEmpty()) {
                playCount = page.regex("播放 [：:][\\s]*([\\d,\\.]+ 万？)");
            }
            
            // 提取视频时长
            String duration = page.$(".video-duration");
            if (duration == null || duration.isEmpty()) {
                duration = page.regex("时长 [：:][\\s]*([\\d:]+)");
            }
            
            // 提取上传者
            String uploader = page.$(".uploader-name");
            if (uploader == null || uploader.isEmpty()) {
                uploader = page.$(".user-name");
            }
            if (uploader == null || uploader.isEmpty()) {
                uploader = page.$("meta[property=video:creator]");
            }
            
            // 提取上传时间
            String uploadTime = page.$(".upload-time");
            if (uploadTime == null || uploadTime.isEmpty()) {
                uploadTime = page.regex("上传时间 [：:][\\s]*([\\d-]+)");
            }
            
            // 提取视频标签
            List<String> tags = page.$$(".video-tag a");
            if (tags == null || tags.isEmpty()) {
                tags = page.$$(".tag-link");
            }
            
            // 提取视频封面
            String coverImage = page.$(".video-cover img");
            if (coverImage == null || coverImage.isEmpty()) {
                coverImage = page.$("meta[property=og:image]");
            }
            
            // 提取视频 URL
            String videoUrl = page.$("video source");
            if (videoUrl == null || videoUrl.isEmpty()) {
                videoUrl = page.$("meta[property=og:video:url]");
            }
            
            // 保存结果
            Map<String, Object> result = new HashMap<>();
            result.put("title", title != null && !title.isEmpty() ? title : "未找到");
            result.put("description", description != null && !description.isEmpty() ? description : "未找到");
            result.put("playCount", playCount != null && !playCount.isEmpty() ? playCount : "未找到");
            result.put("duration", duration != null && !duration.isEmpty() ? duration : "未找到");
            result.put("uploader", uploader != null && !uploader.isEmpty() ? uploader : "未找到");
            result.put("uploadTime", uploadTime != null && !uploadTime.isEmpty() ? uploadTime : "未找到");
            result.put("tags", tags != null ? tags : java.util.Collections.emptyList());
            result.put("coverImage", coverImage != null && !coverImage.isEmpty() ? coverImage : "未找到");
            result.put("videoUrl", videoUrl != null && !videoUrl.isEmpty() ? videoUrl : "未找到");
            result.put("crawlTime", System.currentTimeMillis());
            result.put("sourceUrl", page.getUrl());
            
            page.getResultItems().put("videoInfo", result);
            
            // 输出结果
            System.out.println("\n========== 视频信息 ==========");
            System.out.println("标题：" + result.get("title"));
            System.out.println("简介：" + result.get("description"));
            System.out.println("播放次数：" + result.get("playCount"));
            System.out.println("时长：" + result.get("duration"));
            System.out.println("上传者：" + result.get("uploader"));
            System.out.println("上传时间：" + result.get("uploadTime"));
            System.out.println("标签：" + result.get("tags"));
            System.out.println("封面：" + result.get("coverImage"));
            System.out.println("视频 URL: " + result.get("videoUrl"));
            System.out.println("爬取时间：" + new java.util.Date((Long) result.get("crawlTime")));
            System.out.println("==============================\n");
        }
        
        @Override
        public Site getSite() {
            return Site.of("youku.tv")
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
