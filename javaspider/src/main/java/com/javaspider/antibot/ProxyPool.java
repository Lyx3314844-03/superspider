package com.javaspider.antibot;

import lombok.extern.slf4j.Slf4j;

import java.io.*;
import java.net.*;
import java.util.*;
import java.util.concurrent.*;

/**
 * IP 代理池
 * 
 * 特性:
 * 1. ✅ 代理 IP 管理
 * 2. ✅ 自动健康检查
 * 3. ✅ 故障转移
 * 4. ✅ 代理轮换
 * 
 * @author Lan
 * @version 1.0.0
 */
@Slf4j
public class ProxyPool implements AutoCloseable {
    
    private final List<ProxyInfo> proxyList = new CopyOnWriteArrayList<>();
    private final Map<String, Integer> proxyUsageCount = new ConcurrentHashMap<>();
    private final Map<String, Long> proxyLastCheck = new ConcurrentHashMap<>();
    private final Map<String, Boolean> proxyHealth = new ConcurrentHashMap<>();
    
    private final ScheduledExecutorService healthCheckExecutor;
    private final int healthCheckInterval;
    private final int proxyTimeout;
    
    /**
     * 代理信息类
     */
    public static class ProxyInfo {
        private final String ip;
        private final int port;
        private final String protocol;
        private final String username;
        private final String password;
        private final String country;
        private final long addedTime;
        
        public ProxyInfo(String ip, int port, String protocol) {
            this(ip, port, protocol, null, null, "Unknown");
        }
        
        public ProxyInfo(String ip, int port, String protocol, String username, String password, String country) {
            this.ip = ip;
            this.port = port;
            this.protocol = protocol;
            this.username = username;
            this.password = password;
            this.country = country;
            this.addedTime = System.currentTimeMillis();
        }
        
        public Proxy toJavaProxy() {
            return new Proxy(Proxy.Type.HTTP, new InetSocketAddress(ip, port));
        }
        
        @Override
        public String toString() {
            return String.format("%s://%s:%d (%s)", protocol, ip, port, country);
        }
    }
    
    public ProxyPool() {
        this(300, 5000); // 默认 5 分钟检查一次，超时 5 秒
    }
    
    public ProxyPool(int healthCheckIntervalSeconds, int timeoutMs) {
        this.healthCheckInterval = healthCheckIntervalSeconds;
        this.proxyTimeout = timeoutMs;
        
        // 启动健康检查
        healthCheckExecutor = Executors.newSingleThreadScheduledExecutor(r -> {
            Thread t = new Thread(r, "ProxyHealthCheck");
            t.setDaemon(true);
            return t;
        });
        
        healthCheckExecutor.scheduleAtFixedRate(
            this::healthCheckAll,
            healthCheckInterval,
            healthCheckInterval,
            TimeUnit.SECONDS
        );
        
        log.info("ProxyPool 初始化完成，健康检查间隔：{}秒", healthCheckInterval);
    }
    
    /**
     * 添加代理
     */
    public void addProxy(ProxyInfo proxy) {
        if (!proxyList.contains(proxy)) {
            proxyList.add(proxy);
            proxyUsageCount.put(proxy.toString(), 0);
            proxyHealth.put(proxy.toString(), true); // 默认健康
            log.info("添加代理：{}", proxy);
        }
    }
    
    /**
     * 批量添加代理
     */
    public void addProxies(List<ProxyInfo> proxies) {
        for (ProxyInfo proxy : proxies) {
            addProxy(proxy);
        }
        log.info("批量添加 {} 个代理", proxies.size());
    }
    
    /**
     * 从文件加载代理
     */
    public void loadFromFile(String filePath) throws IOException {
        List<ProxyInfo> proxies = new ArrayList<>();
        
        try (BufferedReader reader = new BufferedReader(new FileReader(filePath))) {
            String line;
            while ((line = reader.readLine()) != null) {
                line = line.trim();
                if (line.isEmpty() || line.startsWith("#")) {
                    continue;
                }
                
                // 格式：ip:port 或 ip:port:username:password
                String[] parts = line.split(":");
                if (parts.length >= 2) {
                    String ip = parts[0];
                    int port = Integer.parseInt(parts[1]);
                    String protocol = parts.length > 2 ? parts[2] : "http";
                    String username = parts.length > 3 ? parts[3] : null;
                    String password = parts.length > 4 ? parts[4] : null;
                    
                    proxies.add(new ProxyInfo(ip, port, protocol, username, password, "Unknown"));
                }
            }
        }
        
        addProxies(proxies);
        log.info("从文件加载 {} 个代理：{}", proxies.size(), filePath);
    }
    
    /**
     * 获取随机代理
     */
    public ProxyInfo getRandomProxy() {
        List<ProxyInfo> healthyProxies = getHealthyProxies();
        
        if (healthyProxies.isEmpty()) {
            log.warn("没有可用的健康代理");
            return null;
        }
        
        ThreadLocalRandom random = ThreadLocalRandom.current();
        ProxyInfo proxy = healthyProxies.get(random.nextInt(healthyProxies.size()));
        proxyUsageCount.put(proxy.toString(), proxyUsageCount.getOrDefault(proxy.toString(), 0) + 1);
        
        return proxy;
    }
    
    /**
     * 获取最少使用的代理
     */
    public ProxyInfo getLeastUsedProxy() {
        List<ProxyInfo> healthyProxies = getHealthyProxies();
        
        if (healthyProxies.isEmpty()) {
            return null;
        }
        
        ProxyInfo leastUsed = healthyProxies.get(0);
        int minCount = proxyUsageCount.getOrDefault(leastUsed.toString(), 0);
        
        for (ProxyInfo proxy : healthyProxies) {
            int count = proxyUsageCount.getOrDefault(proxy.toString(), 0);
            if (count < minCount) {
                minCount = count;
                leastUsed = proxy;
            }
        }
        
        proxyUsageCount.put(leastUsed.toString(), minCount + 1);
        return leastUsed;
    }
    
    /**
     * 获取健康代理列表
     */
    public List<ProxyInfo> getHealthyProxies() {
        List<ProxyInfo> healthy = new ArrayList<>();
        
        for (ProxyInfo proxy : proxyList) {
            Boolean isHealthy = proxyHealth.get(proxy.toString());
            if (isHealthy == null || isHealthy) {
                healthy.add(proxy);
            }
        }
        
        return healthy;
    }
    
    /**
     * 标记代理为不健康
     */
    public void markUnhealthy(ProxyInfo proxy) {
        proxyHealth.put(proxy.toString(), false);
        log.warn("标记代理为不健康：{}", proxy);
    }
    
    /**
     * 健康检查
     */
    private void healthCheckAll() {
        log.info("开始代理健康检查...");
        
        int healthyCount = 0;
        int unhealthyCount = 0;
        
        for (ProxyInfo proxy : proxyList) {
            boolean isHealthy = checkProxyHealth(proxy);
            proxyHealth.put(proxy.toString(), isHealthy);
            proxyLastCheck.put(proxy.toString(), System.currentTimeMillis());
            
            if (isHealthy) {
                healthyCount++;
            } else {
                unhealthyCount++;
            }
        }
        
        log.info("代理健康检查完成：健康={}, 不健康={}, 总计={}", 
            healthyCount, unhealthyCount, proxyList.size());
    }
    
    /**
     * 检查单个代理健康
     */
    public boolean checkProxyHealth(ProxyInfo proxy) {
        try {
            // 尝试访问 Google 或百度
            URL url = new URL("https://www.google.com");
            HttpURLConnection conn = (HttpURLConnection) url.openConnection(proxy.toJavaProxy());
            conn.setConnectTimeout(proxyTimeout);
            conn.setReadTimeout(proxyTimeout);
            conn.setRequestMethod("GET");
            
            int responseCode = conn.getResponseCode();
            conn.disconnect();
            
            return responseCode == 200 || responseCode == 302;
            
        } catch (Exception e) {
            log.debug("代理健康检查失败 {}: {}", proxy, e.getMessage());
            return false;
        }
    }
    
    /**
     * 获取统计信息
     */
    public Map<String, Object> getStats() {
        Map<String, Object> stats = new HashMap<>();
        stats.put("total_proxies", proxyList.size());
        stats.put("healthy_proxies", getHealthyProxies().size());
        stats.put("unhealthy_proxies", proxyList.size() - getHealthyProxies().size());
        
        int totalRequests = proxyUsageCount.values().stream().mapToInt(Integer::intValue).sum();
        stats.put("total_requests", totalRequests);
        
        return stats;
    }
    
    /**
     * 移除代理
     */
    public void removeProxy(ProxyInfo proxy) {
        proxyList.remove(proxy);
        proxyUsageCount.remove(proxy.toString());
        proxyHealth.remove(proxy.toString());
        proxyLastCheck.remove(proxy.toString());
        log.info("移除代理：{}", proxy);
    }
    
    /**
     * 清空代理池
     */
    public void clear() {
        proxyList.clear();
        proxyUsageCount.clear();
        proxyHealth.clear();
        proxyLastCheck.clear();
        log.info("清空代理池");
    }
    
    @Override
    public void close() {
        healthCheckExecutor.shutdown();
        try {
            if (!healthCheckExecutor.awaitTermination(5, TimeUnit.SECONDS)) {
                healthCheckExecutor.shutdownNow();
            }
        } catch (InterruptedException e) {
            healthCheckExecutor.shutdownNow();
            Thread.currentThread().interrupt();
        }
        log.info("ProxyPool 已关闭");
    }
}
