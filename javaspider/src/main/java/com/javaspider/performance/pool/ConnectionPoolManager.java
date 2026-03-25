package com.javaspider.performance.pool;

import org.apache.http.HttpHost;
import org.apache.http.conn.routing.HttpRoute;
import org.apache.http.impl.conn.PoolingHttpClientConnectionManager;
import org.apache.http.pool.ConnPoolControl;
import org.apache.http.pool.PoolStats;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;

/**
 * 高性能连接池管理器
 * 类似 Scrapy 的 HTTPConnectionPool
 *
 * 特性:
 * - 连接复用
 * - 自动过期清理
 * - 连接池监控
 * - 动态调整池大小
 */
public class ConnectionPoolManager {
    private static final Logger logger = LoggerFactory.getLogger(ConnectionPoolManager.class);

    // 默认配置
    private static final int DEFAULT_MAX_TOTAL = 200;
    private static final int DEFAULT_MAX_PER_ROUTE = 10;
    private static final int DEFAULT_CONNECTION_TTL = -1; // 无限
    private static final int DEFAULT_CLOSE_IDLE_INTERVAL = 30; // 秒

    private final PoolingHttpClientConnectionManager connectionManager;
    private final Map<String, Integer> maxPerRouteConfig = new ConcurrentHashMap<>();

    private final int maxTotal;
    private final int defaultMaxPerRoute;
    private final long connectionTtl;
    private final int closeIdleInterval;

    private volatile boolean running = true;

    /**
     * 构造函数
     */
    public ConnectionPoolManager() {
        this(DEFAULT_MAX_TOTAL, DEFAULT_MAX_PER_ROUTE);
    }

    /**
     * 构造函数
     *
     * @param maxTotal 最大总连接数
     * @param defaultMaxPerRoute 每个路由默认最大连接数
     */
    public ConnectionPoolManager(int maxTotal, int defaultMaxPerRoute) {
        this(maxTotal, defaultMaxPerRoute, DEFAULT_CONNECTION_TTL, DEFAULT_CLOSE_IDLE_INTERVAL);
    }

    /**
     * 构造函数
     *
     * @param maxTotal 最大总连接数
     * @param defaultMaxPerRoute 每个路由默认最大连接数
     * @param connectionTtl 连接存活时间 (ms), -1 表示无限
     * @param closeIdleInterval 空闲连接关闭间隔 (秒)
     */
    public ConnectionPoolManager(int maxTotal, int defaultMaxPerRoute,
                                  long connectionTtl, int closeIdleInterval) {
        this.maxTotal = maxTotal;
        this.defaultMaxPerRoute = defaultMaxPerRoute;
        this.connectionTtl = connectionTtl;
        this.closeIdleInterval = closeIdleInterval;

        this.connectionManager = new PoolingHttpClientConnectionManager();
        this.connectionManager.setMaxTotal(maxTotal);
        this.connectionManager.setDefaultMaxPerRoute(defaultMaxPerRoute);

        // 启动后台清理线程
        startIdleConnectionCloser();

        logger.info("ConnectionPoolManager initialized: maxTotal={}, defaultMaxPerRoute={}",
                maxTotal, defaultMaxPerRoute);
    }

    /**
     * 获取连接池管理器
     */
    public PoolingHttpClientConnectionManager getConnectionManager() {
        return connectionManager;
    }

    /**
     * 设置特定路由的最大连接数
     *
     * @param route 路由 (host:port)
     * @param max 最大连接数
     */
    public void setMaxPerRoute(String route, int max) {
        maxPerRouteConfig.put(route, max);
        // 使用默认端口
        int port = route.contains(":") ? Integer.parseInt(route.split(":")[1]) : 80;
        String host = route.split(":")[0];
        HttpHost httpHost = new HttpHost(host, port);
        HttpRoute httpRoute = new HttpRoute(httpHost);
        connectionManager.setMaxPerRoute(httpRoute, max);
        logger.debug("Set max per route {}: {}", route, max);
    }

    /**
     * 获取连接池统计信息
     */
    public PoolStats getStats() {
        ConnPoolControl control = connectionManager;
        return control.getTotalStats();
    }

    /**
     * 获取特定路由的统计信息
     */
    public PoolStats getRouteStats(String route) {
        int port = route.contains(":") ? Integer.parseInt(route.split(":")[1]) : 80;
        String host = route.split(":")[0];
        HttpHost httpHost = new HttpHost(host, port);
        HttpRoute httpRoute = new HttpRoute(httpHost);
        return connectionManager.getStats(httpRoute);
    }
    
    /**
     * 关闭空闲连接
     */
    public void closeIdleConnections() {
        connectionManager.closeIdleConnections(closeIdleInterval, TimeUnit.SECONDS);
        logger.debug("Closed idle connections");
    }
    
    /**
     * 关闭过期连接
     */
    public void closeExpiredConnections() {
        connectionManager.closeExpiredConnections();
        logger.debug("Closed expired connections");
    }
    
    /**
     * 清空连接池
     */
    public void clear() {
        connectionManager.closeIdleConnections(0, TimeUnit.SECONDS);
        logger.info("Connection pool cleared");
    }
    
    /**
     * 关闭连接池
     */
    public void shutdown() {
        running = false;
        connectionManager.shutdown();
        logger.info("ConnectionPoolManager shutdown. Stats: {}", getStats());
    }
    
    /**
     * 启动后台空闲连接清理线程
     */
    private void startIdleConnectionCloser() {
        Thread cleanerThread = new Thread(() -> {
            while (running) {
                try {
                    Thread.sleep(closeIdleInterval * 1000L);
                    closeIdleConnections();
                    closeExpiredConnections();
                    
                    // 记录池状态
                    PoolStats stats = getStats();
                    logger.trace("Pool stats: leased={}, pending={}, available={}", 
                            stats.getLeased(), stats.getPending(), stats.getAvailable());
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    break;
                }
            }
        }, "ConnectionPool-Cleaner");
        cleanerThread.setDaemon(true);
        cleanerThread.start();
    }
    
    /**
     * 获取池使用率
     */
    public double getUtilizationRate() {
        PoolStats stats = getStats();
        if (maxTotal == 0) return 0;
        return (double) stats.getLeased() / maxTotal;
    }
    
    /**
     * 检查是否需要扩展池
     */
    public boolean needsExpansion() {
        PoolStats stats = getStats();
        return stats.getPending() > 0 || getUtilizationRate() > 0.8;
    }
    
    /**
     * 动态扩展连接池
     */
    public void expand(int additionalConnections) {
        int newMax = maxTotal + additionalConnections;
        connectionManager.setMaxTotal(newMax);
        logger.info("Connection pool expanded from {} to {}", maxTotal, newMax);
    }
    
    /**
     * 创建连接池构建器
     */
    public static Builder builder() {
        return new Builder();
    }
    
    /**
     * 构建器
     */
    public static class Builder {
        private int maxTotal = DEFAULT_MAX_TOTAL;
        private int defaultMaxPerRoute = DEFAULT_MAX_PER_ROUTE;
        private long connectionTtl = DEFAULT_CONNECTION_TTL;
        private int closeIdleInterval = DEFAULT_CLOSE_IDLE_INTERVAL;
        
        public Builder maxTotal(int maxTotal) {
            this.maxTotal = maxTotal;
            return this;
        }
        
        public Builder defaultMaxPerRoute(int defaultMaxPerRoute) {
            this.defaultMaxPerRoute = defaultMaxPerRoute;
            return this;
        }
        
        public Builder connectionTtl(long connectionTtl) {
            this.connectionTtl = connectionTtl;
            return this;
        }
        
        public Builder closeIdleInterval(int closeIdleInterval) {
            this.closeIdleInterval = closeIdleInterval;
            return this;
        }
        
        public ConnectionPoolManager build() {
            return new ConnectionPoolManager(maxTotal, defaultMaxPerRoute, 
                    connectionTtl, closeIdleInterval);
        }
    }
}
