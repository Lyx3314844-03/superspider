package com.javaspider.monitor;

import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.ConcurrentHashMap;
import java.util.Map;
import java.util.HashMap;
import java.util.List;
import java.util.ArrayList;

/**
 * 爬虫监控系统
 * 实时监控爬虫状态和性能指标
 */
public class SpiderMonitor {
    
    private final String spiderName;
    private final long startTime;
    private final AtomicInteger successCount = new AtomicInteger(0);
    private final AtomicInteger failCount = new AtomicInteger(0);
    private final AtomicInteger skipCount = new AtomicInteger(0);
    private final AtomicInteger totalRequests = new AtomicInteger(0);
    private final AtomicInteger currentThreads = new AtomicInteger(0);
    private final Map<String, Long> domainStats = new ConcurrentHashMap<>();
    private final List<Long> latencySamples = java.util.Collections.synchronizedList(new ArrayList<>());
    private volatile boolean running = false;
    private volatile boolean paused = false;
    
    public SpiderMonitor(String spiderName) {
        this.spiderName = spiderName;
        this.startTime = System.currentTimeMillis();
    }
    
    /**
     * 记录成功
     */
    public void onSuccess(String url) {
        successCount.incrementAndGet();
        totalRequests.incrementAndGet();
        updateDomainStats(url, true);
    }

    public void recordResponseTime(long latencyMs) {
        if (latencyMs <= 0) {
            return;
        }
        latencySamples.add(latencyMs);
        if (latencySamples.size() > 512) {
            latencySamples.remove(0);
        }
    }
    
    /**
     * 记录失败
     */
    public void onFail(String url) {
        failCount.incrementAndGet();
        totalRequests.incrementAndGet();
        updateDomainStats(url, false);
    }
    
    /**
     * 记录跳过
     */
    public void onSkip(String url) {
        skipCount.incrementAndGet();
    }
    
    /**
     * 更新线程数
     */
    public void updateThreads(int count) {
        currentThreads.set(count);
    }
    
    /**
     * 设置运行状态
     */
    public void setRunning(boolean running) {
        this.running = running;
        if (running) {
            this.paused = false;
        }
    }
    
    /**
     * 设置暂停状态
     */
    public void setPaused(boolean paused) {
        this.paused = paused;
    }
    
    /**
     * 更新域名统计
     */
    private void updateDomainStats(String url, boolean success) {
        try {
            String domain = extractDomain(url);
            if (domain != null) {
                domainStats.compute(domain, (k, v) -> {
                    if (v == null) v = 0L;
                    return v + (success ? 1 : -1);
                });
            }
        } catch (Exception e) {
            // 忽略域名统计错误
        }
    }
    
    /**
     * 提取域名
     */
    private String extractDomain(String url) {
        try {
            java.net.URL u = new java.net.URL(url);
            return u.getHost();
        } catch (Exception e) {
            return null;
        }
    }
    
    /**
     * 获取监控统计
     */
    public MonitorStats getStats() {
        MonitorStats stats = new MonitorStats();
        stats.setSpiderName(spiderName);
        stats.setStartTime(startTime);
        stats.setRunningTime(System.currentTimeMillis() - startTime);
        stats.setSuccessCount(successCount.get());
        stats.setFailCount(failCount.get());
        stats.setSkipCount(skipCount.get());
        stats.setTotalRequests(totalRequests.get());
        stats.setCurrentThreads(currentThreads.get());
        stats.setRunning(running);
        stats.setPaused(paused);
        
        // 计算成功率
        int total = successCount.get() + failCount.get();
        stats.setSuccessRate(total > 0 ? (double) successCount.get() / total * 100 : 0);
        
        // 计算速度
        long elapsedSeconds = stats.getRunningTime() / 1000;
        stats.setSpeed(elapsedSeconds > 0 ? (double) totalRequests.get() / elapsedSeconds : 0);
        stats.setQps(stats.getSpeed());
        stats.setLatencyP95(percentile(0.95));
        stats.setLatencyP99(percentile(0.99));
        
        // 域名统计
        stats.setDomainStats(new HashMap<>(domainStats));
        
        return stats;
    }
    
    /**
     * 打印监控信息
     */
    public void printStats() {
        MonitorStats stats = getStats();
        
        System.out.println("\n========== Spider Monitor ==========");
        System.out.println("Spider Name: " + stats.getSpiderName());
        System.out.println("Status: " + (stats.isPaused() ? "PAUSED" : (stats.isRunning() ? "RUNNING" : "STOPPED")));
        System.out.println("Running Time: " + formatDuration(stats.getRunningTime()));
        System.out.println();
        System.out.println("Requests:");
        System.out.println("  Total: " + stats.getTotalRequests());
        System.out.println("  Success: " + stats.getSuccessCount());
        System.out.println("  Failed: " + stats.getFailCount());
        System.out.println("  Skipped: " + stats.getSkipCount());
        System.out.println();
        System.out.println("Performance:");
        System.out.println("  Success Rate: " + String.format("%.2f", stats.getSuccessRate()) + "%");
        System.out.println("  Speed: " + String.format("%.2f", stats.getSpeed()) + " req/s");
        System.out.println("  P95: " + String.format("%.2f", stats.getLatencyP95()) + "ms");
        System.out.println("  P99: " + String.format("%.2f", stats.getLatencyP99()) + "ms");
        System.out.println("  Threads: " + stats.getCurrentThreads());
        System.out.println("=====================================\n");
    }

    private double percentile(double p) {
        if (latencySamples.isEmpty()) {
            return 0.0;
        }
        List<Long> copy = new ArrayList<>(latencySamples);
        copy.sort(Long::compareTo);
        int index = (int) Math.floor((copy.size() - 1) * p);
        if (index < 0) index = 0;
        if (index >= copy.size()) index = copy.size() - 1;
        return copy.get(index);
    }
    
    /**
     * 格式化持续时间
     */
    private String formatDuration(long ms) {
        long seconds = ms / 1000;
        long minutes = seconds / 60;
        long hours = minutes / 60;
        
        return String.format("%02d:%02d:%02d", hours, minutes % 60, seconds % 60);
    }
    
    /**
     * 监控统计类
     */
    public static class MonitorStats {
        private String spiderName;
        private long startTime;
        private long runningTime;
        private int totalRequests;
        private int successCount;
        private int failCount;
        private int skipCount;
        private int currentThreads;
        private boolean running;
        private boolean paused;
        private double successRate;
        private double speed;
        private double qps;
        private double latencyP95;
        private double latencyP99;
        private Map<String, Long> domainStats;
        
        // Getters and Setters
        public String getSpiderName() { return spiderName; }
        public void setSpiderName(String spiderName) { this.spiderName = spiderName; }
        
        public long getStartTime() { return startTime; }
        public void setStartTime(long startTime) { this.startTime = startTime; }
        
        public long getRunningTime() { return runningTime; }
        public void setRunningTime(long runningTime) { this.runningTime = runningTime; }
        
        public int getTotalRequests() { return totalRequests; }
        public void setTotalRequests(int totalRequests) { this.totalRequests = totalRequests; }
        
        public int getSuccessCount() { return successCount; }
        public void setSuccessCount(int successCount) { this.successCount = successCount; }
        
        public int getFailCount() { return failCount; }
        public void setFailCount(int failCount) { this.failCount = failCount; }
        
        public int getSkipCount() { return skipCount; }
        public void setSkipCount(int skipCount) { this.skipCount = skipCount; }
        
        public int getCurrentThreads() { return currentThreads; }
        public void setCurrentThreads(int currentThreads) { this.currentThreads = currentThreads; }
        
        public boolean isRunning() { return running; }
        public void setRunning(boolean running) { this.running = running; }
        
        public boolean isPaused() { return paused; }
        public void setPaused(boolean paused) { this.paused = paused; }
        
        public double getSuccessRate() { return successRate; }
        public void setSuccessRate(double successRate) { this.successRate = successRate; }
        
        public double getSpeed() { return speed; }
        public void setSpeed(double speed) { this.speed = speed; }

        public double getQps() { return qps; }
        public void setQps(double qps) { this.qps = qps; }

        public double getLatencyP95() { return latencyP95; }
        public void setLatencyP95(double latencyP95) { this.latencyP95 = latencyP95; }

        public double getLatencyP99() { return latencyP99; }
        public void setLatencyP99(double latencyP99) { this.latencyP99 = latencyP99; }

        public Map<String, Long> getDomainStats() { return domainStats; }
        public void setDomainStats(Map<String, Long> domainStats) { this.domainStats = domainStats; }
    }
}
