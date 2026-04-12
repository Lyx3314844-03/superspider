package com.javaspider.core;

import com.fasterxml.jackson.core.type.TypeReference;
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
import java.sql.*;
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
 * CheckpointManager checkpoint = new CheckpointManager("artifacts/checkpoints");
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
    private final Path sqliteDbPath;
    
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
        this.sqliteDbPath = Paths.get(checkpointDir, "checkpoints.sqlite3");
        
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

        if (storageType == StorageType.SQLITE) {
            try {
                initSqliteStorage();
            } catch (IOException e) {
                throw new RuntimeException("初始化 SQLite checkpoint 存储失败", e);
            }
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
            saveSqlite(spiderId, state);
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

        writeJsonVersion(spiderId, json);
        
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
            return loadSqlite(spiderId);
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
        if (maxCheckpoints <= 0) {
            return;
        }

        if (storageType == StorageType.SQLITE) {
            cleanupSqliteCheckpointVersions(spiderId);
            return;
        }

        File dir = Paths.get(checkpointDir).toFile();
        File[] historyFiles = dir.listFiles((currentDir, name) ->
            name.startsWith(spiderId + ".checkpoint.")
                && name.endsWith(".json")
                && !name.equals(spiderId + ".checkpoint.json")
        );
        if (historyFiles == null || historyFiles.length <= maxCheckpoints) {
            return;
        }

        Arrays.sort(historyFiles, Comparator.comparing(File::getName).reversed());
        for (int i = maxCheckpoints; i < historyFiles.length; i++) {
            if (!historyFiles[i].delete()) {
                log.warn("删除旧 checkpoint 历史失败：{}", historyFiles[i].getAbsolutePath());
            }
        }
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

            if (storageType == StorageType.SQLITE) {
                deleteSqliteCheckpoint(spiderId);
            } else {
                // 从存储删除
                Path filePath = Paths.get(checkpointDir, spiderId + ".checkpoint.json");
                if (Files.exists(filePath)) {
                    Files.delete(filePath);
                    log.info("Checkpoint 已删除：{}", spiderId);
                }

                deleteHistoryFiles(spiderId);
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
        if (storageType == StorageType.SQLITE) {
            return listSqliteCheckpoints();
        }
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

    private void writeJsonVersion(String spiderId, String json) throws IOException {
        if (maxCheckpoints <= 0) {
            return;
        }

        String versionSuffix = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd'T'HHmmss.SSSSSSSSS"));
        Path versionPath = Paths.get(checkpointDir, spiderId + ".checkpoint." + versionSuffix + ".json");
        Files.writeString(versionPath, json);
    }

    private void deleteHistoryFiles(String spiderId) throws IOException {
        File dir = Paths.get(checkpointDir).toFile();
        File[] historyFiles = dir.listFiles((currentDir, name) ->
            name.startsWith(spiderId + ".checkpoint.")
                && name.endsWith(".json")
                && !name.equals(spiderId + ".checkpoint.json")
        );
        if (historyFiles == null) {
            return;
        }
        for (File historyFile : historyFiles) {
            Files.deleteIfExists(historyFile.toPath());
        }
    }

    private void initSqliteStorage() throws IOException {
        try (Connection connection = openSqliteConnection();
             Statement statement = connection.createStatement()) {
            statement.executeUpdate("""
                CREATE TABLE IF NOT EXISTS checkpoints (
                    spider_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    visited_urls TEXT NOT NULL,
                    pending_urls TEXT NOT NULL,
                    stats TEXT NOT NULL,
                    config TEXT NOT NULL,
                    checksum TEXT NOT NULL
                )
                """);
            statement.executeUpdate("""
                CREATE TABLE IF NOT EXISTS checkpoint_versions (
                    version_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    spider_id TEXT NOT NULL,
                    version_timestamp TEXT NOT NULL,
                    visited_urls TEXT NOT NULL,
                    pending_urls TEXT NOT NULL,
                    stats TEXT NOT NULL,
                    config TEXT NOT NULL,
                    checksum TEXT NOT NULL
                )
                """);
            statement.executeUpdate("""
                CREATE INDEX IF NOT EXISTS idx_checkpoint_versions_spider_time
                ON checkpoint_versions (spider_id, version_timestamp DESC, version_id DESC)
                """);
        } catch (SQLException e) {
            throw new IOException("初始化 SQLite 存储失败", e);
        }
    }

    private void saveSqlite(String spiderId, CheckpointState state) throws IOException {
        String visitedJson = objectMapper.writeValueAsString(state.getVisitedUrls());
        String pendingJson = objectMapper.writeValueAsString(state.getPendingUrls());
        String statsJson = objectMapper.writeValueAsString(state.getStats());
        String configJson = objectMapper.writeValueAsString(state.getConfig());

        try (Connection connection = openSqliteConnection()) {
            connection.setAutoCommit(false);
            try (PreparedStatement upsert = connection.prepareStatement("""
                    INSERT INTO checkpoints (
                        spider_id, timestamp, visited_urls, pending_urls, stats, config, checksum
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(spider_id) DO UPDATE SET
                        timestamp = excluded.timestamp,
                        visited_urls = excluded.visited_urls,
                        pending_urls = excluded.pending_urls,
                        stats = excluded.stats,
                        config = excluded.config,
                        checksum = excluded.checksum
                    """);
                 PreparedStatement insertHistory = connection.prepareStatement("""
                    INSERT INTO checkpoint_versions (
                        spider_id, version_timestamp, visited_urls, pending_urls, stats, config, checksum
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """)) {
                bindCheckpointStatement(upsert, spiderId, state, visitedJson, pendingJson, statsJson, configJson);
                upsert.executeUpdate();

                bindCheckpointStatement(insertHistory, spiderId, state, visitedJson, pendingJson, statsJson, configJson);
                insertHistory.executeUpdate();

                connection.commit();
            } catch (SQLException e) {
                connection.rollback();
                throw e;
            } finally {
                connection.setAutoCommit(true);
            }
        } catch (SQLException e) {
            throw new IOException("保存 SQLite checkpoint 失败", e);
        }

        cleanupOldCheckpoints(spiderId);
    }

    private CheckpointState loadSqlite(String spiderId) throws IOException {
        try (Connection connection = openSqliteConnection();
             PreparedStatement statement = connection.prepareStatement("""
                SELECT spider_id, timestamp, visited_urls, pending_urls, stats, config, checksum
                FROM checkpoints
                WHERE spider_id = ?
                """)) {
            statement.setString(1, spiderId);
            try (ResultSet rs = statement.executeQuery()) {
                if (!rs.next()) {
                    return null;
                }

                CheckpointState state = new CheckpointState(
                    rs.getString("spider_id"),
                    rs.getString("timestamp"),
                    readList(rs.getString("visited_urls")),
                    readList(rs.getString("pending_urls")),
                    readMap(rs.getString("stats")),
                    readMap(rs.getString("config"))
                );
                state.setChecksum(rs.getString("checksum"));
                return state;
            }
        } catch (SQLException e) {
            throw new IOException("加载 SQLite checkpoint 失败", e);
        }
    }

    private List<String> listSqliteCheckpoints() {
        List<String> checkpoints = new ArrayList<>();
        try (Connection connection = openSqliteConnection();
             PreparedStatement statement = connection.prepareStatement(
                 "SELECT spider_id FROM checkpoints ORDER BY spider_id");
             ResultSet rs = statement.executeQuery()) {
            while (rs.next()) {
                checkpoints.add(rs.getString(1));
            }
        } catch (SQLException e) {
            log.error("列出 SQLite checkpoint 失败", e);
        }
        return checkpoints;
    }

    private void deleteSqliteCheckpoint(String spiderId) throws IOException {
        try (Connection connection = openSqliteConnection()) {
            connection.setAutoCommit(false);
            try (PreparedStatement deleteCurrent = connection.prepareStatement(
                    "DELETE FROM checkpoints WHERE spider_id = ?");
                 PreparedStatement deleteHistory = connection.prepareStatement(
                    "DELETE FROM checkpoint_versions WHERE spider_id = ?")) {
                deleteCurrent.setString(1, spiderId);
                deleteCurrent.executeUpdate();
                deleteHistory.setString(1, spiderId);
                deleteHistory.executeUpdate();
                connection.commit();
                log.info("Checkpoint 已删除：{}", spiderId);
            } catch (SQLException e) {
                connection.rollback();
                throw e;
            } finally {
                connection.setAutoCommit(true);
            }
        } catch (SQLException e) {
            throw new IOException("删除 SQLite checkpoint 失败", e);
        }
    }

    private void cleanupSqliteCheckpointVersions(String spiderId) {
        try (Connection connection = openSqliteConnection();
             PreparedStatement statement = connection.prepareStatement("""
                DELETE FROM checkpoint_versions
                WHERE version_id IN (
                    SELECT version_id
                    FROM checkpoint_versions
                    WHERE spider_id = ?
                    ORDER BY version_timestamp DESC, version_id DESC
                    LIMIT -1 OFFSET ?
                )
                """)) {
            statement.setString(1, spiderId);
            statement.setInt(2, maxCheckpoints);
            statement.executeUpdate();
        } catch (SQLException e) {
            log.error("清理 SQLite checkpoint 历史失败：{}", spiderId, e);
        }
    }

    private Connection openSqliteConnection() throws SQLException {
        return DriverManager.getConnection("jdbc:sqlite:" + sqliteDbPath.toAbsolutePath());
    }

    private void bindCheckpointStatement(
        PreparedStatement statement,
        String spiderId,
        CheckpointState state,
        String visitedJson,
        String pendingJson,
        String statsJson,
        String configJson
    ) throws SQLException {
        statement.setString(1, spiderId);
        statement.setString(2, state.getTimestamp());
        statement.setString(3, visitedJson);
        statement.setString(4, pendingJson);
        statement.setString(5, statsJson);
        statement.setString(6, configJson);
        statement.setString(7, state.getChecksum());
    }

    private List<String> readList(String json) throws IOException {
        return objectMapper.readValue(json, new TypeReference<List<String>>() {});
    }

    private Map<String, Object> readMap(String json) throws IOException {
        return objectMapper.readValue(json, new TypeReference<Map<String, Object>>() {});
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
