package com.javaspider.scheduler;

import com.javaspider.core.Request;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Assumptions;
import org.junit.jupiter.api.Test;
import redis.clients.jedis.Jedis;

import java.util.concurrent.TimeUnit;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

class RedisSchedulerIntegrationTest {
    private static final String REDIS_HOST = "127.0.0.1";
    private static final int REDIS_PORT = 6379;

    @AfterEach
    void cleanup() {
        if (!redisAvailable()) {
            return;
        }
        try (Jedis jedis = new Jedis(REDIS_HOST, REDIS_PORT)) {
            jedis.del("spider:shared:queue", "spider:shared:pending", "spider:shared:processing", "spider:shared:dead", "spider:shared:visited", "spider:shared:stats");
        }
    }

    @Test
    void redisSchedulerLeasesAndDeadLettersAgainstRealRedis() throws Exception {
        Assumptions.assumeTrue(redisAvailable(), "local redis is not available");

        RedisScheduler scheduler = new RedisScheduler(REDIS_HOST, REDIS_PORT, "integration");
        Request request = new Request("https://example.com/integration");
        request.setPriority(10);
        scheduler.push(request);

        Request leased = scheduler.leaseTask("worker-1", 5);
        assertNotNull(leased);
        assertTrue(scheduler.heartbeatTask("https://example.com/integration", 50));

        Thread.sleep(10);
        int reaped = scheduler.reapExpiredLeases(System.currentTimeMillis() + 10, 0);
        assertEquals(1, reaped);

        try (Jedis jedis = new Jedis(REDIS_HOST, REDIS_PORT)) {
            assertEquals(1, jedis.llen("spider:shared:dead"));
        }
        scheduler.close();
    }

    private boolean redisAvailable() {
        try (Jedis jedis = new Jedis(REDIS_HOST, REDIS_PORT)) {
            return "PONG".equalsIgnoreCase(jedis.ping());
        } catch (Exception ignored) {
            return false;
        }
    }
}
