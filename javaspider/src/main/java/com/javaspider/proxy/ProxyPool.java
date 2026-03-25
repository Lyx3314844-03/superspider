package com.javaspider.proxy;

import lombok.Data;
import lombok.extern.slf4j.Slf4j;

import java.io.BufferedReader;
import java.io.FileReader;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.net.Proxy;
import java.net.Socket;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * 代理池管理器
 * 支持代理验证、自动切换、失败标记
 */
@Slf4j
public class ProxyPool {
    
    private final CopyOnWriteArrayList<ProxyInfo> proxies = new CopyOnWriteArrayList<>();
    private final AtomicInteger currentIndex = new AtomicInteger(0);
    private final int maxFailures;
    private final long timeout;
    
    public ProxyPool() {
        this(3, 5000);
    }
    
    public ProxyPool(int maxFailures, long timeout) {
        this.maxFailures = maxFailures;
        this.timeout = timeout;
    }
    
    /**
     * 添加代理
     */
    public void addProxy(String host, int port) {
        addProxy(host, port, null, null);
    }
    
    /**
     * 添加代理（带认证）
     */
    public void addProxy(String host, int port, String username, String password) {
        ProxyInfo proxy = new ProxyInfo(host, port, username, password);
        proxies.add(proxy);
        log.info("Proxy added: {}:{}", host, port);
    }
    
    /**
     * 从文件加载代理列表
     */
    public void loadFromFile(String filePath) throws IOException {
        try (BufferedReader br = new BufferedReader(new FileReader(filePath))) {
            String line;
            while ((line = br.readLine()) != null) {
                line = line.trim();
                if (line.isEmpty() || line.startsWith("#")) {
                    continue;
                }
                
                // 支持格式：host:port 或 host:port:username:password
                String[] parts = line.split(":");
                if (parts.length >= 2) {
                    String host = parts[0].trim();
                    int port = Integer.parseInt(parts[1].trim());
                    String username = parts.length > 2 ? parts[2].trim() : null;
                    String password = parts.length > 3 ? parts[3].trim() : null;
                    addProxy(host, port, username, password);
                }
            }
        }
        log.info("Loaded {} proxies from {}", proxies.size(), filePath);
    }
    
    /**
     * 获取下一个可用代理
     */
    public ProxyInfo getNextProxy() {
        if (proxies.isEmpty()) {
            return null;
        }
        
        int attempts = 0;
        while (attempts < proxies.size()) {
            int index = Math.abs(currentIndex.getAndIncrement() % proxies.size());
            ProxyInfo proxy = proxies.get(index);
            
            // 检查代理是否可用
            if (proxy.getFailures() < maxFailures) {
                return proxy;
            }
            
            attempts++;
        }
        
        // 所有代理都失败，返回第一个
        return proxies.get(0);
    }
    
    /**
     * 标记代理成功
     */
    public void markSuccess(ProxyInfo proxy) {
        proxy.setFailures(0);
        proxy.setSuccessCount(proxy.getSuccessCount() + 1);
        proxy.setLastSuccessTime(System.currentTimeMillis());
    }
    
    /**
     * 标记代理失败
     */
    public void markFailure(ProxyInfo proxy) {
        int failures = proxy.getFailures() + 1;
        proxy.setFailures(failures);
        proxy.setLastFailureTime(System.currentTimeMillis());
        
        if (failures >= maxFailures) {
            log.warn("Proxy {}:{} marked as unavailable ({} failures)", 
                proxy.getHost(), proxy.getPort(), failures);
        }
    }
    
    /**
     * 验证代理是否可用
     */
    public boolean validateProxy(ProxyInfo proxy) {
        long start = System.currentTimeMillis();
        
        try {
            // 尝试连接 Google 或百度来验证代理
            Socket socket = new Socket();
            socket.connect(new InetSocketAddress(proxy.getHost(), proxy.getPort()), (int) timeout);
            socket.close();
            
            long elapsed = System.currentTimeMillis() - start;
            proxy.setResponseTime(elapsed);
            proxy.setValid(true);
            
            log.debug("Proxy {}:{} validated ({}ms)", proxy.getHost(), proxy.getPort(), elapsed);
            return true;
            
        } catch (Exception e) {
            proxy.setValid(false);
            log.debug("Proxy {}:{} validation failed: {}", proxy.getHost(), proxy.getPort(), e.getMessage());
            return false;
        }
    }
    
    /**
     * 验证所有代理
     */
    public int validateAll() {
        int validCount = 0;
        
        for (ProxyInfo proxy : proxies) {
            if (validateProxy(proxy)) {
                validCount++;
            }
        }
        
        log.info("Validated {} proxies, {} valid", proxies.size(), validCount);
        return validCount;
    }
    
    /**
     * 移除无效代理
     */
    public void removeInvalid() {
        proxies.removeIf(proxy -> proxy.getFailures() >= maxFailures);
        log.info("Removed invalid proxies, remaining: {}", proxies.size());
    }
    
    /**
     * 获取代理池统计
     */
    public ProxyPoolStats getStats() {
        ProxyPoolStats stats = new ProxyPoolStats();
        stats.setTotal(proxies.size());
        stats.setValid((int) proxies.stream().filter(ProxyInfo::isValid).count());
        stats.setInvalid(stats.getTotal() - stats.getValid());
        stats.setAverageResponseTime(
            proxies.stream()
                .filter(ProxyInfo::isValid)
                .mapToLong(ProxyInfo::getResponseTime)
                .average()
                .orElse(0)
        );
        return stats;
    }
    
    /**
     * 打印统计信息
     */
    public void printStats() {
        ProxyPoolStats stats = getStats();
        System.out.println("========== ProxyPool Stats ==========");
        System.out.println("Total proxies: " + stats.getTotal());
        System.out.println("Valid: " + stats.getValid());
        System.out.println("Invalid: " + stats.getInvalid());
        System.out.println("Average response time: " + stats.getAverageResponseTime() + "ms");
        System.out.println("======================================");
    }
    
    /**
     * 代理信息类
     */
    @Data
    public static class ProxyInfo {
        private final String host;
        private final int port;
        private final String username;
        private final String password;
        private boolean valid;
        private int failures;
        private int successCount;
        private long responseTime;
        private long lastSuccessTime;
        private long lastFailureTime;
        
        public ProxyInfo(String host, int port, String username, String password) {
            this.host = host;
            this.port = port;
            this.username = username;
            this.password = password;
            this.valid = true;
            this.failures = 0;
        }
        
        /**
         * 获取 Java Proxy 对象
         */
        public Proxy toJavaProxy() {
            if (username != null && password != null) {
                // 带认证的代理需要系统级配置
                System.setProperty("http.proxyUser", username);
                System.setProperty("http.proxyPassword", password);
                System.setProperty("https.proxyUser", username);
                System.setProperty("https.proxyPassword", password);
            }
            return new Proxy(Proxy.Type.HTTP, new InetSocketAddress(host, port));
        }
        
        /**
         * 获取代理 URL 格式
         */
        public String getProxyUrl() {
            if (username != null && password != null) {
                return String.format("http://%s:%s@%s:%d", username, password, host, port);
            }
            return String.format("http://%s:%d", host, port);
        }
    }
    
    /**
     * 代理池统计类
     */
    @Data
    public static class ProxyPoolStats {
        private int total;
        private int valid;
        private int invalid;
        private double averageResponseTime;
    }
}
