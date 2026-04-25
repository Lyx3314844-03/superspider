package com.javaspider.downloader;

import com.javaspider.core.Page;
import com.javaspider.core.Request;
import com.javaspider.core.Site;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.Test;

import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

class HttpClientDownloaderAccessFrictionTest {

    @Test
    void downloaderAttachesAccessFrictionReport() throws Exception {
        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/", exchange -> {
            byte[] body = "checking your browser".getBytes();
            exchange.getResponseHeaders().add("Retry-After", "45");
            exchange.getResponseHeaders().add("CF-Ray", "demo");
            exchange.sendResponseHeaders(429, body.length);
            try (OutputStream output = exchange.getResponseBody()) {
                output.write(body);
            }
        });
        server.start();
        try {
            String url = "http://127.0.0.1:" + server.getAddress().getPort() + "/";
            Site site = new Site();
            site.setRetryTimes(0);
            site.setRespectRobotsTxt(false);
            Request request = new Request(url);
            request.meta("allow_private_network", true);

            Page page = new HttpClientDownloader().download(request, site);

            @SuppressWarnings("unchecked")
            Map<String, Object> report = (Map<String, Object>) page.getField("access_friction");
            assertNotNull(report);
            assertEquals("high", report.get("level"));
            assertEquals(true, report.get("blocked"));
            assertEquals(45, report.get("retry_after_seconds"));
            assertTrue((Boolean) report.get("should_upgrade_to_browser"));
        } finally {
            server.stop(0);
        }
    }

    @Test
    void downloaderDoesNotRetryHumanAccessChallenge() throws Exception {
        AtomicInteger hits = new AtomicInteger();
        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/", exchange -> {
            hits.incrementAndGet();
            byte[] body = "hcaptcha security check".getBytes();
            exchange.getResponseHeaders().add("Retry-After", "0");
            exchange.sendResponseHeaders(429, body.length);
            try (OutputStream output = exchange.getResponseBody()) {
                output.write(body);
            }
        });
        server.start();
        try {
            String url = "http://127.0.0.1:" + server.getAddress().getPort() + "/";
            Site site = new Site();
            site.setRetryTimes(3);
            site.setRespectRobotsTxt(false);
            Request request = new Request(url);
            request.meta("allow_private_network", true);

            Page page = new HttpClientDownloader().download(request, site);

            assertEquals(429, page.getStatusCode());
            assertEquals(1, hits.get());
        } finally {
            server.stop(0);
        }
    }
}
