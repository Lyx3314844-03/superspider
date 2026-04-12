package com.javaspider.examples;

import com.javaspider.core.Page;
import com.javaspider.core.Site;
import com.javaspider.core.Spider;
import com.javaspider.processor.BasePageProcessor;
import com.javaspider.scheduler.RedisScheduler;

/**
 * 分布式爬虫示例 (Java)
 * 与 Go, Python, Rust 共享任务队列
 */
public class DistributedExample {
    
    /**
     * 简单的分布式处理器
     */
    static class SimpleDistributedProcessor extends BasePageProcessor {
        private Site site = Site.me();
        
        @Override
        public Site getSite() {
            return site;
        }
        
        @Override
        public void process(Page page) {
            System.out.println("[Java] 正在处理: " + page.getUrl());
            // 可以在这里产生新任务，它们会自动进入共享队列
            // page.addTargetRequest("...");
        }
    }
    
    public static void main(String[] args) {
        // 创建处理器
        SimpleDistributedProcessor processor = new SimpleDistributedProcessor();
        
        // 创建 Redis 调度器 (指向统一队列)
        RedisScheduler scheduler = new RedisScheduler("localhost", 6379, "JavaSpiderNode");

        // 创建爬虫
        Spider spider = Spider.create(processor)
                .name("SharedSpider")
                .scheduler(scheduler)
                .thread(2);

        System.out.println("Java 分布式爬虫节点启动...");
        spider.start();
    }
}
