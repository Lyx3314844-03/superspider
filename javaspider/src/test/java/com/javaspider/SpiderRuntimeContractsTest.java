package com.javaspider;

import com.javaspider.contracts.AutoscaledFrontier;
import com.javaspider.contracts.RequestFingerprint;
import com.javaspider.contracts.RuntimeArtifactStore;
import com.javaspider.contracts.RuntimeObservability;
import com.javaspider.core.IncrementalCrawler;
import com.javaspider.core.Page;
import com.javaspider.core.Request;
import com.javaspider.core.Site;
import com.javaspider.core.Spider;
import com.javaspider.processor.PageProcessor;
import org.junit.jupiter.api.Test;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;

import static org.junit.jupiter.api.Assertions.*;

class SpiderRuntimeContractsTest {
    @Test
    void fingerprintIsStableForSameRequest() {
        Request first = new Request("https://example.com");
        first.header("Accept", "text/html");
        first.getMeta().put("page", 1);
        Request second = new Request("https://example.com");
        second.header("Accept", "text/html");
        second.getMeta().put("page", 1);

        assertEquals(
            RequestFingerprint.fromRequest(first).getValue(),
            RequestFingerprint.fromRequest(second).getValue()
        );
    }

    @Test
    void frontierRespectsBackpressureAndPersists() {
        Path tempDir;
        try {
            tempDir = Files.createTempDirectory("javaspider-frontier");
        } catch (Exception exception) {
            throw new RuntimeException(exception);
        }

        AutoscaledFrontier.FrontierConfig config = new AutoscaledFrontier.FrontierConfig();
        config.checkpointDir = tempDir.resolve("checkpoints").toString();
        config.checkpointId = "demo-frontier";
        config.maxInflightPerDomain = 1;
        AutoscaledFrontier frontier = new AutoscaledFrontier(config);

        Request first = new Request("https://example.com/a");
        first.setPriority(10);
        Request second = new Request("https://example.com/b");
        second.setPriority(5);
        Request other = new Request("https://other.example.com/c");
        other.setPriority(1);

        assertTrue(frontier.push(first));
        assertTrue(frontier.push(second));
        assertTrue(frontier.push(other));

        assertEquals("https://example.com/a", frontier.lease().getUrl());
        assertEquals("https://other.example.com/c", frontier.lease().getUrl());

        frontier.persist();

        AutoscaledFrontier restored = new AutoscaledFrontier(config);
        assertTrue(restored.load());
        assertEquals(1, ((java.util.List<?>) restored.snapshot().get("pending")).size());
    }

    @Test
    void incrementalCrawlerPersistsDeltaState() {
        Path tempDir;
        try {
            tempDir = Files.createTempDirectory("javaspider-incremental");
        } catch (Exception exception) {
            throw new RuntimeException(exception);
        }
        Path store = tempDir.resolve("incremental.json");
        IncrementalCrawler crawler = new IncrementalCrawler();
        assertTrue(crawler.updateCache(
            "https://example.com/a",
            "etag-1",
            "Sat, 11 Apr 2026 00:00:00 GMT",
            "alpha".getBytes(),
            200
        ));
        String token = crawler.deltaToken("https://example.com/a");
        assertNotNull(token);
        crawler.save(store.toString());

        IncrementalCrawler restored = new IncrementalCrawler();
        restored.load(store.toString());
        assertEquals(token, restored.deltaToken("https://example.com/a"));
    }

    @Test
    void observabilityAndArtifactsCaptureEvidence() throws Exception {
        RuntimeArtifactStore.FileArtifactStore store = new RuntimeArtifactStore.FileArtifactStore(
            Files.createTempDirectory("javaspider-artifacts").toString()
        );
        RuntimeArtifactStore.ArtifactRecord record = store.putBytes("frontier", "json", "{}".getBytes(), Map.of());
        RuntimeObservability.ObservabilityCollector collector = new RuntimeObservability.ObservabilityCollector();
        String traceId = collector.startTrace("crawl");
        String classification = collector.recordResult(new Request("https://example.com"), 42, 403, new RuntimeException("captcha challenge"), traceId);
        collector.endTrace(traceId, Map.of("artifact", record.path()));

        assertEquals("blocked", classification);
        assertEquals(1, collector.summary().get("traces"));
    }

    @Test
    void spiderDoesNotProcessBlockedAccessFrictionPage() {
        AtomicInteger processed = new AtomicInteger(0);
        TestSpider spider = new TestSpider(new PageProcessor() {
            @Override
            public void process(Page page) {
                processed.incrementAndGet();
            }

            @Override
            public Site getSite() {
                return new Site();
            }
        });
        spider.downloader((request, site) -> {
            Page page = new Page();
            page.setRequest(request);
            page.setUrl(request.getUrl());
            page.setStatusCode(200);
            page.putField("access_friction", Map.of(
                "level", "high",
                "signals", java.util.List.of("captcha"),
                "blocked", true
            ));
            return page;
        });

        spider.process(new Request("https://example.com/challenge"));

        assertEquals(0, processed.get());
        assertEquals(1, spider.getFailedRequests().get());
        assertEquals(0, spider.getSuccessRequests().get());
    }

    private static class TestSpider extends Spider {
        TestSpider(PageProcessor processor) {
            super(processor);
            site(new Site());
        }

        void process(Request request) {
            processRequest(request);
        }
    }
}
