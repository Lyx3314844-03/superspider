package com.javaspider.cli;

import com.javaspider.core.Page;
import com.javaspider.core.Request;
import com.javaspider.core.Site;
import com.javaspider.core.Spider;
import com.javaspider.downloader.HttpClientDownloader;
import com.javaspider.pipeline.ConsolePipeline;
import com.javaspider.pipeline.FilePipeline;
import com.javaspider.processor.PageProcessor;
import com.javaspider.selector.Html;

import java.util.List;

/**
 * 简单网页爬虫 - 快速测试版本
 * 单线程同步爬取，立即输出结果
 */
public class QuickSpider implements PageProcessor {
    
    private Site site;
    
    public QuickSpider() {
        this.site = Site.create()
                .setUserAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
                .setRetryTimes(3)
                .setTimeout(15000);
    }
    
    @Override
    public void process(Page page) {
        System.out.println("\n═══════════════════════════════════════════════════════════");
        System.out.println("正在处理：" + page.getUrl());
        System.out.println("状态码：" + page.getStatusCode());
        System.out.println("═══════════════════════════════════════════════════════════\n");
        
        Html html = page.getHtml();
        if (html == null) {
            System.out.println("无法解析页面内容");
            return;
        }
        
        // 提取页面标题
        String title = html.xpath("//title/text()").get();
        System.out.println("【页面标题】");
        System.out.println("  " + (title != null ? title : "无标题"));
        System.out.println();
        
        // 提取所有链接
        List<String> links = html.xpath("//a/@href").all();
        System.out.println("【外部链接】(前 10 个)");
        int linkCount = 0;
        if (links != null) {
            for (String href : links) {
                if (linkCount >= 10) break;
                if (href != null && href.startsWith("http")) {
                    System.out.println("  • " + href);
                    linkCount++;
                }
            }
        }
        if (linkCount == 0) {
            System.out.println("  无外部链接");
        }
        System.out.println();
        
        // 提取所有图片
        List<String> images = html.xpath("//img/@src").all();
        System.out.println("【图片资源】(前 5 个)");
        int imgCount = 0;
        if (images != null) {
            for (String src : images) {
                if (imgCount >= 5) break;
                if (src != null && !src.isEmpty()) {
                    System.out.println("  📷 " + src);
                    imgCount++;
                }
            }
        }
        if (imgCount == 0) {
            System.out.println("  无图片资源");
        }
        System.out.println();
        
        // 提取段落文本
        List<String> paragraphs = html.xpath("//p/text()").all();
        System.out.println("【文本段落】(前 3 个)");
        int pCount = 0;
        if (paragraphs != null) {
            for (String text : paragraphs) {
                if (pCount >= 3) break;
                String trimmed = text != null ? text.trim() : "";
                if (trimmed.length() > 30) {
                    String summary = trimmed.length() > 80 ? trimmed.substring(0, 80) + "..." : trimmed;
                    System.out.println("  \"" + summary + "\"");
                    pCount++;
                }
            }
        }
        if (pCount == 0) {
            System.out.println("  无合适段落");
        }
        System.out.println();
        
        // 保存结果
        page.getResultItems().put("title", title);
        page.getResultItems().put("url", page.getUrl());
        page.getResultItems().put("links", linkCount);
        page.getResultItems().put("images", imgCount);
        
        System.out.println("✓ 页面处理完成\n");
    }
    
    @Override
    public Site getSite() {
        return site;
    }
    
    /**
     * 主方法 - 快速测试
     */
    public static void main(String[] args) {
        System.out.println("\n╔════════════════════════════════════════════════════════════╗");
        System.out.println("║     JavaSpider Quick Test - 快速网页爬虫测试               ║");
        System.out.println("╚════════════════════════════════════════════════════════════╝\n");
        
        String targetUrl = "https://example.com";
        if (args != null && args.length > 0) {
            targetUrl = args[0];
        }
        
        System.out.println("目标 URL: " + targetUrl);
        System.out.println("开始爬取...\n");
        System.out.println("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n");
        
        long startTime = System.currentTimeMillis();
        
        try {
            QuickSpider processor = new QuickSpider();
            HttpClientDownloader downloader = new HttpClientDownloader();
            
            // 创建请求
            Request request = new Request(targetUrl);
            
            // 下载页面
            System.out.println("⏳ 正在下载页面...");
            Page page = null;
            try {
                page = downloader.download(request, processor.getSite());
            } catch (Exception e) {
                System.out.println("✗ 页面下载异常：" + e.getMessage());
                System.out.println("\n详细错误:");
                e.printStackTrace();
                return;
            }
            
            if (page == null) {
                System.out.println("✗ 页面下载失败：返回为空");
                return;
            }
            
            if (page.isSkip()) {
                System.out.println("✗ 页面被跳过 (可能是网络错误)");
                System.out.println("   状态码：" + page.getStatusCode());
                return;
            }
            
            System.out.println("✓ 页面下载完成 (状态码：" + page.getStatusCode() + ")");
            System.out.println("   原始内容长度：" + (page.getRawText() != null ? page.getRawText().length() : 0) + " 字节");
            
            long downloadTime = System.currentTimeMillis() - startTime;
            System.out.println("✓ 页面下载完成 (耗时：" + downloadTime + "ms)\n");
            
            // 处理页面
            processor.process(page);
            
            // 输出统计
            long totalTime = System.currentTimeMillis() - startTime;
            System.out.println("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
            System.out.println("测试完成！");
            System.out.println("下载耗时：" + downloadTime + "ms");
            System.out.println("总耗时：" + totalTime + "ms");
            System.out.println("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n");
            
        } catch (Exception e) {
            System.err.println("✗ 测试失败：" + e.getMessage());
            e.printStackTrace();
        }
    }
}
