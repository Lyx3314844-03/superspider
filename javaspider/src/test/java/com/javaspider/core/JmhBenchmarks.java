package com.javaspider.core;

import com.javaspider.downloader.HttpClientDownloader;
import com.javaspider.antibot.UrlValidator;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.DisplayName;
import org.openjdk.jmh.annotations.*;
import org.openjdk.jmh.runner.Runner;
import org.openjdk.jmh.runner.RunnerException;
import org.openjdk.jmh.runner.options.Options;
import org.openjdk.jmh.runner.options.OptionsBuilder;

import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicLong;

import static org.junit.jupiter.api.Assertions.*;

/**
 * javaspider 基准测试 (修复版)
 */
@DisplayName("javaspider 基准测试")
public class JmhBenchmarks {

    @Test
    @DisplayName("运行 JMH 基准测试")
    void runBenchmarks() throws RunnerException {
        Options opt = new OptionsBuilder()
            .include(this.getClass().getSimpleName())
            .forks(1)
            .warmupIterations(1)
            .measurementIterations(2)
            .build();

        new Runner(opt).run();
    }

    /**
     * Spider 基准测试
     */
    @State(Scope.Thread)
    @BenchmarkMode(Mode.AverageTime)
    @OutputTimeUnit(TimeUnit.MICROSECONDS)
    public static class SpiderBenchmarks {

        private SpiderEnhanced spider;

        @Setup
        public void setup() {
            spider = new SpiderEnhanced();
            spider.setSpiderName("bench");
            spider.setThreadCount(5);
        }

        @TearDown
        public void tearDown() {
            if (spider != null) {
                spider.stop();
                try {
                    spider.close();
                } catch (Exception e) {}
            }
        }

        @Benchmark
        public void benchmarkSpiderCreation() {
            SpiderEnhanced s = new SpiderEnhanced();
            s.stop();
        }

        @Benchmark
        public void benchmarkAddRequest() {
            Request req = new Request("https://example.com");
            spider.addRequest(req);
        }

        @Benchmark
        public void benchmarkGetStats() {
            spider.getTotalRequests().get();
        }
    }

    /**
     * 下载器基准测试
     */
    @State(Scope.Thread)
    @BenchmarkMode(Mode.AverageTime)
    @OutputTimeUnit(TimeUnit.MICROSECONDS)
    public static class DownloaderBenchmarks {

        private HttpClientDownloader downloader;

        @Setup
        public void setup() {
            downloader = new HttpClientDownloader();
        }

        @Benchmark
        public void benchmarkDownloaderCreation() {
            HttpClientDownloader d = new HttpClientDownloader();
        }
    }

    /**
     * 安全模块基准测试
     */
    @State(Scope.Thread)
    @BenchmarkMode(Mode.AverageTime)
    @OutputTimeUnit(TimeUnit.MICROSECONDS)
    public static class SecurityBenchmarks {

        @Benchmark
        public void benchmarkURLValidation() {
            UrlValidator.isValidUrl("https://example.com");
        }
    }
}
