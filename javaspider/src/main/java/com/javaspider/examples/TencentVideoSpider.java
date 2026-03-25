package com.javaspider.examples;

import com.javaspider.core.*;
import com.javaspider.downloader.*;
import com.javaspider.media.*;
import com.javaspider.media.parser.*;
import com.javaspider.pipeline.*;
import com.javaspider.processor.*;

import java.util.*;

/**
 * 腾讯视频爬虫
 * 爬取腾讯视频网站视频信息
 */
public class TencentVideoSpider {
    
    public static void main(String[] args) {
        String videoUrl = "https://v.qq.com/x/cover/mzc00200rgazpwa/c4102t9ai7s.html";
        String outputDir = "./downloads/tencent_video";
        
        System.out.println("========== 腾讯视频爬虫 ==========");
        System.out.println("视频 URL: " + videoUrl);
        System.out.println("保存目录：" + outputDir);
        System.out.println();
        
        // 创建处理器
        TencentVideoProcessor processor = new TencentVideoProcessor();
        
        // 创建爬虫
        Spider.create(processor)
            .name("TencentVideoSpider")
            .thread(1)
            .addUrl(videoUrl)
            .addPipeline(new ConsolePipeline())
            .addPipeline(new FilePipeline(outputDir + "/video_info.json"))
            .start();
        
        // 等待爬虫完成
        try {
            Thread.sleep(15000);
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
        
        // 输出结果
        Map<String, Object> result = processor.getResult();
        if (!result.isEmpty()) {
            System.out.println("\n========== 爬取结果 ==========");
            System.out.println("视频标题：" + result.get("videoTitle"));
            System.out.println("视频描述：" + result.get("videoDescription"));
            System.out.println("播放次数：" + result.get("playCount"));
            System.out.println("封面图片：" + result.get("coverImage"));
            System.out.println("视频 URL: " + result.get("videoUrl"));
            System.out.println("==============================\n");
            
            // 尝试下载
            String downloadUrl = (String) result.get("videoUrl");
            if (downloadUrl != null && !downloadUrl.isEmpty()) {
                System.out.println("尝试下载视频...");
                AdvancedMediaDownloader downloader = new AdvancedMediaDownloader(outputDir);
                try {
                    MediaItem item = new MediaItem(
                        (String) result.get("videoTitle"), 
                        downloadUrl, 
                        MediaType.VIDEO
                    );
                    String filePath = downloader.downloadWithResume(item);
                    System.out.println("下载成功：" + filePath);
                } catch (Exception e) {
                    System.out.println("下载失败：" + e.getMessage());
                }
            }
        } else {
            System.out.println("\n未找到视频信息");
        }
        
        System.out.println("\n爬取完成！详细信息已保存到 " + outputDir + "/video_info.json");
    }
    
    static class TencentVideoProcessor extends BasePageProcessor {
        
        private final Map<String, Object> result;
        
        public TencentVideoProcessor() {
            this.result = new HashMap<>();
        }
        
        @Override
        public void process(Page page) {
            System.out.println("\n正在处理页面：" + page.getUrl());
            
            // 提取页面标题
            String pageTitle = page.$("title");
            result.put("pageTitle", pageTitle);
            System.out.println("页面标题：" + pageTitle);
            
            // 提取视频信息
            extractVideoInfo(page);
            
            // 提取图片
            extractImages(page);
            
            // 保存结果
            page.getResultItems().put("result", result);
        }
        
        private void extractVideoInfo(Page page) {
            // 尝试多种选择器提取标题
            String[] titleSelectors = {
                "h1.title", ".video-title", ".play-title", ".video-info-title", 
                ".meta-title", "[property=\"og:title\"]"
            };
            
            for (String selector : titleSelectors) {
                String title = page.$(selector);
                if (title != null && !title.isEmpty()) {
                    result.put("videoTitle", title.trim());
                    System.out.println("视频标题：" + title);
                    break;
                }
            }
            
            // 提取描述
            String[] descSelectors = {
                ".video-intro", ".desc", ".summary", ".video-desc", 
                ".detail-desc", "[property=\"og:description\"]"
            };
            
            for (String selector : descSelectors) {
                String desc = page.$(selector);
                if (desc != null && !desc.isEmpty()) {
                    result.put("videoDescription", desc.trim());
                    System.out.println("视频描述：" + desc);
                    break;
                }
            }
            
            // 提取播放次数
            String[] playSelectors = {
                ".play-count", ".view-count", ".hot-value"
            };
            
            for (String selector : playSelectors) {
                String count = page.$(selector);
                if (count != null && !count.isEmpty()) {
                    result.put("playCount", count.trim());
                    System.out.println("播放次数：" + count);
                    break;
                }
            }
            
            // 提取封面
            String[] coverSelectors = {
                "[property=\"og:image\"]", ".video-cover img", ".poster img"
            };
            
            for (String selector : coverSelectors) {
                String cover = page.$(selector);
                if (cover != null && !cover.isEmpty()) {
                    result.put("coverImage", cover);
                    System.out.println("封面图片：" + cover);
                    break;
                }
            }
            
            // 提取视频 URL（从 meta 标签）
            String[] videoSelectors = {
                "[property=\"og:video:url\"]", "[property=\"og:video\"]", 
                "video source", "meta[itemprop=\"contentUrl\"]"
            };
            
            for (String selector : videoSelectors) {
                String videoUrl = page.$(selector);
                if (videoUrl != null && !videoUrl.isEmpty()) {
                    result.put("videoUrl", videoUrl);
                    System.out.println("视频 URL: " + videoUrl);
                    break;
                }
            }
            
            // 如果没有找到视频 URL，尝试从页面 HTML 中提取
            if (!result.containsKey("videoUrl")) {
                extractVideoUrlFromHTML(page);
            }
        }
        
        private void extractVideoUrlFromHTML(Page page) {
            String html = page.getRawText();
            if (html == null) {
                html = page.getHtml().getDocumentHtml();
            }
            
            // 腾讯视频通常使用内嵌 JSON 数据
            // 尝试提取 video_info 或 similar
            if (html.contains("videoInfo")) {
                System.out.println("Found videoInfo in HTML");
                // 这里可以添加更复杂的解析逻辑
            }
            
            // 提取可能的视频 URL 模式
            java.util.regex.Pattern pattern = java.util.regex.Pattern.compile(
                "\"(https?://[^\"']*\\.(mp4|flv|webm|m3u8)[^\"']*)\"",
                java.util.regex.Pattern.CASE_INSENSITIVE
            );
            
            java.util.regex.Matcher matcher = pattern.matcher(html);
            StringBuilder sb = new StringBuilder();
            int count = 0;
            
            while (matcher.find() && count < 3) {
                String url = matcher.group(1);
                sb.append(url).append("\n");
                count++;
            }
            
            if (sb.length() > 0) {
                result.put("possibleVideoUrls", sb.toString());
                System.out.println("找到可能的视频 URL: " + count + " 个");
                
                // 保存第一个作为视频 URL
                String firstUrl = sb.toString().split("\n")[0];
                result.put("videoUrl", firstUrl);
            }
        }
        
        private void extractImages(Page page) {
            List<String> images = page.$$("img");
            System.out.println("找到图片：" + images.size() + " 张");
            
            // 保存前 5 张图片 URL
            StringBuilder sb = new StringBuilder();
            int count = 0;
            for (String img : images) {
                if (count >= 5) break;
                String src = extractAttribute(img, "src");
                if (src != null && !src.isEmpty() && !src.startsWith("data:")) {
                    sb.append(src).append("\n");
                    count++;
                }
            }
            result.put("images", sb.toString());
        }
        
        private String extractAttribute(String html, String attr) {
            if (html == null) return null;
            java.util.regex.Pattern pattern = java.util.regex.Pattern.compile(
                attr + "=[\"']([^\"']+)[\"']"
            );
            java.util.regex.Matcher matcher = pattern.matcher(html);
            if (matcher.find()) {
                return matcher.group(1);
            }
            return null;
        }
        
        public Map<String, Object> getResult() {
            return result;
        }
        
        @Override
        public Site getSite() {
            return Site.of("v.qq.com")
                .setUserAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
                .addCookie("pgv_pvid", java.util.UUID.randomUUID().toString())
                .setRetryTimes(3)
                .setRetrySleep(1000)
                .addHeader("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8")
                .addHeader("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8")
                .addHeader("Connection", "keep-alive")
                .addHeader("Upgrade-Insecure-Requests", "1");
        }
    }
}
