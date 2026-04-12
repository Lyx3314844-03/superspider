package com.javaspider.scrapy;

import com.javaspider.scrapy.item.Item;
import com.javaspider.scrapy.project.ProjectRuntime;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class SpiderTest {

    @Test
    @DisplayName("Scrapy-style Spider follows links and collects items")
    void testCrawlerProcessCollectsItemsAndFollowRequests() throws Exception {
        HttpServer server = HttpServer.create(new InetSocketAddress(0), 0);
        server.createContext("/", new HtmlHandler("<html><title>Home</title><a href=\"/next\">Next</a></html>"));
        server.createContext("/next", new HtmlHandler("<html><title>Next</title></html>"));
        server.start();

        try {
            String baseUrl = "http://127.0.0.1:" + server.getAddress().getPort();
            Spider spider = new Spider() {
                {
                    setName("demo");
                    addStartUrl(baseUrl + "/");
                }

                @Override
                public List<Object> parse(Response response) {
                    if (response.getUrl().endsWith("/next")) {
                        return List.of(new Item().set("title", response.selector().css("title").firstText()).set("url", response.getUrl()));
                    }
                    return List.of(
                        new Item().set("title", response.selector().css("title").firstText()),
                        response.follow("/next", this::parse)
                    );
                }
            };

            List<Item> items = new CrawlerProcess(spider)
                .addPipeline((item, currentSpider) -> item.set("spider", currentSpider.getName()))
                .crawl();

            assertEquals(2, items.size());
            assertEquals("Home", items.get(0).get("title"));
            assertEquals(baseUrl + "/next", items.get(1).get("url"));
            assertEquals("demo", items.get(1).get("spider"));
        } finally {
            server.stop(0);
        }
    }

    @Test
    @DisplayName("Scrapy-style Response follow resolves relative URLs")
    void testResponseFollowResolvesRelativeUrls() {
        Spider.Response response = new Spider.Response(
            "https://example.com/root",
            200,
            java.util.Map.of(),
            "<html></html>",
            null
        );

        Spider.Request request = response.follow("/next", ignored -> List.of());

        assertEquals("https://example.com/next", request.getUrl());
    }

    @Test
    @DisplayName("Selector integration remains available from scrapy response")
    void testResponseSelectorUsesExistingSelectorImplementation() {
        Spider.Response response = new Spider.Response(
            "https://example.com",
            200,
            java.util.Map.of(),
            "<html><body><h1>Demo</h1></body></html>",
            null
        );

        assertTrue(response.selector().css("h1").firstText().contains("Demo"));
    }

    @Test
    @DisplayName("Scrapy plugin hooks and injected pipelines work")
    void testCrawlerProcessRunsPluginHooksAndInjectedPipelines() throws Exception {
        HttpServer server = HttpServer.create(new InetSocketAddress(0), 0);
        server.createContext("/", new HtmlHandler("<html><title>Plugin Demo</title></html>"));
        server.start();

        try {
            String baseUrl = "http://127.0.0.1:" + server.getAddress().getPort();
            boolean[] opened = {false};
            boolean[] closed = {false};

            Spider spider = new Spider() {
                {
                    setName("demo");
                    addStartUrl(baseUrl + "/");
                }

                @Override
                public List<Object> parse(Spider.Response response) {
                    return List.of(new Item().set("title", response.selector().css("title").firstText()));
                }
            };

            ScrapyPlugin plugin = new ScrapyPlugin() {
                @Override
                public void prepareSpider(Spider spider) {
                    spider.setName("prepared-" + spider.getName());
                }

                @Override
                public List<Spider.ItemPipeline> providePipelines() {
                    return List.of((item, currentSpider) -> item.set("pipeline", "active"));
                }

                @Override
                public void onSpiderOpened(Spider spider) {
                    opened[0] = true;
                }

                @Override
                public void onSpiderClosed(Spider spider) {
                    closed[0] = true;
                }

                @Override
                public Item processItem(Item item, Spider spider) {
                    return item.set("plugin", spider.getName());
                }
            };

            List<Item> items = new CrawlerProcess(spider)
                .addPlugin(plugin)
                .crawl();

            assertTrue(opened[0]);
            assertTrue(closed[0]);
            assertEquals("active", items.get(0).get("pipeline"));
            assertEquals("prepared-demo", items.get(0).get("plugin"));
        } finally {
            server.stop(0);
        }
    }

    @Test
    @DisplayName("Project runtime registries resolve spiders and plugins")
    void testProjectRuntimeRegistries() {
        ProjectRuntime.registerSpider("registry-demo", () -> new Spider() {
            @Override
            public List<Object> parse(Spider.Response response) {
                return List.of();
            }
        });
        ProjectRuntime.registerPlugin("registry-plugin", () -> new ScrapyPlugin() {});

        Spider spider = ProjectRuntime.resolveSpider("registry-demo");
        List<ScrapyPlugin> plugins = ProjectRuntime.resolvePlugins(List.of("registry-plugin"));

        assertTrue(spider != null);
        assertEquals(1, plugins.size());
    }

    @Test
    @DisplayName("CrawlerProcess supports config, middleware hooks, and browser fetch runner")
    void testCrawlerProcessSupportsConfigMiddlewareAndBrowserRunner() {
        boolean[] configured = {false};

        Spider spider = new Spider() {
            {
                setName("demo");
                addStartUrl("https://example.com");
            }

            @Override
            public List<Object> parse(Spider.Response response) {
                return List.of(new Item().set("title", response.selector().css("title").firstText()));
            }
        };

        ScrapyPlugin plugin = new ScrapyPlugin() {
            @Override
            public void configure(Map<String, Object> config) {
                configured[0] = "browser".equals(config.get("runner"));
            }

            @Override
            public List<SpiderMiddleware> provideSpiderMiddlewares() {
                return List.of((response, result, currentSpider) -> {
                    java.util.ArrayList<Object> next = new java.util.ArrayList<>(result);
                    next.add(new Item().set("middleware", "spider"));
                    return next;
                });
            }

            @Override
            public List<DownloaderMiddleware> provideDownloaderMiddlewares() {
                return List.of(new DownloaderMiddleware() {
                    @Override
                    public Spider.Request processRequest(Spider.Request request, Spider spider) {
                        return request.header("X-Test", "active");
                    }

                    @Override
                    public Spider.Response processResponse(Spider.Response response, Spider spider) {
                        return response;
                    }
                });
            }

            @Override
            public Item processItem(Item item, Spider spider) {
                return item.set("configured", configured[0]);
            }
        };

        List<Item> items = new CrawlerProcess(spider)
            .withConfig(Map.of("runner", "browser"))
            .withBrowserFetcher((request, currentSpider) -> new Spider.Response(
                request.getUrl(),
                200,
                new LinkedHashMap<>(),
                "<html><title>Browser Demo</title></html>",
                request
            ))
            .addPlugin(plugin)
            .crawl();

        assertEquals(2, items.size());
        assertEquals("Browser Demo", items.get(0).get("title"));
        assertEquals(true, items.get(0).get("configured"));
        assertEquals("spider", items.get(1).get("middleware"));
    }

    private static final class HtmlHandler implements HttpHandler {
        private final byte[] body;

        private HtmlHandler(String body) {
            this.body = body.getBytes(StandardCharsets.UTF_8);
        }

        @Override
        public void handle(HttpExchange exchange) throws IOException {
            exchange.getResponseHeaders().add("Content-Type", "text/html; charset=utf-8");
            exchange.sendResponseHeaders(200, body.length);
            exchange.getResponseBody().write(body);
            exchange.close();
        }
    }
}
