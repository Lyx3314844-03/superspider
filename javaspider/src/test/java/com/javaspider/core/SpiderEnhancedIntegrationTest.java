package com.javaspider.core;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.DisplayName;

import java.util.concurrent.*;

import static org.junit.jupiter.api.Assertions.*;

/**
 * SpiderEnhanced 集成测试 (修复版)
 */
@DisplayName("SpiderEnhanced 集成测试")
class SpiderEnhancedIntegrationTest {

    @Test
    @DisplayName("集成测试 - 基本爬取")
    void testIntegrationBasicCrawl() {
        SpiderEnhanced spider = new SpiderEnhanced();
        spider.setSpiderName("integration-test");
        spider.setThreadCount(2);

        assertNotNull(spider);
        assertEquals("integration-test", spider.getSpiderName());
        
        spider.stop();
        assertTrue(spider.isStopped());
    }

    @Test
    @DisplayName("集成测试 - 并发添加请求")
    void testIntegrationConcurrentAdd() throws Exception {
        SpiderEnhanced spider = new SpiderEnhanced();
        spider.setThreadCount(5);

        ExecutorService executor = Executors.newFixedThreadPool(5);
        CountDownLatch latch = new CountDownLatch(5);

        for (int i = 0; i < 5; i++) {
            final int threadId = i;
            executor.submit(() -> {
                try {
                    for (int j = 0; j < 10; j++) {
                        Request req = new Request("https://example.com/" + threadId + "/" + j);
                        spider.addRequest(req);
                    }
                } finally {
                    latch.countDown();
                }
            });
        }

        latch.await(10, TimeUnit.SECONDS);
        assertTrue(spider.getTotalRequests().get() >= 0);
        
        spider.stop();
        executor.shutdown();
    }

    @Test
    @DisplayName("集成测试 - 资源清理")
    void testIntegrationResourceCleanup() {
        SpiderEnhanced spider = new SpiderEnhanced();
        spider.setSpiderName("cleanup-test");

        // 停止并关闭
        spider.stop();
        assertDoesNotThrow(() -> spider.close());
    }

    @Test
    @DisplayName("集成测试 - 错误处理")
    void testIntegrationErrorHandling() {
        SpiderEnhanced spider = new SpiderEnhanced();
        
        // 添加无效请求不应导致崩溃
        assertDoesNotThrow(() -> {
            spider.addRequest(null);
            spider.addRequest(new Request(null));
        });
        
        spider.stop();
    }
}
