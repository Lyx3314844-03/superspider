package com.javaspider.core;

import java.util.*;
import java.util.concurrent.*;
import java.util.logging.Logger;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * 代理池管理器 - 支持多代理轮换、健康检查和自动故障转移
 */
public class ProxyPool {
    private static final Logger logger = Logger.getLogger(ProxyPool.class.getName());
    
    public enum ProxyStatus {
        UNKNOWN, ALIVE, DEAD
    }
    
    public static class Proxy {
        public String host;
        public int port;
        public String protocol = "http";
        public String username;
        public String password;
        public ProxyStatus status = ProxyStatus.UNKNOWN;
        public int successCount = 0;
        public int failureCount = 0;
        public long lastChecked = 0;
        public long responseTime = 0;
        
        public Proxy(String host, int port) {
            this.host = host;
            this.port = port;
        }
        
        public Proxy(String host, int port, String protocol) {
            this.host = host;
            this.port = port;
            this.protocol = protocol;
        }
        
        public String getUrl() {
            if (username != null && !username.isEmpty()) {
                return String.format("%s://%s:%s@%s:%d", protocol, username, password, host, port);
            }
            return String.format("%s://%s:%d", protocol, host, port);
        }
        
        public float getSuccessRate() {
            int total = successCount + failureCount;
            return total > 0 ? (float) successCount / total : 0.0f;
        }
    }
    
    private final List<Proxy> proxies = Collections.synchronizedList(new ArrayList<>());
    private volatile int currentIndex = 0;
    private final String checkUrl;
    private final long checkIntervalMs;
    private final int maxFailures;
    private volatile boolean running = false;
    private ExecutorService healthCheckExecutor;
    
    public ProxyPool() {
        this("https://httpbin.org/ip", 300_000, 3);
    }
    
    public ProxyPool(String checkUrl, long checkIntervalMs, int maxFailures) {
        this.checkUrl = checkUrl;
        this.checkIntervalMs = checkIntervalMs;
        this.maxFailures = maxFailures;
    }
    
    public void addProxy(Proxy proxy) {
        proxies.add(proxy);
        logger.info("Proxy added: " + proxy.getUrl());
    }
    
    public void addProxyFromString(String proxyStr) {
        // 支持格式: http://host:port, http://user:pass@host:port, host:port
        Pattern pattern = Pattern.compile("^(?:(\\w+)://)?(?:(\\w+):(\\w+)@)?([\\w.-]+):(\\d+)$");
        Matcher matcher = pattern.matcher(proxyStr);
        if (matcher.matches()) {
            String protocol = matcher.group(1) != null ? matcher.group(1) : "http";
            String username = matcher.group(2);
            String password = matcher.group(3);
            String host = matcher.group(4);
            int port = Integer.parseInt(matcher.group(5));
            
            Proxy proxy = new Proxy(host, port, protocol);
            proxy.username = username;
            proxy.password = password;
            addProxy(proxy);
        } else {
            logger.warning("Invalid proxy format: " + proxyStr);
        }
    }
    
    public synchronized Proxy getProxy() {
        if (proxies.isEmpty()) {
            return null;
        }
        
        // 尝试最多 len(proxies) 次找到可用代理
        for (int i = 0; i < proxies.size(); i++) {
            int idx = (currentIndex + i) % proxies.size();
            Proxy proxy = proxies.get(idx);
            if (proxy.status == ProxyStatus.ALIVE && proxy.failureCount < maxFailures) {
                currentIndex = (idx + 1) % proxies.size();
                return proxy;
            }
        }
        
        // 返回未知状态代理
        for (Proxy proxy : proxies) {
            if (proxy.status == ProxyStatus.UNKNOWN) {
                return proxy;
            }
        }
        
        return null; // 所有代理都不可用
    }
    
    public void recordSuccess(Proxy proxy) {
        if (proxy == null) return;
        proxy.successCount++;
        proxy.status = ProxyStatus.ALIVE;
        proxy.lastChecked = System.currentTimeMillis();
    }
    
    public void recordFailure(Proxy proxy) {
        if (proxy == null) return;
        proxy.failureCount++;
        proxy.lastChecked = System.currentTimeMillis();
        if (proxy.failureCount >= maxFailures) {
            proxy.status = ProxyStatus.DEAD;
            logger.warning("Proxy marked as dead: " + proxy.getUrl());
        }
    }
    
    public void startHealthCheck() {
        if (running) return;
        running = true;
        healthCheckExecutor = Executors.newSingleThreadExecutor(r -> {
            Thread t = new Thread(r, "proxy-health-check");
            t.setDaemon(true);
            return t;
        });
        healthCheckExecutor.submit(this::healthCheckLoop);
        logger.info("Proxy health check started");
    }
    
    public void stopHealthCheck() {
        running = false;
        if (healthCheckExecutor != null) {
            healthCheckExecutor.shutdownNow();
        }
        logger.info("Proxy health check stopped");
    }
    
    private void healthCheckLoop() {
        while (running) {
            List<Proxy> copy = new ArrayList<>(proxies);
            for (Proxy proxy : copy) {
                if (!running) break;
                if (proxy.status == ProxyStatus.DEAD) {
                    if (System.currentTimeMillis() - proxy.lastChecked > checkIntervalMs * 2) {
                        checkProxy(proxy);
                    }
                } else {
                    checkProxy(proxy);
                }
            }
            try {
                Thread.sleep(checkIntervalMs);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                break;
            }
        }
    }
    
    private void checkProxy(Proxy proxy) {
        if (proxy == null) return;
        
        try {
            long startTime = System.currentTimeMillis();
            
            // 使用 HttpURLConnection 进行健康检查
            java.net.URL url = new java.net.URL(checkUrl);
            java.net.Proxy proxyConn = new java.net.Proxy(
                java.net.Proxy.Type.HTTP,
                new java.net.InetSocketAddress(proxy.host, proxy.port)
            );
            
            java.net.HttpURLConnection conn = (java.net.HttpURLConnection) url.openConnection(proxyConn);
            conn.setConnectTimeout(5000);
            conn.setReadTimeout(5000);
            conn.setRequestMethod("GET");
            
            int responseCode = conn.getResponseCode();
            long responseTime = System.currentTimeMillis() - startTime;
            
            conn.disconnect();
            
            if (responseCode == 200) {
                proxy.status = ProxyStatus.ALIVE;
                proxy.responseTime = responseTime;
                proxy.successCount++;
                proxy.lastChecked = System.currentTimeMillis();
            } else {
                proxy.failureCount++;
                if (proxy.failureCount >= maxFailures) {
                    proxy.status = ProxyStatus.DEAD;
                }
            }
        } catch (Exception e) {
            proxy.failureCount++;
            proxy.lastChecked = System.currentTimeMillis();
            if (proxy.failureCount >= maxFailures) {
                proxy.status = ProxyStatus.DEAD;
                logger.warning("Proxy marked as dead: " + proxy.getUrl() + " - " + e.getMessage());
            }
        }
    }
    
    public int size() { return proxies.size(); }
    
    public int aliveCount() {
        return (int) proxies.stream().filter(p -> p.status == ProxyStatus.ALIVE).count();
    }
    
    public int deadCount() {
        return (int) proxies.stream().filter(p -> p.status == ProxyStatus.DEAD).count();
    }
    
    public Map<String, Object> stats() {
        Map<String, Object> s = new HashMap<>();
        s.put("total", size());
        s.put("alive", aliveCount());
        s.put("dead", deadCount());
        s.put("unknown", (int) proxies.stream().filter(p -> p.status == ProxyStatus.UNKNOWN).count());
        return s;
    }
    
    // 常用 User-Agent 池
    public static final String[] USER_AGENTS = {
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    };
    
    private static volatile int uaIndex = 0;
    public static synchronized String getNextUserAgent() {
        return USER_AGENTS[(uaIndex++) % USER_AGENTS.length];
    }
}
