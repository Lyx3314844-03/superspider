package com.javaspider.scrapy;

import com.javaspider.scrapy.item.Item;

import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.net.URI;
import java.time.Duration;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

public final class CrawlerProcess {
    @FunctionalInterface
    public interface BrowserFetcher {
        Spider.Response fetch(Spider.Request request, Spider spider);
    }

    private final Spider spider;
    private final HttpClient client;
    private final List<Spider.ItemPipeline> pipelines = new ArrayList<>();
    private final List<ScrapyPlugin> plugins = new ArrayList<>();
    private final List<SpiderMiddleware> spiderMiddlewares = new ArrayList<>();
    private final List<DownloaderMiddleware> downloaderMiddlewares = new ArrayList<>();
    private final Map<String, Object> config = new LinkedHashMap<>();
    private BrowserFetcher browserFetcher;

    public CrawlerProcess(Spider spider) {
        this.spider = spider;
        this.client = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(10))
            .build();
    }

    public CrawlerProcess addPipeline(Spider.ItemPipeline pipeline) {
        this.pipelines.add(pipeline);
        return this;
    }

    public CrawlerProcess addPlugin(ScrapyPlugin plugin) {
        this.plugins.add(plugin);
        return this;
    }

    public CrawlerProcess addSpiderMiddleware(SpiderMiddleware middleware) {
        this.spiderMiddlewares.add(middleware);
        return this;
    }

    public CrawlerProcess addDownloaderMiddleware(DownloaderMiddleware middleware) {
        this.downloaderMiddlewares.add(middleware);
        return this;
    }

    public CrawlerProcess withConfig(Map<String, Object> values) {
        this.config.clear();
        if (values != null) {
            this.config.putAll(values);
        }
        return this;
    }

    public CrawlerProcess withBrowserFetcher(BrowserFetcher fetcher) {
        this.browserFetcher = fetcher;
        return this;
    }

    public List<Item> crawl() {
        ArrayDeque<Spider.Request> queue = new ArrayDeque<>(spider.startRequests());
        Set<String> seen = new LinkedHashSet<>();
        List<Item> items = new ArrayList<>();
        List<Spider.ItemPipeline> activePipelines = new ArrayList<>(pipelines);

        for (ScrapyPlugin plugin : plugins) {
            plugin.configure(config);
            plugin.prepareSpider(spider);
            activePipelines.addAll(plugin.providePipelines());
            spiderMiddlewares.addAll(plugin.provideSpiderMiddlewares());
            downloaderMiddlewares.addAll(plugin.provideDownloaderMiddlewares());
            plugin.onSpiderOpened(spider);
        }

        try {
            while (!queue.isEmpty()) {
                Spider.Request request = queue.removeFirst();
                for (DownloaderMiddleware middleware : downloaderMiddlewares) {
                    request = middleware.processRequest(request, spider);
                }
                if (!seen.add(request.getUrl())) {
                    continue;
                }
                Spider.Response wrapped = fetchResponse(request);
                for (DownloaderMiddleware middleware : downloaderMiddlewares) {
                    wrapped = middleware.processResponse(wrapped, spider);
                }

                Spider.Callback callback = request.getCallback() != null ? request.getCallback() : spider::parse;
                List<Object> results = callback.handle(wrapped);
                for (SpiderMiddleware middleware : spiderMiddlewares) {
                    results = middleware.processSpiderOutput(wrapped, results, spider);
                }

                for (Object result : results) {
                    if (result instanceof Spider.Request nextRequest) {
                        if (!seen.contains(nextRequest.getUrl())) {
                            queue.addLast(nextRequest);
                        }
                        continue;
                    }

                    Item item;
                    if (result instanceof Item scrapyItem) {
                        item = scrapyItem;
                    } else if (result instanceof Map<?, ?> map) {
                        @SuppressWarnings("unchecked")
                        Map<String, Object> typed = (Map<String, Object>) map;
                        item = Item.fromMap(typed);
                    } else {
                        continue;
                    }

                    for (Spider.ItemPipeline pipeline : activePipelines) {
                        item = pipeline.processItem(item, spider);
                    }
                    for (ScrapyPlugin plugin : plugins) {
                        item = plugin.processItem(item, spider);
                    }
                    items.add(item);
                }
            }
        } finally {
            for (ScrapyPlugin plugin : plugins) {
                plugin.onSpiderClosed(spider);
            }
        }

        return items;
    }

    private Spider.Response fetchResponse(Spider.Request request) {
        String runner = resolveRunner(request.getMeta(), config);
        if ("browser".equals(runner) && browserFetcher != null) {
            return browserFetcher.fetch(request, spider);
        }
        HttpRequest.Builder builder = HttpRequest.newBuilder()
            .uri(URI.create(request.getUrl()))
            .timeout(Duration.ofSeconds(30));
        for (Map.Entry<String, String> entry : request.getHeaders().entrySet()) {
            builder.header(entry.getKey(), entry.getValue());
        }
        if ("GET".equalsIgnoreCase(request.getMethod())) {
            builder.GET();
        } else if (request.getBody() != null) {
            builder.method(request.getMethod(), HttpRequest.BodyPublishers.ofString(request.getBody()));
        } else {
            builder.method(request.getMethod(), HttpRequest.BodyPublishers.noBody());
        }

        HttpResponse<String> response;
        try {
            response = client.send(builder.build(), HttpResponse.BodyHandlers.ofString());
        } catch (Exception e) {
            throw new RuntimeException("scrapy-style crawl failed for " + request.getUrl(), e);
        }

        Map<String, String> headers = new LinkedHashMap<>();
        response.headers().map().forEach((key, values) -> headers.put(key, String.join(", ", values)));
        return new Spider.Response(
            request.getUrl(),
            response.statusCode(),
            headers,
            response.body(),
            request
        );
    }

    private static String resolveRunner(Map<String, Object> meta, Map<String, Object> config) {
        String runner = normalizeRunner(meta.get("runner"));
        if (!runner.isBlank()) {
            return runner;
        }
        runner = normalizeRunner(config.get("runner"));
        return runner.isBlank() ? "http" : runner;
    }

    private static String normalizeRunner(Object value) {
        if (!(value instanceof String text)) {
            return "";
        }
        text = text.trim().toLowerCase();
        return switch (text) {
            case "browser", "http", "hybrid" -> text;
            default -> "";
        };
    }
}
