package com.javaspider.downloader;

import com.javaspider.antibot.UrlValidator;
import com.javaspider.core.Request;
import com.javaspider.core.Site;
import com.javaspider.core.Page;
import com.javaspider.core.RobotsChecker;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpHeaders;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.time.Instant;
import java.time.ZonedDateTime;
import java.time.format.DateTimeFormatter;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import javax.net.ssl.SSLContext;
import javax.net.ssl.TrustManager;
import javax.net.ssl.X509TrustManager;
import java.security.cert.X509Certificate;
import java.security.KeyManagementException;
import java.security.NoSuchAlgorithmException;

/**
 * HTTP 客户端下载器 (使用 Java 11+ HttpClient)
 */
public class HttpClientDownloader implements Downloader {

    private static final Set<Integer> RETRYABLE_STATUSES = Set.of(429, 500, 502, 503, 504);
    private final boolean trustAllCerts;
    private final HttpClient httpClient;
    private final RobotsChecker robotsChecker;

    public HttpClientDownloader() {
        this(false);
    }

    /**
     * 构造函数
     * @param trustAllCerts 是否信任所有证书（仅用于测试环境，生产环境应为 false）
     */
    public HttpClientDownloader(boolean trustAllCerts) {
        this.trustAllCerts = trustAllCerts;
        this.httpClient = createHttpClient();
        this.robotsChecker = new RobotsChecker();
    }

    /**
     * 创建 HttpClient（根据配置选择 SSL 策略）
     */
    private HttpClient createHttpClient() {
        try {
            SSLContext sslContext = trustAllCerts ? createTrustAllSSLContext() : createDefaultSSLContext();

            return HttpClient.newBuilder()
                    .connectTimeout(Duration.ofSeconds(10))
                    .sslContext(sslContext)
                    .build();
        } catch (Exception e) {
            System.err.println("创建 HttpClient 失败，使用默认配置：" + e.getMessage());
            return HttpClient.newBuilder()
                    .connectTimeout(Duration.ofSeconds(10))
                    .build();
        }
    }

    /**
     * 创建使用系统默认证书库的 SSLContext（生产环境推荐）
     */
    private static SSLContext createDefaultSSLContext() throws NoSuchAlgorithmException, KeyManagementException {
        SSLContext sslContext = SSLContext.getInstance("TLS");
        sslContext.init(null, null, new java.security.SecureRandom());
        return sslContext;
    }

    @Override
    public Page download(Request request, Site site) {
        long startedAt = System.currentTimeMillis();
        Page page = new Page();
        page.setRequest(request);
        page.setUrl(request.getUrl());

        String method = request != null && request.getMethod() != null && !request.getMethod().isBlank()
                ? request.getMethod().toUpperCase(Locale.ROOT)
                : "GET";
        String userAgent = resolveUserAgent(request, site);

        try {
            if (site != null && site.isRespectRobotsTxt()) {
                robotsChecker.setRespectRobots(true);
                if (!robotsChecker.isAllowed(request.getUrl(), userAgent)) {
                    page.setStatusCode(403);
                    page.setRawText("");
                    page.setError("robots.txt forbids " + request.getUrl());
                    page.setSkip(true);
                    page.setDownloadDuration(System.currentTimeMillis() - startedAt);
                    return page;
                }
                double crawlDelay = robotsChecker.getCrawlDelay(request.getUrl());
                if (crawlDelay > 0) {
                    Thread.sleep((long) (crawlDelay * 1000));
                }
            } else {
                robotsChecker.setRespectRobots(false);
            }

            int maxAttempts = Math.max(1, (site != null ? site.getRetryTimes() : 0) + 1);
            int retryBaseMs = Math.max(250, site != null ? site.getRetrySleep() : 1000);
            Exception lastError = null;

            for (int attempt = 0; attempt < maxAttempts; attempt++) {
                try {
                    HttpRequest httpRequest = buildRequest(request, site, method, userAgent);
                    HttpResponse<String> response = httpClient.send(httpRequest, HttpResponse.BodyHandlers.ofString());
                    page.setStatusCode(response.statusCode());
                    page.setRawText(response.body());
                    page.setHeaders(flattenHeaders(response.headers()));
                    page.setSkip(false);
                    page.setDownloadDuration(System.currentTimeMillis() - startedAt);

                    if (RETRYABLE_STATUSES.contains(response.statusCode()) && attempt < maxAttempts - 1) {
                        Thread.sleep(computeRetryDelayMs(retryBaseMs, attempt, response.headers()));
                        continue;
                    }
                    return page;
                } catch (Exception e) {
                    lastError = e;
                    if (attempt < maxAttempts - 1) {
                        Thread.sleep(computeRetryDelayMs(retryBaseMs, attempt, null));
                        continue;
                    }
                }
            }

            page.setSkip(true);
            page.setError(lastError != null ? lastError.getMessage() : "request failed");
            page.setDownloadDuration(System.currentTimeMillis() - startedAt);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            page.setSkip(true);
            page.setError("request interrupted");
            page.setDownloadDuration(System.currentTimeMillis() - startedAt);
        } catch (Exception e) {
            page.setSkip(true);
            page.setError(e.getMessage());
            page.setDownloadDuration(System.currentTimeMillis() - startedAt);
        }

        return page;
    }

    private HttpRequest buildRequest(Request request, Site site, String method, String userAgent) {
        String safeUrl = UrlValidator.validateAndNormalize(
            request.getUrl(),
            Boolean.TRUE.equals(request.getMeta().get("allow_private_network"))
        );
        HttpRequest.Builder requestBuilder = HttpRequest.newBuilder()
                .uri(URI.create(safeUrl))
                .timeout(Duration.ofMillis(site != null ? site.getTimeout() : 30_000));

        Map<String, String> headers = new HashMap<>();
        if (site != null && site.getUserAgent() != null && !site.getUserAgent().isBlank()) {
            headers.put("User-Agent", site.getUserAgent());
        }
        headers.put("User-Agent", userAgent);
        if (request.getHeaders() != null) {
            headers.putAll(request.getHeaders());
        }
        for (Map.Entry<String, String> entry : headers.entrySet()) {
            if (entry.getValue() != null) {
                requestBuilder.header(entry.getKey(), entry.getValue());
            }
        }

        byte[] body = request.getBody();
        if (body != null && body.length > 0 && !"GET".equals(method)) {
            requestBuilder.method(method, HttpRequest.BodyPublishers.ofByteArray(body));
        } else if ("GET".equals(method)) {
            requestBuilder.GET();
        } else {
            requestBuilder.method(method, HttpRequest.BodyPublishers.noBody());
        }
        return requestBuilder.build();
    }

    private String resolveUserAgent(Request request, Site site) {
        if (request != null && request.getHeaders() != null) {
            String candidate = request.getHeaders().get("User-Agent");
            if (candidate != null && !candidate.isBlank()) {
                return candidate;
            }
        }
        if (site != null && site.getUserAgent() != null && !site.getUserAgent().isBlank()) {
            return site.getUserAgent();
        }
        return "javaspider/2.1";
    }

    private long computeRetryDelayMs(long baseDelayMs, int attempt, HttpHeaders headers) {
        long backoff = baseDelayMs * (1L << Math.min(attempt, 6));
        long capped = Math.min(backoff, 10_000L);
        long retryAfter = parseRetryAfter(headers);
        return Math.max(capped, retryAfter);
    }

    private long parseRetryAfter(HttpHeaders headers) {
        if (headers == null) {
            return 0L;
        }
        List<String> values = headers.allValues("Retry-After");
        if (values == null || values.isEmpty()) {
            return 0L;
        }
        String raw = values.get(0);
        if (raw == null || raw.isBlank()) {
            return 0L;
        }
        try {
            long seconds = Long.parseLong(raw.trim());
            return Math.max(0L, seconds * 1000L);
        } catch (NumberFormatException ignored) {
            // continue with HTTP-date parse
        }
        try {
            ZonedDateTime target = ZonedDateTime.parse(raw.trim(), DateTimeFormatter.RFC_1123_DATE_TIME);
            long millis = Duration.between(Instant.now(), target.toInstant()).toMillis();
            return Math.max(0L, millis);
        } catch (Exception ignored) {
            return 0L;
        }
    }

    private Map<String, String> flattenHeaders(HttpHeaders headers) {
        Map<String, String> flattened = new HashMap<>();
        if (headers == null || headers.map() == null) {
            return flattened;
        }
        for (Map.Entry<String, List<String>> entry : headers.map().entrySet()) {
            flattened.put(entry.getKey(), String.join(", ", entry.getValue()));
        }
        return flattened;
    }

    /**
     * 创建信任所有证书的 SSLContext（仅用于测试环境）
     * 警告：这会带来中间人攻击风险，生产环境应使用 createDefaultSSLContext
     */
    private static SSLContext createTrustAllSSLContext() throws NoSuchAlgorithmException, KeyManagementException {
        TrustManager[] trustAllCerts = new TrustManager[] {
            new X509TrustManager() {
                public X509Certificate[] getAcceptedIssuers() {
                    return new X509Certificate[0];
                }
                public void checkClientTrusted(X509Certificate[] certs, String authType) {
                    // 不执行任何检查，信任所有客户端证书
                }
                public void checkServerTrusted(X509Certificate[] certs, String authType) {
                    // 不执行任何检查，信任所有服务器证书
                }
            }
        };

        SSLContext sslContext = SSLContext.getInstance("TLS");
        sslContext.init(null, trustAllCerts, new java.security.SecureRandom());
        return sslContext;
    }
}
