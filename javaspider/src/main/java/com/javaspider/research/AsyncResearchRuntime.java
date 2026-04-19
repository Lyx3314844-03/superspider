package com.javaspider.research;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicInteger;

public class AsyncResearchRuntime implements AutoCloseable {
    private final AsyncResearchConfig config;
    private final ExecutorService executor;
    private final ResearchRuntime runtime;
    private final AtomicInteger tasksStarted = new AtomicInteger();
    private final AtomicInteger tasksCompleted = new AtomicInteger();
    private final AtomicInteger tasksFailed = new AtomicInteger();
    private final AtomicInteger currentInflight = new AtomicInteger();
    private final AtomicInteger peakInflight = new AtomicInteger();
    private volatile double totalDurationMs = 0.0;
    private volatile double maxDurationMs = 0.0;
    private volatile String lastError = "";

    public AsyncResearchRuntime() {
        this(new AsyncResearchConfig());
    }

    public AsyncResearchRuntime(AsyncResearchConfig config) {
        this.config = config == null ? new AsyncResearchConfig() : config;
        this.executor = Executors.newFixedThreadPool(Math.max(1, this.config.maxConcurrent()));
        this.runtime = new ResearchRuntime();
    }

    public AsyncResearchConfig getConfig() {
        return config;
    }

    public CompletableFuture<AsyncResearchResult> runSingle(ResearchJob job, String content) {
        return CompletableFuture.supplyAsync(() -> {
            int inflight = currentInflight.incrementAndGet();
            tasksStarted.incrementAndGet();
            peakInflight.accumulateAndGet(inflight, Math::max);
            long started = System.nanoTime();
            try {
                Object delay = job.getPolicy().get("simulate_delay_ms");
                if (delay instanceof Number number && number.longValue() > 0) {
                    Thread.sleep(number.longValue());
                }
                Map<String, Object> result = runtime.run(job, content);
                SiteProfile profile = (SiteProfile) result.get("profile");
                @SuppressWarnings("unchecked")
                Map<String, Object> extract = (Map<String, Object>) result.get("extract");
                @SuppressWarnings("unchecked")
                Map<String, Object> dataset = (Map<String, Object>) result.getOrDefault("dataset", Map.of());
                double durationMs = (System.nanoTime() - started) / 1_000_000.0;
                recordCompletion(durationMs, "");
                return new AsyncResearchResult(firstSeed(job), profile, extract, durationMs, dataset, "");
            } catch (RuntimeException e) {
                double durationMs = (System.nanoTime() - started) / 1_000_000.0;
                recordCompletion(durationMs, e.getMessage());
                return new AsyncResearchResult(firstSeed(job), null, Map.of(), durationMs, Map.of(), e.getMessage());
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                double durationMs = (System.nanoTime() - started) / 1_000_000.0;
                recordCompletion(durationMs, "interrupted");
                return new AsyncResearchResult(firstSeed(job), null, Map.of(), durationMs, Map.of(), "interrupted");
            } finally {
                currentInflight.decrementAndGet();
            }
        }, executor);
    }

    public List<AsyncResearchResult> runMultiple(List<ResearchJob> jobs, List<String> contents) {
        List<CompletableFuture<AsyncResearchResult>> futures = new ArrayList<>();
        for (int index = 0; index < jobs.size(); index++) {
            String content = contents != null && index < contents.size() ? contents.get(index) : null;
            futures.add(runSingle(jobs.get(index), content));
        }
        return futures.stream().map(CompletableFuture::join).toList();
    }

    public Iterable<AsyncResearchResult> runStream(List<ResearchJob> jobs, List<String> contents) {
        BlockingQueue<AsyncResearchResult> queue = new LinkedBlockingQueue<>();
        List<CompletableFuture<Void>> futures = new ArrayList<>();
        for (int index = 0; index < jobs.size(); index++) {
            String content = contents != null && index < contents.size() ? contents.get(index) : null;
            futures.add(runSingle(jobs.get(index), content).thenAccept(queue::add));
        }
        futures.forEach(CompletableFuture::join);
        return List.copyOf(queue);
    }

    public void resetMetrics() {
        tasksStarted.set(0);
        tasksCompleted.set(0);
        tasksFailed.set(0);
        currentInflight.set(0);
        peakInflight.set(0);
        totalDurationMs = 0.0;
        maxDurationMs = 0.0;
        lastError = "";
    }

    public Map<String, Object> runSoak(List<ResearchJob> jobs, List<String> contents, int rounds) {
        int safeRounds = Math.max(1, rounds);
        long started = System.nanoTime();
        resetMetrics();
        List<AsyncResearchResult> allResults = new ArrayList<>();
        for (int round = 0; round < safeRounds; round++) {
            allResults.addAll(runMultiple(jobs, contents));
        }
        long failures = allResults.stream().filter(result -> !result.error().isBlank()).count();
        Map<String, Object> metrics = snapshotMetrics();
        int total = allResults.size();
        int successes = total - (int) failures;
        Map<String, Object> report = new LinkedHashMap<>();
        report.put("jobs", jobs.size());
        report.put("rounds", safeRounds);
        report.put("results", total);
        report.put("successes", successes);
        report.put("failures", (int) failures);
        report.put("success_rate", total == 0 ? 0.0 : successes / (double) total);
        report.put("duration_ms", (System.nanoTime() - started) / 1_000_000.0);
        report.put("peak_inflight", metrics.get("peak_inflight"));
        report.put("max_concurrent", config.maxConcurrent());
        report.put(
            "stable",
            ((Number) metrics.get("current_inflight")).intValue() == 0
                && failures == 0
                && ((Number) metrics.get("tasks_completed")).intValue() == total
        );
        return report;
    }

    public Map<String, Object> snapshotMetrics() {
        int completed = tasksCompleted.get();
        Map<String, Object> metrics = new LinkedHashMap<>();
        metrics.put("max_concurrent", config.maxConcurrent());
        metrics.put("tasks_started", tasksStarted.get());
        metrics.put("tasks_completed", completed);
        metrics.put("tasks_failed", tasksFailed.get());
        metrics.put("current_inflight", currentInflight.get());
        metrics.put("peak_inflight", peakInflight.get());
        metrics.put("average_duration_ms", completed == 0 ? 0.0 : totalDurationMs / completed);
        metrics.put("max_duration_ms", maxDurationMs);
        metrics.put("last_error", lastError);
        return metrics;
    }

    private void recordCompletion(double durationMs, String error) {
        tasksCompleted.incrementAndGet();
        totalDurationMs += durationMs;
        maxDurationMs = Math.max(maxDurationMs, durationMs);
        if (error != null && !error.isBlank()) {
            tasksFailed.incrementAndGet();
            lastError = error;
        }
    }

    private String firstSeed(ResearchJob job) {
        return job.getSeedUrls().isEmpty() ? "" : job.getSeedUrls().get(0);
    }

    @Override
    public void close() {
        executor.shutdownNow();
    }
}
