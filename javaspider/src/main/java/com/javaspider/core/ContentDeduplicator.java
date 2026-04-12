package com.javaspider.core;

import java.util.*;
import java.util.concurrent.*;
import java.util.logging.Logger;
import java.security.MessageDigest;

/**
 * 内容去重器 - 基于内容哈希避免重复处理相同内容的页面
 */
public class ContentDeduplicator {
    private static final Logger logger = Logger.getLogger(ContentDeduplicator.class.getName());
    
    private final Set<String> contentHashes = ConcurrentHashMap.newKeySet();
    
    /**
     * 检查内容是否重复
     * @return true 表示内容重复
     */
    public boolean isDuplicate(byte[] content) {
        if (content == null || content.length == 0) {
            return false;
        }
        
        String hash = computeHash(content);
        return !contentHashes.add(hash);
    }
    
    /**
     * 清除所有哈希
     */
    public void clear() {
        contentHashes.clear();
    }
    
    /**
     * 返回已存储的哈希数量
     */
    public int count() {
        return contentHashes.size();
    }
    
    /**
     * 计算内容哈希 (SHA-256)
     */
    private String computeHash(byte[] content) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] digest = md.digest(content);
            StringBuilder sb = new StringBuilder();
            for (byte b : digest) {
                sb.append(String.format("%02x", b));
            }
            return sb.toString();
        } catch (Exception e) {
            // 回退到 MD5
            return String.valueOf(Arrays.hashCode(content));
        }
    }
}

/**
 * 速率限制器 (令牌桶算法)
 */
class RateLimiter {
    private double tokens;
    private final double maxTokens;
    private volatile double refillRate; // tokens per second
    private volatile long lastRefillTime;
    private final Object lock = new Object();
    
    /**
     * 创建速率限制器
     * @param maxTokens 最大令牌数 (burst size)
     * @param refillRate 每秒补充的令牌数
     */
    public RateLimiter(double maxTokens, double refillRate) {
        this.tokens = maxTokens;
        this.maxTokens = maxTokens;
        this.refillRate = refillRate;
        this.lastRefillTime = System.currentTimeMillis();
    }
    
    /**
     * 等待直到获取到令牌
     */
    public void waitUntilAvailable() {
        while (!tryAcquire()) {
            try {
                Thread.sleep(10);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                return;
            }
        }
    }
    
    /**
     * 尝试获取令牌
     * @return true 表示获取成功
     */
    private boolean tryAcquire() {
        synchronized (lock) {
            long now = System.currentTimeMillis();
            double elapsed = (now - lastRefillTime) / 1000.0;
            tokens += elapsed * refillRate;
            if (tokens > maxTokens) {
                tokens = maxTokens;
            }
            lastRefillTime = now;
            
            if (tokens >= 1.0) {
                tokens -= 1.0;
                return true;
            }
            return false;
        }
    }
    
    /**
     * 动态调整速率
     */
    public void setRate(double refillRate) {
        this.refillRate = refillRate;
    }
    
    /**
     * 返回当前状态
     */
    @Override
    public String toString() {
        return String.format("RateLimiter{tokens: %.2f, max: %.2f, rate: %.2f/s}",
                tokens, maxTokens, refillRate);
    }
}

/**
 * 并发控制器 - 限制同时执行的请求数
 */
class ConcurrencyController {
    private final Semaphore semaphore;
    
    /**
     * 创建并发控制器
     * @param maxConcurrent 最大并发数
     */
    public ConcurrencyController(int maxConcurrent) {
        this.semaphore = new Semaphore(maxConcurrent);
    }
    
    /**
     * 获取执行许可
     */
    public void acquire() throws InterruptedException {
        semaphore.acquire();
    }
    
    /**
     * 释放执行许可
     */
    public void release() {
        semaphore.release();
    }
    
    /**
     * 尝试获取许可(不阻塞)
     * @return true 表示获取成功
     */
    public boolean tryAcquire() {
        return semaphore.tryAcquire();
    }
    
    /**
     * 返回可用许可数
     */
    public int availablePermits() {
        return semaphore.availablePermits();
    }
}
