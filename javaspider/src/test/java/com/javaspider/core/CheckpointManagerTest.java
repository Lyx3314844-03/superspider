package com.javaspider.core;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.io.TempDir;

import java.io.File;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.nio.file.Path;
import java.util.*;

import static org.junit.jupiter.api.Assertions.*;

/**
 * CheckpointManager 单元测试
 * 
 * 测试覆盖率目标：>90%
 */
@DisplayName("CheckpointManager 测试")
class CheckpointManagerTest {
    
    @TempDir
    Path tempDir;
    
    private CheckpointManager checkpointManager;
    
    @BeforeEach
    void setUp() {
        checkpointManager = new CheckpointManager(tempDir.toString());
    }
    
    @AfterEach
    void tearDown() {
        if (checkpointManager != null) {
            checkpointManager.close();
        }
    }
    
    @Test
    @DisplayName("测试初始化")
    void testInitialization() {
        assertNotNull(checkpointManager);
        assertTrue(tempDir.toFile().exists());
    }
    
    @Test
    @DisplayName("测试保存和加载 - 立即保存")
    void testSaveAndLoadImmediate() {
        String spiderId = "test_spider";
        List<String> visitedUrls = Arrays.asList("url1", "url2", "url3");
        List<String> pendingUrls = Arrays.asList("url4", "url5");
        Map<String, Object> stats = new HashMap<>();
        stats.put("total", 100);
        stats.put("success", 95);
        
        // 保存
        checkpointManager.save(spiderId, visitedUrls, pendingUrls, stats, Collections.emptyMap(), true);
        
        // 加载
        CheckpointManager.CheckpointState state = checkpointManager.load(spiderId);
        
        assertNotNull(state);
        assertEquals(spiderId, state.getSpiderId());
        assertEquals(3, state.getVisitedUrls().size());
        assertEquals(2, state.getPendingUrls().size());
        assertEquals(100, ((Number) state.getStats().get("total")).intValue());
    }
    
    @Test
    @DisplayName("测试保存和加载 - 缓存保存")
    void testSaveAndLoadCached() {
        String spiderId = "test_spider_cached";
        List<String> visitedUrls = Arrays.asList("url1");
        List<String> pendingUrls = new ArrayList<>();
        Map<String, Object> stats = new HashMap<>();
        
        // 保存到缓存（不立即保存）
        checkpointManager.save(spiderId, visitedUrls, pendingUrls, stats, Collections.emptyMap(), false);
        
        // 从缓存加载
        CheckpointManager.CheckpointState state = checkpointManager.load(spiderId);
        
        assertNotNull(state);
        assertEquals(spiderId, state.getSpiderId());
    }
    
    @Test
    @DisplayName("测试加载不存在的 checkpoint")
    void testLoadNonexistent() {
        CheckpointManager.CheckpointState state = checkpointManager.load("nonexistent");
        
        assertNull(state);
    }
    
    @Test
    @DisplayName("测试删除 checkpoint")
    void testDelete() {
        String spiderId = "test_delete";
        
        // 保存
        checkpointManager.save(spiderId, new ArrayList<>(), new ArrayList<>(), new HashMap<>(), Collections.emptyMap(), true);
        
        // 验证文件存在
        File checkpointFile = new File(tempDir.toString(), spiderId + ".checkpoint.json");
        assertTrue(checkpointFile.exists());
        
        // 删除
        checkpointManager.delete(spiderId);
        
        // 验证文件不存在
        assertFalse(checkpointFile.exists());
    }
    
    @Test
    @DisplayName("测试列出 checkpoint")
    void testListCheckpoints() {
        // 保存多个 checkpoint
        for (int i = 0; i < 3; i++) {
            checkpointManager.save(
                "spider_" + i,
                new ArrayList<>(),
                new ArrayList<>(),
                new HashMap<>(),
                Collections.emptyMap(),
                true
            );
        }
        
        List<String> checkpoints = checkpointManager.listCheckpoints();
        
        assertEquals(3, checkpoints.size());
        assertTrue(checkpoints.contains("spider_0"));
        assertTrue(checkpoints.contains("spider_1"));
        assertTrue(checkpoints.contains("spider_2"));
    }

    @Test
    @DisplayName("测试保留最近 checkpoint 历史版本")
    void testCheckpointRetentionKeepsRecentVersions() throws InterruptedException {
        try (CheckpointManager manager = new CheckpointManager(
            tempDir.toString(),
            CheckpointManager.StorageType.JSON,
            0,
            2
        )) {
            String spiderId = "history_spider";
            for (int i = 0; i < 3; i++) {
                manager.save(
                    spiderId,
                    Collections.singletonList("url" + i),
                    new ArrayList<>(),
                    Map.of("seq", i),
                    Collections.emptyMap(),
                    true
                );
                Thread.sleep(5);
            }

            File[] historyFiles = tempDir.toFile().listFiles((dir, name) ->
                name.startsWith(spiderId + ".checkpoint.")
                    && name.endsWith(".json")
                    && !name.equals(spiderId + ".checkpoint.json")
            );
            assertNotNull(historyFiles);
            assertEquals(2, historyFiles.length);
        }
    }

    @Test
    @DisplayName("测试 SQLite 保存加载和历史版本保留")
    void testSqliteRoundTripAndRetention() throws Exception {
        String spiderId = "sqlite_spider";
        try (CheckpointManager manager = new CheckpointManager(
            tempDir.toString(),
            CheckpointManager.StorageType.SQLITE,
            0,
            2
        )) {
            for (int i = 0; i < 3; i++) {
                manager.save(
                    spiderId,
                    Arrays.asList("url" + i, "url" + (i + 1)),
                    Collections.singletonList("pending" + i),
                    Map.of("seq", i, "success", 1),
                    Map.of("threads", 2),
                    true
                );
                Thread.sleep(5);
            }

            assertTrue(manager.listCheckpoints().contains(spiderId));

            CheckpointManager.CheckpointState state = manager.load(spiderId);
            assertNotNull(state);
            assertEquals(Collections.singletonList("pending2"), state.getPendingUrls());
            assertEquals(2, state.getVisitedUrls().size());
            assertEquals(2, ((Number) state.getStats().get("seq")).intValue());
        }

        Path dbPath = tempDir.resolve("checkpoints.sqlite3");
        try (Connection connection = DriverManager.getConnection("jdbc:sqlite:" + dbPath.toAbsolutePath());
             ResultSet rs = connection.createStatement().executeQuery(
                 "SELECT COUNT(*) FROM checkpoint_versions WHERE spider_id = '" + spiderId + "'")) {
            assertTrue(rs.next());
            assertEquals(2, rs.getInt(1));
        }

        try (CheckpointManager manager = new CheckpointManager(
            tempDir.toString(),
            CheckpointManager.StorageType.SQLITE,
            0,
            2
        )) {
            manager.delete(spiderId);
            assertNull(manager.load(spiderId));
        }
    }
    
    @Test
    @DisplayName("测试获取统计信息")
    void testGetStats() {
        String spiderId = "test_stats";
        List<String> visitedUrls = Arrays.asList("url1", "url2", "url3");
        List<String> pendingUrls = Arrays.asList("url4");
        Map<String, Object> stats = new HashMap<>();
        stats.put("total", 100);
        
        checkpointManager.save(spiderId, visitedUrls, pendingUrls, stats, Collections.emptyMap(), true);
        
        Map<String, Object> resultStats = checkpointManager.getStats(spiderId);
        
        assertNotNull(resultStats);
        assertEquals(spiderId, resultStats.get("spiderId"));
        assertEquals(3, (int) resultStats.get("visitedCount"));
        assertEquals(1, (int) resultStats.get("pendingCount"));
    }
    
    @Test
    @DisplayName("测试获取不存在的统计信息")
    void testGetStatsNonexistent() {
        Map<String, Object> stats = checkpointManager.getStats("nonexistent");
        
        assertNull(stats);
    }
    
    @Test
    @DisplayName("测试从 SpiderEnhanced 保存")
    void testSaveFromSpider() {
        SpiderEnhanced spider = new SpiderEnhanced();
        spider.setSpiderName("test_spider");
        spider.setThreadCount(5);
        
        checkpointManager.saveFromSpider(spider, true);
        
        Map<String, Object> stats = checkpointManager.getStats(spider.getSpiderId());
        
        assertNotNull(stats);
    }
    
    @Test
    @DisplayName("测试校验和计算")
    void testChecksumComputation() {
        CheckpointManager.CheckpointState state1 = new CheckpointManager.CheckpointState(
            "test",
            "2026-03-23T10:00:00",
            Arrays.asList("url1"),
            new ArrayList<>(),
            new HashMap<>(),
            new HashMap<>()
        );
        state1.setChecksum(state1.computeChecksum());

        CheckpointManager.CheckpointState state2 = new CheckpointManager.CheckpointState(
            "test",
            "2026-03-23T10:00:00",
            Arrays.asList("url1"),
            new ArrayList<>(),
            new HashMap<>(),
            new HashMap<>()
        );
        state2.setChecksum(state2.computeChecksum());

        // 相同状态应该有相同校验和
        assertEquals(state1.getChecksum(), state2.getChecksum());

        // 不同状态应该有不同校验和
        CheckpointManager.CheckpointState state3 = new CheckpointManager.CheckpointState(
            "test",
            "2026-03-23T10:00:00",
            Arrays.asList("url1", "url2"),
            new ArrayList<>(),
            new HashMap<>(),
            new HashMap<>()
        );
        state3.setChecksum(state3.computeChecksum());

        assertNotEquals(state1.getChecksum(), state3.getChecksum());
    }
    
    @Test
    @DisplayName("测试自动保存")
    void testAutoSave() throws InterruptedException {
        // 创建带自动保存的管理器（1 秒间隔）
        CheckpointManager autoSaveManager = new CheckpointManager(
            tempDir.toString(),
            CheckpointManager.StorageType.JSON,
            1,  // 1 秒自动保存
            10
        );
        
        try {
            String spiderId = "test_auto_save";
            
            // 保存到缓存（不立即保存）
            autoSaveManager.save(
                spiderId,
                Arrays.asList("url1"),
                new ArrayList<>(),
                new HashMap<>(),
                Collections.emptyMap(),
                false
            );
            
            // 等待自动保存
            Thread.sleep(1500);
            
            // 检查文件是否被创建
            File checkpointFile = new File(tempDir.toString(), spiderId + ".checkpoint.json");
            assertTrue(checkpointFile.exists(), "自动保存应该创建文件");
            
        } finally {
            autoSaveManager.close();
        }
    }
    
    @Test
    @DisplayName("测试关闭时保存所有缓存")
    void testCloseSavesAllCached() {
        String spiderId = "test_close_save";
        
        // 保存到缓存（不立即保存）
        checkpointManager.save(
            spiderId,
            Arrays.asList("url1"),
            new ArrayList<>(),
            new HashMap<>(),
            Collections.emptyMap(),
            false
        );
        
        // 关闭（应该保存所有缓存）
        checkpointManager.close();
        
        // 检查文件是否存在
        File checkpointFile = new File(tempDir.toString(), spiderId + ".checkpoint.json");
        assertTrue(checkpointFile.exists(), "关闭时应该保存所有缓存状态");
    }
    
    @Test
    @DisplayName("测试上下文管理器")
    void testContextManager() {
        String spiderId = "test_context";
        
        try (CheckpointManager manager = new CheckpointManager(tempDir.toString())) {
            manager.save(
                spiderId,
                Arrays.asList("url1"),
                new ArrayList<>(),
                new HashMap<>(),
                Collections.emptyMap(),
                false
            );
        }
        
        // 退出 try-with-resources 后文件应该被保存
        File checkpointFile = new File(tempDir.toString(), spiderId + ".checkpoint.json");
        assertTrue(checkpointFile.exists());
    }
    
    @Test
    @DisplayName("测试并发保存")
    void testConcurrentSave() throws InterruptedException {
        int threadCount = 5;
        Thread[] threads = new Thread[threadCount];
        
        // 并发保存多个 checkpoint
        for (int i = 0; i < threadCount; i++) {
            final int index = i;
            threads[i] = new Thread(() -> {
                checkpointManager.save(
                    "spider_" + index,
                    Arrays.asList("url_" + index),
                    new ArrayList<>(),
                    new HashMap<>(),
                    Collections.emptyMap(),
                    true
                );
            });
            threads[i].start();
        }
        
        // 等待所有线程完成
        for (Thread thread : threads) {
            thread.join();
        }
        
        // 验证所有 checkpoint 都被保存
        List<String> checkpoints = checkpointManager.listCheckpoints();
        assertEquals(threadCount, checkpoints.size());
    }
    
    @Test
    @DisplayName("测试保存大量 URL")
    void testSaveLargeNumberOfUrls() {
        String spiderId = "test_large";
        List<String> visitedUrls = new ArrayList<>();
        
        // 创建 1000 个 URL
        for (int i = 0; i < 1000; i++) {
            visitedUrls.add("http://example.com/page" + i);
        }
        
        checkpointManager.save(spiderId, visitedUrls, new ArrayList<>(), new HashMap<>(), Collections.emptyMap(), true);
        
        CheckpointManager.CheckpointState state = checkpointManager.load(spiderId);
        
        assertNotNull(state);
        assertEquals(1000, state.getVisitedUrls().size());
    }
    
    @Test
    @DisplayName("测试特殊字符 URL")
    void testSaveUrlsWithSpecialCharacters() {
        String spiderId = "test_special_chars";
        List<String> visitedUrls = Arrays.asList(
            "http://example.com/page?param=value&other=123",
            "http://example.com/page with spaces",
            "http://example.com/page/with/unicode/中文"
        );
        
        assertDoesNotThrow(() -> {
            checkpointManager.save(spiderId, visitedUrls, new ArrayList<>(), new HashMap<>(), Collections.emptyMap(), true);
            
            CheckpointManager.CheckpointState state = checkpointManager.load(spiderId);
            
            assertNotNull(state);
            assertEquals(3, state.getVisitedUrls().size());
        });
    }
    
    @Test
    @DisplayName("测试空状态保存")
    void testSaveEmptyState() {
        String spiderId = "test_empty";
        
        checkpointManager.save(
            spiderId,
            new ArrayList<>(),
            new ArrayList<>(),
            new HashMap<>(),
            Collections.emptyMap(),
            true
        );
        
        CheckpointManager.CheckpointState state = checkpointManager.load(spiderId);
        
        assertNotNull(state);
        assertEquals(0, state.getVisitedUrls().size());
        assertEquals(0, state.getPendingUrls().size());
    }
    
    @Test
    @DisplayName("测试 null 处理")
    void testNullHandling() {
        String spiderId = "test_null";
        
        // 应该能处理 null 值
        assertDoesNotThrow(() -> {
            checkpointManager.save(spiderId, null, null, null, Collections.emptyMap(), true);
        });
    }
}
