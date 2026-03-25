package com.javaspider.scheduler;

import com.javaspider.core.Request;
import redis.clients.jedis.Jedis;
import redis.clients.jedis.JedisPool;
import redis.clients.jedis.JedisPoolConfig;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;

/**
 * Redis 分布式调度器
 * 支持多台机器协同爬取
 */
public class RedisScheduler implements Scheduler {
    
    private final JedisPool jedisPool;
    private final String queueKey;
    private final String processedKey;
    private final String failedKey;
    
    /**
     * 创建 Redis 调度器
     */
    public RedisScheduler(String host, int port, String spiderName) {
        this(host, port, 0, null, spiderName);
    }
    
    /**
     * 创建 Redis 调度器（带密码）
     */
    public RedisScheduler(String host, int port, String password, String spiderName) {
        this(host, port, 0, password, spiderName);
    }
    
    /**
     * 创建 Redis 调度器（完整配置）
     */
    public RedisScheduler(String host, int port, int database, String password, String spiderName) {
        JedisPoolConfig config = new JedisPoolConfig();
        config.setMaxTotal(10);
        config.setMaxIdle(5);
        config.setMinIdle(1);
        
        if (password != null && !password.isEmpty()) {
            this.jedisPool = new JedisPool(config, host, port, 2000, password, database);
        } else {
            this.jedisPool = new JedisPool(config, host, port, 2000, null, database);
        }
        
        this.queueKey = "spider:" + spiderName + ":queue";
        this.processedKey = "spider:" + spiderName + ":processed";
        this.failedKey = "spider:" + spiderName + ":failed";
    }
    
    @Override
    public void push(Request request) {
        try (Jedis jedis = jedisPool.getResource()) {
            String url = request.getUrl();
            
            // 检查是否已处理
            if (!isProcessed(url)) {
                // 添加到队列
                jedis.lpush(queueKey, serializeRequest(request));
                
                // 标记为待处理
                markAsPending(url);
            }
        }
    }
    
    @Override
    public Request poll() {
        try (Jedis jedis = jedisPool.getResource()) {
            String serialized = jedis.rpop(queueKey);
            if (serialized != null) {
                Request request = deserializeRequest(serialized);
                markAsProcessed(request.getUrl());
                return request;
            }
        }
        return null;
    }
    
    @Override
    public Request poll(long timeout, java.util.concurrent.TimeUnit unit) throws InterruptedException {
        // 简单实现，实际应该使用阻塞队列
        long timeoutMs = unit.toMillis(timeout);
        long start = System.currentTimeMillis();
        
        while (System.currentTimeMillis() - start < timeoutMs) {
            Request request = poll();
            if (request != null) {
                return request;
            }
            Thread.sleep(100);
        }
        return null;
    }
    
    @Override
    public Request pollNow() {
        return poll();
    }
    
    @Override
    public int size() {
        try (Jedis jedis = jedisPool.getResource()) {
            return Long.valueOf(jedis.llen(queueKey)).intValue();
        }
    }
    
    @Override
    public int getTotalCount() {
        try (Jedis jedis = jedisPool.getResource()) {
            return Long.valueOf(jedis.scard(processedKey)).intValue();
        }
    }
    
    @Override
    public int getProcessedCount() {
        try (Jedis jedis = jedisPool.getResource()) {
            return Long.valueOf(jedis.scard(processedKey)).intValue();
        }
    }
    
    @Override
    public boolean isEmpty() {
        return size() == 0;
    }
    
    @Override
    public void clear() {
        try (Jedis jedis = jedisPool.getResource()) {
            jedis.del(queueKey, processedKey, failedKey);
        }
    }
    
    @Override
    public void close() {
        jedisPool.close();
    }
    
    /**
     * 检查 URL 是否已处理
     */
    private boolean isProcessed(String url) {
        try (Jedis jedis = jedisPool.getResource()) {
            String hash = urlHash(url);
            return jedis.sismember(processedKey, hash);
        }
    }
    
    /**
     * 标记为待处理
     */
    private void markAsPending(String url) {
        // 可选实现
    }
    
    /**
     * 标记为已处理
     */
    private void markAsProcessed(String url) {
        try (Jedis jedis = jedisPool.getResource()) {
            String hash = urlHash(url);
            jedis.sadd(processedKey, hash);
        }
    }
    
    /**
     * 标记为失败
     */
    public void markAsFailed(String url) {
        try (Jedis jedis = jedisPool.getResource()) {
            String hash = urlHash(url);
            jedis.sadd(failedKey, hash);
        }
    }
    
    /**
     * URL 哈希
     */
    private String urlHash(String url) {
        try {
            MessageDigest md = MessageDigest.getInstance("MD5");
            byte[] digest = md.digest(url.getBytes(StandardCharsets.UTF_8));
            StringBuilder sb = new StringBuilder();
            for (byte b : digest) {
                sb.append(String.format("%02x", b));
            }
            return sb.toString();
        } catch (NoSuchAlgorithmException e) {
            return String.valueOf(url.hashCode());
        }
    }
    
    /**
     * 序列化请求
     */
    private String serializeRequest(Request request) {
        // 简单实现，实际应该使用 JSON
        return request.getUrl();
    }
    
    /**
     * 反序列化请求
     */
    private Request deserializeRequest(String serialized) {
        return new Request(serialized);
    }
    
    /**
     * 获取队列统计
     */
    public RedisSchedulerStats getStats() {
        RedisSchedulerStats stats = new RedisSchedulerStats();
        
        try (Jedis jedis = jedisPool.getResource()) {
            stats.setQueueSize(Long.valueOf(jedis.llen(queueKey)).intValue());
            stats.setProcessedCount(Long.valueOf(jedis.scard(processedKey)).intValue());
            stats.setFailedCount(Long.valueOf(jedis.scard(failedKey)).intValue());
        }
        
        return stats;
    }
    
    /**
     * 打印统计信息
     */
    public void printStats() {
        RedisSchedulerStats stats = getStats();
        System.out.println("========== RedisScheduler Stats ==========");
        System.out.println("Queue size: " + stats.getQueueSize());
        System.out.println("Processed: " + stats.getProcessedCount());
        System.out.println("Failed: " + stats.getFailedCount());
        System.out.println("==========================================");
    }
    
    /**
     * 调度器统计类
     */
    public static class RedisSchedulerStats {
        private int queueSize;
        private int processedCount;
        private int failedCount;
        
        public int getQueueSize() { return queueSize; }
        public void setQueueSize(int queueSize) { this.queueSize = queueSize; }
        
        public int getProcessedCount() { return processedCount; }
        public void setProcessedCount(int processedCount) { this.processedCount = processedCount; }
        
        public int getFailedCount() { return failedCount; }
        public void setFailedCount(int failedCount) { this.failedCount = failedCount; }
    }
}
