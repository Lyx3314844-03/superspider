package com.javaspider.performance;

import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

/**
 * 高性能线程池执行器
 * 兼容 Java 17+，使用虚拟线程(Java 21+)或传统线程池
 */
public class VirtualThreadExecutor {

    private final ExecutorService executor;

    public VirtualThreadExecutor() {
        // 根据 Java 版本选择执行器
        this.executor = createExecutor();
    }

    private ExecutorService createExecutor() {
        try {
            // 尝试使用 Java 21+ 虚拟线程
            var method = Executors.class.getMethod("newVirtualThreadPerTaskExecutor");
            return (ExecutorService) method.invoke(null);
        } catch (Exception e) {
            // Java 17-20: 使用缓存线程池作为降级方案
            System.out.println("Warning: Virtual threads not available (Java 21+ required). Using cached thread pool.");
            return Executors.newCachedThreadPool();
        }
    }

    /**
     * 提交异步任务
     */
    public void submit(Runnable task) {
        executor.submit(task);
    }

    /**
     * 批量并发执行
     * @param tasks 任务列表
     * @param maxConcurrent 最大并发数
     */
    public void executeBatch(java.util.List<Runnable> tasks, int maxConcurrent) {
        var semaphore = new java.util.concurrent.Semaphore(maxConcurrent);

        for (Runnable task : tasks) {
            executor.submit(() -> {
                try {
                    semaphore.acquire();
                    task.run();
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                } finally {
                    semaphore.release();
                }
            });
        }
    }

    /**
     * 优雅关闭
     */
    public void shutdown() {
        executor.shutdown();
        try {
            if (!executor.awaitTermination(60, TimeUnit.SECONDS)) {
                executor.shutdownNow();
            }
        } catch (InterruptedException e) {
            executor.shutdownNow();
            Thread.currentThread().interrupt();
        }
    }

    /**
     * 创建爬虫专用执行器
     */
    public static VirtualThreadExecutor createSpiderExecutor() {
        return new VirtualThreadExecutor();
    }
}
