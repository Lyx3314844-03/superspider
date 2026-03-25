package com.javaspider.antibot;

import lombok.extern.slf4j.Slf4j;

import java.util.*;
import java.util.concurrent.ThreadLocalRandom;

/**
 * User-Agent 轮换器
 * 
 * 特性:
 * 1. ✅ 多浏览器 UA 支持
 * 2. ✅ 自动轮换
 * 3. ✅ 设备类型模拟
 * 4. ✅ 浏览器版本随机化
 * 
 * @author Lan
 * @version 1.0.0
 */
@Slf4j
public class UserAgentRotator {
    
    // 常见浏览器 User-Agent 池
    private static final List<String> CHROME_UAS = Arrays.asList(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
    );
    
    private static final List<String> FIREFOX_UAS = Arrays.asList(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0"
    );
    
    private static final List<String> SAFARI_UAS = Arrays.asList(
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1"
    );
    
    private static final List<String> EDGE_UAS = Arrays.asList(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
    );
    
    // 移动设备 UA
    private static final List<String> MOBILE_UAS = Arrays.asList(
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.43 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 13; Pixel 7 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.43 Mobile Safari/537.36"
    );
    
    private final ThreadLocalRandom random = ThreadLocalRandom.current();
    private final List<String> uaPool = new ArrayList<>();
    private final Map<String, Integer> uaUsageCount = new HashMap<>();
    
    public UserAgentRotator() {
        initializeUAPool();
    }
    
    /**
     * 初始化 UA 池
     */
    private void initializeUAPool() {
        uaPool.addAll(CHROME_UAS);
        uaPool.addAll(FIREFOX_UAS);
        uaPool.addAll(SAFARI_UAS);
        uaPool.addAll(EDGE_UAS);
        uaPool.addAll(MOBILE_UAS);
        
        // 初始化使用计数
        for (String ua : uaPool) {
            uaUsageCount.put(ua, 0);
        }
        
        log.info("UserAgentRotator 初始化完成，共 {} 个 User-Agent", uaPool.size());
    }
    
    /**
     * 获取随机 User-Agent
     */
    public String getRandomUserAgent() {
        int index = random.nextInt(uaPool.size());
        String ua = uaPool.get(index);
        uaUsageCount.put(ua, uaUsageCount.get(ua) + 1);
        return ua;
    }
    
    /**
     * 获取指定浏览器的 User-Agent
     */
    public String getBrowserUserAgent(String browser) {
        List<String> browserPool;
        
        switch (browser.toLowerCase()) {
            case "chrome":
                browserPool = CHROME_UAS;
                break;
            case "firefox":
                browserPool = FIREFOX_UAS;
                break;
            case "safari":
                browserPool = SAFARI_UAS;
                break;
            case "edge":
                browserPool = EDGE_UAS;
                break;
            case "mobile":
                browserPool = MOBILE_UAS;
                break;
            default:
                browserPool = uaPool;
        }
        
        int index = random.nextInt(browserPool.size());
        String ua = browserPool.get(index);
        uaUsageCount.put(ua, uaUsageCount.getOrDefault(ua, 0) + 1);
        return ua;
    }
    
    /**
     * 获取最少使用的 User-Agent (负载均衡)
     */
    public String getLeastUsedUserAgent() {
        String leastUsedUa = uaPool.get(0);
        int minCount = uaUsageCount.get(leastUsedUa);
        
        for (Map.Entry<String, Integer> entry : uaUsageCount.entrySet()) {
            if (entry.getValue() < minCount) {
                minCount = entry.getValue();
                leastUsedUa = entry.getKey();
            }
        }
        
        uaUsageCount.put(leastUsedUa, minCount + 1);
        return leastUsedUa;
    }
    
    /**
     * 重置使用计数
     */
    public void resetUsageCount() {
        for (String ua : uaPool) {
            uaUsageCount.put(ua, 0);
        }
        log.info("User-Agent 使用计数已重置");
    }
    
    /**
     * 获取统计信息
     */
    public Map<String, Object> getStats() {
        Map<String, Object> stats = new HashMap<>();
        stats.put("total_uas", uaPool.size());
        stats.put("total_requests", uaUsageCount.values().stream().mapToInt(Integer::intValue).sum());
        
        // 找出使用最多的 UA
        String mostUsed = uaUsageCount.entrySet().stream()
            .max(Map.Entry.comparingByValue())
            .map(Map.Entry::getKey)
            .orElse("N/A");
        
        stats.put("most_used_ua", mostUsed);
        
        return stats;
    }
    
    /**
     * 添加自定义 User-Agent
     */
    public void addUserAgent(String ua) {
        if (!uaPool.contains(ua)) {
            uaPool.add(ua);
            uaUsageCount.put(ua, 0);
            log.info("添加自定义 User-Agent: {}", ua);
        }
    }
}
