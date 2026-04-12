package com.javaspider.async;

import java.util.*;
import java.util.concurrent.*;
import java.util.function.*;

/**
 * Async batch processor for efficient parallel processing
 */
public class BatchProcessor<T, R> {
    
    private final int batchSize;
    private final int maxConcurrency;
    private final ThreadPoolExecutor executor;
    private final BiFunction<List<T>, Integer, List<R>> processor;
    private final Consumer<R> resultHandler;
    private final Consumer<Exception> errorHandler;
    
    public static class Builder<T, R> {
        private int batchSize = 100;
        private int maxConcurrency = 10;
        private BiFunction<List<T>, Integer, List<R>> processor;
        private Consumer<R> resultHandler;
        private Consumer<Exception> errorHandler;
        
        public Builder<T, R> batchSize(int size) { this.batchSize = size; return this; }
        public Builder<T, R> maxConcurrency(int concurrency) { this.maxConcurrency = concurrency; return this; }
        public Builder<T, R> processor(BiFunction<List<T>, Integer, List<R>> processor) { this.processor = processor; return this; }
        public Builder<T, R> resultHandler(Consumer<R> handler) { this.resultHandler = handler; return this; }
        public Builder<T, R> errorHandler(Consumer<Exception> handler) { this.errorHandler = handler; return this; }
        
        public BatchProcessor<T, R> build() {
            return new BatchProcessor<>(this);
        }
    }
    
    private BatchProcessor(Builder<T, R> builder) {
        this.batchSize = builder.batchSize;
        this.maxConcurrency = builder.maxConcurrency;
        this.processor = builder.processor;
        this.resultHandler = builder.resultHandler;
        this.errorHandler = builder.errorHandler;
        this.executor = (ThreadPoolExecutor) Executors.newFixedThreadPool(maxConcurrency);
    }
    
    public CompletableFuture<Void> processAsync(Collection<T> items) {
        List<T> itemList = new ArrayList<>(items);
        List<CompletableFuture<Void>> futures = new ArrayList<>();
        List<List<T>> batches = partition(itemList, batchSize);
        
        for (int i = 0; i < batches.size(); i++) {
            final int batchIndex = i;
            final List<T> batch = batches.get(i);
            
            CompletableFuture<Void> future = CompletableFuture.supplyAsync(() -> {
                try {
                    List<R> results = processor.apply(batch, batchIndex);
                    if (resultHandler != null) results.forEach(resultHandler);
                    return null;
                } catch (Exception e) {
                    if (errorHandler != null) errorHandler.accept(e);
                    throw new CompletionException(e);
                }
            }, executor);
            futures.add(future);
        }
        return CompletableFuture.allOf(futures.toArray(new CompletableFuture[0]));
    }
    
    private <E> List<List<E>> partition(List<E> list, int size) {
        List<List<E>> partitions = new ArrayList<>();
        for (int i = 0; i < list.size(); i += size) {
            partitions.add(list.subList(i, Math.min(i + size, list.size())));
        }
        return partitions;
    }
    
    public void shutdown() { executor.shutdown(); }
    
    public Map<String, Object> getStats() {
        return Map.of(
            "batchSize", batchSize,
            "maxConcurrency", maxConcurrency,
            "activeCount", executor.getActiveCount(),
            "completedCount", executor.getCompletedTaskCount()
        );
    }
}
