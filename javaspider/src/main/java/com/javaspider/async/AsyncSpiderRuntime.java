package com.javaspider.async;

import com.javaspider.core.SpiderEnhanced;
import com.javaspider.performance.VirtualThreadExecutor;

import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.function.BiFunction;
import java.util.function.Supplier;

public class AsyncSpiderRuntime {
    private final VirtualThreadExecutor executor;

    public AsyncSpiderRuntime() {
        this.executor = VirtualThreadExecutor.createSpiderExecutor();
    }

    public <T> CompletableFuture<T> submit(Supplier<T> task) {
        return executor.supplyAsync(task);
    }

    public CompletableFuture<Void> runSpiderAsync(SpiderEnhanced spider) {
        return spider.startAsync();
    }

    public <T, R> CompletableFuture<List<R>> processInBatches(
        Collection<T> items,
        int batchSize,
        int maxConcurrency,
        BiFunction<List<T>, Integer, List<R>> processor
    ) {
        List<R> collected = Collections.synchronizedList(new ArrayList<>());
        BatchProcessor<T, R> batchProcessor = new BatchProcessor.Builder<T, R>()
            .batchSize(batchSize)
            .maxConcurrency(maxConcurrency)
            .processor(processor)
            .resultHandler(collected::add)
            .build();

        return batchProcessor
            .processAsync(items)
            .thenApply(ignored -> List.copyOf(collected))
            .whenComplete((ignored, throwable) -> batchProcessor.shutdown());
    }

    public void shutdown() {
        executor.shutdown();
    }
}
