package com.javaspider.scheduler;

import com.google.gson.Gson;
import com.javaspider.core.CrawlTask;
import org.junit.jupiter.api.Test;

import java.util.LinkedHashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class RedisSchedulerLeaseSemanticsTest {
    private static final Gson GSON = new Gson();

    @Test
    void expiredLeaseMovesTaskToDeadLetterWhenRetryBudgetExhausted() {
        Map<String, String> processing = new LinkedHashMap<>();
        CrawlTask task = CrawlTask.builder()
            .url("https://example.com")
            .priority(10)
            .retry_count(0)
            .build();
        processing.put(task.getUrl(), GSON.toJson(Map.of(
            "worker_id", "worker-1",
            "expires_at", 1000L,
            "task", task
        )));

        LeaseOutcome outcome = LeaseOutcome.reap(processing, 2000L, 0);
        assertEquals(1, outcome.reaped());
        assertEquals(1, outcome.deadLetters().size());
        assertTrue(outcome.requeued().isEmpty());
        assertFalse(processing.containsKey(task.getUrl()));
    }

    @Test
    void expiredLeaseRequeuesTaskWhileRetryBudgetRemains() {
        Map<String, String> processing = new LinkedHashMap<>();
        CrawlTask task = CrawlTask.builder()
            .url("https://example.com/docs")
            .priority(5)
            .retry_count(0)
            .build();
        processing.put(task.getUrl(), GSON.toJson(Map.of(
            "worker_id", "worker-1",
            "expires_at", 1000L,
            "task", task
        )));

        LeaseOutcome outcome = LeaseOutcome.reap(processing, 2000L, 2);
        assertEquals(1, outcome.reaped());
        assertEquals(1, outcome.requeued().size());
        assertTrue(outcome.deadLetters().isEmpty());
        assertEquals(1, outcome.requeued().get(0).getRetry_count());
        assertFalse(processing.containsKey(task.getUrl()));
    }

    record LeaseOutcome(int reaped, java.util.List<CrawlTask> requeued, java.util.List<CrawlTask> deadLetters) {
        static LeaseOutcome reap(Map<String, String> processing, long nowMillis, int maxRetries) {
            java.util.List<CrawlTask> requeued = new java.util.ArrayList<>();
            java.util.List<CrawlTask> deadLetters = new java.util.ArrayList<>();
            int reaped = 0;
            for (Map.Entry<String, String> entry : new java.util.ArrayList<>(processing.entrySet())) {
                @SuppressWarnings("unchecked")
                Map<String, Object> lease = GSON.fromJson(entry.getValue(), Map.class);
                Object expires = lease.get("expires_at");
                long expiresAt = expires instanceof Number ? ((Number) expires).longValue() : 0L;
                if (expiresAt > nowMillis) {
                    continue;
                }
                reaped++;
                CrawlTask task = GSON.fromJson(GSON.toJson(lease.get("task")), CrawlTask.class);
                task.setRetry_count(task.getRetry_count() + 1);
                if (task.getRetry_count() > maxRetries) {
                    deadLetters.add(task);
                } else {
                    requeued.add(task);
                }
                processing.remove(entry.getKey());
            }
            return new LeaseOutcome(reaped, requeued, deadLetters);
        }
    }
}
