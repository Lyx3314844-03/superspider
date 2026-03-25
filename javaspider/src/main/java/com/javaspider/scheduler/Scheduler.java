package com.javaspider.scheduler;

import com.javaspider.core.Request;

import java.util.concurrent.TimeUnit;

/**
 * 调度器接口
 */
public interface Scheduler {
    void push(Request request);
    Request poll() throws InterruptedException;
    Request poll(long timeout, TimeUnit unit) throws InterruptedException;
    Request pollNow();
    int size();
    int getTotalCount();
    int getProcessedCount();
    boolean isEmpty();
    void clear();
    void close();
}
