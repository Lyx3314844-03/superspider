package com.javaspider.core;

import java.security.MessageDigest;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.logging.Logger;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;

/**
 * 增量爬取支持 - ETag / Last-Modified 检查
 */
public class IncrementalCrawler {
    private static final Logger logger = Logger.getLogger(IncrementalCrawler.class.getName());
    
    public static class PageCacheEntry {
        public String url;
        public String etag;
        public String lastModified;
        public String contentHash;
        public long lastCrawled;
        public int statusCode;
        public boolean contentChanged = true;
        
        PageCacheEntry(String url) {
            this.url = url;
            this.lastCrawled = System.currentTimeMillis();
        }
    }
    
    private final boolean enabled;
    private final long minChangeIntervalMs;
    private final Map<String, PageCacheEntry> cache = new ConcurrentHashMap<>();
    private Path storePath;
    
    public IncrementalCrawler() {
        this(true, 3600_000L);
    }
    
    public IncrementalCrawler(boolean enabled, long minChangeIntervalMs) {
        this.enabled = enabled;
        this.minChangeIntervalMs = minChangeIntervalMs;
    }
    
    /**
     * 检查是否应该跳过此 URL(内容未变更)
     * @return true 表示可以跳过
     */
    public boolean shouldSkip(String url, String etag, String lastModified) {
        if (!enabled) return false;
        
        PageCacheEntry entry = cache.get(url);
        if (entry == null) return false;
        
        long now = System.currentTimeMillis();
        
        // 检查最小变更间隔
        if (now - entry.lastCrawled < minChangeIntervalMs) {
            return true;
        }
        
        // ETag 比较
        if (etag != null && !etag.isEmpty() && entry.etag != null && !entry.etag.isEmpty() && etag.equals(entry.etag)) {
            entry.contentChanged = false;
            logger.fine("ETag match, skipping: " + url);
            return true;
        }
        
        // Last-Modified 比较
        if (lastModified != null && !lastModified.isEmpty() && entry.lastModified != null && !entry.lastModified.isEmpty() && lastModified.equals(entry.lastModified)) {
            entry.contentChanged = false;
            logger.fine("Last-Modified match, skipping: " + url);
            return true;
        }
        
        return false;
    }
    
    /**
     * 获取条件请求头
     */
    public Map<String, String> getConditionalHeaders(String url) {
        Map<String, String> headers = new HashMap<>();
        PageCacheEntry entry = cache.get(url);
        if (entry != null) {
            if (entry.etag != null && !entry.etag.isEmpty()) {
                headers.put("If-None-Match", entry.etag);
            }
            if (entry.lastModified != null && !entry.lastModified.isEmpty()) {
                headers.put("If-Modified-Since", entry.lastModified);
            }
        }
        return headers;
    }
    
    /**
     * 更新缓存
     * @return true 表示内容已变更
     */
    public boolean updateCache(String url, String etag, String lastModified, byte[] content, int statusCode) {
        String contentHash = null;
        if (content != null && content.length > 0) {
            try {
                MessageDigest md = MessageDigest.getInstance("MD5");
                byte[] digest = md.digest(content);
                StringBuilder sb = new StringBuilder();
                for (byte b : digest) {
                    sb.append(String.format("%02x", b));
                }
                contentHash = sb.toString();
            } catch (Exception e) {
                // ignore
            }
        }
        
        PageCacheEntry existing = cache.get(url);
        if (existing != null && existing.contentHash != null && existing.contentHash.equals(contentHash)) {
            existing.lastCrawled = System.currentTimeMillis();
            existing.contentChanged = false;
            return false;
        }
        
        PageCacheEntry entry = new PageCacheEntry(url);
        entry.etag = etag != null ? etag : (existing != null ? existing.etag : null);
        entry.lastModified = lastModified != null ? lastModified : (existing != null ? existing.lastModified : null);
        entry.contentHash = contentHash;
        entry.lastCrawled = System.currentTimeMillis();
        entry.statusCode = statusCode;
        entry.contentChanged = true;
        
        cache.put(url, entry);
        return true;
    }
    
    /**
     * 获取缓存统计
     */
    public Map<String, Object> getCacheStats() {
        int total = cache.size();
        int changed = 0;
        for (PageCacheEntry e : cache.values()) {
            if (e.contentChanged) changed++;
        }
        
        Map<String, Object> stats = new HashMap<>();
        stats.put("total", total);
        stats.put("changed", changed);
        stats.put("unchanged", total - changed);
        stats.put("hit_rate", total > 0 ? (double) (total - changed) / total : 0.0);
        return stats;
    }
    
    public void clearCache() {
        cache.clear();
    }
    
    public void removeUrl(String url) {
        cache.remove(url);
    }

    public String deltaToken(String url) {
        PageCacheEntry entry = cache.get(url);
        if (entry == null) {
            return null;
        }
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] digest = md.digest((
                entry.url + "|" +
                Objects.toString(entry.etag, "") + "|" +
                Objects.toString(entry.lastModified, "") + "|" +
                Objects.toString(entry.contentHash, "") + "|" +
                entry.statusCode
            ).getBytes(java.nio.charset.StandardCharsets.UTF_8));
            StringBuilder sb = new StringBuilder();
            for (byte b : digest) {
                sb.append(String.format("%02x", b));
            }
            return sb.toString();
        } catch (Exception exception) {
            throw new RuntimeException("failed to compute incremental delta token", exception);
        }
    }

    public Map<String, Object> snapshot() {
        Map<String, Object> root = new LinkedHashMap<>();
        root.put("enabled", enabled);
        root.put("min_change_interval_ms", minChangeIntervalMs);
        Map<String, Object> entries = new LinkedHashMap<>();
        for (Map.Entry<String, PageCacheEntry> entry : cache.entrySet()) {
            PageCacheEntry value = entry.getValue();
            entries.put(entry.getKey(), Map.of(
                "url", value.url,
                "etag", value.etag,
                "last_modified", value.lastModified,
                "content_hash", value.contentHash,
                "last_crawled", value.lastCrawled,
                "status_code", value.statusCode,
                "content_changed", value.contentChanged
            ));
        }
        root.put("entries", entries);
        return root;
    }

    @SuppressWarnings("unchecked")
    public void restore(Map<String, Object> snapshot) {
        cache.clear();
        Object rawEntries = snapshot.get("entries");
        if (!(rawEntries instanceof Map<?, ?> entries)) {
            return;
        }
        for (Map.Entry<?, ?> entry : entries.entrySet()) {
            if (!(entry.getKey() instanceof String url) || !(entry.getValue() instanceof Map<?, ?> value)) {
                continue;
            }
            PageCacheEntry restored = new PageCacheEntry(url);
            restored.etag = Objects.toString(value.get("etag"), null);
            restored.lastModified = Objects.toString(value.get("last_modified"), null);
            restored.contentHash = Objects.toString(value.get("content_hash"), null);
            Object lastCrawled = value.get("last_crawled");
            if (lastCrawled instanceof Number number) {
                restored.lastCrawled = number.longValue();
            }
            Object statusCode = value.get("status_code");
            if (statusCode instanceof Number number) {
                restored.statusCode = number.intValue();
            }
            Object contentChanged = value.get("content_changed");
            if (contentChanged instanceof Boolean bool) {
                restored.contentChanged = bool;
            }
            cache.put(url, restored);
        }
    }

    public Path save(String path) {
        Path target = path == null || path.isBlank() ? storePath : Paths.get(path);
        if (target == null) {
            return null;
        }
        try {
            Files.createDirectories(target.getParent());
            new ObjectMapper().writerWithDefaultPrettyPrinter().writeValue(target.toFile(), snapshot());
            storePath = target;
            return target;
        } catch (Exception exception) {
            throw new RuntimeException("failed to save incremental cache", exception);
        }
    }

    public void load(String path) {
        Path target = path == null || path.isBlank() ? storePath : Paths.get(path);
        if (target == null || !Files.exists(target)) {
            return;
        }
        try {
            Map<String, Object> payload = new ObjectMapper().readValue(
                target.toFile(),
                new TypeReference<Map<String, Object>>() {}
            );
            restore(payload);
            storePath = target;
        } catch (Exception exception) {
            throw new RuntimeException("failed to load incremental cache", exception);
        }
    }
}
