package com.javaspider.core;

import lombok.AllArgsConstructor;
import lombok.Data;

/**
 * SpiderStatus - 爬虫状态
 * 
 * 封装爬虫运行状态信息
 * 
 * @author Lan
 * @version 2.0.0
 * @since 2026-03-20
 */
@Data
@AllArgsConstructor
public class SpiderStatus {
    
    /**
     * 爬虫 ID
     */
    private String spiderId;
    
    /**
     * 爬虫名称
     */
    private String spiderName;
    
    /**
     * 是否运行中
     */
    private boolean running;
    
    /**
     * 是否暂停
     */
    private boolean paused;
    
    /**
     * 总请求数
     */
    private long totalRequests;
    
    /**
     * 成功请求数
     */
    private long successRequests;
    
    /**
     * 失败请求数
     */
    private long failedRequests;
    
    /**
     * 开始时间
     */
    private long startTime;
    
    /**
     * 结束时间
     */
    private long endTime;
    
    /**
     * 获取成功率
     * @return 成功率
     */
    public double getSuccessRate() {
        if (totalRequests == 0) {
            return 0.0;
        }
        return (double) successRequests / totalRequests * 100;
    }
    
    /**
     * 获取失败率
     * @return 失败率
     */
    public double getFailureRate() {
        if (totalRequests == 0) {
            return 0.0;
        }
        return (double) failedRequests / totalRequests * 100;
    }
    
    /**
     * 获取运行时长 (毫秒)
     * @return 运行时长
     */
    public long getDuration() {
        if (endTime == 0) {
            return System.currentTimeMillis() - startTime;
        }
        return endTime - startTime;
    }
    
    /**
     * 获取运行时长 (秒)
     * @return 运行时长
     */
    public double getDurationSeconds() {
        return getDuration() / 1000.0;
    }
    
    /**
     * 获取 QPS (每秒请求数)
     * @return QPS
     */
    public long getQPS() {
        long duration = getDuration();
        if (duration == 0) {
            return 0;
        }
        return successRequests * 1000 / duration;
    }
    
    /**
     * 获取状态描述
     * @return 状态描述
     */
    public String getStatusText() {
        if (!running) {
            return "STOPPED";
        }
        if (paused) {
            return "PAUSED";
        }
        return "RUNNING";
    }
    
    /**
     * 获取运行时长格式化
     * @return 格式化后的时长
     */
    public String getDurationFormatted() {
        long duration = getDuration();
        long seconds = duration / 1000;
        long minutes = seconds / 60;
        long hours = minutes / 60;
        
        if (hours > 0) {
            return String.format("%dh %dm %ds", hours, minutes % 60, seconds % 60);
        } else if (minutes > 0) {
            return String.format("%dm %ds", minutes, seconds % 60);
        } else {
            return String.format("%ds", seconds);
        }
    }
    
    /**
     * 转换为字符串
     * @return 字符串表示
     */
    @Override
    public String toString() {
        return String.format(
            "SpiderStatus{id='%s', name='%s', status=%s, total=%d, success=%d, failed=%d, duration=%s, qps=%d}",
            spiderId,
            spiderName,
            getStatusText(),
            totalRequests,
            successRequests,
            failedRequests,
            getDurationFormatted(),
            getQPS()
        );
    }
    
    /**
     * 创建 SpiderStatus 实例
     * @param spiderId 爬虫 ID
     * @param spiderName 爬虫名称
     * @return SpiderStatus 实例
     */
    public static SpiderStatus of(String spiderId, String spiderName) {
        return new SpiderStatus(
            spiderId,
            spiderName,
            false,
            false,
            0,
            0,
            0,
            0,
            0
        );
    }
}
