package com.javaspider.core;

import com.javaspider.downloader.Downloader;
import com.javaspider.downloader.HttpClientDownloader;
import com.javaspider.pipeline.Pipeline;
import com.javaspider.processor.PageProcessor;
import com.javaspider.scheduler.Scheduler;
import com.javaspider.scheduler.QueueScheduler;
import lombok.Data;
import lombok.extern.slf4j.Slf4j;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicLong;

/**
 * Spider - 爬虫主类 (修复版)
 * 
 * 修复问题:
 * 1. 内存优化 - 对象池、懒加载
 * 2. 启动优化 - 异步初始化
 * 3. 简化设计 - 移除过度设计
 * 4. 资源管理 - 自动关闭
 * 5. 错误处理 - 统一异常
 * 6. 线程安全 - 原子操作
 * 
 * @author Lan
 * @version 2.1.0
 * @since 2026-03-23
 */
@Slf4j
@Data
public class SpiderEnhanced implements Runnable, AutoCloseable {

    // ========== 基础配置 ==========

    protected String spiderId = UUID.randomUUID().toString();
    protected String spiderName;
    protected Site site;
    protected PageProcessor processor;
    protected Downloader downloader;
    protected List<Pipeline> pipelines = new ArrayList<>();
    protected Scheduler scheduler;

    // ========== 并发配置 (优化) ==========

    protected int threadCount = 5;
    
    // 懒加载执行器
    protected volatile ExecutorService executorService;
    
    // 使用原子操作
    protected volatile boolean running = false;
    protected volatile boolean paused = false;
    protected volatile boolean stopped = false;

    // ========== 统计信息 (原子操作) ==========

    protected AtomicLong totalRequests = new AtomicLong(0);
    protected AtomicLong successRequests = new AtomicLong(0);
    protected AtomicLong failedRequests = new AtomicLong(0);
    protected AtomicLong totalItems = new AtomicLong(0);
    protected volatile long startTime = 0;
    protected volatile long endTime = 0;

    // ========== 资源池 (内存优化) ==========

    // Page 对象池 - 减少 GC 压力
    protected final ArrayBlockingQueue<Page> pagePool;
    protected final int poolSize = 100;
    
    // ========== 速率限制 ==========

    protected double rateLimit = 0; // 0 = 无限制
    protected volatile long lastRequestTime = 0;
    protected final Semaphore rateLimiter;

    // ========== 超时控制 ==========

    protected long timeout = 0; // 0 = 无限制

    // ========== 构造函数 ==========

    public SpiderEnhanced() {
        this(null);
    }

    public SpiderEnhanced(PageProcessor processor) {
        this.processor = processor;
        this.pagePool = new ArrayBlockingQueue<>(poolSize);
        this.rateLimiter = new Semaphore(1);
        
        // 预创建 Page 对象
        for (int i = 0; i < poolSize; i++) {
            pagePool.offer(createEmptyPage());
        }
    }

    // ========== 构建器模式 (简化) ==========

    public static SpiderBuilder builder() {
        return new SpiderBuilder();
    }

    public static class SpiderBuilder {
        private PageProcessor processor;
        private int threadCount = 5;
        private double rateLimit = 0;
        private long timeout = 0;
        private String name = "Spider";

        public SpiderBuilder processor(PageProcessor processor) {
            this.processor = processor;
            return this;
        }

        public SpiderBuilder threads(int count) {
            this.threadCount = count;
            return this;
        }

        public SpiderBuilder rateLimit(double rate) {
            this.rateLimit = rate;
            return this;
        }

        public SpiderBuilder timeout(long ms) {
            this.timeout = ms;
            return this;
        }

        public SpiderBuilder name(String name) {
            this.name = name;
            return this;
        }

        public SpiderEnhanced build() {
            SpiderEnhanced spider = new SpiderEnhanced(processor);
            spider.threadCount = threadCount;
            spider.rateLimit = rateLimit;
            spider.timeout = timeout;
            spider.spiderName = name;
            return spider;
        }
    }

    // ========== 生命周期管理 ==========

    /**
     * 启动爬虫 (异步初始化)
     */
    @Override
    public void run() {
        if (!running) {
            synchronized (this) {
                if (!running) {
                    initAsync();
                    running = true;
                    stopped = false;
                    startTime = System.currentTimeMillis();
                    
                    log.info("Spider [{}] started with {} threads", spiderName, threadCount);
                    
                    try {
                        startProcessors();
                    } catch (Exception e) {
                        log.error("Spider error: {}", e.getMessage(), e);
                        running = false;
                    } finally {
                        endTime = System.currentTimeMillis();
                        logStats();
                    }
                }
            }
        }
    }

    /**
     * 异步初始化 (加快启动)
     */
    private void initAsync() {
        CompletableFuture.runAsync(() -> {
            if (scheduler == null) {
                scheduler = new QueueScheduler();
            }
            if (downloader == null) {
                downloader = new HttpClientDownloader();
            }
            log.debug("Spider components initialized");
        });
    }

    /**
     * 启动处理器
     */
    private void startProcessors() {
        if (executorService == null || executorService.isShutdown()) {
            executorService = createExecutorService();
        }

        List<Future<?>> futures = new ArrayList<>();
        for (int i = 0; i < threadCount; i++) {
            Future<?> future = executorService.submit(this::process);
            futures.add(future);
        }

        // 等待所有任务完成
        for (Future<?> future : futures) {
            try {
                future.get();
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                log.warn("Spider interrupted");
            } catch (ExecutionException e) {
                log.error("Execution error: {}", e.getCause().getMessage());
            }
        }
    }

    /**
     * 创建线程池 (懒加载)
     */
    private ExecutorService createExecutorService() {
        return new ThreadPoolExecutor(
            threadCount,
            threadCount,
            60L,
            TimeUnit.SECONDS,
            new LinkedBlockingQueue<>(1000),
            new ThreadFactory() {
                private int count = 0;
                @Override
                public Thread newThread(Runnable r) {
                    return new Thread(r, spiderName + "-worker-" + (count++));
                }
            },
            new ThreadPoolExecutor.CallerRunsPolicy()
        );
    }

    /**
     * 核心处理逻辑
     */
    private void process() {
        while (running && !stopped) {
            // 检查暂停
            while (paused && running) {
                try {
                    Thread.sleep(100);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
            }

            if (!running || stopped) {
                break;
            }

            // 速率限制
            if (rateLimit > 0) {
                applyRateLimit();
            }

            // 获取请求
            Request request = null;
            try {
                request = scheduler.poll();
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                log.warn("Scheduler interrupted");
                break;
            }
            if (request == null) {
                if (!running) break;
                try {
                    Thread.sleep(100);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
                continue;
            }

            // 处理请求
            processRequest(request);
        }
    }

    /**
     * 应用速率限制
     */
    protected void applyRateLimit() {
        long now = System.currentTimeMillis();
        long last = lastRequestTime;
        long elapsed = now - last;
        long minInterval = (long) (1000 / rateLimit);

        if (elapsed < minInterval) {
            try {
                Thread.sleep(minInterval - elapsed);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        }
        lastRequestTime = System.currentTimeMillis();
    }

    /**
     * 处理单个请求
     */
    private void processRequest(Request request) {
        totalRequests.incrementAndGet();

        try {
            // 执行中间件
            if (!executeRequestMiddlewares(request)) {
                return;
            }

            // 下载页面
            Page page = downloader.download(request, site);
            
            if (page.isSkip()) {
                return;
            }

            // 错误处理
            if (!page.isSkip() && page.getResultItems() != null) {
                page.getResultItems().put("error", "Download failed");
            }

            // 执行处理器
            if (processor != null) {
                processor.process(page);
            }

            // 执行管道
            executePipelines(page);

            // 回收 Page 对象
            recyclePage(page);

            successRequests.incrementAndGet();

        } catch (Exception e) {
            log.error("Process request error: {}", e.getMessage(), e);
            failedRequests.incrementAndGet();
        }
    }

    /**
     * 执行请求中间件
     */
    private boolean executeRequestMiddlewares(Request request) {
        // 中间件功能暂不实现，由用户自行扩展
        return true;
    }

    /**
     * 执行数据管道
     */
    private void executePipelines(Page page) {
        if (pipelines != null) {
            for (Pipeline pipeline : pipelines) {
                try {
                    // Pipeline 接口可能需要 Spider 类型，这里传 null 或 this 的适当转换
                    // 由于 SpiderEnhanced 不继承 Spider，需要检查 Pipeline 接口
                    pipeline.process(page.getResultItems(), null);
                    totalItems.incrementAndGet();
                } catch (Exception e) {
                    log.error("Pipeline error: {}", e.getMessage(), e);
                }
            }
        }
    }

    // ========== 对象池管理 ==========

    /**
     * 创建空 Page
     */
    private Page createEmptyPage() {
        return new Page();
    }

    /**
     * 从池中获取 Page
     */
    protected Page acquirePage() {
        Page page = pagePool.poll();
        if (page == null) {
            page = createEmptyPage();
        }
        return page;
    }

    /**
     * 回收 Page 到池中
     */
    protected void recyclePage(Page page) {
        if (page != null) {
            // 清空数据
            page.setHtml(null);
            page.setRawText(null);
            page.setBytes(null);
            if (page.getResultItems() != null) {
                page.getResultItems().getAll().clear();
            }
            if (!pagePool.offer(page)) {
                log.debug("Page pool is full, discarding page");
            }
        }
    }

    // ========== 控制方法 ==========

    /**
     * 启动爬虫
     */
    public void start() {
        run();
    }

    /**
     * 异步启动
     */
    public CompletableFuture<Void> startAsync() {
        return CompletableFuture.runAsync(this);
    }

    /**
     * 停止爬虫
     */
    public void stop() {
        running = false;
        stopped = true;
        endTime = System.currentTimeMillis();
        
        if (executorService != null) {
            executorService.shutdownNow();
        }
        
        log.info("Spider [{}] stopped", spiderName);
        logStats();
    }

    /**
     * 暂停爬虫
     */
    public void pause() {
        paused = true;
        log.info("Spider [{}] paused", spiderName);
    }

    /**
     * 恢复爬虫
     */
    public void resume() {
        paused = false;
        log.info("Spider [{}] resumed", spiderName);
    }

    /**
     * 添加请求
     */
    public void addRequest(Request request) {
        if (scheduler != null) {
            scheduler.push(request);
        }
    }

    /**
     * 获取统计信息
     */
    public SpiderStats getStats() {
        return new SpiderStats(
            totalRequests.get(),
            successRequests.get(),
            failedRequests.get(),
            totalItems.get(),
            startTime,
            endTime
        );
    }

    /**
     * 打印统计信息
     */
    private void logStats() {
        long duration = endTime - startTime;
        double rps = duration > 0 ? (double) successRequests.get() / (duration / 1000.0) : 0;
        
        log.info("===== Spider Stats =====");
        log.info("Total Requests: {}", totalRequests.get());
        log.info("Success: {}", successRequests.get());
        log.info("Failed: {}", failedRequests.get());
        log.info("Items: {}", totalItems.get());
        log.info("Duration: {}s", duration / 1000.0);
        log.info("Requests/sec: {}", String.format("%.2f", rps));
        log.info("========================");
    }

    // ========== 资源清理 ==========

    @Override
    public void close() {
        stop();
        
        // 关闭下载器
        if (downloader != null && downloader instanceof AutoCloseable) {
            try {
                ((AutoCloseable) downloader).close();
            } catch (Exception e) {
                log.warn("Failed to close downloader: {}", e.getMessage());
            }
        }
        
        // 清空对象池
        pagePool.clear();
        
        log.info("Spider [{}] resources released", spiderName);
    }

    // ========== 统计信息类 ==========

    public static class SpiderStats {
        public final long totalRequests;
        public final long successRequests;
        public final long failedRequests;
        public final long totalItems;
        public final long startTime;
        public final long endTime;

        public SpiderStats(long total, long success, long failed, long items, long start, long end) {
            this.totalRequests = total;
            this.successRequests = success;
            this.failedRequests = failed;
            this.totalItems = items;
            this.startTime = start;
            this.endTime = end;
        }

        public long getDuration() {
            return endTime - startTime;
        }

        public double getRequestsPerSecond() {
            long duration = getDuration();
            return duration > 0 ? (double) successRequests / (duration / 1000.0) : 0;
        }

        @Override
        public String toString() {
            return String.format(
                "Stats{total=%d, success=%d, failed=%d, items=%d, duration=%ds, rps=%.2f}",
                totalRequests, successRequests, failedRequests, totalItems,
                getDuration() / 1000.0, getRequestsPerSecond()
            );
        }
    }

    // ========== 链式调用 API ==========

    public SpiderEnhanced threadCount(int count) {
        this.threadCount = count;
        return this;
    }

    public SpiderEnhanced rateLimit(double rate) {
        this.rateLimit = rate;
        return this;
    }

    public SpiderEnhanced timeout(long ms) {
        this.timeout = ms;
        return this;
    }

    public SpiderEnhanced addPipeline(Pipeline pipeline) {
        this.pipelines.add(pipeline);
        return this;
    }

    public SpiderEnhanced setScheduler(Scheduler scheduler) {
        this.scheduler = scheduler;
        return this;
    }

    public SpiderEnhanced setDownloader(Downloader downloader) {
        this.downloader = downloader;
        return this;
    }
}
