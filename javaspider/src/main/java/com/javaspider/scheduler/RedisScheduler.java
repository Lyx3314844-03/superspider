package com.javaspider.scheduler;

import com.google.gson.Gson;
import com.javaspider.core.CrawlTask;
import com.javaspider.core.Request;
import redis.clients.jedis.Jedis;
import redis.clients.jedis.JedisPool;
import redis.clients.jedis.JedisPoolConfig;
import redis.clients.jedis.exceptions.JedisException;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.List;
import java.util.Map;

/**
 * Redis 分布式调度器
 * 支持多台机器协同爬取 (Java, Go, Python, Rust 互通)
 */
public class RedisScheduler implements Scheduler {

    private final JedisPool jedisPool;
    private final String queueKey;
    private final String pendingKey;
    private final String processingKey;
    private final String deadLetterKey;
    private final String visitedKey;
    private final String statsKey;
    private final String spiderName;
    private final Gson gson = new Gson();

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

        this.queueKey = "spider:shared:queue";
        this.pendingKey = "spider:shared:pending";
        this.processingKey = "spider:shared:processing";
        this.deadLetterKey = "spider:shared:dead";
        this.visitedKey = "spider:shared:visited";
        this.statsKey = "spider:shared:stats";
        this.spiderName = spiderName;
    }

    @Override
    public void push(Request request) {
        try (Jedis jedis = jedisPool.getResource()) {
            String url = request.getUrl();

            if (!isProcessed(url) && !jedis.sismember(pendingKey, url) && !jedis.hexists(processingKey, url)) {
                CrawlTask task = CrawlTask.builder()
                        .url(url)
                        .priority(request.getPriority())
                        .depth(0)
                        .task_type("crawl")
                        .spider_name(spiderName)
                        .created_at(System.currentTimeMillis() / 1000.0)
                        .retry_count(0)
                        .metadata(request.getMeta())
                        .build();

                // 添加到优先级队列 (ZSET)
                jedis.zadd(queueKey, task.getPriority(), gson.toJson(task));
                jedis.sadd(pendingKey, url);
            }
        }
    }

    @Override
    public Request poll() {
        return leaseTask("scheduler", 30_000L);
    }

    public Request leaseTask(String workerId, long leaseTtlMs) {
        try (Jedis jedis = jedisPool.getResource()) {
            java.util.List<redis.clients.jedis.resps.Tuple> results = jedis.zpopmax(queueKey, 1);
            if (results != null && !results.isEmpty()) {
                String json = results.get(0).getElement();
                CrawlTask task = gson.fromJson(json, CrawlTask.class);
                jedis.srem(pendingKey, task.getUrl());
                jedis.hset(processingKey, task.getUrl(), gson.toJson(Map.of(
                    "worker_id", workerId,
                    "expires_at", System.currentTimeMillis() + leaseTtlMs,
                    "task", task
                )));

                Request request = new Request(task.getUrl());
                request.setPriority(task.getPriority());
                request.setMeta(task.getMetadata());
                return request;
            }
        } catch (JedisException e) {
            System.err.println("Failed to poll from Redis: " + e.getMessage());
        }
        return null;
    }

    public boolean heartbeatTask(String url, long leaseTtlMs) {
        try (Jedis jedis = jedisPool.getResource()) {
            String payload = jedis.hget(processingKey, url);
            if (payload == null) {
                return false;
            }
            @SuppressWarnings("unchecked")
            Map<String, Object> lease = gson.fromJson(payload, Map.class);
            lease.put("expires_at", System.currentTimeMillis() + leaseTtlMs);
            jedis.hset(processingKey, url, gson.toJson(lease));
            return true;
        }
    }

    public boolean ackTask(String url, boolean success, int maxRetries) {
        try (Jedis jedis = jedisPool.getResource()) {
            String payload = jedis.hget(processingKey, url);
            if (payload == null) {
                return false;
            }
            jedis.hdel(processingKey, url);
            @SuppressWarnings("unchecked")
            Map<String, Object> lease = gson.fromJson(payload, Map.class);
            CrawlTask task = gson.fromJson(gson.toJson(lease.get("task")), CrawlTask.class);
            if (success) {
                markAsProcessed(url);
                updateStats(true);
                return true;
            }
            task.setRetry_count(task.getRetry_count() + 1);
            if (task.getRetry_count() > maxRetries) {
                jedis.lpush(deadLetterKey, gson.toJson(task));
                markAsProcessed(url);
            } else {
                jedis.zadd(queueKey, task.getPriority(), gson.toJson(task));
                jedis.sadd(pendingKey, url);
            }
            updateStats(false);
            return true;
        }
    }

    public int reapExpiredLeases(long nowMillis, int maxRetries) {
        int reaped = 0;
        try (Jedis jedis = jedisPool.getResource()) {
            Map<String, String> processing = jedis.hgetAll(processingKey);
            for (Map.Entry<String, String> entry : processing.entrySet()) {
                @SuppressWarnings("unchecked")
                Map<String, Object> lease = gson.fromJson(entry.getValue(), Map.class);
                Object expires = lease.get("expires_at");
                long expiresAt = expires instanceof Number ? ((Number) expires).longValue() : 0L;
                if (expiresAt > nowMillis) {
                    continue;
                }
                if (ackTask(entry.getKey(), false, maxRetries)) {
                    reaped++;
                }
            }
        }
        return reaped;
    }

    @Override
    public void ack(Request request, boolean success) {
        if (request == null || request.getUrl() == null) {
            return;
        }
        ackTask(request.getUrl(), success, 3);
    }

    @Override
    public void heartbeat(Request request, long leaseTtlMs) {
        if (request == null || request.getUrl() == null) {
            return;
        }
        heartbeatTask(request.getUrl(), leaseTtlMs);
    }

    private void updateStats(boolean success) {
        try (Jedis jedis = jedisPool.getResource()) {
            String field = success ? "success" : "failed";
            String langField = success ? "java:success" : "java:failed";
            jedis.hincrBy(statsKey, field, 1);
            jedis.hincrBy(statsKey, langField, 1);
            jedis.hincrBy(statsKey, "processed", 1);
            jedis.hincrBy(statsKey, "java:processed", 1);
        }
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
            return Long.valueOf(jedis.zcard(queueKey)).intValue();
        }
    }

    @Override
    public int getTotalCount() {
        try (Jedis jedis = jedisPool.getResource()) {
            return Long.valueOf(jedis.scard(visitedKey)).intValue();
        }
    }

    @Override
    public int getProcessedCount() {
        try (Jedis jedis = jedisPool.getResource()) {
            return Long.valueOf(jedis.scard(visitedKey)).intValue();
        }
    }

    @Override
    public boolean isEmpty() {
        return size() == 0;
    }

    @Override
    public void clear() {
        try (Jedis jedis = jedisPool.getResource()) {
            jedis.del(queueKey, pendingKey, processingKey, deadLetterKey, visitedKey, statsKey);
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
            return jedis.sismember(visitedKey, url);
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
            jedis.sadd(visitedKey, url);
        }
    }

    /**
     * 标记为失败
     */
    public void markAsFailed(String url) {
        // 标记为失败，但在统一协议中我们主要看 visited
        updateStats(false);
    }

    /**
     * 获取队列统计
     */
    public RedisSchedulerStats getStats() {
        RedisSchedulerStats stats = new RedisSchedulerStats();

        try (Jedis jedis = jedisPool.getResource()) {
            stats.setQueueSize(Long.valueOf(jedis.zcard(queueKey)).intValue());
            stats.setProcessedCount(Long.valueOf(jedis.scard(visitedKey)).intValue());

            String successStr = jedis.hget(statsKey, "success");
            stats.setFailedCount(0); // 默认
            if (successStr != null) {
                // 可以从 statsKey 获取更多细节
            }
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
