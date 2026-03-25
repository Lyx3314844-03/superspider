package com.javaspider.examples;

import com.javaspider.core.*;
import com.javaspider.downloader.*;
import com.javaspider.pipeline.*;
import com.javaspider.processor.*;

import java.util.*;

/**
 * 腾讯视频爬虫（Selenium 增强版）
 */
public class TencentVideoSpiderEnhanced {
    
    public static void main(String[] args) {
        String videoUrl = "https://v.qq.com/x/cover/mzc00200rgazpwa/c4102t9ai7s.html";
        String outputDir = "./downloads/tencent_video_enhanced";
        
        // 创建输出目录
        new java.io.File(outputDir).mkdirs();
        
        System.out.println("========== 腾讯视频爬虫（增强版） ==========");
        System.out.println("视频 URL: " + videoUrl);
        System.out.println("保存目录：" + outputDir);
        System.out.println();
        
        // 创建 Selenium 下载器（简化版）
        SeleniumDownloader downloader = new SeleniumDownloader("chrome", true);
        
        // 创建处理器
        TencentVideoProcessor processor = new TencentVideoProcessor();
        
        System.out.println("开始爬取...");
        
        // 直接使用下载器获取页面
        com.javaspider.core.Request request = new com.javaspider.core.Request(videoUrl);
        com.javaspider.core.Page page = downloader.download(request, getSite());
        
        if (page != null && !page.isSkip()) {
            System.out.println("页面获取成功！");
            processor.process(page);
        } else {
            System.out.println("页面获取失败");
        }
        
        // 输出结果
        Map<String, Object> result = processor.getResult();
        if (!result.isEmpty()) {
            System.out.println("\n========== 爬取结果 ==========");
            System.out.println("视频标题：" + result.get("videoTitle"));
            System.out.println("视频描述：" + result.get("videoDescription"));
            System.out.println("播放次数：" + result.get("playCount"));
            System.out.println("封面图片：" + result.get("coverImage"));
            System.out.println("==============================\n");
            
            // 保存结果
            saveResult(result, outputDir + "/video_info.json");
        }
        
        // 关闭浏览器
        downloader.close();
        
        System.out.println("爬取完成！详细信息已保存到 " + outputDir + "/video_info.json");
    }
    
    private static void saveResult(Map<String, Object> result, String filePath) {
        try (java.io.FileWriter writer = new java.io.FileWriter(filePath)) {
            com.google.gson.Gson gson = new com.google.gson.GsonBuilder().setPrettyPrinting().create();
            writer.write(gson.toJson(result));
            System.out.println("结果已保存：" + filePath);
        } catch (Exception e) {
            System.err.println("保存失败：" + e.getMessage());
        }
    }
    
    private static com.javaspider.core.Site getSite() {
        return com.javaspider.core.Site.of("v.qq.com")
            .setUserAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36");
    }
    
    static class TencentVideoProcessor extends BasePageProcessor {
        
        private final Map<String, Object> result;
        
        public TencentVideoProcessor() {
            this.result = new HashMap<>();
        }
        
        @Override
        public void process(Page page) {
            System.out.println("\n正在处理页面：" + page.getUrl());
            
            // 等待页面加载
            try {
                Thread.sleep(3000);
            } catch (InterruptedException e) {
                e.printStackTrace();
            }
            
            // 提取页面标题
            String pageTitle = page.$("title");
            result.put("pageTitle", pageTitle);
            System.out.println("页面标题：" + pageTitle);
            
            // 提取视频信息
            extractVideoInfo(page);
            
            // 保存结果
            page.getResultItems().put("result", result);
        }
        
        private void extractVideoInfo(Page page) {
            // 尝试多种选择器提取标题
            String[] titleSelectors = {
                "h1.title", ".video-title", ".play-title", ".video-info-title", 
                ".meta-title", "[property=\"og:title\"]", ".video-title-text"
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
                ".detail-desc", "[property=\"og:description\"]", ".video-desc-text"
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
        }
        
        public Map<String, Object> getResult() {
            return result;
        }
        
        @Override
        public Site getSite() {
            return Site.of("v.qq.com")
                .setUserAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
                .addCookie("pgv_pvid", UUID.randomUUID().toString())
                .setRetryTimes(3)
                .setRetrySleep(1000);
        }
    }
}
