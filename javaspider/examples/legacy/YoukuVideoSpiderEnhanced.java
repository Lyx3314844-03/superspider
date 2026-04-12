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
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * 优酷视频爬虫 - 增强版
 * 支持爬取优酷视频信息和媒体文件
 */
@Deprecated(since = "2.1.0", forRemoval = false)
public class YoukuVideoSpiderEnhanced {
    
    public static void main(String[] args) {
        String videoUrl = "https://www.youku.tv/v/v_show/id_XNTk4Mjg1MjEzMg==.html?spm=a2hja.14919748_WEBMOVIE_JINGXUAN.drawer2.d_zj1_1&s=cfeb97262f9f4d29b86b&scm=20140719.manual.37330.show_cfeb97262f9f4d29b86b&s=cfeb97262f9f4d29b86b";
        String outputDir = "./downloads/youku_video_XNTk4Mjg1MjEzMg";
        
        System.out.println("========== 优酷视频爬虫（增强版） ==========");
        System.out.println("视频 URL: " + videoUrl);
        System.out.println("保存目录：" + outputDir);
        System.out.println();
        
        EnhancedYoukuProcessor processor = new EnhancedYoukuProcessor();
        
        Spider.create(processor)
            .name("YoukuVideoSpiderEnhanced")
            .thread(1)
            .addUrl(videoUrl)
            .addPipeline(new ConsolePipeline())
            .addPipeline(new FilePipeline(outputDir + "/video_info.json"))
            .start();
        
        // 等待爬虫完成
        try {
            Thread.sleep(20000);
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
        
        // 输出结果
        Map<String, Object> result = processor.getResult();
        if (!result.isEmpty()) {
            System.out.println("\n========== 爬取结果 ==========");
            System.out.println("页面标题：" + result.get("pageTitle"));
            System.out.println("视频标题：" + result.get("videoTitle"));
            System.out.println("视频描述：" + result.get("videoDescription"));
            System.out.println("播放器 URL: " + result.get("playerUrl"));
            System.out.println("封面图片：" + result.get("coverImage"));
            System.out.println("==============================\n");
            
            // 尝试下载
            String downloadUrl = (String) result.get("downloadUrl");
            if (downloadUrl != null && !downloadUrl.isEmpty()) {
                System.out.println("找到下载 URL，尝试下载...");
                MediaDownloader downloader = new MediaDownloader(outputDir);
                try {
                    MediaItem item = new MediaItem((String) result.get("videoTitle"), downloadUrl, MediaType.VIDEO);
                    String filePath = downloader.download(item);
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
    
    static class EnhancedYoukuProcessor extends BasePageProcessor {
        
        private final Map<String, Object> result;
        
        public EnhancedYoukuProcessor() {
            this.result = new HashMap<>();
        }
        
        @Override
        public void process(Page page) {
            System.out.println("\n正在处理页面：" + page.getUrl());
            
            // 提取页面标题
            String pageTitle = page.$("title");
            result.put("pageTitle", pageTitle);
            System.out.println("页面标题：" + pageTitle);
            
            // 提取视频信息 - 多种选择器尝试
            extractVideoInfo(page);
            
            // 提取图片
            extractImages(page);
            
            // 提取可能的视频 URL
            extractVideoUrls(page);
            
            // 保存结果
            page.getResultItems().put("result", result);
        }
        
        private void extractVideoInfo(Page page) {
            // 尝试多种选择器
            String[] titleSelectors = {
                "h1.title", ".video-title", ".play-title", "h1", ".meta-title"
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
                ".video-intro", ".desc", ".summary", ".video-desc", ".detail-desc"
            };
            
            for (String selector : descSelectors) {
                String desc = page.$(selector);
                if (desc != null && !desc.isEmpty()) {
                    result.put("videoDescription", desc.trim());
                    System.out.println("视频描述：" + desc);
                    break;
                }
            }
            
            // 提取播放器
            String playerUrl = page.$("meta[property=og:video:url]");
            if (playerUrl == null || playerUrl.isEmpty()) {
                playerUrl = page.$("meta[property=og:video]");
            }
            result.put("playerUrl", playerUrl);
            
            // 提取封面
            String coverImage = page.$("meta[property=og:image]");
            if (coverImage == null || coverImage.isEmpty()) {
                coverImage = page.$(".video-cover img");
            }
            result.put("coverImage", coverImage);
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
        
        private void extractVideoUrls(Page page) {
            String html = page.getRawText();
            if (html == null) {
                html = page.getHtml().getDocumentHtml();
            }
            
            // 正则提取视频 URL
            Pattern pattern = Pattern.compile(
                "https?://[^\\s\"']+\\.(mp4|avi|mkv|mov|wmv|flv|webm|m3u8)",
                Pattern.CASE_INSENSITIVE
            );
            
            Matcher matcher = pattern.matcher(html);
            StringBuilder sb = new StringBuilder();
            int count = 0;
            
            while (matcher.find() && count < 5) {
                String url = matcher.group();
                sb.append(url).append("\n");
                count++;
            }
            
            if (sb.length() > 0) {
                result.put("videoUrls", sb.toString());
                System.out.println("找到视频 URL: " + count + " 个");
                
                // 保存第一个作为下载 URL
                String firstUrl = sb.toString().split("\n")[0];
                result.put("downloadUrl", firstUrl);
            }
        }
        
        private String extractAttribute(String html, String attr) {
            if (html == null) return null;
            Pattern pattern = Pattern.compile(attr + "=[\"']([^\"']+)[\"']");
            Matcher matcher = pattern.matcher(html);
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
