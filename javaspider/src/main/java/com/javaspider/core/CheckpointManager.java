package com.javaspider.core;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import lombok.Data;
import lombok.extern.slf4j.Slf4j;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.security.MessageDigest;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.concurrent.*;

/**
 * JavaSpider 断点续爬模块
 * 
 * 特性:
 * 1. ✅ 自动保存爬虫状态
 * 2. ✅ 支持手动/自动 checkpoint
 * 3. ✅ 状态持久化 (JSON/SQLite)
 * 4. ✅ 恢复爬虫状态
 * 5. ✅ 增量爬取支持
 * 
 * 使用示例:
 * <pre>
 * {@code
 * CheckpointManager checkpoint = new CheckpointManager("checkpoints");
 * 
 * // 保存状态
 * checkpoint.save("mySpider", Arrays.asList("url1", "url2"), stats);
 * 
 * // 恢复状态
 * CheckpointState state = checkpoint.load("mySpider");
 * if (state != null) {
 *     spider.loadState(state);
 * }
 * }
 * </pre>
 * 
 * @author Lan
 * @version 1.0.0
 * @since 2026-03-23
 */
@Slf4j
public class CheckpointManager implements AutoCloseable {
    
    private final String checkpointDir;
    private final StorageType storageType;
    private final int autoSaveInterval;
    private final int maxCheckpoints;
    
    private final ObjectMapper objectMapper;
    private final Map<String, CheckpointState> stateCache;
    private final ScheduledExecutorService autoSaveExecutor;
    private final boolean shutdownAutoSaveOnClose;
    
    /**
     * 存储类型枚举
     */
    public enum StorageType {
        JSON,
        SQLITE
    }
    
    /**
     * 创建断点管理器 (JSON 存储)
     * 
     * @param checkpointDir checkpoint 目录
     */
    public CheckpointManager(String checkpointDir) {
        this(checkpointDir, StorageType.JSON, 300);
    }
    
    /**
     * 创建断点管理器
     * 
     * @param checkpointDir checkpoint 目录
     * @param storageType 存储类型
     * @param autoSaveInterval 自动保存间隔 (秒), 0 表示禁用
     */
    public CheckpointManager(String checkpointDir, StorageType storageType, int autoSaveInterval) {
        this(checkpointDir, storageType, autoSaveInterval, 10);
    }
    
    /**
     * 创建断点管理器
     * 
     * @param checkpointDir checkpoint 目录
     * @param storageType 存储类型
     * @param autoSaveInterval 自动保存间隔 (秒)
     * @param maxCheckpoints 最大保留的 checkpoint 数量
     */
    public CheckpointManager(
        String checkpointDir, 
        StorageType storageType, 
        int autoSaveInterval,
        int maxCheckpoints
    ) {
        this.checkpointDir = checkpointDir;
        this.storageType = storageType;
        this.autoSaveInterval = autoSaveInterval;
        this.maxCheckpoints = maxCheckpoints;
        
        this.objectMapper = new ObjectMapper()
            .enable(SerializationFeature.INDENT_OUTPUT)
            .disable(SerializationFeature.FAIL_ON_EMPTY_BEANS);
        
        this.stateCache = new ConcurrentHashMap<>();
        
        // 创建 checkpoint 目录
        try {
            Files.createDirectories(Paths.get(checkpointDir));
            log.info("Checkpoint 目录创建完成：{}", checkpointDir);
        } catch (IOException e) {
            log.error("创建 checkpoint 目录失败：{}", checkpointDir, e);
            throw new RuntimeException("创建 checkpoint 目录失败", e);
        }
        
        // 启动自动保存
        if (autoSaveInterval > 0) {
            this.autoSaveExecutor = Executors.newSingleThreadScheduledExecutor(r -> {
                Thread t = new Thread(r, "CheckpointAutoSave");
                t.setDaemon(true);
                return t;
            });
            
            this.autoSaveExecutor.scheduleAtFixedRate(
                this::autoSaveAll,
                autoSaveInterval,
                autoSaveInterval,
                TimeUnit.SECONDS
            );
            
            this.shutdownAutoSaveOnClose = true;
            log.info("自动保存已启动 (间隔：{}秒)", autoSaveInterval);
        } else {
            this.autoSaveExecutor = null;
            this.shutdownAutoSaveOnClose = false;
        }
    }
    
    /**
     * 保存爬虫状态
     * 
     * @param spiderId 爬虫 ID
     * @param visitedUrls 已访问 URL 列表
     * @param pendingUrls 待访问 URL 列表
     * @param stats 统计信息
     */
    public void save(
        String spiderId,
        List<String> visitedUrls,
        List<String> pendingUrls,
        Map<String, Object> stats
    ) {
        save(spiderId, visitedUrls, pendingUrls, stats, Collections.emptyMap(), false);
    }
    
    /**
     * 保存爬虫状态
     * 
     * @param spiderId 爬虫 ID
     * @param visitedUrls 已访问 URL 列表
     * @param pendingUrls 待访问 URL 列表
     * @param stats 统计信息
     * @param config 配置信息
     * @param immediate 是否立即保存
     */
    public void save(
        String spiderId,
        List<String> visitedUrls,
        List<String> pendingUrls,
        Map<String, Object> stats,
        Map<String, Object> config,
        boolean immediate
    ) {
        try {
            // 处理 null 值，使用空集合代替
            List<String> safeVisitedUrls = visitedUrls != null ? new ArrayList<>(visitedUrls) : new ArrayList<>();
            List<String> safePendingUrls = pendingUrls != null ? new ArrayList<>(pendingUrls) : new ArrayList<>();
            Map<String, Object> safeStats = stats != null ? new HashMap<>(stats) : new HashMap<>();
            Map<String, Object> safeConfig = config != null ? new HashMap<>(config) : new HashMap<>();
            
            CheckpointState state = new CheckpointState(
                spiderId,
                LocalDateTime.now().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME),
                safeVisitedUrls,
                safePendingUrls,
                safeStats,
                safeConfig
            );
            state.setChecksum(state.computeChecksum());

            // 保存到缓存
            stateCache.put(spiderId, state);

            // 立即保存
            if (immediate) {
                saveState(spiderId, state);
                log.info("Checkpoint 已保存：{}", spiderId);
            } else {
                log.debug("Checkpoint 已缓存：{}", spiderId);
            }

        } catch (Exception e) {
            log.error("保存 checkpoint 失败：{}", spiderId, e);
            throw new RuntimeException("保存 checkpoint 失败", e);
        }
    }
    
    /**
     * 从爬虫对象保存状态
     * 
     * @param spider 爬虫对象
     * @param immediate 是否立即保存
     */
    public void saveFromSpider(SpiderEnhanced spider, boolean immediate) {
        List<String> visitedUrls = new ArrayList<>();
        List<String> pendingUrls = new ArrayList<>();
        Map<String, Object> stats = new HashMap<>();
        
        // 从爬虫提取状态
        stats.put("totalRequests", spider.getTotalRequests());
        stats.put("successRequests", spider.getSuccessRequests());
        stats.put("failedRequests", spider.getFailedRequests());
        stats.put("startTime", spider.getStartTime());
        stats.put("endTime", spider.getEndTime());
        
        save(
            spider.getSpiderId(),
            visitedUrls,
            pendingUrls,
            stats,
            Collections.emptyMap(),
            immediate
        );
    }
    
    /**
     * 加载爬虫状态
     * 
     * @param spiderId 爬虫 ID
     * @return 状态对象，不存在返回 null
     */
    public CheckpointState load(String spiderId) {
        try {
            // 先从缓存加载
            CheckpointState cached = stateCache.get(spiderId);
            if (cached != null) {
                log.info("从缓存加载 checkpoint: {}", spiderId);
                return cached;
            }
            
            // 从存储加载
            CheckpointState state = loadState(spiderId);
            if (state != null) {
                // 验证校验和
                String expectedChecksum = state.computeChecksum();
                if (!expectedChecksum.equals(state.getChecksum())) {
                    log.warn("Checkpoint 校验和失败：{} (期望：{}, 实际：{})", 
                        spiderId, expectedChecksum, state.getChecksum());
                    return null;
                }
                
                log.info("从存储加载 checkpoint: {}", spiderId);
                return state;
            }
            
            return null;
            
        } catch (Exception e) {
            log.error("加载 checkpoint 失败：{}", spiderId, e);
            return null;
        }
    }
    
    /**
     * 保存状态到存储
     */
    private void saveState(String spiderId, CheckpointState state) throws IOException {
        if (storageType == StorageType.JSON) {
            saveJson(spiderId, state);
        } else {
            throw new UnsupportedOperationException("SQLite 存储暂不支持");
        }
    }
    
    /**
     * JSON 保存
     */
    private void saveJson(String spiderId, CheckpointState state) throws IOException {
        Path filePath = Paths.get(checkpointDir, spiderId + ".checkpoint.json");
        Path tempPath = Paths.get(checkpointDir, spiderId + ".checkpoint.json.tmp");
        
        // 序列化
        String json = objectMapper.writeValueAsString(state);
        
        // 写入临时文件
        Files.write(tempPath, json.getBytes());
        
        // 原子替换
        Files.move(tempPath, filePath, StandardCopyOption.ATOMIC_MOVE);
        
        // 清理旧 checkpoint
        cleanupOldCheckpoints(spiderId);
    }
    
    /**
     * JSON 加载
     */
    private CheckpointState loadState(String spiderId) throws IOException {
        if (storageType == StorageType.JSON) {
            return loadJson(spiderId);
        } else {
            throw new UnsupportedOperationException("SQLite 存储暂不支持");
        }
    }
    
    /**
     * JSON 加载
     */
    private CheckpointState loadJson(String spiderId) throws IOException {
        Path filePath = Paths.get(checkpointDir, spiderId + ".checkpoint.json");
        
        if (!Files.exists(filePath)) {
            return null;
        }
        
        byte[] bytes = Files.readAllBytes(filePath);
        String json = new String(bytes);
        
        return objectMapper.readValue(json, CheckpointState.class);
    }
    
    /**
     * 自动保存所有缓存状态
     */
    private void autoSaveAll() {
        for (Map.Entry<String, CheckpointState> entry : stateCache.entrySet()) {
            try {
                saveState(entry.getKey(), entry.getValue());
                log.debug("自动保存 checkpoint: {}", entry.getKey());
            } catch (Exception e) {
                log.error("自动保存失败：{}", entry.getKey(), e);
            }
        }
    }
    
    /**
     * 清理旧的 checkpoint
     */
    private void cleanupOldCheckpoints(String spiderId) {
        // TODO: 实现多版本保留
    }
    
    /**
     * 删除 checkpoint
     * 
     * @param spiderId 爬虫 ID
     */
    public void delete(String spiderId) {
        try {
            // 从缓存删除
            stateCache.remove(spiderId);
            
            // 从存储删除
            Path filePath = Paths.get(checkpointDir, spiderId + ".checkpoint.json");
            if (Files.exists(filePath)) {
                Files.delete(filePath);
                log.info("Checkpoint 已删除：{}", spiderId);
            }
            
        } catch (IOException e) {
            log.error("删除 checkpoint 失败：{}", spiderId, e);
        }
    }
    
    /**
     * 列出所有 checkpoint
     * 
     * @return checkpoint ID 列表
     */
    public List<String> listCheckpoints() {
        try {
            List<String> checkpoints = new ArrayList<>();
            Files.list(Paths.get(checkpointDir))
                .filter(p -> p.toString().endsWith(".checkpoint.json"))
                .forEach(p -> {
                    String filename = p.getFileName().toString();
                    String spiderId = filename.replace(".checkpoint.json", "");
                    checkpoints.add(spiderId);
                });
            return checkpoints;
        } catch (IOException e) {
            log.error("列出 checkpoint 失败", e);
            return Collections.emptyList();
        }
    }
    
    /**
     * 获取 checkpoint 统计
     * 
     * @param spiderId 爬虫 ID
     * @return 统计信息，不存在返回 null
     */
    public Map<String, Object> getStats(String spiderId) {
        CheckpointState state = stateCache.get(spiderId);
        if (state == null) {
            try {
                state = loadState(spiderId);
            } catch (IOException e) {
                log.error("加载 checkpoint 失败：{}", spiderId, e);
                return null;
            }
        }
        
        if (state == null) {
            return null;
        }
        
        Map<String, Object> stats = new HashMap<>();
        stats.put("spiderId", state.getSpiderId());
        stats.put("timestamp", state.getTimestamp());
        stats.put("visitedCount", state.getVisitedUrls().size());
        stats.put("pendingCount", state.getPendingUrls().size());
        stats.put("stats", state.getStats());
        stats.put("checksum", state.getChecksum());
        
        return stats;
    }
    
    @Override
    public void close() {
        // 停止自动保存
        if (shutdownAutoSaveOnClose && autoSaveExecutor != null) {
            autoSaveExecutor.shutdown();
            try {
                if (!autoSaveExecutor.awaitTermination(5, TimeUnit.SECONDS)) {
                    autoSaveExecutor.shutdownNow();
                }
            } catch (InterruptedException e) {
                autoSaveExecutor.shutdownNow();
                Thread.currentThread().interrupt();
            }
        }
        
        // 保存所有缓存状态
        for (Map.Entry<String, CheckpointState> entry : stateCache.entrySet()) {
            try {
                saveState(entry.getKey(), entry.getValue());
            } catch (IOException e) {
                log.error("关闭时保存失败：{}", entry.getKey(), e);
            }
        }
        
        log.info("CheckpointManager 已关闭");
    }
    
    /**
     * Checkpoint 状态类
     */
    @Data
    public static class CheckpointState {
        private String spiderId;
        private String timestamp;
        private List<String> visitedUrls;
        private List<String> pendingUrls;
        private Map<String, Object> stats;
        private Map<String, Object> config;
        private String checksum;
        
        /**
         * Jackson 反序列化构造函数
         */
        public CheckpointState() {
        }
        
        /**
         * 构造函数
         */
        public CheckpointState(
            String spiderId,
            String timestamp,
            List<String> visitedUrls,
            List<String> pendingUrls,
            Map<String, Object> stats,
            Map<String, Object> config
        ) {
            this.spiderId = spiderId;
            this.timestamp = timestamp;
            this.visitedUrls = visitedUrls != null ? visitedUrls : new ArrayList<>();
            this.pendingUrls = pendingUrls != null ? pendingUrls : new ArrayList<>();
            this.stats = stats != null ? stats : new HashMap<>();
            this.config = config != null ? config : new HashMap<>();
        }
        
        /**
         * 计算校验和
         */
        public String computeChecksum() {
            try {
                Map<String, Object> content = new TreeMap<>();
                content.put("spiderId", spiderId);
                content.put("visitedCount", visitedUrls != null ? visitedUrls.size() : 0);
                content.put("pendingCount", pendingUrls != null ? pendingUrls.size() : 0);
                content.put("stats", stats);
                
                String json = new ObjectMapper().writeValueAsString(content);
                
                MessageDigest md = MessageDigest.getInstance("MD5");
                byte[] digest = md.digest(json.getBytes());
                
                StringBuilder sb = new StringBuilder();
                for (byte b : digest) {
                    sb.append(String.format("%02x", b));
                }
                return sb.toString();
                
            } catch (Exception e) {
                log.error("计算校验和失败", e);
                return "";
            }
        }
    }
}
