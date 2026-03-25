package com.javaspider.performance.ratelimit;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Semaphore;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;

/**
 * 智能速率限制器
 * 类似 Scrapy 的 AutoThrottle
 * 
 * 特性:
 * - 自适应速率调整
 * - 基于响应时间动态调整
 * - 域名级别限流
 * - 背压机制
 */
public class AdaptiveRateLimiter {
    private static final Logger logger = LoggerFactory.getLogger(AdaptiveRateLimiter.class);
    
    // 默认配置
    private static final double DEFAULT_INITIAL_DELAY = 1.0; // 秒
    private static final double DEFAULT_MIN_DELAY = 0.1; // 秒
    private static final double DEFAULT_MAX_DELAY = 60.0; // 秒
    private static final int DEFAULT_CONCURRENT_REQUESTS = 16;
    private static final int DEFAULT_CONCURRENT_REQUESTS_PER_DOMAIN = 8;
    private static final double DEFAULT_TARGET_RESPONSE_TIME = 2.0; // 秒
    
    // 域名级别的延迟配置
    private final Map<String, AtomicLong> domainDelays = new ConcurrentHashMap<>();
    private final Map<String, AtomicLong> domainLastRequestTime = new ConcurrentHashMap<>();
    private final Map<String, AtomicLong> domainResponseTimes = new ConcurrentHashMap<>();
    
    // 全局信号量控制并发
    private final Semaphore globalSemaphore;
    private final Map<String, Semaphore> domainSemaphores = new ConcurrentHashMap<>();
    
    // 配置
    private final double initialDelay;
    private final double minDelay;
    private final double maxDelay;
    private final int maxConcurrentRequests;
    private final int maxConcurrentRequestsPerDomain;
    private final double targetResponseTime;
    
    // 统计
    private final AtomicLong totalRequests = new AtomicLong(0);
    private final AtomicLong totalThrottled = new AtomicLong(0);
    
    /**
     * 构造函数
     */
    public AdaptiveRateLimiter() {
        this(DEFAULT_INITIAL_DELAY, DEFAULT_MIN_DELAY, DEFAULT_MAX_DELAY,
             DEFAULT_CONCURRENT_REQUESTS, DEFAULT_CONCURRENT_REQUESTS_PER_DOMAIN,
             DEFAULT_TARGET_RESPONSE_TIME);
    }
    
    /**
     * 构造函数
     */
    public AdaptiveRateLimiter(double initialDelay, double minDelay, double maxDelay,
                               int maxConcurrentRequests, int maxConcurrentRequestsPerDomain,
                               double targetResponseTime) {
        this.initialDelay = initialDelay;
        this.minDelay = minDelay;
        this.maxDelay = maxDelay;
        this.maxConcurrentRequests = maxConcurrentRequests;
        this.maxConcurrentRequestsPerDomain = maxConcurrentRequestsPerDomain;
        this.targetResponseTime = targetResponseTime;
        
        this.globalSemaphore = new Semaphore(maxConcurrentRequests);
        
        logger.info("AdaptiveRateLimiter initialized: initialDelay={}s, minDelay={}s, maxDelay={}s, " +
                        "maxConcurrent={}, maxConcurrentPerDomain={}, targetResponseTime={}s",
                initialDelay, minDelay, maxDelay, maxConcurrentRequests, 
                maxConcurrentRequestsPerDomain, targetResponseTime);
    }
    
    /**
     * 获取域名
     */
    private String extractDomain(String url) {
        try {
            java.net.URI uri = new java.net.URI(url);
            return uri.getHost();
        } catch (Exception e) {
            return "unknown";
        }
    }
    
    /**
     * 获取域名的当前延迟
     */
    private double getDomainDelay(String domain) {
        AtomicLong delay = domainDelays.get(domain);
        if (delay == null) {
            domainDelays.putIfAbsent(domain, new AtomicLong((long)(initialDelay * 1000)));
            delay = domainDelays.get(domain);
        }
        return delay.get() / 1000.0;
    }
    
    /**
     * 设置域名的延迟
     */
    private void setDomainDelay(String domain, long delayMs) {
        long clampedDelay = Math.max((long)(minDelay * 1000), 
                              Math.min((long)(maxDelay * 1000), delayMs));
        AtomicLong delay = domainDelays.computeIfAbsent(domain, k -> new AtomicLong(0));
        delay.set(clampedDelay);
    }
    
    /**
     * 请求前调用（获取许可）
     * 
     * @param url 请求 URL
     * @return 等待时间 (ms)
     */
    public long beforeRequest(String url) {
        String domain = extractDomain(url);
        long waitTime = 0;
        
        try {
            // 全局并发控制
            if (!globalSemaphore.tryAcquire(100, TimeUnit.MILLISECONDS)) {
                totalThrottled.incrementAndGet();
                waitTime += 100;
                logger.trace("Global rate limit hit for {}", url);
            }
            
            // 域名级别并发控制
            Semaphore domainSemaphore = domainSemaphores.computeIfAbsent(domain, 
                k -> new Semaphore(maxConcurrentRequestsPerDomain));
            
            if (!domainSemaphore.tryAcquire(100, TimeUnit.MILLISECONDS)) {
                totalThrottled.incrementAndGet();
                waitTime += 100;
                logger.trace("Domain rate limit hit for {} on {}", url, domain);
            }
            
            // 域名级别延迟控制
            long lastRequestTime = domainLastRequestTime.computeIfAbsent(domain, 
                k -> new AtomicLong(0)).get();
            long currentTime = System.currentTimeMillis();
            long domainDelay = (long)(getDomainDelay(domain) * 1000);
            
            long timeSinceLastRequest = currentTime - lastRequestTime;
            if (timeSinceLastRequest < domainDelay) {
                waitTime += (domainDelay - timeSinceLastRequest);
            }
            
            domainLastRequestTime.get(domain).set(currentTime + waitTime);
            totalRequests.incrementAndGet();
            
            return waitTime;
            
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            return 0;
        }
    }
    
    /**
     * 请求后调用（更新统计）
     * 
     * @param url 请求 URL
     * @param responseTime 响应时间 (ms)
     * @param statusCode HTTP 状态码
     */
    public void afterRequest(String url, long responseTime, int statusCode) {
        String domain = extractDomain(url);
        
        // 更新响应时间统计（移动平均）
        AtomicLong avgResponseTime = domainResponseTimes.computeIfAbsent(domain, 
            k -> new AtomicLong(0));
        long currentAvg = avgResponseTime.get();
        avgResponseTime.set((long)(currentAvg * 0.8 + responseTime * 0.2));
        
        // 自适应调整延迟
        adjustDelay(domain, responseTime, statusCode);
        
        // 释放域名信号量
        Semaphore domainSemaphore = domainSemaphores.get(domain);
        if (domainSemaphore != null) {
            domainSemaphore.release();
        }
        
        // 释放全局信号量
        globalSemaphore.release();
    }
    
    /**
     * 自适应调整延迟
     */
    private void adjustDelay(String domain, long responseTime, int statusCode) {
        double currentDelay = getDomainDelay(domain);
        double newDelay = currentDelay;
        
        // 根据响应时间调整
        double responseTimeSecs = responseTime / 1000.0;
        
        if (responseTimeSecs < targetResponseTime) {
            // 响应快，减少延迟（增加爬取速度）
            newDelay = currentDelay * 0.9;
        } else if (responseTimeSecs > targetResponseTime * 2) {
            // 响应慢，增加延迟（减少爬取速度）
            newDelay = currentDelay * 1.5;
        }
        
        // 根据状态码调整
        if (statusCode == 429 || statusCode == 503) {
            // 被限流或服务不可用，大幅增加延迟
            newDelay = currentDelay * 2.0;
            logger.warn("Rate limit detected for domain {}, increasing delay to {}s", domain, newDelay);
        } else if (statusCode >= 500) {
            // 服务器错误，适度增加延迟
            newDelay = currentDelay * 1.2;
        }
        
        // 应用限制
        newDelay = Math.max(minDelay, Math.min(maxDelay, newDelay));
        
        if (Math.abs(newDelay - currentDelay) > 0.1) {
            setDomainDelay(domain, (long)(newDelay * 1000));
            logger.debug("Adjusted delay for {}: {}s -> {}s (responseTime={}ms, statusCode={})", 
                    domain, currentDelay, newDelay, responseTime, statusCode);
        }
    }
    
    /**
     * 获取统计信息
     */
    public RateLimitStats getStats() {
        return new RateLimitStats(
            totalRequests.get(),
            totalThrottled.get(),
            domainDelays.size()
        );
    }
    
    /**
     * 重置特定域名的限流配置
     */
    public void resetDomain(String domain) {
        domainDelays.remove(domain);
        domainLastRequestTime.remove(domain);
        domainResponseTimes.remove(domain);
        logger.info("Reset rate limit for domain: {}", domain);
    }
    
    /**
     * 获取所有域名的延迟
     */
    public Map<String, Double> getAllDomainDelays() {
        Map<String, Double> delays = new ConcurrentHashMap<>();
        domainDelays.forEach((domain, delay) -> delays.put(domain, delay.get() / 1000.0));
        return delays;
    }
    
    /**
     * 统计信息类
     */
    public static class RateLimitStats {
        public final long totalRequests;
        public final long totalThrottled;
        public final int domainCount;
        
        public RateLimitStats(long totalRequests, long totalThrottled, int domainCount) {
            this.totalRequests = totalRequests;
            this.totalThrottled = totalThrottled;
            this.domainCount = domainCount;
        }
        
        public double getThrottleRate() {
            if (totalRequests == 0) return 0;
            return (double) totalThrottled / totalRequests;
        }
        
        @Override
        public String toString() {
            return String.format("RateLimitStats{totalRequests=%d, throttled=%d, throttleRate=%.2f%%, domains=%d}",
                    totalRequests, totalThrottled, getThrottleRate() * 100, domainCount);
        }
    }
    
    /**
     * 创建构建器
     */
    public static Builder builder() {
        return new Builder();
    }
    
    /**
     * 构建器
     */
    public static class Builder {
        private double initialDelay = DEFAULT_INITIAL_DELAY;
        private double minDelay = DEFAULT_MIN_DELAY;
        private double maxDelay = DEFAULT_MAX_DELAY;
        private int maxConcurrentRequests = DEFAULT_CONCURRENT_REQUESTS;
        private int maxConcurrentRequestsPerDomain = DEFAULT_CONCURRENT_REQUESTS_PER_DOMAIN;
        private double targetResponseTime = DEFAULT_TARGET_RESPONSE_TIME;
        
        public Builder initialDelay(double initialDelay) {
            this.initialDelay = initialDelay;
            return this;
        }
        
        public Builder minDelay(double minDelay) {
            this.minDelay = minDelay;
            return this;
        }
        
        public Builder maxDelay(double maxDelay) {
            this.maxDelay = maxDelay;
            return this;
        }
        
        public Builder maxConcurrentRequests(int maxConcurrentRequests) {
            this.maxConcurrentRequests = maxConcurrentRequests;
            return this;
        }
        
        public Builder maxConcurrentRequestsPerDomain(int maxConcurrentRequestsPerDomain) {
            this.maxConcurrentRequestsPerDomain = maxConcurrentRequestsPerDomain;
            return this;
        }
        
        public Builder targetResponseTime(double targetResponseTime) {
            this.targetResponseTime = targetResponseTime;
            return this;
        }
        
        public AdaptiveRateLimiter build() {
            return new AdaptiveRateLimiter(
                initialDelay, minDelay, maxDelay,
                maxConcurrentRequests, maxConcurrentRequestsPerDomain,
                targetResponseTime
            );
        }
    }
}
