package com.javaspider.cli;

import com.javaspider.core.Page;
import com.javaspider.core.Site;
import com.javaspider.core.Spider;
import com.javaspider.selector.Html;
import com.javaspider.pipeline.ConsolePipeline;
import com.javaspider.pipeline.FilePipeline;
import com.javaspider.processor.PageProcessor;

import java.util.List;

/**
 * 通用网页爬虫处理器
 * 支持基础网页抓取、链接提取、内容输出
 */
public class SimplePageProcessor implements PageProcessor {
    
    private Site site;
    private String startUrl;
    
    public SimplePageProcessor(String startUrl) {
        this.startUrl = startUrl;
        this.site = Site.create()
                .setUserAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
                .setDownloadDelay(1000)
                .setRetryTimes(3)
                .setTimeout(10000);
    }
    
    @Override
    public void process(Page page) {
        Html html = page.getHtml();
        if (html == null) {
            System.out.println("无法获取页面内容：" + page.getUrl());
            return;
        }
        
        // 提取页面标题
        String title = html.xpath("//title/text()").get();
        System.out.println("\n═══════════════════════════════════════════════════════════");
        System.out.println("页面标题：" + (title != null ? title : "无标题"));
        System.out.println("页面 URL: " + page.getUrl());
        System.out.println("═══════════════════════════════════════════════════════════\n");
        
        // 提取所有链接
        List<String> links = html.xpath("//a/@href").all();
        System.out.println("发现链接数：" + (links != null ? links.size() : 0));
        
        // 输出前 10 个链接
        int count = 0;
        if (links != null) {
            for (String href : links) {
                if (count >= 10) break;
                if (href != null && !href.isEmpty()) {
                    System.out.println("  [" + (count + 1) + "] " + href);
                    
                    // 添加新链接到爬虫队列
                    if (href.startsWith("http") && count < 5) {
                        page.addTargetRequest(href);
                    }
                }
                count++;
            }
        }
        
        // 提取所有图片
        List<String> images = html.xpath("//img/@src").all();
        System.out.println("\n发现图片数：" + (images != null ? images.size() : 0));
        
        // 输出前 5 个图片
        count = 0;
        if (images != null) {
            for (String src : images) {
                if (count >= 5) break;
                if (src != null && !src.isEmpty()) {
                    System.out.println("  [图片" + (count + 1) + "] " + src);
                }
                count++;
            }
        }
        
        // 提取所有段落
        List<String> paragraphs = html.xpath("//p/text()").all();
        System.out.println("\n发现段落数：" + (paragraphs != null ? paragraphs.size() : 0));
        
        // 输出前 3 个段落的内容摘要
        count = 0;
        if (paragraphs != null) {
            for (String text : paragraphs) {
                if (count >= 3) break;
                if (text != null && text.trim().length() > 20) {
                    String summary = text.trim().length() > 100 ? text.trim().substring(0, 100) + "..." : text.trim();
                    System.out.println("  [段落" + (count + 1) + "] " + summary);
                }
                count++;
            }
        }
        
        // 保存结果
        page.getResultItems().put("title", title);
        page.getResultItems().put("url", page.getUrl());
        page.getResultItems().put("linkCount", links != null ? links.size() : 0);
        page.getResultItems().put("imageCount", images != null ? images.size() : 0);
    }
    
    @Override
    public Site getSite() {
        return site;
    }
    
    /**
     * 创建爬虫实例
     */
    public static Spider createSpider(String startUrl) {
        SimplePageProcessor processor = new SimplePageProcessor(startUrl);
        Spider spider = new Spider();
        spider.setProcessor(processor);
        spider.setSite(processor.getSite());
        spider.setThreadCount(3);
        
        // 添加管道
        spider.addPipeline(new ConsolePipeline());
        spider.addPipeline(new FilePipeline("C:\\Users\\Administrator\\spider\\javaspider\\output"));
        
        return spider;
    }
    
    /**
     * 主方法 - 命令行入口
     */
    public static void main(String[] args) {
        System.out.println("\n╔════════════════════════════════════════════════════════════╗");
        System.out.println("║          JavaSpider Enhanced v2.0.0                      ║");
        System.out.println("║          通用网页爬虫处理器                                ║");
        System.out.println("╚════════════════════════════════════════════════════════════╝\n");
        
        String targetUrl = "https://example.com";
        
        // 解析命令行参数
        if (args != null && args.length > 0) {
            targetUrl = args[0];
        } else {
            System.out.println("使用方法：");
            System.out.println("  mvn exec:java -Dexec.mainClass=\"com.javaspider.cli.SimplePageProcessor\" -Dexec.args=\"<URL>\"");
            System.out.println("\n未指定 URL，使用默认 URL: " + targetUrl);
        }
        
        System.out.println("目标 URL: " + targetUrl);
        System.out.println("开始爬取...\n");
        
        try {
            Spider spider = createSpider(targetUrl);
            
            // 添加起始请求
            spider.addUrl(targetUrl);
            
            // 运行爬虫（同步模式）
            spider.thread(3).start();
            
            // 等待完成（最多等待 30 秒）
            spider.await(30000);
            
            // 停止爬虫
            spider.stop();
            
            System.out.println("\n═══════════════════════════════════════════════════════════");
            System.out.println("爬虫完成！");
            System.out.println("总请求数：" + spider.getTotalRequests());
            System.out.println("成功数：" + spider.getSuccessRequests());
            System.out.println("失败数：" + spider.getFailedRequests());
            System.out.println("输出目录：C:\\Users\\Administrator\\spider\\javaspider\\output");
            System.out.println("═══════════════════════════════════════════════════════════\n");
            
        } catch (Exception e) {
            System.err.println("爬虫运行失败：" + e.getMessage());
            e.printStackTrace();
        }
    }
}
