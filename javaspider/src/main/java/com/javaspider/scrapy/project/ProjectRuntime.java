package com.javaspider.scrapy.project;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.javaspider.nodereverse.NodeReverseClient;
import com.javaspider.scrapy.CrawlerProcess;
import com.javaspider.scrapy.DownloaderMiddleware;
import com.javaspider.scrapy.ScrapyPlugin;
import com.javaspider.scrapy.Spider;
import com.javaspider.scrapy.SpiderMiddleware;
import com.javaspider.scrapy.feed.FeedExporter;
import com.javaspider.scrapy.item.Item;
import org.yaml.snakeyaml.Yaml;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Collections;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.function.Supplier;

public final class ProjectRuntime {
    private static final Map<String, Supplier<Spider>> SPIDERS = new TreeMap<>();
    private static final Map<String, Supplier<ScrapyPlugin>> PLUGINS = new TreeMap<>();
    private static final ObjectMapper MAPPER = new ObjectMapper();

    public static final class PluginSpec {
        private final String name;
        private final boolean enabled;
        private final int priority;
        private final Map<String, Object> config;

        public PluginSpec(String name, boolean enabled, int priority, Map<String, Object> config) {
            this.name = name == null ? "" : name.trim();
            this.enabled = enabled;
            this.priority = priority;
            this.config = config == null ? Map.of() : Map.copyOf(config);
        }

        public String name() {
            return name;
        }

        public boolean enabled() {
            return enabled;
        }

        public int priority() {
            return priority;
        }

        public Map<String, Object> config() {
            return config;
        }
    }

    private ProjectRuntime() {
    }

    public static Map<String, Object> loadAIProjectAssets(Path projectRoot) {
        Map<String, Object> schema = Map.of(
            "type", "object",
            "properties", Map.of(
                "title", Map.of("type", "string"),
                "summary", Map.of("type", "string"),
                "url", Map.of("type", "string")
            )
        );
        Map<String, Object> blueprint = new LinkedHashMap<>();
        String extractionPrompt = "提取标题、摘要和 URL";
        boolean paginationEnabled = false;
        List<String> paginationSelectors = new ArrayList<>();
        String recommendedRunner = "http";
        Map<String, String> requestHeaders = new LinkedHashMap<>();
        boolean authRequired = false;
        String storageStateFile = "";
        String cookiesFile = "";

        try {
            Path schemaPath = projectRoot.resolve("ai-schema.json");
            if (Files.exists(schemaPath)) {
                schema = MAPPER.readValue(Files.readString(schemaPath), new TypeReference<Map<String, Object>>() {});
            }
            Path blueprintPath = projectRoot.resolve("ai-blueprint.json");
            if (Files.exists(blueprintPath)) {
                blueprint = MAPPER.readValue(Files.readString(blueprintPath), new TypeReference<Map<String, Object>>() {});
                extractionPrompt = firstNonBlank(stringValue(blueprint.get("extraction_prompt"), ""), extractionPrompt);
                Map<String, Object> pagination = nestedMap(blueprint, "pagination");
                paginationEnabled = Boolean.TRUE.equals(pagination.get("enabled"));
                paginationSelectors = stringListValue(pagination.get("selectors"));
                authRequired = Boolean.TRUE.equals(nestedMap(blueprint, "authentication").get("required"));
                String jsRunner = stringValue(nestedMap(blueprint, "javascript_runtime").get("recommended_runner"), "");
                String antiBotRunner = stringValue(nestedMap(blueprint, "anti_bot_strategy").get("recommended_runner"), "");
                recommendedRunner = firstNonBlank(jsRunner, antiBotRunner, "http");
            }
            Path promptPath = projectRoot.resolve("ai-extract-prompt.txt");
            if (Files.exists(promptPath) && extractionPrompt.isBlank()) {
                extractionPrompt = firstNonBlank(Files.readString(promptPath).trim(), extractionPrompt);
            }
            Path authPath = projectRoot.resolve("ai-auth.json");
            if (Files.exists(authPath)) {
                Map<String, Object> auth = MAPPER.readValue(Files.readString(authPath), new TypeReference<Map<String, Object>>() {});
                Map<String, Object> headers = nestedMap(auth, "headers");
                for (Map.Entry<String, Object> entry : headers.entrySet()) {
                    String key = entry.getKey();
                    String value = stringValue(entry.getValue(), "");
                    if (!key.isBlank() && !value.isBlank()) {
                        requestHeaders.put(key, value);
                    }
                }
                storageStateFile = stringValue(auth.get("storage_state_file"), "");
                cookiesFile = stringValue(auth.get("cookies_file"), "");
            }
        } catch (IOException ignored) {
        }
        String authCookie = System.getenv("SPIDER_AUTH_COOKIE");
        if (authCookie != null && !authCookie.isBlank()) {
            requestHeaders.put("Cookie", authCookie);
        }
        String authHeadersJson = System.getenv("SPIDER_AUTH_HEADERS_JSON");
        if (authHeadersJson != null && !authHeadersJson.isBlank()) {
            try {
                Map<String, Object> headers = MAPPER.readValue(authHeadersJson, new TypeReference<Map<String, Object>>() {});
                for (Map.Entry<String, Object> entry : headers.entrySet()) {
                    String key = entry.getKey();
                    String value = stringValue(entry.getValue(), "");
                    if (!key.isBlank() && !value.isBlank()) {
                        requestHeaders.put(key, value);
                    }
                }
            } catch (IOException ignored) {
            }
        }
        if (authRequired && "http".equals(recommendedRunner)) {
            recommendedRunner = "browser";
        }

        Map<String, Object> assets = new LinkedHashMap<>();
        assets.put("schema", schema);
        assets.put("blueprint", blueprint);
        assets.put("extraction_prompt", extractionPrompt);
        assets.put("pagination_enabled", paginationEnabled);
        assets.put("pagination_selectors", paginationSelectors);
        assets.put("recommended_runner", recommendedRunner);
        assets.put("request_headers", requestHeaders);
        assets.put("auth_required", authRequired);
        assets.put("storage_state_file", storageStateFile);
        assets.put("cookies_file", cookiesFile);
        return assets;
    }

    public static Spider applyAIStartMeta(Spider spider, Map<String, Object> assets) {
        String runner = stringValue(assets.get("recommended_runner"), "http");
        if (!runner.isBlank() && !"http".equals(runner)) {
            spider.startMeta("runner", runner);
        }
        String storageStateFile = stringValue(assets.get("storage_state_file"), "");
        String cookiesFile = stringValue(assets.get("cookies_file"), "");
        if (!storageStateFile.isBlank() || !cookiesFile.isBlank()) {
            Map<String, Object> browserMeta = new LinkedHashMap<>();
            if (!storageStateFile.isBlank()) {
                browserMeta.put("storage_state_file", storageStateFile);
            }
            if (!cookiesFile.isBlank()) {
                browserMeta.put("cookies_file", cookiesFile);
            }
            spider.startMeta("browser", browserMeta);
        }
        @SuppressWarnings("unchecked")
        Map<String, String> headers = (Map<String, String>) assets.getOrDefault("request_headers", Map.of());
        for (Map.Entry<String, String> entry : headers.entrySet()) {
            spider.startHeader(entry.getKey(), entry.getValue());
        }
        return spider;
    }

    public static Spider.Request applyAIRequestStrategy(Spider.Request request, Map<String, Object> assets) {
        String runner = stringValue(assets.get("recommended_runner"), "http");
        if (!runner.isBlank() && !"http".equals(runner)) {
            request = request.meta("runner", runner);
        }
        String storageStateFile = stringValue(assets.get("storage_state_file"), "");
        String cookiesFile = stringValue(assets.get("cookies_file"), "");
        if (!storageStateFile.isBlank() || !cookiesFile.isBlank()) {
            Map<String, Object> browserMeta = new LinkedHashMap<>();
            Object existing = request.getMeta().get("browser");
            if (existing instanceof Map<?, ?> raw) {
                for (Map.Entry<?, ?> entry : raw.entrySet()) {
                    browserMeta.put(String.valueOf(entry.getKey()), entry.getValue());
                }
            }
            if (!storageStateFile.isBlank()) {
                browserMeta.put("storage_state_file", storageStateFile);
            }
            if (!cookiesFile.isBlank()) {
                browserMeta.put("cookies_file", cookiesFile);
            }
            request = request.meta("browser", browserMeta);
        }
        @SuppressWarnings("unchecked")
        Map<String, String> headers = (Map<String, String>) assets.getOrDefault("request_headers", Map.of());
        for (Map.Entry<String, String> entry : headers.entrySet()) {
            request = request.header(entry.getKey(), entry.getValue());
        }
        return request;
    }

    public static List<Spider.Request> collectAIPaginationRequests(Spider.Response response, Spider.Callback callback, Map<String, Object> assets) {
        boolean enabled = Boolean.TRUE.equals(assets.get("pagination_enabled"));
        if (!enabled) {
            return List.of();
        }
        List<String> selectors = stringListValue(assets.get("pagination_selectors"));
        if (selectors.isEmpty()) {
            return List.of();
        }
        String runner = stringValue(assets.get("recommended_runner"), "http");
        com.javaspider.parser.HtmlParser parser = new com.javaspider.parser.HtmlParser(response.getBody());
        List<Spider.Request> requests = new ArrayList<>();
        Map<String, Boolean> seen = new LinkedHashMap<>();
        for (String selector : selectors) {
            for (String link : parser.cssAttr(selector, "href")) {
                if (link == null || link.isBlank() || seen.putIfAbsent(link, true) != null) {
                    continue;
                }
                requests.add(applyAIRequestStrategy(response.follow(link, callback), assets));
            }
        }
        return requests;
    }

    public static void registerSpider(String name, Supplier<Spider> factory) {
        if (factory == null || name == null || name.isBlank()) {
            return;
        }
        SPIDERS.put(name.trim(), factory);
    }

    public static void registerPlugin(String name, Supplier<ScrapyPlugin> factory) {
        if (factory == null || name == null || name.isBlank()) {
            return;
        }
        PLUGINS.put(name.trim(), factory);
    }

    public static List<String> spiderNames() {
        return new ArrayList<>(SPIDERS.keySet());
    }

    public static List<String> pluginNames() {
        return new ArrayList<>(PLUGINS.keySet());
    }

    public static Spider resolveSpider(String name) {
        if (SPIDERS.isEmpty()) {
            throw new IllegalStateException("no registered scrapy spiders");
        }
        String target = (name == null || name.isBlank()) ? spiderNames().get(0) : name.trim();
        Supplier<Spider> factory = SPIDERS.get(target);
        if (factory == null) {
            throw new IllegalArgumentException("unknown registered spider: " + target);
        }
        return factory.get();
    }

    public static List<ScrapyPlugin> resolvePlugins(List<String> selected) {
        List<PluginSpec> specs = new ArrayList<>();
        if (selected != null) {
            for (String name : selected) {
                specs.add(new PluginSpec(name, true, 0, Map.of()));
            }
        }
        return resolvePluginSpecs(specs);
    }

    public static List<ScrapyPlugin> resolvePluginSpecs(List<PluginSpec> selected) {
        List<PluginSpec> specs = normalizePluginSpecs(selected);
        if (specs.isEmpty()) {
            specs = pluginNames().stream().map(name -> new PluginSpec(name, true, 0, Map.of())).toList();
        }
        List<ScrapyPlugin> plugins = new ArrayList<>();
        for (PluginSpec spec : specs) {
            if (!spec.enabled()) {
                continue;
            }
            Supplier<ScrapyPlugin> factory = PLUGINS.get(spec.name());
            if (factory != null) {
                plugins.add(factory.get());
                continue;
            }
            ScrapyPlugin plugin = createBuiltinPlugin(spec);
            if (plugin != null) {
                plugins.add(plugin);
                continue;
            }
            throw new IllegalArgumentException("unknown registered plugin: " + spec.name());
        }
        return plugins;
    }

    public static boolean runFromEnv() {
        if (!"1".equals(System.getenv("JAVASPIDER_SCRAPY_RUNNER"))) {
            return false;
        }
        String selectedSpider = firstNonBlank(System.getenv("JAVASPIDER_SCRAPY_SPIDER"), "");
        String targetUrl = firstNonBlank(System.getenv("JAVASPIDER_SCRAPY_URL"), "https://example.com");
        String htmlFile = firstNonBlank(System.getenv("JAVASPIDER_SCRAPY_HTML_FILE"), "");
        String outputPath = firstNonBlank(System.getenv("JAVASPIDER_SCRAPY_OUTPUT"), "artifacts/exports/items.json");
        List<String> selectedPlugins = splitCSV(System.getenv("JAVASPIDER_SCRAPY_PLUGINS"));
        String projectRoot = firstNonBlank(System.getenv("JAVASPIDER_SCRAPY_PROJECT"), "");
        String reverseUrl = firstNonBlank(System.getenv("JAVASPIDER_SCRAPY_REVERSE_URL"), "");
        Map<String, Object> projectConfig = projectRoot.isBlank() ? Map.of() : loadProjectConfig(Path.of(projectRoot));
        if (reverseUrl.isBlank()) {
            reverseUrl = firstNonBlank(String.valueOf(nestedMap(projectConfig, "node_reverse").getOrDefault("base_url", "")), "");
        }
        List<PluginSpec> selectedPluginSpecs = selectedPlugins.isEmpty() && !projectRoot.isBlank()
            ? loadPluginSpecsFromManifest(Path.of(projectRoot))
            : selectedPlugins.stream().map(name -> new PluginSpec(name, true, 0, Map.of())).toList();
        if (selectedPluginSpecs.isEmpty()) {
            selectedPluginSpecs = configuredPluginSpecs(projectConfig);
        }

        Spider spider = resolveSpider(selectedSpider);
        if (spider.startRequests().isEmpty() && !targetUrl.isBlank()) {
            spider.addStartUrl(targetUrl);
        }
        List<ScrapyPlugin> plugins = resolvePluginSpecs(selectedPluginSpecs);

        List<Item> items;
        try {
            items = runSpiderWithPlugins(spider, plugins, targetUrl, htmlFile, projectConfig);

            try (FeedExporter exporter = FeedExporter.json(outputPath)) {
                exporter.exportItems(items);
            }

            List<String> declarativePipelines = stringListValue(nestedMap(projectConfig, "scrapy").get("pipelines"));
            List<String> declarativeSpiderMiddlewares = stringListValue(nestedMap(projectConfig, "scrapy").get("spider_middlewares"));
            List<String> declarativeDownloaderMiddlewares = stringListValue(nestedMap(projectConfig, "scrapy").get("downloader_middlewares"));
            int pipelineCount = buildDeclarativePipelines(projectConfig).size()
                + plugins.stream().mapToInt(plugin -> plugin.providePipelines().size()).sum();
            int spiderMiddlewareCount = buildDeclarativeSpiderMiddlewares(projectConfig).size()
                + plugins.stream().mapToInt(plugin -> plugin.provideSpiderMiddlewares().size()).sum();
            int downloaderMiddlewareCount = buildDeclarativeDownloaderMiddlewares(projectConfig).size()
                + plugins.stream().mapToInt(plugin -> plugin.provideDownloaderMiddlewares().size()).sum();

            Map<String, Object> payload = new LinkedHashMap<>();
            payload.put("command", "scrapy run");
            payload.put("runtime", "java");
            payload.put("runner", "artifact-project");
            payload.put("spider", spider.getName());
            payload.put("plugins", selectedPluginSpecs.isEmpty() ? pluginNames() : pluginSpecNames(selectedPluginSpecs));
            payload.put("settings_source", projectRoot.isBlank() ? null : Path.of(projectRoot).resolve("spider-framework.yaml").toString());
            payload.put("pipelines", declarativePipelines);
            payload.put("spider_middlewares", declarativeSpiderMiddlewares);
            payload.put("downloader_middlewares", declarativeDownloaderMiddlewares);
            payload.put("pipeline_count", pipelineCount);
            payload.put("spider_middleware_count", spiderMiddlewareCount);
            payload.put("downloader_middleware_count", downloaderMiddlewareCount);
            payload.put("item_count", items.size());
            payload.put("output", outputPath);
            payload.put("reverse", collectReverseSummary(reverseUrl, targetUrl, htmlFile));
            System.out.println(MAPPER.writerWithDefaultPrettyPrinter().writeValueAsString(payload));
        } catch (IOException e) {
            throw new RuntimeException("project runtime failed", e);
        }
        return true;
    }

    public static Object collectReverseSummary(String reverseUrl, String targetUrl, String htmlFile) {
        if (reverseUrl == null || reverseUrl.isBlank()) {
            return null;
        }
        try {
            String html = htmlFile != null && !htmlFile.isBlank()
                ? Files.readString(Path.of(htmlFile))
                : "";
            if (html.isBlank()) {
                return null;
            }
            NodeReverseClient client = new NodeReverseClient(reverseUrl);
            JsonNode detect = client.detectAntiBot(html, "", Collections.emptyMap(), "", 200, targetUrl);
            JsonNode profile = client.profileAntiBot(html, "", Collections.emptyMap(), "", 200, targetUrl);
            JsonNode spoof = client.spoofFingerprint("chrome", "windows");
            JsonNode tls = client.generateTlsFingerprint("chrome", "120");
            JsonNode canvas = client.canvasFingerprint();
            Map<String, Object> payload = new LinkedHashMap<>();
            payload.put("detect", detect);
            payload.put("profile", profile);
            payload.put("fingerprint_spoof", spoof);
            payload.put("tls_fingerprint", tls);
            payload.put("canvas_fingerprint", canvas);
            String scriptSample = extractScriptSample(html);
            if (!scriptSample.isBlank()) {
                payload.put("crypto_analysis", client.analyzeCrypto(scriptSample));
            }
            return payload;
        } catch (Exception ignored) {
            return null;
        }
    }

    private static String extractScriptSample(String html) {
        String lowered = html.toLowerCase();
        int start = 0;
        List<String> parts = new ArrayList<>();
        while (true) {
            int openRel = lowered.indexOf("<script", start);
            if (openRel < 0) {
                break;
            }
            int tagEnd = lowered.indexOf(">", openRel);
            if (tagEnd < 0) {
                break;
            }
            int close = lowered.indexOf("</script>", tagEnd);
            if (close < 0) {
                break;
            }
            String snippet = html.substring(tagEnd + 1, close).trim();
            if (!snippet.isBlank()) {
                parts.add(snippet);
            }
            start = close + "</script>".length();
        }
        String joined = String.join("\n", parts);
        if (!joined.isBlank()) {
            return joined.length() > 32000 ? joined.substring(0, 32000) : joined;
        }
        return html.length() > 32000 ? html.substring(0, 32000) : html;
    }

    private static String firstNonBlank(String... values) {
        for (String value : values) {
            if (value != null && !value.isBlank()) {
                return value;
            }
        }
        return "";
    }

    private static String stringValue(Object value, String defaultValue) {
        if (value == null) {
            return defaultValue;
        }
        String stringValue = String.valueOf(value);
        return stringValue.isBlank() ? defaultValue : stringValue;
    }

    private static List<String> splitCSV(String value) {
        List<String> items = new ArrayList<>();
        if (value == null || value.isBlank()) {
            return items;
        }
        for (String item : value.split(",")) {
            String trimmed = item.trim();
            if (!trimmed.isBlank()) {
                items.add(trimmed);
            }
        }
        return items;
    }

    private static Map<String, Object> loadProjectConfig(Path projectRoot) {
        Path path = projectRoot.resolve("spider-framework.yaml");
        if (!Files.exists(path)) {
            return Map.of();
        }
        try {
            Object payload = new Yaml().load(Files.readString(path));
            if (payload instanceof Map<?, ?> map) {
                @SuppressWarnings("unchecked")
                Map<String, Object> typed = (Map<String, Object>) map;
                return typed;
            }
        } catch (IOException ignored) {
        }
        return Map.of();
    }

    private static List<PluginSpec> configuredPluginSpecs(Map<String, Object> config) {
        return stringListValue(nestedMap(config, "scrapy").get("plugins")).stream()
            .map(name -> new PluginSpec(name, true, 0, Map.of()))
            .toList();
    }

    public static List<Item> runSpiderWithPlugins(Spider spider, List<ScrapyPlugin> plugins, String targetUrl, String htmlFile) throws IOException {
        return runSpiderWithPlugins(spider, plugins, targetUrl, htmlFile, Map.of());
    }

    public static List<Item> runSpiderWithPlugins(Spider spider, List<ScrapyPlugin> plugins, String targetUrl, String htmlFile, Map<String, Object> config) throws IOException {
        List<Spider.ItemPipeline> declarativePipelines = buildDeclarativePipelines(config);
        List<SpiderMiddleware> declarativeSpiderMiddlewares = buildDeclarativeSpiderMiddlewares(config);
        List<DownloaderMiddleware> declarativeDownloaderMiddlewares = buildDeclarativeDownloaderMiddlewares(config);
        if (!htmlFile.isBlank()) {
            List<SpiderMiddleware> spiderMiddlewares = new ArrayList<>(declarativeSpiderMiddlewares);
            List<DownloaderMiddleware> downloaderMiddlewares = new ArrayList<>(declarativeDownloaderMiddlewares);
            for (ScrapyPlugin plugin : plugins) {
                plugin.configure(config);
                plugin.prepareSpider(spider);
                spiderMiddlewares.addAll(plugin.provideSpiderMiddlewares());
                downloaderMiddlewares.addAll(plugin.provideDownloaderMiddlewares());
                plugin.onSpiderOpened(spider);
            }
            Spider.Request request = new Spider.Request(targetUrl, spider::parse);
            for (DownloaderMiddleware middleware : downloaderMiddlewares) {
                request = middleware.processRequest(request, spider);
            }
            String html = Files.readString(Path.of(htmlFile));
            Spider.Response response = new Spider.Response(
                targetUrl,
                200,
                Map.of(),
                html,
                request
            );
            for (DownloaderMiddleware middleware : downloaderMiddlewares) {
                response = middleware.processResponse(response, spider);
            }
            List<Spider.ItemPipeline> pipelines = new ArrayList<>(declarativePipelines);
            for (ScrapyPlugin plugin : plugins) {
                pipelines.addAll(plugin.providePipelines());
            }
            List<Item> items = new ArrayList<>();
            List<Object> results = spider.parse(response);
            for (SpiderMiddleware middleware : spiderMiddlewares) {
                results = middleware.processSpiderOutput(response, results, spider);
            }
            for (Object result : results) {
                if (!(result instanceof Item item)) {
                    continue;
                }
                for (Spider.ItemPipeline pipeline : pipelines) {
                    item = pipeline.processItem(item, spider);
                }
                for (ScrapyPlugin plugin : plugins) {
                    item = plugin.processItem(item, spider);
                }
                items.add(item);
            }
            for (ScrapyPlugin plugin : plugins) {
                plugin.onSpiderClosed(spider);
            }
            return items;
        }
        CrawlerProcess process = new CrawlerProcess(spider);
        process.withConfig(config);
        for (Spider.ItemPipeline pipeline : declarativePipelines) {
            process.addPipeline(pipeline);
        }
        for (SpiderMiddleware middleware : declarativeSpiderMiddlewares) {
            process.addSpiderMiddleware(middleware);
        }
        for (DownloaderMiddleware middleware : declarativeDownloaderMiddlewares) {
            process.addDownloaderMiddleware(middleware);
        }
        for (ScrapyPlugin plugin : plugins) {
            process.addPlugin(plugin);
        }
        return process.crawl();
    }

    public static List<Spider.ItemPipeline> buildDeclarativePipelines(Map<String, Object> config) {
        List<Spider.ItemPipeline> pipelines = new ArrayList<>();
        Map<String, Object> scrapy = nestedMap(config, "scrapy");
        Map<String, Object> componentConfig = nestedMap(scrapy, "component_config");
        for (String name : stringListValue(scrapy.get("pipelines"))) {
            if ("field-injector".equals(name)) {
                Map<String, Object> fields = nestedMap(nestedMap(componentConfig, "field_injector"), "fields");
                pipelines.add((item, spider) -> {
                    Item current = item;
                    for (Map.Entry<String, Object> entry : fields.entrySet()) {
                        current = current.set(entry.getKey(), entry.getValue());
                    }
                    return current;
                });
            }
        }
        return pipelines;
    }

    public static List<SpiderMiddleware> buildDeclarativeSpiderMiddlewares(Map<String, Object> config) {
        List<SpiderMiddleware> middlewares = new ArrayList<>();
        Map<String, Object> scrapy = nestedMap(config, "scrapy");
        for (String name : stringListValue(scrapy.get("spider_middlewares"))) {
            if ("response-context".equals(name)) {
                middlewares.add((response, result, spider) -> {
                    List<Object> enriched = new ArrayList<>(result.size());
                    for (Object entry : result) {
                        if (entry instanceof Item item) {
                            enriched.add(item.set("response_url", response.getUrl()).set("response_status", response.getStatusCode()));
                        } else if (entry instanceof Map<?, ?> map) {
                            @SuppressWarnings("unchecked")
                            Map<String, Object> typed = new LinkedHashMap<>((Map<String, Object>) map);
                            typed.put("response_url", response.getUrl());
                            typed.put("response_status", response.getStatusCode());
                            enriched.add(typed);
                        } else {
                            enriched.add(entry);
                        }
                    }
                    return enriched;
                });
            }
        }
        return middlewares;
    }

    public static List<DownloaderMiddleware> buildDeclarativeDownloaderMiddlewares(Map<String, Object> config) {
        List<DownloaderMiddleware> middlewares = new ArrayList<>();
        Map<String, Object> scrapy = nestedMap(config, "scrapy");
        Map<String, Object> componentConfig = nestedMap(scrapy, "component_config");
        for (String name : stringListValue(scrapy.get("downloader_middlewares"))) {
            if ("request-headers".equals(name)) {
                Map<String, Object> headers = nestedMap(nestedMap(componentConfig, "request_headers"), "headers");
                middlewares.add(new DownloaderMiddleware() {
                    @Override
                    public Spider.Request processRequest(Spider.Request request, Spider spider) {
                        Spider.Request current = request;
                        for (Map.Entry<String, Object> entry : headers.entrySet()) {
                            current = current.header(entry.getKey(), String.valueOf(entry.getValue()));
                        }
                        return current;
                    }

                    @Override
                    public Spider.Response processResponse(Spider.Response response, Spider spider) {
                        return response;
                    }
                });
            }
        }
        return middlewares;
    }

    public static List<PluginSpec> loadPluginSpecsFromManifest(Path projectRoot) {
        Path path = projectRoot.resolve("scrapy-plugins.json");
        if (!Files.exists(path)) {
            return List.of();
        }
        try {
            Object payload = MAPPER.readValue(Files.readString(path), Object.class);
            List<PluginSpec> specs = new ArrayList<>();
            if (payload instanceof List<?> list) {
                for (Object item : list) {
                    if (item instanceof String name && !name.isBlank()) {
                        specs.add(new PluginSpec(name, true, 0, Map.of()));
                    }
                }
                return normalizePluginSpecs(specs);
            }
            if (payload instanceof Map<?, ?> map) {
                Object plugins = map.get("plugins");
                if (plugins instanceof List<?> list) {
                    for (Object item : list) {
                        if (item instanceof String name && !name.isBlank()) {
                            specs.add(new PluginSpec(name, true, 0, Map.of()));
                        } else if (item instanceof Map<?, ?> object) {
                            Object name = object.get("name");
                            if (name instanceof String string && !string.isBlank()) {
                                int priority = object.get("priority") instanceof Number number ? number.intValue() : 0;
                                @SuppressWarnings("unchecked")
                                Map<String, Object> config = object.get("config") instanceof Map<?, ?> raw ? (Map<String, Object>) raw : Map.of();
                                boolean enabled = !(object.get("enabled") instanceof Boolean bool) || bool;
                                specs.add(new PluginSpec(string, enabled, priority, config));
                            }
                        }
                    }
                }
            }
            return normalizePluginSpecs(specs);
        } catch (IOException ignored) {
            return List.of();
        }
    }

    private static List<String> pluginSpecNames(List<PluginSpec> specs) {
        return normalizePluginSpecs(specs).stream()
            .filter(PluginSpec::enabled)
            .map(PluginSpec::name)
            .toList();
    }

    private static List<PluginSpec> normalizePluginSpecs(List<PluginSpec> specs) {
        if (specs == null || specs.isEmpty()) {
            return List.of();
        }
        return specs.stream()
            .filter(spec -> spec != null && !spec.name().isBlank())
            .sorted((left, right) -> {
                int priority = Integer.compare(left.priority(), right.priority());
                return priority != 0 ? priority : left.name().compareTo(right.name());
            })
            .toList();
    }

    private static ScrapyPlugin createBuiltinPlugin(PluginSpec spec) {
        if ("field-injector".equals(spec.name())) {
            return new FieldInjectorPlugin(spec.config());
        }
        return null;
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> nestedMap(Map<String, Object> root, String key) {
        Object value = root.get(key);
        if (value instanceof Map<?, ?> map) {
            return (Map<String, Object>) map;
        }
        return Map.of();
    }

    private static List<String> stringListValue(Object value) {
        List<String> items = new ArrayList<>();
        if (value instanceof List<?> list) {
            for (Object item : list) {
                if (item instanceof String stringValue && !stringValue.isBlank()) {
                    items.add(stringValue.trim());
                }
            }
        }
        return items;
    }

    private static final class FieldInjectorPlugin implements ScrapyPlugin {
        private final Map<String, Object> fields;

        private FieldInjectorPlugin(Map<String, Object> config) {
            Object rawFields = config.get("fields");
            if (rawFields instanceof Map<?, ?> map) {
                LinkedHashMap<String, Object> collected = new LinkedHashMap<>();
                for (Map.Entry<?, ?> entry : map.entrySet()) {
                    if (entry.getKey() != null) {
                        collected.put(String.valueOf(entry.getKey()), entry.getValue());
                    }
                }
                this.fields = collected;
            } else {
                this.fields = Map.of();
            }
        }

        @Override
        public Item processItem(Item item, Spider spider) {
            Item current = item;
            for (Map.Entry<String, Object> entry : fields.entrySet()) {
                current = current.set(entry.getKey(), entry.getValue());
            }
            return current;
        }
    }
}
