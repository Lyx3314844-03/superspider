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
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicLong;

/**
 * Spider - 爬虫主类
 *
 * 吸收 webmagic Spider 设计，支持链式调用 API
 * 集成 AI 提取、多平台支持、分布式爬虫等功能
 *
 * @author Lan
 * @version 2.0.0
 * @since 2026-03-20
 */
@Slf4j
@Data
public class Spider implements Runnable {

    // ========== 基础配置 ==========

    /**
     * 爬虫 ID
     */
    protected String spiderId = UUID.randomUUID().toString();

    /**
     * 爬虫名称
     */
    protected String spiderName;

    /**
     * 站点配置
     */
    protected Site site;

    /**
     * 页面处理器
     */
    protected PageProcessor processor;

    /**
     * 下载器
     */
    protected Downloader downloader;

    /**
     * 管道列表
     */
    protected List<Pipeline> pipelines = new ArrayList<>();

    /**
     * 调度器
     */
    protected Scheduler scheduler;

    // ========== 并发配置 ==========

    /**
     * 线程数
     */
    protected int threadCount = 1;

    /**
     * 执行器服务
     */
    protected ExecutorService executorService;

    /**
     * 是否运行中
     */
    protected volatile boolean running = false;

    /**
     * 是否暂停
     */
    protected volatile boolean paused = false;

    // ========== 统计信息 ==========

    /**
     * 总请求数
     */
    protected AtomicLong totalRequests = new AtomicLong(0);

    /**
     * 成功请求数
     */
    protected AtomicLong successRequests = new AtomicLong(0);

    /**
     * 失败请求数
     */
    protected AtomicLong failedRequests = new AtomicLong(0);

    /**
     * 开始时间
     */
    protected long startTime;

    /**
     * 结束时间
     */
    protected long endTime;

    // ========== 构造函数 ==========

    public Spider() {
        this(null);
    }

    public Spider(PageProcessor processor) {
        this.processor = processor;
        this.scheduler = new QueueScheduler();
        this.downloader = new HttpClientDownloader();
        this.site = new Site();
    }

    // ========== 链式调用 API ==========

    /**
     * 设置爬虫名称
     * @param name 爬虫名称
     * @return this
     */
    public Spider name(String name) {
        this.spiderName = name;
        return this;
    }

    /**
     * 设置站点配置
     * @param site 站点配置
     * @return this
     */
    public Spider site(Site site) {
        this.site = site;
        return this;
    }

    /**
     * 添加管道
     * @param pipeline 管道
     * @return this
     */
    public Spider addPipeline(Pipeline pipeline) {
        this.pipelines.add(pipeline);
        return this;
    }

    /**
     * 添加多个管道
     * @param pipelines 管道列表
     * @return this
     */
    public Spider addPipelines(List<Pipeline> pipelines) {
        this.pipelines.addAll(pipelines);
        return this;
    }

    /**
     * 设置下载器
     * @param downloader 下载器
     * @return this
     */
    public Spider downloader(Downloader downloader) {
        this.downloader = downloader;
        return this;
    }

    /**
     * 设置调度器
     * @param scheduler 调度器
     * @return this
     */
    public Spider scheduler(Scheduler scheduler) {
        this.scheduler = scheduler;
        return this;
    }

    /**
     * 设置线程数
     * @param threadCount 线程数
     * @return this
     */
    public Spider thread(int threadCount) {
        this.threadCount = threadCount;
        return this;
    }

    /**
     * 添加初始请求 URL
     * @param urls URL 列表
     * @return this
     */
    public Spider addUrl(String... urls) {
        for (String url : urls) {
            Request request = new Request(url);
            request.setSpiderId(this.spiderId);
            scheduler.push(request);
            totalRequests.incrementAndGet();
        }
        return this;
    }

    /**
     * 添加初始请求
     * @param requests 请求列表
     * @return this
     */
    public Spider addRequest(Request... requests) {
        for (Request request : requests) {
            request.setSpiderId(this.spiderId);
            scheduler.push(request);
            totalRequests.incrementAndGet();
        }
        return this;
    }

    // ========== 爬虫控制 ==========

    /**
     * 启动爬虫
     */
    public void start() {
        if (running) {
            log.warn("Spider [{}] is already running!", spiderName);
            return;
        }

        if (processor == null) {
            throw new IllegalStateException("PageProcessor must be set before starting spider");
        }

        running = true;
        paused = false;
        startTime = System.currentTimeMillis();
        executorService = Executors.newFixedThreadPool(threadCount);

        log.info("Spider [{}] started with {} threads", spiderName, threadCount);

        for (int i = 0; i < threadCount; i++) {
            executorService.submit(this);
        }
    }

    /**
     * 停止爬虫
     */
    public void stop() {
        running = false;
        paused = false;
        endTime = System.currentTimeMillis();

        if (executorService != null) {
            executorService.shutdown();
            log.info("Executor service shutdown, waiting for tasks to complete...");

            // 等待任务完成，最多等待 30 秒
            try {
                if (!executorService.awaitTermination(30, TimeUnit.SECONDS)) {
                    log.warn("Executor service did not terminate in time, forcing shutdown...");
                    executorService.shutdownNow();

                    // 再等待 5 秒
                    if (!executorService.awaitTermination(5, TimeUnit.SECONDS)) {
                        log.error("Executor service still running after shutdownNow");
                    }
                }
            } catch (InterruptedException e) {
                log.error("Interrupted while waiting for executor service to terminate", e);
                executorService.shutdownNow();
                Thread.currentThread().interrupt();
            }
        }

        log.info("Spider [{}] stopped. Total: {}, Success: {}, Failed: {}, Duration: {}ms",
                spiderName, totalRequests.get(), successRequests.get(), failedRequests.get(),
                (endTime - startTime));
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
        if (paused) {
            paused = false;
            log.info("Spider [{}] resumed", spiderName);
        }
    }

    /**
     * 等待爬虫完成
     * @throws InterruptedException 中断异常
     */
    public void await() throws InterruptedException {
        while (running && !executorService.isTerminated()) {
            Thread.sleep(1000);
        }
    }

    /**
     * 等待爬虫完成 (带超时)
     * @param timeout 超时时间 (毫秒)
     * @throws InterruptedException 中断异常
     */
    public void await(long timeout) throws InterruptedException {
        long start = System.currentTimeMillis();
        while (running && !executorService.isTerminated()) {
            if (System.currentTimeMillis() - start > timeout) {
                log.warn("Spider [{}] await timeout", spiderName);
                break;
            }
            Thread.sleep(1000);
        }
    }

    // ========== 核心运行逻辑 ==========

    @Override
    public void run() {
        while (running) {
            scheduler.reapExpiredLeases(System.currentTimeMillis(), site.getRetryTimes());
            // 检查是否暂停
            if (paused) {
                try {
                    Thread.sleep(1000);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    break;
                }
                continue;
            }

            // 从调度器获取请求
            Request request = scheduler.pollNow();
            if (request == null) {
                try {
                    Thread.sleep(1000);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    break;
                }
                continue;
            }

            // 处理请求
            processRequest(request);
        }
    }

    /**
     * 处理请求
     * @param request 请求
     */
    protected void processRequest(Request request) {
        AtomicBoolean stopHeartbeat = new AtomicBoolean(false);
        Thread heartbeatThread = startLeaseHeartbeat(request, stopHeartbeat);
        try {
            log.debug("Processing request: {}", request.getUrl());

            // 下载页面
            Page page = downloader.download(request, site);

            if (page == null || page.isSkip()) {
                scheduler.ack(request, true);
                return;
            }

            // 处理页面
            processor.process(page);

            // 执行管道
            for (Pipeline pipeline : pipelines) {
                try {
                    pipeline.process(page.getResultItems(), this);
                } catch (Exception e) {
                    log.error("Error in pipeline: {}", pipeline.getClass().getName(), e);
                }
            }

            // 添加新请求
            for (Request newRequest : page.getTargetRequests()) {
                newRequest.setSpiderId(this.spiderId);
                scheduler.push(newRequest);
                totalRequests.incrementAndGet();
            }

            successRequests.incrementAndGet();
            scheduler.ack(request, true);

        } catch (Exception e) {
            log.error("Error processing request: {}", request.getUrl(), e);
            failedRequests.incrementAndGet();
            scheduler.ack(request, false);

            // 重试逻辑
            if (request.getRetryCount() < site.getRetryTimes()) {
                request.setRetryCount(request.getRetryCount() + 1);
                try {
                    Thread.sleep(site.getRetrySleep());
                } catch (InterruptedException ie) {
                    Thread.currentThread().interrupt();
                }
                scheduler.push(request);
                log.info("Retry request: {} (retry {})", request.getUrl(), request.getRetryCount());
            }
        } finally {
            stopHeartbeat.set(true);
            if (heartbeatThread != null) {
                heartbeatThread.interrupt();
                try {
                    heartbeatThread.join(500);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
            }
        }
    }

    private Thread startLeaseHeartbeat(Request request, AtomicBoolean stopHeartbeat) {
        Thread thread = new Thread(() -> {
            while (!stopHeartbeat.get()) {
                try {
                    Thread.sleep(10_000L);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    break;
                }
                if (stopHeartbeat.get()) {
                    break;
                }
                scheduler.heartbeat(request, 30_000L);
            }
        }, "scheduler-heartbeat-" + spiderId);
        thread.setDaemon(true);
        thread.start();
        return thread;
    }

    // ========== 统计信息 ==========

    /**
     * 获取爬虫状态
     * @return 爬虫状态
     */
    public SpiderStatus getStatus() {
        return new SpiderStatus(
            spiderId,
            spiderName,
            running,
            paused,
            totalRequests.get(),
            successRequests.get(),
            failedRequests.get(),
            startTime,
            endTime
        );
    }

    /**
     * 打印统计信息
     */
    public void printStats() {
        long duration = (endTime == 0) ? (System.currentTimeMillis() - startTime) : (endTime - startTime);
        long qps = duration > 0 ? (successRequests.get() * 1000 / duration) : 0;

        log.info("========== Spider Statistics ==========");
        log.info("Spider ID:   {}", spiderId);
        log.info("Spider Name: {}", spiderName);
        log.info("Status:      {} {}", running ? "RUNNING" : "STOPPED", paused ? "(PAUSED)" : "");
        log.info("Total:       {}", totalRequests.get());
        log.info("Success:     {}", successRequests.get());
        log.info("Failed:      {}", failedRequests.get());
        log.info("Duration:    {}ms", duration);
        log.info("QPS:         {}", qps);
        log.info("======================================");
    }

    // ========== 便捷方法 ==========

    /**
     * 创建 Spider 实例
     * @param processor 页面处理器
     * @return Spider 实例
     */
    public static Spider create(PageProcessor processor) {
        return new Spider(processor);
    }

    /**
     * 创建 Spider 实例并设置名称
     * @param name 爬虫名称
     * @param processor 页面处理器
     * @return Spider 实例
     */
    public static Spider of(String name, PageProcessor processor) {
        return new Spider(processor).name(name);
    }
}
