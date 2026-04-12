package com.javaspider.examples;

import com.javaspider.core.Page;
import com.javaspider.core.Spider;
import com.javaspider.core.Site;
import com.javaspider.media.MediaDownloader;
import com.javaspider.media.MediaItem;
import com.javaspider.media.MediaType;
import com.javaspider.pipeline.ConsolePipeline;
import com.javaspider.processor.MediaProcessor;

import java.util.List;

/**
 * 优酷视频爬虫增强版
 * 支持下载视频、图片、音乐
 */
@Deprecated(since = "2.1.0", forRemoval = false)
public class YoukuMediaSpider {
    
    public static void main(String[] args) {
        String videoUrl = "https://www.youku.tv/v/v_show/id_XNTk4Mjg1MjEzMg==.html?spm=a2hja.14919748_WEBMOVIE_JINGXUAN.drawer2.d_zj1_1&s=cfeb97262f9f4d29b86b&scm=20140719.manual.37330.show_cfeb97262f9f4d29b86b&s=cfeb97262f9f4d29b86b";
        String outputDir = "./downloads/youku_video_XNTk4Mjg1MjEzMg";
        
        System.out.println("========== 优酷媒体爬虫 ==========");
        System.out.println("视频 URL: " + videoUrl);
        System.out.println("保存目录：" + outputDir);
        System.out.println();
        
        MediaProcessor processor = new MediaProcessor(true);
        
        Spider.create(processor)
            .name("YoukuMediaSpider")
            .thread(1)
            .addUrl(videoUrl)
            .addPipeline(new ConsolePipeline())
            .start();
        
        // 等待爬虫完成
        try {
            Thread.sleep(15000);
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
        
        // 下载找到的媒体
        List<MediaItem> mediaItems = processor.getMediaItems();
        if (!mediaItems.isEmpty()) {
            System.out.println("\n========== 开始下载媒体文件 ==========");
            System.out.println("找到 " + mediaItems.size() + " 个媒体文件");
            
            MediaDownloader downloader = new MediaDownloader(outputDir, true);
            
            int downloaded = 0;
            for (MediaItem item : mediaItems) {
                try {
                    String filePath = downloader.download(item);
                    downloaded++;
                    System.out.println("[" + downloaded + "/" + mediaItems.size() + "] 已下载：" + filePath);
                } catch (Exception e) {
                    System.out.println("下载失败：" + item.getUrl() + " - " + e.getMessage());
                }
                
                // 限制下载数量
                if (downloaded >= 10) {
                    System.out.println("已达到最大下载数量 (10 个)");
                    break;
                }
            }
            
            System.out.println("\n下载完成！共下载 " + downloaded + " 个文件");
            System.out.println("保存目录：" + outputDir);
        } else {
            System.out.println("\n未找到任何媒体文件");
        }
        
        System.out.println("===================================\n");
    }
}
