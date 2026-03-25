package com.javaspider.performance.circuit;

import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;

/**
 * 熔断器实现
 * 三种状态：CLOSED（正常）、OPEN（熔断）、HALF_OPEN（半开）
 */
public class CircuitBreaker {
    
    public enum State {
        CLOSED,     // 正常状态，允许请求通过
        OPEN,       // 熔断状态，拒绝请求
        HALF_OPEN   // 半开状态，允许部分请求通过测试
    }
    
    private final int failureThreshold;      // 失败阈值
    private final int successThreshold;      // 成功阈值（半开状态）
    private final long timeoutMs;            // 超时时间（毫秒）
    private final AtomicInteger failureCount;
    private final AtomicInteger successCount;
    private final AtomicLong lastFailureTime;
    private volatile State state;
    
    public CircuitBreaker(int failureThreshold, int successThreshold, long timeoutMs) {
        this.failureThreshold = failureThreshold;
        this.successThreshold = successThreshold;
        this.timeoutMs = timeoutMs;
        this.failureCount = new AtomicInteger(0);
        this.successCount = new AtomicInteger(0);
        this.lastFailureTime = new AtomicLong(0);
        this.state = State.CLOSED;
    }
    
    public CircuitBreaker() {
        this(5, 3, 60000); // 默认：5 次失败，3 次成功，60 秒超时
    }
    
    /**
     * 检查是否允许请求通过
     */
    public synchronized boolean allowRequest() {
        long now = System.currentTimeMillis();
        
        if (state == State.OPEN) {
            // 检查是否超过超时时间
            if (now - lastFailureTime.get() > timeoutMs) {
                state = State.HALF_OPEN;
                successCount.set(0);
                return true;
            }
            return false;
        }
        
        return true;
    }
    
    /**
     * 记录成功请求
     */
    public synchronized void recordSuccess() {
        if (state == State.HALF_OPEN) {
            int count = successCount.incrementAndGet();
            if (count >= successThreshold) {
                state = State.CLOSED;
                failureCount.set(0);
                successCount.set(0);
            }
        } else if (state == State.CLOSED) {
            failureCount.set(0);
        }
    }
    
    /**
     * 记录失败请求
     */
    public synchronized void recordFailure() {
        long now = System.currentTimeMillis();
        lastFailureTime.set(now);
        
        if (state == State.HALF_OPEN) {
            state = State.OPEN;
            successCount.set(0);
        } else if (state == State.CLOSED) {
            int count = failureCount.incrementAndGet();
            if (count >= failureThreshold) {
                state = State.OPEN;
            }
        }
    }
    
    /**
     * 获取当前状态
     */
    public State getState() {
        return state;
    }
    
    /**
     * 重置熔断器
     */
    public synchronized void reset() {
        state = State.CLOSED;
        failureCount.set(0);
        successCount.set(0);
        lastFailureTime.set(0);
    }
    
    /**
     * 获取统计信息
     */
    public String getStats() {
        return String.format("CircuitBreaker{state=%s, failures=%d, successes=%d}",
                state, failureCount.get(), successCount.get());
    }
}
