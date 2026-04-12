package com.javaspider;

import java.util.*;
import java.util.concurrent.*;

/**
 * JavaSpider 反爬增强模块 - 代理池和 User-Agent 轮换
 */
public class AntiBot {
    
    // 静态 User-Agent 池
    private static final String[] USER_AGENTS = {
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    };
    
    // 代理池
    private static final List<String> proxyPool = new CopyOnWriteArrayList<>();
    private static final Map<String, Integer> failedCount = new ConcurrentHashMap<>();
    private static final Random random = new Random();
    private static int maxFailed = 3;
    
    // 初始化代理池
    static {
        // 可以从配置文件或环境变量加载代理
        String proxyList = System.getenv("PROXY_LIST");
        if (proxyList != null && !proxyList.isEmpty()) {
            for (String proxy : proxyList.split(",")) {
                proxyPool.add(proxy.trim());
            }
        }
    }
    
    /**
     * 获取随机 User-Agent
     */
    public static String getRandomUserAgent() {
        return USER_AGENTS[random.nextInt(USER_AGENTS.length)];
    }
    
    /**
     * 获取随机代理
     */
    public static String getRandomProxy() {
        if (proxyPool.isEmpty()) {
            return null;
        }
        return proxyPool.get(random.nextInt(proxyPool.size()));
    }
    
    /**
     * 添加代理到池中
     */
    public static void addProxy(String proxy) {
        if (!proxyPool.contains(proxy)) {
            proxyPool.add(proxy);
        }
    }
    
    /**
     * 移除失败的代理
     */
    public static void removeProxy(String proxy) {
        proxyPool.remove(proxy);
        failedCount.remove(proxy);
    }
    
    /**
     * 记录代理失败次数
     */
    public static void recordFailure(String proxy) {
        int count = failedCount.getOrDefault(proxy, 0) + 1;
        failedCount.put(proxy, count);
        
        if (count >= maxFailed) {
            removeProxy(proxy);
        }
    }
    
    /**
     * 获取代理池大小
     */
    public static int getProxyPoolSize() {
        return proxyPool.size();
    }
    
    /**
     * 显示所有代理
     */
    public static void listProxies() {
        System.out.println("代理池中的代理数量: " + proxyPool.size());
        for (String proxy : proxyPool) {
            int failed = failedCount.getOrDefault(proxy, 0);
            System.out.println("  - " + proxy + " (失败: " + failed + ")");
        }
    }
    
    /**
     * 清空代理池
     */
    public static void clearProxies() {
        proxyPool.clear();
        failedCount.clear();
    }
}
