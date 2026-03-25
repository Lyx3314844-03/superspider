package com.javaspider.core;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.DisplayName;
import static org.junit.jupiter.api.Assertions.*;

import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;

/**
 * SpiderEnhanced 单元测试
 */
@DisplayName("SpiderEnhanced 测试")
class SpiderEnhancedTest {

    @Test
    @DisplayName("测试初始化")
    void testInitialization() {
        SpiderEnhanced spider = new SpiderEnhanced();
        
        assertNotNull(spider);
        assertNotNull(spider.spiderId);
        assertEquals(5, spider.threadCount);
        assertFalse(spider.running);
        assertFalse(spider.stopped);
    }

    @Test
    @DisplayName("测试构建器模式")
    void testBuilder() {
        SpiderEnhanced spider = SpiderEnhanced.builder()
            .name("TestSpider")
            .threads(10)
            .rateLimit(100.0)
            .timeout(5000)
            .build();
        
        assertEquals("TestSpider", spider.spiderName);
        assertEquals(10, spider.threadCount);
        assertEquals(100.0, spider.rateLimit, 0.01);
        assertEquals(5000, spider.timeout);
    }

    @Test
    @DisplayName("测试启动和停止")
    void testStartAndStop() {
        SpiderEnhanced spider = SpiderEnhanced.builder()
            .name("StartStopTest")
            .threads(1)
            .build();
        
        assertFalse(spider.running);
        
        spider.stop();
        
        assertTrue(spider.stopped);
        assertFalse(spider.running);
    }

    @Test
    @DisplayName("测试异步启动")
    void testAsyncStart() {
        SpiderEnhanced spider = SpiderEnhanced.builder()
            .name("AsyncTest")
            .threads(1)
            .build();
        
        CompletableFuture<Void> future = spider.startAsync();
        
        // 等待一小段时间
        try {
            Thread.sleep(100);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
        
        spider.stop();
        
        // 不应该抛出异常
        assertDoesNotThrow(() -> future.cancel(true));
    }

    @Test
    @DisplayName("测试暂停和恢复")
    void testPauseAndResume() {
        SpiderEnhanced spider = new SpiderEnhanced();
        
        assertFalse(spider.paused);
        
        spider.pause();
        assertTrue(spider.paused);
        
        spider.resume();
        assertFalse(spider.paused);
    }

    @Test
    @DisplayName("测试统计信息")
    void testStats() {
        SpiderEnhanced spider = SpiderEnhanced.builder()
            .name("StatsTest")
            .build();
        
        SpiderEnhanced.SpiderStats stats = spider.getStats();
        
        assertNotNull(stats);
        assertEquals(0, stats.totalRequests);
        assertEquals(0, stats.successRequests);
        assertEquals(0, stats.failedRequests);
        assertEquals(0, stats.totalItems);
    }

    @Test
    @DisplayName("测试链式调用")
    void testChaining() {
        SpiderEnhanced spider = SpiderEnhanced.builder()
            .name("ChainTest")
            .build();
        
        SpiderEnhanced result = spider
            .threadCount(10)
            .rateLimit(50.0)
            .timeout(3000);
        
        assertSame(spider, result);
        assertEquals(10, spider.threadCount);
        assertEquals(50.0, spider.rateLimit, 0.01);
        assertEquals(3000, spider.timeout);
    }

    @Test
    @DisplayName("测试对象池")
    void testObjectPool() {
        SpiderEnhanced spider = new SpiderEnhanced();
        
        // 对象池应该预填充
        assertEquals(100, spider.pagePool.size());
        
        // 获取一个 Page
        var page = spider.acquirePage();
        assertNotNull(page);
        
        // 回收 Page
        spider.recyclePage(page);
        
        // 池大小应该恢复
        assertEquals(100, spider.pagePool.size());
    }

    @Test
    @DisplayName("测试速率限制")
    void testRateLimit() {
        SpiderEnhanced spider = SpiderEnhanced.builder()
            .rateLimit(10.0) // 每秒 10 个请求
            .build();
        
        long start = System.currentTimeMillis();
        
        // 模拟多次速率限制检查
        for (int i = 0; i < 5; i++) {
            spider.applyRateLimit();
        }
        
        long elapsed = System.currentTimeMillis() - start;
        
        // 应该有适当的延迟
        assertTrue(elapsed >= 400, "Rate limit should cause delay");
    }

    @Test
    @DisplayName("测试资源清理")
    void testResourceCleanup() {
        SpiderEnhanced spider = SpiderEnhanced.builder()
            .name("CleanupTest")
            .build();
        
        // 启动然后停止
        spider.start();
        spider.stop();
        
        // 关闭应该不抛出异常
        assertDoesNotThrow(() -> spider.close());
    }

    @Test
    @DisplayName("测试并发安全")
    void testConcurrency() {
        SpiderEnhanced spider = SpiderEnhanced.builder()
            .name("ConcurrencyTest")
            .threads(5)
            .build();
        
        // 并发启动和停止
        Thread startThread = new Thread(spider::start);
        Thread stopThread = new Thread(spider::stop);
        
        startThread.start();
        
        try {
            Thread.sleep(50);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
        
        stopThread.start();
        
        assertDoesNotThrow(() -> {
            startThread.join(1000);
            stopThread.join(1000);
        });
    }

    @Test
    @DisplayName("测试统计计算")
    void testStatsCalculation() {
        SpiderEnhanced.SpiderStats stats = new SpiderEnhanced.SpiderStats(
            1000,  // total
            950,   // success
            50,    // failed
            900,   // items
            System.currentTimeMillis() - 10000,  // start (10s ago)
            System.currentTimeMillis()           // end
        );
        
        assertEquals(1000, stats.totalRequests);
        assertEquals(950, stats.successRequests);
        assertEquals(50, stats.failedRequests);
        assertEquals(900, stats.totalItems);
        
        // 测试 RPS 计算
        double rps = stats.getRequestsPerSecond();
        assertTrue(rps > 0 && rps <= 100, "RPS should be reasonable");
    }

    @Test
    @DisplayName("测试超时设置")
    void testTimeout() {
        SpiderEnhanced spider = SpiderEnhanced.builder()
            .timeout(5000)
            .build();
        
        assertEquals(5000, spider.timeout);
        
        spider.timeout(10000);
        assertEquals(10000, spider.timeout);
    }

    @Test
    @DisplayName("测试多次启动")
    void testMultipleStarts() {
        SpiderEnhanced spider = SpiderEnhanced.builder()
            .name("MultiStartTest")
            .threads(1)
            .build();
        
        // 第一次启动
        spider.start();
        spider.stop();
        
        // 第二次启动应该不抛出异常
        assertDoesNotThrow(() -> {
            spider.start();
            spider.stop();
        });
    }

    @Test
    @DisplayName("测试空处理器")
    void testNullProcessor() {
        SpiderEnhanced spider = new SpiderEnhanced(null);
        
        // 没有处理器也应该能启动和停止
        assertDoesNotThrow(() -> {
            spider.start();
            spider.stop();
        });
    }

    @Test
    @DisplayName("测试对象池性能")
    void testObjectPoolPerformance() {
        SpiderEnhanced spider = new SpiderEnhanced();
        
        long start = System.currentTimeMillis();
        
        // 快速获取和回收 1000 次
        for (int i = 0; i < 1000; i++) {
            var page = spider.acquirePage();
            spider.recyclePage(page);
        }
        
        long elapsed = System.currentTimeMillis() - start;
        
        // 应该在 100ms 内完成
        assertTrue(elapsed < 100, "Object pool should be fast");
    }
}
