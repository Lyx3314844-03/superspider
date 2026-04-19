package com.javaspider.async;

import com.javaspider.core.SpiderEnhanced;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.concurrent.TimeUnit;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

class AsyncSpiderRuntimeTest {

    @Test
    void submitReturnsFutureResult() throws Exception {
        AsyncSpiderRuntime runtime = new AsyncSpiderRuntime();
        try {
            String result = runtime.submit(() -> "async-ok").get(5, TimeUnit.SECONDS);
            assertEquals("async-ok", result);
        } finally {
            runtime.shutdown();
        }
    }

    @Test
    void processInBatchesCollectsResults() throws Exception {
        AsyncSpiderRuntime runtime = new AsyncSpiderRuntime();
        try {
            List<Integer> results = runtime
                .processInBatches(
                    List.of(1, 2, 3, 4),
                    2,
                    2,
                    (batch, index) -> batch.stream().map(value -> value * 10 + index).toList()
                )
                .get(5, TimeUnit.SECONDS);
            assertEquals(4, results.size());
            assertTrue(results.contains(10));
        } finally {
            runtime.shutdown();
        }
    }

    @Test
    void runSpiderAsyncDelegatesToSpiderEnhanced() {
        AsyncSpiderRuntime runtime = new AsyncSpiderRuntime();
        SpiderEnhanced spider = SpiderEnhanced.builder().name("async-runtime").threads(1).build();
        try {
            var future = runtime.runSpiderAsync(spider);
            assertNotNull(future);
            future.cancel(true);
        } finally {
            spider.stop();
            runtime.shutdown();
        }
    }
}
