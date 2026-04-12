package com.javaspider.scheduler;

import com.javaspider.core.Request;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Comparator;
import java.util.Set;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * 基于队列的调度器
 */
public class QueueScheduler implements Scheduler {
    private static final Logger logger = LoggerFactory.getLogger(QueueScheduler.class);

    private final BlockingQueue<Request> queue;
    private final Set<String> processedUrls;
    private final AtomicInteger submittedCount = new AtomicInteger(0);  // 总提交数
    private final AtomicInteger dequeuedCount = new AtomicInteger(0);  // 出队处理数

    public QueueScheduler() {
        this.queue = new PriorityBlockingQueue<>(100, Comparator.comparingInt(Request::getPriority));
        this.processedUrls = ConcurrentHashMap.newKeySet();
    }

    @Override
    public void push(Request request) {
        if (request != null && processedUrls.add(request.getUrl())) {
            queue.offer(request);
            submittedCount.incrementAndGet();
        }
    }

    @Override
    public Request poll() throws InterruptedException {
        Request request = queue.take();
        if (request != null) {
            dequeuedCount.incrementAndGet();
        }
        return request;
    }

    @Override
    public Request poll(long timeout, TimeUnit unit) throws InterruptedException {
        Request request = queue.poll(timeout, unit);
        if (request != null) {
            dequeuedCount.incrementAndGet();
        }
        return request;
    }

    @Override
    public Request pollNow() {
        Request request = queue.poll();
        if (request != null) {
            dequeuedCount.incrementAndGet();
        }
        return request;
    }

    @Override
    public int size() {
        return queue.size();
    }

    @Override
    public int getTotalCount() {
        return submittedCount.get();
    }

    @Override
    public int getProcessedCount() {
        return dequeuedCount.get();
    }

    @Override
    public boolean isEmpty() {
        return queue.isEmpty();
    }

    @Override
    public void clear() {
        queue.clear();
        processedUrls.clear();
        submittedCount.set(0);
        dequeuedCount.set(0);
    }

    @Override
    public void close() {
        clear();
    }
}
