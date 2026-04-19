package com.javaspider;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.javaspider.advanced.UltimateSpiderProcessor;
import com.javaspider.ai.AIExtractor;
import com.javaspider.antibot.AntiBotHandler;
import com.javaspider.cli.MediaDownloaderCLI;
import com.javaspider.cli.QuickSpider;
import com.javaspider.cli.SuperSpiderCLI;
import com.javaspider.cli.WorkflowSpiderCLI;
import com.javaspider.core.Page;
import com.javaspider.core.Request;
import com.javaspider.downloader.HttpClientDownloader;
import com.javaspider.media.FFmpegUtil;
import com.javaspider.nodereverse.NodeReverseClient;
import com.javaspider.parser.HtmlParser;
import com.javaspider.scrapy.CrawlerProcess;
import com.javaspider.scrapy.DownloaderMiddleware;
import com.javaspider.scrapy.ScrapyPlugin;
import com.javaspider.scrapy.Spider;
import com.javaspider.scrapy.SpiderMiddleware;
import com.javaspider.scrapy.feed.FeedExporter;
import com.javaspider.scrapy.item.Item;
import com.javaspider.scrapy.project.ProjectRuntime;
import com.spider.converter.CurlToJavaConverter;

import java.io.IOException;
import java.io.InputStream;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.function.Supplier;
import java.util.ArrayList;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.net.URL;

import org.yaml.snakeyaml.Yaml;

/**
 * JavaSpider 通用框架入口。
 *
 * <p>这里不再伪装成搜索/Apify 演示脚本，而是提供真实的框架 CLI：
 * crawl/doctor/media/version/help。</p>
 */
public class EnhancedSpider {

    private static final String VERSION = "2.1.0";
    private static Supplier<BrowserFetchRunner> browserFetchRunnerFactory = DefaultBrowserFetchRunner::new;

    public static void main(String[] args) {
        if (args.length == 0) {
            printHelp();
            return;
        }

        String command = args[0];
        String[] rest = slice(args, 1);

        switch (command) {
            case "config":
                handleConfig(rest);
                break;
            case "crawl":
                handleCrawl(rest);
                break;
            case "browser":
                handleBrowser(rest);
                break;
            case "ai":
                handleAI(rest);
                break;
            case "doctor":
                handleDoctor(rest);
                break;
            case "preflight":
                handleDoctor(rest, "preflight");
                break;
            case "export":
                handleExport(rest);
                break;
            case "curl":
                handleCurl(rest);
                break;
            case "jobdir":
                handleJobdir(rest);
                break;
            case "http-cache":
                handleHttpCache(rest);
                break;
            case "console":
                handleConsole(rest);
                break;
            case "audit":
                handleAudit(rest);
                break;
            case "web":
            case "run":
            case "async-job":
            case "research":
                SuperSpiderCLI.main(args);
                break;
            case "ultimate":
                UltimateSpiderProcessor.main(rest);
                break;
            case "sitemap-discover":
                handleSitemapDiscover(rest);
                break;
            case "plugins":
                handlePlugins(rest);
                break;
            case "selector-studio":
                handleSelectorStudio(rest);
                break;
            case "scrapy":
                handleScrapy(rest);
                break;
            case "profile-site":
                handleProfileSite(rest);
                break;
            case "node-reverse":
                handleNodeReverse(rest);
                break;
            case "anti-bot":
            case "antibot":
                handleAntiBot(rest);
                break;
            case "workflow":
                WorkflowSpiderCLI.main(rest);
                break;
            case "job":
            case "capabilities":
                SuperSpiderCLI.main(args);
                break;
            case "media":
                MediaDownloaderCLI.main(rest);
                break;
            case "version":
            case "-v":
            case "--version":
                System.out.println("JavaSpider Framework CLI v" + VERSION);
                break;
            case "help":
            case "-h":
            case "--help":
                printHelp();
                break;
            default:
                System.out.println("未知命令: " + command);
                printHelp();
        }
    }

    private static void printHelp() {
        System.out.println("JavaSpider Framework CLI v" + VERSION);
        System.out.println("用法: java com.javaspider.EnhancedSpider <command> [options]");
        System.out.println();
        System.out.println("可用命令:");
        System.out.println("  config  生成共享配置文件");
        System.out.println("          用法: config init [--output <path>]");
        System.out.println("  crawl   真正执行一次页面抓取");
        System.out.println("          用法: crawl <url> 或 crawl --url <url> [--config <path>]");
        System.out.println("  browser 动态页面抓取");
        System.out.println("          用法: browser fetch --url <url> [--config <path>] [--screenshot <path>]");
        System.out.println("          用法: browser trace|mock|codegen ...");
        System.out.println("  ai      运行 AI 辅助提取、理解或爬虫配置生成");
        System.out.println("          用法: ai --url <url> [--instructions <text>] [--schema-json <json>]");
        System.out.println("  doctor  输出运行时和文件系统检查");
        System.out.println("          用法: doctor [--json] [--config <path>]");
        System.out.println("  preflight 运行前自检，是 doctor 的跨运行时别名");
        System.out.println("            用法: preflight [--json] [--config <path>]");
        System.out.println("  export  统一导出接口");
        System.out.println("          用法: export --input <path> --format <json|jsonl|csv|md> --output <path>");
        System.out.println("  curl    将 curl 命令转换为 Java 代码");
        System.out.println("          用法: curl convert --command <curl> [--target <java|http|okhttp|apache>]");
        System.out.println("  jobdir  共享作业目录管理");
        System.out.println("          用法: jobdir <init|status|pause|resume|clear> --path <path>");
        System.out.println("  http-cache 共享 HTTP cache 管理");
        System.out.println("             用法: http-cache <status|clear|seed> --path <path>");
        System.out.println("  console 共享运行时控制台");
        System.out.println("          用法: console <snapshot|tail> --control-plane <dir>");
        System.out.println("  audit   共享审计控制台");
        System.out.println("          用法: audit <snapshot|tail> --control-plane <dir> [--job-name <name>]");
        System.out.println("  web     启动内置 Web 服务");
        System.out.println("          用法: web [--port <port>]");
        System.out.println("  research 运行 pyspider 风格 research runtime");
        System.out.println("           用法: research <run|async|soak> ...");
        System.out.println("  ultimate 运行高级终极爬虫");
        System.out.println("           用法: ultimate <url>");
        System.out.println("  sitemap-discover 在抓取前发现 sitemap URL");
        System.out.println("                   用法: sitemap-discover --url <url> [--sitemap-file <path>]");
        System.out.println("  plugins 查看共享插件/集成清单");
        System.out.println("          用法: plugins <list|run> ...");
        System.out.println("  selector-studio 调试选择器和抽取表达式");
        System.out.println("                  用法: selector-studio --html-file <path> --type <css|css_attr|xpath|regex> --expr <expr>");
        System.out.println("  scrapy scrapy 风格 authoring 演示入口");
        System.out.println("         用法: scrapy demo [--url <url>] [--html-file <path>] [--output <path>]");
        System.out.println("         用法: scrapy shell [--url <url>] [--html-file <path>] [--type <css|css_attr|xpath|regex>] --expr <expr>");
        System.out.println("         用法: scrapy contracts <init|validate> --project <dir>");
        System.out.println("  profile-site 在抓取前对站点做画像");
        System.out.println("               用法: profile-site --url <url> [--html-file <path>] [--base-url <url>]");
        System.out.println("  node-reverse 调用 Node.js 逆向服务");
        System.out.println("               用法: node-reverse <health|profile|detect|fingerprint-spoof|tls-fingerprint|canvas-fingerprint|analyze-crypto|signature-reverse|ast|webpack|function-call|browser-simulate> [options]");
        System.out.println("  anti-bot 运行反反爬诊断工具");
        System.out.println("           用法: anti-bot <headers|profile> [options]");
        System.out.println("  workflow  执行工作流 CLI");
        System.out.println("            用法: workflow <step...>");
        System.out.println("  run     执行 pyspider 风格的内联 URL 任务");
        System.out.println("          用法: run <url> [--runtime <http|browser|media|ai>] [--output <path>]");
        System.out.println("  job     执行统一 JobSpec JSON");
        System.out.println("          用法: job --file <job.json>");
        System.out.println("  async-job 执行统一 JobSpec JSON 的异步兼容入口");
        System.out.println("            用法: async-job --file <job.json>");
        System.out.println("  capabilities 输出框架能力清单");
        System.out.println("  media   委托给媒体下载 CLI");
        System.out.println("  version 显示版本");
        System.out.println("  help    显示帮助");
    }

    private static void handleConfig(String[] args) {
        if (args.length == 0 || !"init".equals(args[0])) {
            System.out.println("用法: config init [--output <path>]");
            return;
        }
        String output = extractOption(slice(args, 1), "--output");
        if (output == null || output.isBlank()) {
            output = "spider-framework.yaml";
        }
        try {
            writeContractConfig(Paths.get(output), "java");
            System.out.println("Wrote shared config: " + output);
        } catch (IOException e) {
            throw new RuntimeException("写入共享配置失败", e);
        }
    }

    private static void handleCrawl(String[] args) {
        Map<String, Object> cfg = loadContractConfig(extractOption(args, "--config"));
        String url = extractOption(args, "--url", "-u");
        if ((url == null || url.isBlank()) && args.length > 0) {
            url = args[0];
        }
        if ((url == null || url.isBlank())) {
            url = firstConfiguredUrl(cfg);
        }

        if (url == null || url.isBlank()) {
            System.out.println("错误: crawl 需要 URL");
            System.out.println("用法: crawl <url> 或 crawl --url <url>");
            return;
        }

        QuickSpider processor = new QuickSpider();
        Map<String, Object> browser = nestedMap(cfg, "browser");
        Map<String, Object> antiBot = nestedMap(cfg, "anti_bot");
        Map<String, Object> nodeReverse = nestedMap(cfg, "node_reverse");

        AntiBotHandler antiBotHandler = new AntiBotHandler();
        String profile = stringValue(antiBot.get("profile"), "default").toLowerCase();
        String userAgent = stringValue(browser.get("user_agent"), "");
        Map<String, String> headers = new LinkedHashMap<>();
        if (Boolean.TRUE.equals(antiBot.get("enabled"))) {
            switch (profile) {
                case "cloudflare" -> headers.putAll(antiBotHandler.createCloudflareBypass().getHeaders());
                case "akamai" -> headers.putAll(antiBotHandler.createAkamaiBypass().getHeaders());
                default -> headers.putAll(antiBotHandler.getRandomHeaders());
            }
        }
        if (userAgent.isBlank()) {
            userAgent = headers.getOrDefault("User-Agent", processor.getSite().getUserAgent());
        }

        processor.getSite().setUserAgent(userAgent);
        processor.getSite().setHeaders(headers);
        processor.getSite().setBypassCloudflare("cloudflare".equals(profile));
        processor.getSite().setBypassAkamai("akamai".equals(profile));
        processor.getSite().setSolveCaptcha(Boolean.TRUE.equals(antiBot.get("enabled")));

        String proxyPool = stringValue(antiBot.get("proxy_pool"), "");
        if (!proxyPool.isBlank() && !"local".equals(proxyPool)) {
            String firstProxy = proxyPool.split(",")[0].trim();
            if (!firstProxy.isBlank()) {
                try {
                    java.net.URI proxyUri = java.net.URI.create(firstProxy);
                    processor.getSite().setProxyHost(proxyUri.getHost());
                    processor.getSite().setProxyPort(proxyUri.getPort());
                    processor.getSite().setRotateProxy(true);
                } catch (Exception ignored) {
                }
            }
        }

        HttpClientDownloader downloader = new HttpClientDownloader();
        int delayMs = Math.max(
            integerValue(nestedMap(cfg, "middleware").get("min_request_interval_ms"), 0),
            boolValue(nestedMap(cfg, "auto_throttle").get("enabled"), false)
                ? integerValue(nestedMap(cfg, "auto_throttle").get("start_delay_ms"), 0)
                : 0
        );
        processor.getSite().downloadDelay(delayMs);

        List<String> targets = new ArrayList<>();
        targets.add(url);
        Map<String, Object> sitemap = nestedMap(cfg, "sitemap");
        if (boolValue(sitemap.get("enabled"), false)) {
            try {
                targets = mergeUniqueTargets(targets, discoverSitemapTargets(url, sitemap));
            } catch (IOException exception) {
                System.out.println("警告: 站点地图发现失败，将继续抓取原始 URL: " + exception.getMessage());
            }
        }

        try {
            for (String target : targets) {
                Request request = new Request(target);
                request.headers(headers).userAgent(userAgent);
                Page page = downloader.download(request, processor.getSite());
                if (page == null) {
                    System.out.println("页面下载失败：返回为空");
                    continue;
                }
                if (Boolean.TRUE.equals(nodeReverse.get("enabled"))) {
                    String baseUrl = stringValue(nodeReverse.get("base_url"), "http://localhost:3000");
                    NodeReverseClient reverseClient = new NodeReverseClient(baseUrl);
                    JsonNode profilePayload = reverseClient.profileAntiBot(
                        page.getRawText() != null ? page.getRawText() : "",
                        "",
                        Map.of(),
                        "",
                        page.getStatusCode(),
                        target
                    );
                    if (profilePayload.path("success").asBoolean(false)) {
                        System.out.println(
                            "anti-bot: level=" + profilePayload.path("level").asText("")
                                + " signals=" + profilePayload.path("signals").toString()
                        );
                    }
                }
                processor.process(page);
            }
        } catch (Exception e) {
            throw new RuntimeException("crawl failed", e);
        }
    }

    private static void handleBrowser(String[] args) {
        if (args.length == 0) {
            System.out.println("用法: browser <fetch|trace|mock|codegen> ...");
            return;
        }

        if ("trace".equals(args[0]) || "mock".equals(args[0]) || "codegen".equals(args[0])) {
            handleBrowserTooling(args[0], slice(args, 1));
            return;
        }
        if (!"fetch".equals(args[0])) {
            System.out.println("用法: browser <fetch|trace|mock|codegen> ...");
            return;
        }

        String[] rest = slice(args, 1);
        Map<String, Object> cfg = loadContractConfig(extractOption(rest, "--config"));
        String url = extractOption(rest, "--url", "-u");
        if ((url == null || url.isBlank()) && rest.length > 0) {
            url = rest[0];
        }
        if (url == null || url.isBlank()) {
            url = firstConfiguredUrl(cfg);
        }
        if (url == null || url.isBlank()) {
            System.out.println("browser fetch 需要 URL 或配置中的 crawl.urls");
            return;
        }

        String screenshot = extractOption(rest, "--screenshot");
        if (screenshot == null || screenshot.isBlank()) {
            screenshot = stringValue(nestedMap(cfg, "browser").get("screenshot_path"), "artifacts/browser/page.png");
        }
        String htmlPath = extractOption(rest, "--html");
        if (htmlPath == null || htmlPath.isBlank()) {
            htmlPath = stringValue(nestedMap(cfg, "browser").get("html_path"), "artifacts/browser/page.html");
        }

        BrowserFetchRunner browser = browserFetchRunnerFactory.get();
        try {
            BrowserFetchResult result = browser.fetch(url, screenshot, htmlPath, cfg);
            System.out.println("title: " + result.title);
            System.out.println("url: " + result.url);
        } catch (IOException e) {
            throw new RuntimeException("保存浏览器输出失败", e);
        } finally {
            browser.close();
        }
    }

    private static void handleBrowserTooling(String tooling, String[] args) {
        String url = stringValue(extractOption(args, "--url"), "");
        String tracePath = stringValue(extractOption(args, "--trace-path"), "");
        String harPath = stringValue(extractOption(args, "--har-path"), "");
        String routeManifest = stringValue(extractOption(args, "--route-manifest"), "");
        String htmlPath = stringValue(extractOption(args, "--html"), "");
        String screenshot = stringValue(extractOption(args, "--screenshot"), "");
        String output = stringValue(extractOption(args, "--output"), "");
        String language = stringValue(extractOption(args, "--language"), "python");

        if (url.isBlank()) {
            System.out.println("browser " + tooling + " 需要 --url");
            return;
        }
        if ("trace".equals(tooling) && tracePath.isBlank()) {
            System.out.println("browser trace 需要 --trace-path");
            return;
        }
        if ("mock".equals(tooling) && routeManifest.isBlank()) {
            System.out.println("browser mock 需要 --route-manifest");
            return;
        }
        if ("codegen".equals(tooling) && output.isBlank()) {
            System.out.println("browser codegen 需要 --output");
            return;
        }

        List<String> toolArgs = new ArrayList<>(List.of("--tooling-command", tooling, "--url", url));
        if (!tracePath.isBlank()) {
            toolArgs.add("--trace-path");
            toolArgs.add(tracePath);
        }
        if (!harPath.isBlank()) {
            toolArgs.add("--har-path");
            toolArgs.add(harPath);
        }
        if (!routeManifest.isBlank()) {
            toolArgs.add("--route-manifest");
            toolArgs.add(routeManifest);
        }
        if (!htmlPath.isBlank()) {
            toolArgs.add("--html");
            toolArgs.add(htmlPath);
        }
        if (!screenshot.isBlank()) {
            toolArgs.add("--screenshot");
            toolArgs.add(screenshot);
        }
        if (!output.isBlank()) {
            toolArgs.add("--codegen-out");
            toolArgs.add(output);
        }
        if (!language.isBlank()) {
            toolArgs.add("--codegen-language");
            toolArgs.add(language);
        }

        int exitCode = runSharedPythonTool("playwright_fetch.py", toolArgs);
        if (exitCode != 0) {
            throw new RuntimeException("browser " + tooling + " failed with exit code " + exitCode);
        }
    }

    private static void handleJobdir(String[] args) {
        if (args.length == 0) {
            System.out.println("用法: jobdir <init|status|pause|resume|clear> --path <path>");
            return;
        }
        String subcommand = args[0];
        if (!List.of("init", "status", "pause", "resume", "clear").contains(subcommand)) {
            System.out.println("用法: jobdir <init|status|pause|resume|clear> --path <path>");
            return;
        }

        String[] rest = slice(args, 1);
        String path = stringValue(extractOption(rest, "--path"), "");
        if (path.isBlank()) {
            System.out.println("jobdir 需要 --path");
            return;
        }

        List<String> toolArgs = new ArrayList<>(List.of(subcommand, "--path", path));
        if ("init".equals(subcommand)) {
            toolArgs.add("--runtime");
            toolArgs.add(stringValue(extractOption(rest, "--runtime"), "java"));
            for (String url : extractOptions(rest, "--url")) {
                toolArgs.add("--url");
                toolArgs.add(url);
            }
        }
        int exitCode = runSharedPythonTool("jobdir_tool.py", toolArgs);
        if (exitCode != 0) {
            throw new RuntimeException("jobdir command failed with exit code " + exitCode);
        }
    }

    private static void handleHttpCache(String[] args) {
        if (args.length == 0) {
            System.out.println("用法: http-cache <status|clear|seed> --path <path>");
            return;
        }
        String subcommand = args[0];
        if (!List.of("status", "clear", "seed").contains(subcommand)) {
            System.out.println("用法: http-cache <status|clear|seed> --path <path>");
            return;
        }

        String[] rest = slice(args, 1);
        String path = stringValue(extractOption(rest, "--path"), "");
        if (path.isBlank()) {
            System.out.println("http-cache 需要 --path");
            return;
        }

        List<String> toolArgs = new ArrayList<>(List.of(subcommand, "--path", path));
        if ("seed".equals(subcommand)) {
            String url = stringValue(extractOption(rest, "--url"), "");
            if (url.isBlank()) {
                System.out.println("http-cache seed 需要 --url");
                return;
            }
            toolArgs.add("--url");
            toolArgs.add(url);
            toolArgs.add("--status-code");
            toolArgs.add(stringValue(extractOption(rest, "--status-code"), "200"));
            String etag = stringValue(extractOption(rest, "--etag"), "");
            String lastModified = stringValue(extractOption(rest, "--last-modified"), "");
            String contentHash = stringValue(extractOption(rest, "--content-hash"), "");
            if (!etag.isBlank()) {
                toolArgs.add("--etag");
                toolArgs.add(etag);
            }
            if (!lastModified.isBlank()) {
                toolArgs.add("--last-modified");
                toolArgs.add(lastModified);
            }
            if (!contentHash.isBlank()) {
                toolArgs.add("--content-hash");
                toolArgs.add(contentHash);
            }
        }
        int exitCode = runSharedPythonTool("http_cache_tool.py", toolArgs);
        if (exitCode != 0) {
            throw new RuntimeException("http-cache command failed with exit code " + exitCode);
        }
    }

    private static void handleConsole(String[] args) {
        handleConsoleTool(args, "console", "runtime_console.py");
    }

    private static void handleAudit(String[] args) {
        handleConsoleTool(args, "audit", "audit_console.py");
    }

    private static void handleConsoleTool(String[] args, String commandName, String scriptName) {
        if (args.length == 0) {
            System.out.println("用法: " + commandName + " <snapshot|tail> --control-plane <dir>");
            return;
        }
        String subcommand = args[0];
        if (!List.of("snapshot", "tail").contains(subcommand)) {
            System.out.println("用法: " + commandName + " <snapshot|tail> --control-plane <dir>");
            return;
        }

        String[] rest = slice(args, 1);
        String controlPlane = stringValue(extractOption(rest, "--control-plane"), "artifacts/control-plane");
        String lines = stringValue(extractOption(rest, "--lines"), "20");
        List<String> toolArgs = new ArrayList<>(List.of(subcommand, "--control-plane", controlPlane, "--lines", lines));
        if ("console".equals(commandName) && "snapshot".equals(subcommand)) {
            String jobdir = stringValue(extractOption(rest, "--jobdir"), "");
            if (!jobdir.isBlank()) {
                toolArgs.add("--jobdir");
                toolArgs.add(jobdir);
            }
        }
        if ("tail".equals(subcommand)) {
            toolArgs.add("--stream");
            toolArgs.add(
                stringValue(
                    extractOption(rest, "--stream"),
                    "console".equals(commandName) ? "both" : "all"
                )
            );
        }
        if ("audit".equals(commandName)) {
            toolArgs.add("--job-name");
            toolArgs.add(stringValue(extractOption(rest, "--job-name"), ""));
        }

        int exitCode = runSharedPythonTool(scriptName, toolArgs);
        if (exitCode != 0) {
            throw new RuntimeException(commandName + " command failed with exit code " + exitCode);
        }
    }

    private static void handleAI(String[] args) {
        Map<String, Object> cfg = loadContractConfig(extractOption(args, "--config"));
        String explicitUrl = stringValue(extractOption(args, "--url"), "");
        String htmlFile = stringValue(extractOption(args, "--html-file"), "");
        String instructions = stringValue(extractOption(args, "--instructions"), "");
        String schemaFile = stringValue(extractOption(args, "--schema-file"), "");
        String schemaJson = stringValue(extractOption(args, "--schema-json"), "");
        String question = stringValue(extractOption(args, "--question"), "");
        String description = stringValue(extractOption(args, "--description"), "");
        String output = stringValue(extractOption(args, "--output"), "");

        String mode = detectAIMode(instructions, question, description, schemaFile, schemaJson);
        List<String> warnings = new ArrayList<>();
        String engine = "heuristic-fallback";
        String source = "description";
        String resolvedUrl = "";
        Object result;

        if ("generate-config".equals(mode)) {
            result = heuristicAIGenerateConfig(description);
            try {
                result = AIExtractor.fromEnv().generateSpiderConfig(description);
                engine = "llm";
            } catch (Exception e) {
                warnings.add(stringValue(e.getMessage(), "AI_API_KEY / OPENAI_API_KEY 未设置，已回退到启发式模式"));
            }
        } else {
            String targetUrl = explicitUrl.isBlank() ? firstConfiguredUrl(cfg) : explicitUrl;
            String html;
            try {
                html = loadHtmlInput(targetUrl, htmlFile);
            } catch (IOException e) {
                throw new RuntimeException("读取 AI 输入失败", e);
            }
            if (html == null || html.isBlank()) {
                System.out.println("ai 需要 --url、--html-file 或配置中的 crawl.urls");
                return;
            }
            if (!htmlFile.isBlank()) {
                source = "html-file";
                resolvedUrl = !targetUrl.isBlank()
                    ? targetUrl
                    : Path.of(htmlFile).toAbsolutePath().normalize().toUri().toString();
            } else {
                source = explicitUrl.isBlank() ? "config" : "url";
                resolvedUrl = targetUrl;
            }

            if ("extract".equals(mode)) {
                Map<String, Object> schema = loadAISchema(schemaFile, schemaJson);
                String instructionText = instructions.isBlank() ? "提取页面中的核心结构化字段" : instructions;
                result = heuristicAIExtract(resolvedUrl, html, schema);
                try {
                    result = AIExtractor.fromEnv().extractStructured(
                        truncateAIContent(html, 12000),
                        instructionText,
                        schema
                    );
                    engine = "llm";
                } catch (Exception e) {
                    warnings.add(stringValue(e.getMessage(), "AI_API_KEY / OPENAI_API_KEY 未设置，已回退到启发式模式"));
                }
            } else {
                @SuppressWarnings("unchecked")
                Map<String, Object> fallback = (Map<String, Object>) heuristicAIUnderstand(resolvedUrl, html, question);
                result = fallback;
                try {
                    String answer = AIExtractor.fromEnv().understandPage(
                        truncateAIContent(html, 12000),
                        question.isBlank() ? "请总结页面类型、核心内容和推荐提取字段。" : question
                    );
                    Map<String, Object> llmPayload = new LinkedHashMap<>();
                    llmPayload.put("answer", answer);
                    llmPayload.put("page_profile", fallback.get("page_profile"));
                    result = llmPayload;
                    engine = "llm";
                } catch (Exception e) {
                    warnings.add(stringValue(e.getMessage(), "AI_API_KEY / OPENAI_API_KEY 未设置，已回退到启发式模式"));
                }
            }
        }

        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("command", "ai");
        payload.put("runtime", "java");
        payload.put("mode", mode);
        payload.put("summary", "passed");
        payload.put("summary_text", mode + " mode completed with engine " + engine);
        payload.put("exit_code", 0);
        payload.put("engine", engine);
        payload.put("source", source);
        payload.put("warnings", warnings);
        payload.put("result", result);
        if (!resolvedUrl.isBlank()) {
            payload.put("url", resolvedUrl);
        }

        try {
            String encoded = new ObjectMapper().writerWithDefaultPrettyPrinter().writeValueAsString(payload);
            if (!output.isBlank()) {
                Path outputPath = Paths.get(output);
                if (outputPath.getParent() != null) {
                    Files.createDirectories(outputPath.getParent());
                }
                Files.writeString(outputPath, encoded, StandardCharsets.UTF_8);
            }
            System.out.println(encoded);
        } catch (IOException e) {
            throw new RuntimeException("输出 AI 结果失败", e);
        }
    }

    private static void handleDoctor(String[] args) {
        handleDoctor(args, "doctor");
    }

    private static void handleDoctor(String[] args, String commandName) {
        Map<String, Object> cfg = loadContractConfig(extractOption(args, "--config"));
        boolean json = contains(args, "--json");
        String javaVersion = System.getProperty("java.version", "unknown");
        String osName = System.getProperty("os.name", "unknown");
        String workingDir = Path.of("").toAbsolutePath().normalize().toString();
        String tempDir = System.getProperty("java.io.tmpdir", "");
        boolean tempWritable = isWritableDirectory(Path.of(tempDir));
        Map<String, Object> storage = nestedMap(cfg, "storage");
        Map<String, Object> doctor = nestedMap(cfg, "doctor");
        boolean checkpointsWritable = isWritableDirectory(Paths.get(stringValue(storage.get("checkpoint_dir"), "artifacts/checkpoints")));
        boolean datasetsWritable = isWritableDirectory(Paths.get(stringValue(storage.get("dataset_dir"), "artifacts/datasets")));
        boolean exportsWritable = isWritableDirectory(Paths.get(stringValue(storage.get("export_dir"), "artifacts/exports")));
        List<Map<String, Object>> checks = new ArrayList<>(List.of(
            doctorCheck("temp_directory", tempWritable, tempDir),
            doctorCheck("artifacts/checkpoints", checkpointsWritable, stringValue(storage.get("checkpoint_dir"), "artifacts/checkpoints")),
            doctorCheck("artifacts/datasets", datasetsWritable, stringValue(storage.get("dataset_dir"), "artifacts/datasets")),
            doctorCheck("artifacts/exports", exportsWritable, stringValue(storage.get("export_dir"), "artifacts/exports"))
        ));
        List<String> networkTargets = stringListValue(doctor.get("network_targets"));
        if (networkTargets.isEmpty()) {
            checks.add(doctorCheck("network_targets", "skipped", "not configured"));
        } else {
            for (String target : networkTargets) {
                checks.add(checkNetworkTarget(target));
            }
        }
        String redisUrl = stringValue(doctor.get("redis_url"), "");
        if (redisUrl.isBlank()) {
            checks.add(doctorCheck("redis", "skipped", "not configured"));
        } else {
            checks.add(checkRedisTarget(redisUrl));
        }
        String ffmpegPath = FFmpegUtil.findFFmpeg();
        if (ffmpegPath == null || ffmpegPath.isBlank()) {
            checks.add(doctorCheck("ffmpeg", "warning", "not found; media conversion may be unavailable"));
        } else {
            checks.add(doctorCheck("ffmpeg", "passed", ffmpegPath));
        }
        String browserBinary = detectBrowserBinary();
        if (browserBinary.isBlank()) {
            checks.add(doctorCheck("browser", "warning", "no Chrome/Edge/chromedriver found"));
        } else {
            checks.add(doctorCheck("browser", "passed", browserBinary));
        }
        boolean passed = checks.stream().noneMatch(check -> "failed".equals(check.get("status")));

        if (json) {
            Map<String, Object> payload = new LinkedHashMap<>();
            payload.put("command", commandName);
            payload.put("framework", "javaspider");
            payload.put("runtime", "java");
            payload.put("version", VERSION);
            payload.put("summary", passed ? "passed" : "failed");
            payload.put("summary_text", doctorSummaryText(checks));
            payload.put("exit_code", passed ? 0 : 1);
            payload.put("java_version", javaVersion);
            payload.put("os", osName);
            payload.put("working_directory", workingDir);
            payload.put("temp_directory", tempDir);
            payload.put("shared_contracts", List.of(
                "shared-cli",
                "shared-config",
                "scrapy-project",
                "scrapy-plugins-manifest",
                "web-control-plane"
            ));
            payload.put("checks", checks);
            try {
                System.out.println(new ObjectMapper().writerWithDefaultPrettyPrinter().writeValueAsString(payload));
            } catch (IOException e) {
                throw new RuntimeException("输出 doctor JSON 失败", e);
            }
            return;
        }

        System.out.println("========== JavaSpider " + commandName + " ==========");
        System.out.println("Java: " + javaVersion);
        System.out.println("OS: " + osName);
        System.out.println("Working directory: " + workingDir);
        System.out.println("Temp directory: " + tempDir);
        System.out.println("Temp writable: " + (tempWritable ? "yes" : "no"));
        System.out.println("Checkpoints writable: " + (checkpointsWritable ? "yes" : "no"));
        System.out.println("Datasets writable: " + (datasetsWritable ? "yes" : "no"));
        System.out.println("Exports writable: " + (exportsWritable ? "yes" : "no"));
        for (Map<String, Object> check : checks) {
            String status = stringValue(check.get("status"), "failed");
            String prefix = switch (status) {
                case "passed" -> "[OK]";
                case "warning" -> "[WARN]";
                case "skipped" -> "[SKIP]";
                default -> "[FAIL]";
            };
            System.out.println(prefix + " " + check.get("name") + ": " + check.get("details"));
        }
    }

    private static void handleExport(String[] args) {
        String input = extractOption(args, "--input");
        String format = extractOption(args, "--format");
        String output = extractOption(args, "--output");
        if (input == null || output == null) {
            System.out.println("用法: export --input <path> --format <json|jsonl|csv|md> --output <path>");
            return;
        }

        try {
            ObjectMapper mapper = new ObjectMapper();
            String raw = Files.readString(Paths.get(input));
            List<Map<String, String>> items;
            if (raw.trim().startsWith("{")) {
                Map<String, Object> envelope = mapper.readValue(raw, new TypeReference<Map<String, Object>>() {});
                Object data = envelope.get("items");
                if (data == null) {
                    data = envelope.get("data");
                }
                items = mapper.convertValue(data, new TypeReference<List<Map<String, String>>>() {});
            } else {
                items = mapper.readValue(raw, new TypeReference<List<Map<String, String>>>() {});
            }
            Path outputPath = Paths.get(output);
            Path outputDir = outputPath.getParent() != null ? outputPath.getParent() : Paths.get(".");
            Exporter exporter = new Exporter(outputDir.toString());
            String filename = outputPath.getFileName().toString();
            if ("jsonl".equals(format)) {
                exporter.exportJSONL(items, filename);
            } else if ("csv".equals(format)) {
                exporter.exportCSV(items, filename);
            } else if ("md".equals(format)) {
                exporter.exportMD(items, filename);
            } else {
                exporter.exportJSON(items, filename);
            }
            System.out.println("exported: " + output);
        } catch (IOException e) {
            throw new RuntimeException("导出失败", e);
        }
    }

    private static void handleCurl(String[] args) {
        if (args.length == 0 || !"convert".equals(args[0])) {
            System.out.println("用法: curl convert --command <curl> [--target <java|http|okhttp|apache>]");
            return;
        }

        String[] rest = slice(args, 1);
        String curlCommand = stringValue(extractOption(rest, "--command", "-c"), "");
        if (curlCommand.isBlank() && rest.length > 0) {
            List<String> trailing = new ArrayList<>();
            for (int i = 0; i < rest.length; i++) {
                String token = rest[i];
                if ("--target".equals(token) || "--command".equals(token) || "-c".equals(token)) {
                    i += 1;
                    continue;
                }
                trailing.add(token);
            }
            curlCommand = String.join(" ", trailing).trim();
        }
        if (curlCommand.isBlank()) {
            System.out.println("curl convert 需要 --command 或直接追加 curl 命令");
            return;
        }

        String requestedTarget = stringValue(extractOption(rest, "--target"), "http");
        String target = requestedTarget.toLowerCase();
        CurlToJavaConverter converter = new CurlToJavaConverter();
        String code;
        switch (target) {
            case "java" -> {
                code = CurlToJavaConverter.curlToJava(curlCommand);
                if (code.startsWith("// 转换失败")) {
                    target = "http";
                    code = converter.convertToHttpURLConnection(curlCommand);
                }
            }
            case "http", "http-url-connection", "httpurlconnection" ->
                code = converter.convertToHttpURLConnection(curlCommand);
            case "okhttp" -> code = converter.convertToOkHttp(curlCommand);
            case "apache", "apache-httpclient", "apachehttpclient" -> {
                target = "apache";
                code = converter.convertToApacheHttpClient(curlCommand);
            }
            default -> {
                System.out.println("不支持的 target: " + requestedTarget);
                System.out.println("可选值: java, http, okhttp, apache");
                return;
            }
        }

        try {
            Map<String, Object> payload = new LinkedHashMap<>();
            payload.put("command", "curl convert");
            payload.put("runtime", "java");
            payload.put("target", target);
            payload.put("curl", curlCommand);
            payload.put("code", code);
            System.out.println(new ObjectMapper().writerWithDefaultPrettyPrinter().writeValueAsString(payload));
        } catch (IOException e) {
            throw new RuntimeException("渲染 curl 转换结果失败", e);
        }
    }

    private static void handleNodeReverse(String[] args) {
        if (args.length == 0) {
            System.out.println("用法: node-reverse <health|profile|detect|fingerprint-spoof|tls-fingerprint|canvas-fingerprint|analyze-crypto|signature-reverse|ast|webpack|function-call|browser-simulate> [options]");
            return;
        }
        String subcommand = args[0];
        String[] rest = slice(args, 1);
        String baseUrl = stringValue(extractOption(rest, "--base-url"), "http://localhost:3000");
        NodeReverseClient client = new NodeReverseClient(baseUrl);

        try {
            switch (subcommand) {
                case "health" -> {
                    Map<String, Object> payload = new LinkedHashMap<>();
                    payload.put("command", "node-reverse health");
                    payload.put("runtime", "java");
                    payload.put("base_url", baseUrl);
                    payload.put("healthy", client.healthCheck());
                    System.out.println(new ObjectMapper().writerWithDefaultPrettyPrinter().writeValueAsString(payload));
                }
                case "profile" -> {
                    String url = stringValue(extractOption(rest, "--url"), "");
                    String htmlFile = stringValue(extractOption(rest, "--html-file"), "");
                    String html = loadHtmlInput(url, htmlFile);
                    if (html.isBlank()) {
                        throw new IllegalArgumentException("node-reverse profile 需要 --url 或 --html-file");
                    }
                    Integer statusCode = parseIntegerOption(extractOption(rest, "--status-code"));
                    JsonNode payload = client.profileAntiBot(html, "", Map.of(), "", statusCode, url);
                    System.out.println(new ObjectMapper().writerWithDefaultPrettyPrinter().writeValueAsString(payload));
                }
                case "detect" -> {
                    String url = stringValue(extractOption(rest, "--url"), "");
                    String htmlFile = stringValue(extractOption(rest, "--html-file"), "");
                    String html = loadHtmlInput(url, htmlFile);
                    if (html.isBlank()) {
                        throw new IllegalArgumentException("node-reverse detect 需要 --url 或 --html-file");
                    }
                    Integer statusCode = parseIntegerOption(extractOption(rest, "--status-code"));
                    JsonNode payload = client.detectAntiBot(html, "", Map.of(), "", statusCode, url);
                    System.out.println(new ObjectMapper().writerWithDefaultPrettyPrinter().writeValueAsString(payload));
                }
                case "fingerprint-spoof" -> {
                    String browser = stringValue(extractOption(rest, "--browser"), "chrome");
                    String platform = stringValue(extractOption(rest, "--platform"), "windows");
                    JsonNode payload = client.spoofFingerprint(browser, platform);
                    System.out.println(new ObjectMapper().writerWithDefaultPrettyPrinter().writeValueAsString(payload));
                }
                case "tls-fingerprint" -> {
                    String browser = stringValue(extractOption(rest, "--browser"), "chrome");
                    String version = stringValue(extractOption(rest, "--version"), "120");
                    JsonNode payload = client.generateTlsFingerprint(browser, version);
                    System.out.println(new ObjectMapper().writerWithDefaultPrettyPrinter().writeValueAsString(payload));
                }
                case "canvas-fingerprint" -> {
                    JsonNode payload = client.canvasFingerprint();
                    System.out.println(new ObjectMapper().writerWithDefaultPrettyPrinter().writeValueAsString(payload));
                }
                case "analyze-crypto" -> {
                    String codeFile = stringValue(extractOption(rest, "--code-file"), "");
                    if (codeFile.isBlank()) {
                        throw new IllegalArgumentException("node-reverse analyze-crypto 需要 --code-file");
                    }
                    String code = Files.readString(Paths.get(codeFile));
                    JsonNode payload = client.analyzeCrypto(code);
                    System.out.println(new ObjectMapper().writerWithDefaultPrettyPrinter().writeValueAsString(payload));
                }
                case "signature-reverse" -> {
                    String codeFile = stringValue(extractOption(rest, "--code-file"), "");
                    String inputData = stringValue(extractOption(rest, "--input-data"), "");
                    String expectedOutput = stringValue(extractOption(rest, "--expected-output"), "");
                    if (codeFile.isBlank() || inputData.isBlank() || expectedOutput.isBlank()) {
                        throw new IllegalArgumentException("node-reverse signature-reverse 需要 --code-file、--input-data 和 --expected-output");
                    }
                    String code = Files.readString(Paths.get(codeFile));
                    JsonNode payload = client.reverseSignature(code, inputData, expectedOutput);
                    System.out.println(new ObjectMapper().writerWithDefaultPrettyPrinter().writeValueAsString(payload));
                }
                case "ast" -> {
                    String codeFile = stringValue(extractOption(rest, "--code-file"), "");
                    if (codeFile.isBlank()) {
                        throw new IllegalArgumentException("node-reverse ast 需要 --code-file");
                    }
                    String analysis = stringValue(extractOption(rest, "--analysis"), "crypto,obfuscation,anti-debug");
                    List<String> analysisTypes = java.util.Arrays.stream(analysis.split(","))
                        .map(String::trim)
                        .filter(value -> !value.isBlank())
                        .toList();
                    String code = Files.readString(Paths.get(codeFile));
                    JsonNode payload = client.analyzeAST(code, analysisTypes);
                    System.out.println(new ObjectMapper().writerWithDefaultPrettyPrinter().writeValueAsString(payload));
                }
                case "webpack" -> {
                    String codeFile = stringValue(extractOption(rest, "--code-file"), "");
                    if (codeFile.isBlank()) {
                        throw new IllegalArgumentException("node-reverse webpack 需要 --code-file");
                    }
                    String code = Files.readString(Paths.get(codeFile));
                    JsonNode payload = client.analyzeWebpack(code);
                    System.out.println(new ObjectMapper().writerWithDefaultPrettyPrinter().writeValueAsString(payload));
                }
                case "function-call" -> {
                    String codeFile = stringValue(extractOption(rest, "--code-file"), "");
                    String functionName = stringValue(extractOption(rest, "--function-name"), "");
                    if (codeFile.isBlank() || functionName.isBlank()) {
                        throw new IllegalArgumentException("node-reverse function-call 需要 --code-file 和 --function-name");
                    }
                    String code = Files.readString(Paths.get(codeFile));
                    JsonNode payload = client.callFunction(functionName, new ArrayList<>(extractOptions(rest, "--arg")), code);
                    System.out.println(new ObjectMapper().writerWithDefaultPrettyPrinter().writeValueAsString(payload));
                }
                case "browser-simulate" -> {
                    String codeFile = stringValue(extractOption(rest, "--code-file"), "");
                    if (codeFile.isBlank()) {
                        throw new IllegalArgumentException("node-reverse browser-simulate 需要 --code-file");
                    }
                    String code = Files.readString(Paths.get(codeFile));
                    JsonNode payload = client.simulateBrowser(
                        code,
                        Map.of(
                            "userAgent", stringValue(extractOption(rest, "--user-agent"), "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"),
                            "language", stringValue(extractOption(rest, "--language"), "zh-CN"),
                            "platform", stringValue(extractOption(rest, "--platform"), "Win32")
                        )
                    );
                    System.out.println(new ObjectMapper().writerWithDefaultPrettyPrinter().writeValueAsString(payload));
                }
                default -> throw new IllegalArgumentException("未知 node-reverse 子命令: " + subcommand);
            }
        } catch (IOException e) {
            throw new RuntimeException("node-reverse 调用失败", e);
        }
    }

    private static void handleAntiBot(String[] args) {
        if (args.length == 0) {
            System.out.println("用法: anti-bot <headers|profile> [options]");
            return;
        }
        String subcommand = args[0];
        String[] rest = slice(args, 1);
        AntiBotHandler handler = new AntiBotHandler();

        try {
            switch (subcommand) {
                case "headers" -> {
                    String profile = stringValue(extractOption(rest, "--profile"), "default");
                    Map<String, String> headers = switch (profile) {
                        case "cloudflare" -> handler.createCloudflareBypass().getHeaders();
                        case "akamai" -> handler.createAkamaiBypass().getHeaders();
                        default -> handler.getRandomHeaders();
                    };
                    Map<String, Object> payload = new LinkedHashMap<>();
                    payload.put("command", "anti-bot headers");
                    payload.put("runtime", "java");
                    payload.put("profile", profile);
                    payload.put("headers", headers);
                    payload.put("fingerprint", handler.generateFingerprint());
                    System.out.println(new ObjectMapper().writerWithDefaultPrettyPrinter().writeValueAsString(payload));
                }
                case "profile" -> {
                    String url = stringValue(extractOption(rest, "--url"), "");
                    String htmlFile = stringValue(extractOption(rest, "--html-file"), "");
                    String html = loadHtmlInput(url, htmlFile);
                    if (html.isBlank()) {
                        throw new IllegalArgumentException("anti-bot profile 需要 --url 或 --html-file");
                    }
                    int statusCode = parseIntegerOption(extractOption(rest, "--status-code")) == null
                        ? 200
                        : parseIntegerOption(extractOption(rest, "--status-code"));
                    boolean blocked = handler.isBlocked(html, statusCode);
                    List<String> signals = localAntiBotSignals(html, statusCode);
                    Map<String, Object> payload = new LinkedHashMap<>();
                    payload.put("command", "anti-bot profile");
                    payload.put("runtime", "java");
                    payload.put("url", url);
                    payload.put("blocked", blocked);
                    payload.put("status_code", statusCode);
                    payload.put("signals", signals);
                    payload.put("level", blocked ? "medium" : "low");
                    payload.put("fingerprint", handler.generateFingerprint());
                    System.out.println(new ObjectMapper().writerWithDefaultPrettyPrinter().writeValueAsString(payload));
                }
                default -> throw new IllegalArgumentException("未知 anti-bot 子命令: " + subcommand);
            }
        } catch (IOException e) {
            throw new RuntimeException("anti-bot 调用失败", e);
        }
    }

    private static void handleProfileSite(String[] args) {
        String url = stringValue(extractOption(args, "--url"), "");
        String htmlFile = stringValue(extractOption(args, "--html-file"), "");
        String baseUrl = stringValue(extractOption(args, "--base-url"), "http://localhost:3000");

        try {
            String html = loadHtmlInput(url, htmlFile);
            if (html.isBlank()) {
                throw new IllegalArgumentException("profile-site 需要 --url 或 --html-file");
            }
            Map<String, Object> payload = localSiteProfilePayload(url, html);
            payload.put("framework", "javaspider");
            payload.put("version", VERSION);
            try {
                NodeReverseClient client = new NodeReverseClient(baseUrl);
                JsonNode detect = client.detectAntiBot(html, "", Map.of(), "", null, url);
                JsonNode profile = client.profileAntiBot(html, "", Map.of(), "", null, url);
                JsonNode spoof = client.spoofFingerprint("chrome", "windows");
                JsonNode tls = client.generateTlsFingerprint("chrome", "120");
                JsonNode canvas = client.canvasFingerprint();
                JsonNode crypto = client.analyzeCrypto(html);
                Map<String, Object> reverse = new LinkedHashMap<>();
                reverse.put("detect", detect);
                reverse.put("profile", profile);
                reverse.put("fingerprint_spoof", spoof);
                reverse.put("tls_fingerprint", tls);
                reverse.put("canvas_fingerprint", canvas);
                reverse.put("crypto_analysis", crypto);
                payload.put("reverse", reverse);
                Map<String, Object> reverseFocus = buildReverseFocus(reverse);
                if (!reverseFocus.isEmpty()) {
                    payload.put("reverse_focus", reverseFocus);
                }
                if (profile.path("success").asBoolean(false)) {
                    payload.put("anti_bot_level", profile.path("level").asText(""));
                    payload.put("anti_bot_signals", profile.path("signals"));
                    payload.put("node_reverse_recommended", profile.path("signals").size() > 0);
                }
            } catch (Exception ignored) {
            }
            System.out.println(new ObjectMapper().writerWithDefaultPrettyPrinter().writeValueAsString(payload));
        } catch (IOException e) {
            throw new RuntimeException("profile-site 调用失败", e);
        }
    }

    private static void handleSitemapDiscover(String[] args) {
        String url = stringValue(extractOption(args, "--url"), "");
        String sitemapFile = stringValue(extractOption(args, "--sitemap-file"), "");
        try {
            String content;
            String source;
            if (!sitemapFile.isBlank()) {
                content = Files.readString(Paths.get(sitemapFile));
                source = sitemapFile;
            } else if (!url.isBlank()) {
                source = url.replaceAll("/+$", "") + "/sitemap.xml";
                content = loadHtmlInput(source, "");
            } else {
                throw new IllegalArgumentException("sitemap-discover 需要 --url 或 --sitemap-file");
            }
            List<String> urls = extractSitemapUrls(content);
            Map<String, Object> payload = new LinkedHashMap<>();
            payload.put("command", "sitemap-discover");
            payload.put("runtime", "java");
            payload.put("source", source);
            payload.put("url_count", urls.size());
            payload.put("urls", urls);
            System.out.println(new ObjectMapper().writerWithDefaultPrettyPrinter().writeValueAsString(payload));
        } catch (IOException e) {
            throw new RuntimeException("sitemap-discover 调用失败", e);
        }
    }

    private static Map<String, Object> buildReverseFocus(Map<String, Object> reverse) {
        Object cryptoRaw = reverse.get("crypto_analysis");
        if (!(cryptoRaw instanceof JsonNode crypto)) {
            return Map.of();
        }
        JsonNode chains = crypto.path("analysis").path("keyFlowChains");
        if (!chains.isArray() || chains.isEmpty()) {
            return Map.of();
        }
        JsonNode top = null;
        double bestConfidence = -1.0;
        int bestSinkCount = -1;
        int bestDerivationCount = -1;
        for (JsonNode chain : chains) {
            double confidence = chain.path("confidence").asDouble(0.0);
            int sinkCount = chain.path("sinks").size();
            int derivationCount = chain.path("derivations").size();
            if (top == null
                || confidence > bestConfidence
                || (confidence == bestConfidence && sinkCount > bestSinkCount)
                || (confidence == bestConfidence && sinkCount == bestSinkCount && derivationCount > bestDerivationCount)) {
                top = chain;
                bestConfidence = confidence;
                bestSinkCount = sinkCount;
                bestDerivationCount = derivationCount;
            }
        }
        if (top == null) {
            return Map.of();
        }
        String sourceKind = top.path("source").path("kind").asText("unknown");
        String primarySink = top.path("sinks").isArray() && top.path("sinks").size() > 0
            ? top.path("sinks").get(0).asText("unknown-sink")
            : "unknown-sink";
        List<String> nextSteps = new ArrayList<>();
        if (sourceKind.startsWith("storage.")) {
            nextSteps.add("instrument browser storage reads first");
        }
        if (sourceKind.startsWith("network.")) {
            nextSteps.add("capture response body before key derivation");
        }
        if (primarySink.contains("crypto.subtle.")) {
            nextSteps.add("hook WebCrypto at the sink boundary");
        }
        if (primarySink.startsWith("jwt.") || crypto.toString().contains("HMAC")) {
            nextSteps.add("rebuild canonical signing input before reproducing the sink");
        }
        if (nextSteps.isEmpty()) {
            nextSteps.add("trace the chain from source through derivations into the first sink");
        }
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("priority_chain", top);
        payload.put(
            "summary",
            "trace `" + top.path("variable").asText("") + "` from `" + sourceKind + "` into `" + primarySink + "`"
        );
        payload.put("next_steps", nextSteps);
        return payload;
    }

    private static void handlePlugins(String[] args) {
        if (args.length == 0) {
            System.out.println("用法: plugins <list|run> ...");
            return;
        }
        if ("run".equals(args[0])) {
            handlePluginsRun(slice(args, 1));
            return;
        }
        if (!"list".equals(args[0])) {
            System.out.println("用法: plugins <list|run> ...");
            return;
        }
        String manifest = stringValue(extractOption(slice(args, 1), "--manifest"), "contracts/integration-catalog.json");
        try {
            Map<String, Object> payload = new ObjectMapper().readValue(
                Files.readString(Paths.get(manifest)),
                new TypeReference<Map<String, Object>>() {}
            );
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("command", "plugins list");
            result.put("runtime", "java");
            result.put("manifest", manifest);
            result.put("plugins", payload.getOrDefault("plugins", payload.get("entrypoints")));
            System.out.println(new ObjectMapper().writerWithDefaultPrettyPrinter().writeValueAsString(result));
        } catch (IOException e) {
            throw new RuntimeException("plugins list 调用失败", e);
        }
    }

    private static void handlePluginsRun(String[] args) {
        String plugin = stringValue(extractOption(args, "--plugin"), "");
        if (plugin.isBlank()) {
            throw new IllegalArgumentException("plugins run 需要 --plugin");
        }
        List<String> passthrough = new ArrayList<>();
        boolean separatorSeen = false;
        for (String arg : args) {
            if (separatorSeen) {
                passthrough.add(arg);
            }
            if ("--".equals(arg)) {
                separatorSeen = true;
            }
        }
        String[] delegated = passthrough.toArray(new String[0]);
        switch (plugin) {
            case "profile-site" -> handleProfileSite(delegated);
            case "sitemap-discover" -> handleSitemapDiscover(delegated);
            case "selector-studio" -> handleSelectorStudio(delegated);
            case "anti-bot" -> handleAntiBot(delegated);
            case "node-reverse" -> handleNodeReverse(delegated);
            default -> throw new IllegalArgumentException("未知 plugin id: " + plugin);
        }
    }

    private static void handleSelectorStudio(String[] args) {
        String url = stringValue(extractOption(args, "--url"), "");
        String htmlFile = stringValue(extractOption(args, "--html-file"), "");
        String mode = stringValue(extractOption(args, "--type"), "css");
        String expr = stringValue(extractOption(args, "--expr"), "");
        String attr = stringValue(extractOption(args, "--attr"), "");
        try {
            String html = loadHtmlInput(url, htmlFile);
            if (html.isBlank()) {
                throw new IllegalArgumentException("selector-studio 需要 --url 或 --html-file");
            }
            HtmlParser parser = new HtmlParser(html);
            List<String> values = switch (mode) {
                case "css" -> parser.css(expr);
                case "css_attr" -> parser.cssAttr(expr, attr);
                case "xpath" -> {
                    String value = parser.xpathFirst(expr);
                    yield value == null ? List.of() : List.of(value);
                }
                case "regex" -> parser.regex(expr);
                default -> List.of();
            };
            Map<String, Object> payload = new LinkedHashMap<>();
            payload.put("command", "selector-studio");
            payload.put("runtime", "java");
            payload.put("framework", "javaspider");
            payload.put("version", VERSION);
            payload.put("source", htmlFile.isBlank() ? url : htmlFile);
            payload.put("type", mode);
            payload.put("expr", expr);
            payload.put("attr", attr);
            payload.put("count", values.size());
            payload.put("values", values);
            payload.put("suggested_xpaths", com.javaspider.selector.SmartXPathSuggester.suggest(mode, expr, attr));
            System.out.println(new ObjectMapper().writerWithDefaultPrettyPrinter().writeValueAsString(payload));
        } catch (IOException e) {
            throw new RuntimeException("selector-studio 调用失败", e);
        }
    }

    private static void handleScrapy(String[] args) {
        if (args.length == 0 || (!"demo".equals(args[0]) && !"run".equals(args[0]) && !"export".equals(args[0]) && !"plan-ai".equals(args[0]) && !"sync-ai".equals(args[0]) && !"auth-validate".equals(args[0]) && !"auth-capture".equals(args[0]) && !"scaffold-ai".equals(args[0]) && !"profile".equals(args[0]) && !"doctor".equals(args[0]) && !"bench".equals(args[0]) && !"init".equals(args[0]) && !"shell".equals(args[0]) && !"list".equals(args[0]) && !"validate".equals(args[0]) && !"genspider".equals(args[0]) && !"contracts".equals(args[0]))) {
            System.out.println("用法: scrapy <demo|run|plan-ai|sync-ai|auth-validate|auth-capture|scaffold-ai|contracts> ...");
            return;
        }
        String subcommand = args[0];

        if ("contracts".equals(subcommand)) {
            if (args.length < 2 || (!"init".equals(args[1]) && !"validate".equals(args[1]))) {
                System.out.println("用法: scrapy contracts <init|validate> --project <dir>");
                return;
            }
            String project = stringValue(extractOption(slice(args, 2), "--project"), "");
            if (project.isBlank()) {
                System.out.println("scrapy contracts 需要 --project");
                return;
            }
            int exitCode = runSharedPythonTool(
                "spider_contracts.py",
                List.of(args[1], "--project", project)
            );
            if (exitCode != 0) {
                throw new RuntimeException("scrapy contracts failed with exit code " + exitCode);
            }
            return;
        }

        String[] rest = slice(args, 1);
        String url = stringValue(extractOption(rest, "--url"), "https://example.com");
        String project = stringValue(extractOption(rest, "--project"), "");
        String selectedSpider = stringValue(extractOption(rest, "--spider"), "");
        String initPath = stringValue(extractOption(rest, "--path"), "");
        String htmlFile = stringValue(extractOption(rest, "--html-file"), "");
        String output = stringValue(extractOption(rest, "--output"), "artifacts/exports/javaspider-scrapy-demo.json");
        String exportFormat = stringValue(extractOption(rest, "--format"), "json");
        String spiderName = stringValue(extractOption(rest, "--name"), "");
        String spiderDomain = stringValue(extractOption(rest, "--domain"), "");
        String sessionName = stringValue(extractOption(rest, "--session"), "auth");
        boolean aiTemplate = contains(rest, "--ai");
        String mode = stringValue(extractOption(rest, "--type"), "css");
        String expr = stringValue(extractOption(rest, "--expr"), "");
        String attr = stringValue(extractOption(rest, "--attr"), "");

        java.util.function.Function<String, Map<String, Object>> readManifest = (projectRoot) -> {
            Path manifestPath = Paths.get(projectRoot).resolve("scrapy-project.json");
            try {
                Map<String, Object> manifest = new ObjectMapper().readValue(
                    Files.readString(manifestPath),
                    new TypeReference<Map<String, Object>>() {}
                );
                if (!"java".equals(stringValue(manifest.get("runtime"), ""))) {
                    throw new IllegalArgumentException("runtime mismatch in " + manifestPath + ": expected 'java'");
                }
                return manifest;
            } catch (IOException e) {
                throw new RuntimeException("读取 scrapy project 失败", e);
            }
        };
        java.util.function.Function<Path, Map<String, String>> parseSpiderMetadata = (path) -> {
            Map<String, String> metadata = new LinkedHashMap<>();
            try {
                for (String line : Files.readAllLines(path).stream().limit(5).toList()) {
                    String trimmed = line.trim();
                    if (!trimmed.startsWith("// scrapy:")) {
                        continue;
                    }
                    String payload = trimmed.substring("// scrapy:".length()).trim();
                    for (String part : payload.split("\\s+")) {
                        if (!part.contains("=")) {
                            continue;
                        }
                        String[] pair = part.split("=", 2);
                        metadata.put(pair[0].trim(), pair[1].trim());
                    }
                }
            } catch (IOException ignored) {
            }
            return metadata;
        };
        java.util.function.BiFunction<String, Map<String, Object>, List<Map<String, Object>>> discoverSpiders = (projectRoot, manifest) -> {
            List<Map<String, Object>> spiders = new ArrayList<>();
            String entry = stringValue(manifest.get("entry"), "");
            if (!entry.isBlank()) {
                Map<String, Object> item = new LinkedHashMap<>();
                item.put("path", entry);
                item.putAll(parseSpiderMetadata.apply(Paths.get(projectRoot).resolve(entry)));
                item.putIfAbsent("name", Paths.get(entry).getFileName().toString().replaceFirst("\\.java$", ""));
                spiders.add(item);
            }
            for (Path spidersDir : List.of(
                Paths.get(projectRoot).resolve("src").resolve("main").resolve("java").resolve("project").resolve("spiders"),
                Paths.get(projectRoot).resolve("spiders")
            )) {
                if (Files.exists(spidersDir)) {
                    try (var stream = Files.list(spidersDir)) {
                        stream.filter(path -> path.toString().endsWith(".java")).forEach(path -> {
                        Map<String, Object> item = new LinkedHashMap<>();
                        item.put("path", Paths.get(projectRoot).relativize(path).toString());
                        item.putAll(parseSpiderMetadata.apply(path));
                        item.putIfAbsent("name", path.getFileName().toString().replaceFirst("\\.java$", ""));
                        spiders.add(item);
                    });
                    } catch (IOException e) {
                        throw new RuntimeException("列出 spider 失败", e);
                    }
                }
            }
            return spiders;
        };
        java.util.function.BiFunction<Map<String, Object>, String, Path> resolveProjectOutput = (manifest, spider) -> {
            String defaultOutput = stringValue(manifest.get("output"), "artifacts/exports/items.json");
            if (!spider.isBlank() && defaultOutput.endsWith("items.json")) {
                return Paths.get(project).resolve("artifacts").resolve("exports").resolve(spider + ".json");
            }
            return Paths.get(project).resolve(defaultOutput);
        };
        java.util.function.BiFunction<String, Map<String, Object>, List<Map<String, Object>>> resolveSpiderDisplay = (projectRoot, manifest) -> {
            List<Map<String, Object>> spiders = discoverSpiders.apply(projectRoot, manifest);
            Path configPath = Paths.get(projectRoot).resolve("spider-framework.yaml");
            Map<String, Object> projectCfg = Files.exists(configPath) ? readContractConfig(configPath) : defaultContractConfig("java");
            for (Map<String, Object> spider : spiders) {
                String name = stringValue(spider.get("name"), "");
                String[] detail = resolveScrapyRunnerDetail(projectCfg, stringValue(spider.get("name"), ""), spider);
                spider.put("runner", detail[0]);
                spider.put("runner_source", detail[1]);
                String[] urlDetail = resolveScrapyUrlDetail(
                    projectCfg,
                    name,
                    spider,
                    stringValue(manifest.get("url"), "")
                );
                spider.put("url", urlDetail[0]);
                spider.put("url_source", urlDetail[1]);
                spider.put("pipelines", configuredScrapyPipelines(projectCfg, name));
                spider.put("spider_middlewares", configuredScrapySpiderMiddlewares(projectCfg, name));
                spider.put("downloader_middlewares", configuredScrapyDownloaderMiddlewares(projectCfg, name));
            }
            return spiders;
        };

        if ("list".equals(subcommand)) {
            if (project.isBlank()) {
                System.out.println("scrapy list 需要 --project");
                return;
            }
            Map<String, Object> manifest = readManifest.apply(project);
            List<Map<String, Object>> spiders = resolveSpiderDisplay.apply(project, manifest);
            Path configPath = Paths.get(project).resolve("spider-framework.yaml");
            Map<String, Object> projectCfg = Files.exists(configPath) ? readContractConfig(configPath) : defaultContractConfig("java");
            List<ProjectRuntime.PluginSpec> pluginSpecs = ProjectRuntime.loadPluginSpecsFromManifest(Paths.get(project));
            if (pluginSpecs.isEmpty()) {
                pluginSpecs = configuredScrapyPluginSpecs(projectCfg);
            }
            try {
                System.out.println(new ObjectMapper().writerWithDefaultPrettyPrinter().writeValueAsString(Map.of(
                    "command", "scrapy list",
                    "runtime", "java",
                    "project", project,
                    "spiders", spiders,
                    "plugins", pluginSpecs.isEmpty() ? ProjectRuntime.pluginNames() : enabledPluginSpecNames(pluginSpecs),
                    "pipelines", configuredScrapyPipelines(projectCfg),
                    "spider_middlewares", configuredScrapySpiderMiddlewares(projectCfg),
                    "downloader_middlewares", configuredScrapyDownloaderMiddlewares(projectCfg)
                )));
            } catch (IOException e) {
                throw new RuntimeException(e);
            }
            return;
        }

        if ("shell".equals(subcommand)) {
            try {
                String html = loadHtmlInput(url, htmlFile);
                if (html.isBlank()) {
                    throw new IllegalArgumentException("scrapy shell 需要 --url 或 --html-file");
                }
                HtmlParser parser = new HtmlParser(html);
                List<String> values = switch (mode) {
                    case "css" -> parser.css(expr);
                    case "css_attr" -> parser.cssAttr(expr, attr);
                    case "xpath" -> {
                        String value = parser.xpathFirst(expr);
                        yield value == null ? List.of() : List.of(value);
                    }
                    case "regex" -> parser.regex(expr);
                    default -> List.of();
                };
                System.out.println(new ObjectMapper().writerWithDefaultPrettyPrinter().writeValueAsString(Map.of(
                    "command", "scrapy shell",
                    "runtime", "java",
                    "source", htmlFile.isBlank() ? url : htmlFile,
                    "type", mode,
                    "expr", expr,
                    "attr", attr,
                    "count", values.size(),
                    "values", values
                )));
            } catch (IOException e) {
                throw new RuntimeException("scrapy shell 调用失败", e);
            }
            return;
        }

        if ("profile".equals(subcommand)) {
            try {
                String source;
                String html;
                String resolvedRunner = "http";
                String runnerSource = "default";
                String urlSource = "default";
                if (!project.isBlank()) {
                    Map<String, Object> manifest = readManifest.apply(project);
                    if (!selectedSpider.isBlank()) {
                        List<Map<String, Object>> spiders = resolveSpiderDisplay.apply(project, manifest);
                        Map<String, Object> match = spiders.stream()
                            .filter(spider -> selectedSpider.equals(String.valueOf(spider.get("name"))))
                            .findFirst()
                            .orElse(null);
                        if (match == null) {
                            throw new IllegalArgumentException("unknown spider in " + project + ": " + selectedSpider);
                        }
                        url = stringValue(match.get("url"), url);
                        resolvedRunner = stringValue(match.get("runner"), "http");
                        runnerSource = stringValue(match.get("runner_source"), "default");
                        urlSource = stringValue(match.get("url_source"), "default");
                    } else if (url.isBlank()) {
                        Map<String, Object> cfg = Files.exists(Paths.get(project).resolve("spider-framework.yaml"))
                            ? readContractConfig(Paths.get(project).resolve("spider-framework.yaml"))
                            : defaultContractConfig("java");
                        String[] resolved = resolveScrapyUrlDetail(cfg, "", Map.of(), stringValue(manifest.get("url"), ""));
                        String[] runner = resolveScrapyRunnerDetail(cfg, "", Map.of());
                        url = resolved[0];
                        urlSource = resolved[1];
                        resolvedRunner = runner[0];
                        runnerSource = runner[1];
                    }
                }

                if (!htmlFile.isBlank()) {
                    source = htmlFile;
                    html = Files.readString(Paths.get(htmlFile));
                } else if (!url.isBlank()) {
                    source = url;
                    html = loadHtmlInput(url, "");
                } else {
                    throw new IllegalArgumentException("scrapy profile 需要 --project、--url 或 --html-file");
                }

                HtmlParser parser = new HtmlParser(html);
                Map<String, Object> payload = new LinkedHashMap<>();
                payload.put("command", "scrapy profile");
                payload.put("runtime", "java");
                payload.put("project", project.isBlank() ? null : project);
                payload.put("spider", selectedSpider.isBlank() ? null : selectedSpider);
                payload.put("source", source);
                payload.put("resolved_runner", resolvedRunner);
                payload.put("runner_source", htmlFile.isBlank() ? runnerSource : "html-fixture");
                payload.put("resolved_url", url);
                payload.put("url_source", htmlFile.isBlank() ? urlSource : "html-fixture");
                payload.put("title", parser.title());
                payload.put("link_count", parser.links().size());
                payload.put("image_count", parser.images().size());
                payload.put("text_length", parser.text().length());
                payload.put("html_length", html.length());
                System.out.println(new ObjectMapper().writerWithDefaultPrettyPrinter().writeValueAsString(payload));
            } catch (IOException e) {
                throw new RuntimeException("scrapy profile 失败", e);
            }
            return;
        }

        if ("plan-ai".equals(subcommand) || "sync-ai".equals(subcommand)) {
            if ("sync-ai".equals(subcommand) && project.isBlank()) {
                System.out.println("scrapy sync-ai 需要 --project");
                return;
            }
            try {
                String source;
                String html;
                String resolvedUrl = url;
                if (!project.isBlank()) {
                    Map<String, Object> manifest = readManifest.apply(project);
                    if (!selectedSpider.isBlank()) {
                        List<Map<String, Object>> spiders = resolveSpiderDisplay.apply(project, manifest);
                        Map<String, Object> match = spiders.stream()
                            .filter(spider -> selectedSpider.equals(String.valueOf(spider.get("name"))))
                            .findFirst()
                            .orElse(null);
                        if (match == null) {
                            throw new IllegalArgumentException("unknown spider in " + project + ": " + selectedSpider);
                        }
                        resolvedUrl = stringValue(match.get("url"), resolvedUrl);
                    } else if (resolvedUrl.isBlank()) {
                        resolvedUrl = stringValue(manifest.get("url"), "");
                    }
                }

                if (!htmlFile.isBlank()) {
                    source = htmlFile;
                    html = Files.readString(Paths.get(htmlFile));
                    if (resolvedUrl.isBlank()) {
                        resolvedUrl = Paths.get(htmlFile).toAbsolutePath().normalize().toUri().toString();
                    }
                } else if (!resolvedUrl.isBlank()) {
                    source = resolvedUrl;
                    html = loadHtmlInput(resolvedUrl, "");
                } else {
                    throw new IllegalArgumentException("scrapy " + subcommand + " 需要 --project、--url 或 --html-file");
                }

                Map<String, Object> profile = localSiteProfilePayload(resolvedUrl, html);
                @SuppressWarnings("unchecked")
                List<String> candidateFields = new ArrayList<>((List<String>) profile.getOrDefault("candidate_fields", List.of()));
                Map<String, Object> schema = schemaFromCandidateFields(candidateFields);
                String plannedSpiderName = spiderName.isBlank() ? "ai_spider" : spiderName;
                Map<String, Object> blueprint = buildJavaAIBlueprint(resolvedUrl, plannedSpiderName, profile, schema, html);
                Map<String, Object> payload = new LinkedHashMap<>();
                payload.put("command", "scrapy " + subcommand);
                payload.put("runtime", "java");
                payload.put("project", project.isBlank() ? null : project);
                payload.put("spider", selectedSpider.isBlank() ? null : selectedSpider);
                payload.put("spider_name", plannedSpiderName);
                payload.put("source", source);
                payload.put("resolved_url", resolvedUrl);
                payload.put("recommended_runtime", profile.get("recommended_runtime"));
                payload.put("page_profile", profile);
                payload.put("schema", schema);
                payload.put("blueprint", blueprint);
                payload.put("suggested_commands", List.of(
                    "java com.javaspider.EnhancedSpider scrapy genspider --name " + plannedSpiderName + " --domain " + deriveDomainFromUrl(resolvedUrl) + " --project " + (project.isBlank() ? "." : project) + " --ai",
                    "java com.javaspider.EnhancedSpider ai --url " + resolvedUrl + " --instructions \"提取核心字段\" --schema-file ai-schema.json"
                ));
                List<String> writtenFiles = new ArrayList<>();
                if (!project.isBlank()) {
                    Path projectRoot = Paths.get(project);
                    Path schemaPath = projectRoot.resolve("ai-schema.json");
                    Path blueprintPath = projectRoot.resolve("ai-blueprint.json");
                    Path promptPath = projectRoot.resolve("ai-extract-prompt.txt");
                    Path authPath = projectRoot.resolve("ai-auth.json");
                    Path planPath = (output.isBlank() || "artifacts/exports/javaspider-scrapy-demo.json".equals(output))
                        ? projectRoot.resolve("ai-plan.json")
                        : Paths.get(output);
                    Files.writeString(schemaPath, new ObjectMapper().writerWithDefaultPrettyPrinter().writeValueAsString(schema) + System.lineSeparator());
                    Files.writeString(blueprintPath, new ObjectMapper().writerWithDefaultPrettyPrinter().writeValueAsString(blueprint) + System.lineSeparator());
                    Files.writeString(promptPath, stringValue(blueprint.get("extraction_prompt"), "") + System.lineSeparator());
                    Files.writeString(authPath, new ObjectMapper().writerWithDefaultPrettyPrinter().writeValueAsString(Map.of(
                        "headers", Map.of(),
                        "cookies", Map.of(),
                        "storage_state_file", "",
                        "cookies_file", "",
                        "session", "auth",
                        "actions", List.of(),
                        "action_examples", defaultAuthActionExamples(),
                        "node_reverse_base_url", "http://localhost:3000",
                        "capture_reverse_profile", false,
                        "notes", "Fill session headers/cookies here when authentication is required."
                    )) + System.lineSeparator());
                    writtenFiles.add(schemaPath.toString());
                    writtenFiles.add(blueprintPath.toString());
                    writtenFiles.add(promptPath.toString());
                    writtenFiles.add(authPath.toString());
                    writtenFiles.add(planPath.toString());
                    payload.put("written_files", writtenFiles);
                    if ("sync-ai".equals(subcommand)) {
                        Path aiJobPath = projectRoot.resolve("ai-job.json");
                        List<Map<String, Object>> extract = new ArrayList<>();
                        for (String field : nestedMap(schema, "properties").keySet()) {
                            extract.add(Map.of("field", field, "type", "ai"));
                        }
                        Files.writeString(aiJobPath, new ObjectMapper().writerWithDefaultPrettyPrinter().writeValueAsString(Map.of(
                            "name", plannedSpiderName + "-ai-job",
                            "runtime", "ai",
                            "target", Map.of("url", resolvedUrl),
                            "extract", extract,
                            "output", Map.of("format", "json", "path", "artifacts/exports/ai-job-output.json"),
                            "metadata", Map.of("schema_file", "ai-schema.json")
                        )) + System.lineSeparator());
                        writtenFiles.add(aiJobPath.toString());
                        payload.put("written_files", writtenFiles);
                    }
                    Files.writeString(planPath, new ObjectMapper().writerWithDefaultPrettyPrinter().writeValueAsString(payload) + System.lineSeparator());
                } else if (!output.isBlank()) {
                    Path outputPath = Paths.get(output);
                    ensureParentDirectory(outputPath);
                    writtenFiles.add(outputPath.toString());
                    payload.put("written_files", writtenFiles);
                    Files.writeString(outputPath, new ObjectMapper().writerWithDefaultPrettyPrinter().writeValueAsString(payload) + System.lineSeparator());
                }
                payload.put("written_files", writtenFiles);
                System.out.println(new ObjectMapper().writerWithDefaultPrettyPrinter().writeValueAsString(payload));
            } catch (IOException e) {
                throw new RuntimeException("scrapy plan-ai 失败", e);
            }
            return;
        }

        if ("auth-validate".equals(subcommand)) {
            if (project.isBlank()) {
                System.out.println("scrapy auth-validate 需要 --project");
                return;
            }
            try {
                Map<String, Object> manifest = readManifest.apply(project);
                if (!selectedSpider.isBlank()) {
                    List<Map<String, Object>> spiders = resolveSpiderDisplay.apply(project, manifest);
                    Map<String, Object> match = spiders.stream()
                        .filter(spider -> selectedSpider.equals(String.valueOf(spider.get("name"))))
                        .findFirst()
                        .orElse(null);
                    if (match == null) {
                        throw new IllegalArgumentException("unknown spider in " + project + ": " + selectedSpider);
                    }
                    url = stringValue(match.get("url"), url);
                } else if (url.isBlank()) {
                    url = stringValue(manifest.get("url"), "");
                }

                Map<String, Object> assets = ProjectRuntime.loadAIProjectAssets(Paths.get(project));
                String source;
                String html;
                String resolvedUrl = url;
                String runnerUsed = "fixture";
                if (!htmlFile.isBlank()) {
                    source = htmlFile;
                    html = Files.readString(Paths.get(htmlFile));
                    if (resolvedUrl.isBlank()) {
                        resolvedUrl = Paths.get(htmlFile).toAbsolutePath().normalize().toUri().toString();
                    }
                } else if (!resolvedUrl.isBlank()) {
                    source = resolvedUrl;
                    if ("browser".equals(stringValue(assets.get("recommended_runner"), "http"))) {
                        Map<String, Object> browserCfg = new LinkedHashMap<>(defaultContractConfig("java"));
                        Map<String, Object> browser = new LinkedHashMap<>(nestedMap(browserCfg, "browser"));
                        browser.put("storage_state_file", stringValue(assets.get("storage_state_file"), ""));
                        browser.put("cookies_file", stringValue(assets.get("cookies_file"), ""));
                        browserCfg.put("browser", browser);
                        BrowserFetchRunner runner = browserFetchRunnerFactory.get();
                        try {
                            BrowserFetchResult result = runner.fetch(
                                resolvedUrl,
                                stringValue(browser.get("screenshot_path"), "artifacts/browser/page.png"),
                                stringValue(browser.get("html_path"), "artifacts/browser/page.html"),
                                browserCfg
                            );
                            html = Files.readString(Paths.get(stringValue(result.html_path, stringValue(browser.get("html_path"), "artifacts/browser/page.html"))));
                            resolvedUrl = stringValue(result.url, resolvedUrl);
                            runnerUsed = "browser";
                        } finally {
                            runner.close();
                        }
                    } else {
                        html = loadHtmlInput(resolvedUrl, "");
                        runnerUsed = "http";
                    }
                } else {
                    throw new IllegalArgumentException("scrapy auth-validate 需要 --project 加 --url、manifest url 或 --html-file");
                }

                Map<String, Object> validation = authValidationStatus(html);
                Map<String, Object> payload = new LinkedHashMap<>();
                payload.put("command", "scrapy auth-validate");
                payload.put("runtime", "java");
                payload.put("project", project);
                payload.put("spider", selectedSpider.isBlank() ? null : selectedSpider);
                payload.put("source", source);
                payload.put("resolved_url", resolvedUrl);
                payload.put("authentication_required", Boolean.TRUE.equals(nestedMap(nestedMap(assets, "blueprint"), "authentication").get("required")));
                payload.put("recommended_runner", assets.get("recommended_runner"));
                payload.put("runner_used", runnerUsed);
                payload.put("authenticated", validation.get("authenticated"));
                payload.put("indicators", validation.get("indicators"));
                payload.put("auth_assets", Map.of(
                    "has_headers", !nestedMap(Map.of("headers", assets.get("request_headers")), "headers").isEmpty(),
                    "storage_state_file", stringValue(assets.get("storage_state_file"), ""),
                    "cookies_file", stringValue(assets.get("cookies_file"), "")
                ));
                System.out.println(new ObjectMapper().writerWithDefaultPrettyPrinter().writeValueAsString(payload));
            } catch (IOException e) {
                throw new RuntimeException("scrapy auth-validate 失败", e);
            }
            return;
        }

        if ("auth-capture".equals(subcommand)) {
            if (project.isBlank()) {
                System.out.println("scrapy auth-capture 需要 --project");
                return;
            }
            try {
                Map<String, Object> manifest = readManifest.apply(project);
                if (!selectedSpider.isBlank()) {
                    List<Map<String, Object>> spiders = resolveSpiderDisplay.apply(project, manifest);
                    Map<String, Object> match = spiders.stream()
                        .filter(spider -> selectedSpider.equals(String.valueOf(spider.get("name"))))
                        .findFirst()
                        .orElse(null);
                    if (match == null) {
                        throw new IllegalArgumentException("unknown spider in " + project + ": " + selectedSpider);
                    }
                    url = stringValue(match.get("url"), url);
                } else if (url.isBlank()) {
                    url = stringValue(manifest.get("url"), "");
                }
                if (!htmlFile.isBlank() && url.isBlank()) {
                    url = Paths.get(htmlFile).toAbsolutePath().normalize().toUri().toString();
                }
                if (url.isBlank()) {
                    throw new IllegalArgumentException("scrapy auth-capture 需要 --project 加 --url、manifest url 或 --html-file");
                }

                Map<String, Object> browserCfg = new LinkedHashMap<>(defaultContractConfig("java"));
                Path authDir = Paths.get(project).resolve("artifacts").resolve("auth");
                Files.createDirectories(authDir);
                Path statePath = authDir.resolve(sessionName + "-state.json");
                Path cookiesPath = authDir.resolve(sessionName + "-cookies.json");
                Path authPath = Paths.get(project).resolve("ai-auth.json");
                Map<String, Object> browser = new LinkedHashMap<>(nestedMap(browserCfg, "browser"));
                browser.put("storage_state_file", statePath.toString());
                browser.put("cookies_file", cookiesPath.toString());
                browser.put("auth_file", authPath.toString());
                browserCfg.put("browser", browser);

                BrowserFetchRunner runner = browserFetchRunnerFactory.get();
                try {
                    runner.fetch(
                        url,
                        stringValue(browser.get("screenshot_path"), "artifacts/browser/page.png"),
                        stringValue(browser.get("html_path"), "artifacts/browser/page.html"),
                        browserCfg
                    );
                } finally {
                    runner.close();
                }

                Map<String, Object> authPayload;
                if (Files.exists(authPath)) {
                    authPayload = new ObjectMapper().readValue(Files.readString(authPath), new TypeReference<Map<String, Object>>() {});
                } else {
                    authPayload = new LinkedHashMap<>();
                }
                authPayload.put("headers", Map.of());
                authPayload.put("cookies", Map.of());
                authPayload.put("storage_state_file", "artifacts/auth/" + sessionName + "-state.json");
                authPayload.put("cookies_file", "artifacts/auth/" + sessionName + "-cookies.json");
                authPayload.put("session", sessionName);
                authPayload.putIfAbsent("actions", List.of());
                authPayload.putIfAbsent("action_examples", defaultAuthActionExamples());
                authPayload.putIfAbsent("node_reverse_base_url", "http://localhost:3000");
                authPayload.putIfAbsent("capture_reverse_profile", false);
                if (Boolean.TRUE.equals(authPayload.get("capture_reverse_profile"))) {
                    Object reverse = com.javaspider.scrapy.project.ProjectRuntime.collectReverseSummary(
                        String.valueOf(authPayload.get("node_reverse_base_url")),
                        url,
                        stringValue(browser.get("html_path"), "artifacts/browser/page.html")
                    );
                    if (reverse != null) {
                        authPayload.put("reverse_runtime", reverse);
                    }
                }
                authPayload.put("notes", "Fill session headers/cookies here when authentication is required.");
                Files.writeString(authPath, new ObjectMapper().writerWithDefaultPrettyPrinter().writeValueAsString(authPayload) + System.lineSeparator());
                Map<String, Object> payload = new LinkedHashMap<>();
                payload.put("command", "scrapy auth-capture");
                payload.put("runtime", "java");
                payload.put("project", project);
                payload.put("spider", selectedSpider.isBlank() ? null : selectedSpider);
                payload.put("session", sessionName);
                payload.put("resolved_url", url);
                payload.put("written_files", List.of(authPath.toString(), statePath.toString(), cookiesPath.toString()));
                System.out.println(new ObjectMapper().writerWithDefaultPrettyPrinter().writeValueAsString(payload));
            } catch (IOException e) {
                throw new RuntimeException("scrapy auth-capture 失败", e);
            }
            return;
        }

        if ("scaffold-ai".equals(subcommand)) {
            if (project.isBlank()) {
                System.out.println("scrapy scaffold-ai 需要 --project");
                return;
            }
            try {
                Map<String, Object> manifest = readManifest.apply(project);
                if (!selectedSpider.isBlank()) {
                    List<Map<String, Object>> spiders = resolveSpiderDisplay.apply(project, manifest);
                    Map<String, Object> match = spiders.stream()
                        .filter(spider -> selectedSpider.equals(String.valueOf(spider.get("name"))))
                        .findFirst()
                        .orElse(null);
                    if (match == null) {
                        throw new IllegalArgumentException("unknown spider in " + project + ": " + selectedSpider);
                    }
                    url = stringValue(match.get("url"), url);
                } else if (url.isBlank()) {
                    url = stringValue(manifest.get("url"), "");
                }

                String source;
                String html;
                String resolvedUrl = url;
                if (!htmlFile.isBlank()) {
                    source = htmlFile;
                    html = Files.readString(Paths.get(htmlFile));
                    if (resolvedUrl.isBlank()) {
                        resolvedUrl = Paths.get(htmlFile).toAbsolutePath().normalize().toUri().toString();
                    }
                } else if (!resolvedUrl.isBlank()) {
                    source = resolvedUrl;
                    html = loadHtmlInput(resolvedUrl, "");
                } else {
                    throw new IllegalArgumentException("scrapy scaffold-ai 需要 --project 加 --url、manifest url 或 --html-file");
                }

                Map<String, Object> profile = localSiteProfilePayload(resolvedUrl, html);
                @SuppressWarnings("unchecked")
                List<String> candidateFields = new ArrayList<>((List<String>) profile.getOrDefault("candidate_fields", List.of()));
                Map<String, Object> schema = schemaFromCandidateFields(candidateFields);
                String plannedSpiderName = spiderName.isBlank() ? "ai_spider" : spiderName;
                Map<String, Object> blueprint = buildJavaAIBlueprint(resolvedUrl, plannedSpiderName, profile, schema, html);
                String domain = deriveDomainFromUrl(resolvedUrl);
                Path spidersDir = Paths.get(project).resolve("spiders");
                Path target = spidersDir.resolve(plannedSpiderName + ".java");
                Path sourceDir = Paths.get(project).resolve("src").resolve("main").resolve("java").resolve("project").resolve("spiders");
                Path sourceTarget = sourceDir.resolve(plannedSpiderName.substring(0, 1).toUpperCase() + plannedSpiderName.substring(1) + "SpiderFactory.java");
                Files.createDirectories(spidersDir);
                Files.createDirectories(sourceDir);
                Files.writeString(target, "// scrapy: name=" + plannedSpiderName + " url=https://" + domain + System.lineSeparator() + "// Generated AI spider template for " + domain + System.lineSeparator());
                Files.writeString(sourceTarget, renderJavaAISpiderTemplate(plannedSpiderName, domain));

                Path registry = Paths.get(project).resolve("src").resolve("main").resolve("java").resolve("project").resolve("Spiders.java");
                if (Files.exists(registry)) {
                    String className = plannedSpiderName.substring(0, 1).toUpperCase() + plannedSpiderName.substring(1) + "SpiderFactory";
                    String current = Files.readString(registry);
                    if (!current.contains(className + ".register();")) {
                        current = current.replace("import project.spiders.DemoSpiderFactory;", "import project.spiders.DemoSpiderFactory;\nimport project.spiders." + className + ";");
                        current = current.replace("DemoSpiderFactory.register();", "DemoSpiderFactory.register();\n        " + className + ".register();");
                        Files.writeString(registry, current);
                    }
                }

                Path schemaPath = Paths.get(project).resolve("ai-schema.json");
                Files.writeString(schemaPath, new ObjectMapper().writerWithDefaultPrettyPrinter().writeValueAsString(schema) + System.lineSeparator());
                Path blueprintPath = Paths.get(project).resolve("ai-blueprint.json");
                Files.writeString(blueprintPath, new ObjectMapper().writerWithDefaultPrettyPrinter().writeValueAsString(blueprint) + System.lineSeparator());
                Path promptPath = Paths.get(project).resolve("ai-extract-prompt.txt");
                Files.writeString(promptPath, stringValue(blueprint.get("extraction_prompt"), "") + System.lineSeparator());
                Path authPath = Paths.get(project).resolve("ai-auth.json");
                Files.writeString(authPath, new ObjectMapper().writerWithDefaultPrettyPrinter().writeValueAsString(Map.of(
                    "headers", Map.of(),
                    "cookies", Map.of(),
                    "storage_state_file", "",
                    "cookies_file", "",
                    "session", "auth",
                    "actions", List.of(),
                    "action_examples", defaultAuthActionExamples(),
                    "node_reverse_base_url", "http://localhost:3000",
                    "capture_reverse_profile", false,
                    "notes", "Fill session headers/cookies here when authentication is required."
                )) + System.lineSeparator());
                Path planPath = (output.isBlank() || "artifacts/exports/javaspider-scrapy-demo.json".equals(output))
                    ? Paths.get(project).resolve("ai-plan.json")
                    : Paths.get(output);

                Map<String, Object> payload = new LinkedHashMap<>();
                payload.put("command", "scrapy scaffold-ai");
                payload.put("runtime", "java");
                payload.put("project", project);
                payload.put("spider", selectedSpider.isBlank() ? null : selectedSpider);
                payload.put("spider_name", plannedSpiderName);
                payload.put("source", source);
                payload.put("resolved_url", resolvedUrl);
                payload.put("recommended_runtime", profile.get("recommended_runtime"));
                payload.put("page_profile", profile);
                payload.put("schema", schema);
                payload.put("blueprint", blueprint);
                payload.put("written_files", List.of(schemaPath.toString(), blueprintPath.toString(), promptPath.toString(), authPath.toString(), planPath.toString(), sourceTarget.toString()));
                payload.put("suggested_commands", List.of(
                    "java com.javaspider.EnhancedSpider scrapy run --project " + project + " --spider " + plannedSpiderName,
                    "java com.javaspider.EnhancedSpider ai --url " + resolvedUrl + " --instructions \"提取核心字段\" --schema-file ai-schema.json"
                ));
                ensureParentDirectory(planPath);
                Files.writeString(planPath, new ObjectMapper().writerWithDefaultPrettyPrinter().writeValueAsString(payload) + System.lineSeparator());
                System.out.println(new ObjectMapper().writerWithDefaultPrettyPrinter().writeValueAsString(payload));
            } catch (IOException e) {
                throw new RuntimeException("scrapy scaffold-ai 失败", e);
            }
            return;
        }

        if ("doctor".equals(subcommand)) {
            if (project.isBlank()) {
                System.out.println("scrapy doctor 需要 --project");
                return;
            }
            List<Map<String, Object>> checks = new ArrayList<>();
            Path manifestPath = Paths.get(project).resolve("scrapy-project.json");
            checks.add(Map.of("name", "manifest", "status", Files.exists(manifestPath) ? "passed" : "failed", "details", manifestPath.toString()));
            if (Files.exists(manifestPath)) {
                try {
                    Map<String, Object> manifest = readManifest.apply(project);
                    checks.add(Map.of("name", "runtime", "status", "passed", "details", "java"));
                    String runner = stringValue(manifest.get("runner"), "");
                    Path runnerPath = runner.isBlank() ? null : Paths.get(project).resolve(runner);
                    checks.add(Map.of(
                        "name", "runner_artifact",
                        "status", runnerPath != null && Files.exists(runnerPath) ? "passed" : "warning",
                        "details", runnerPath == null ? "project runner artifact not configured; built-in metadata runner will be used" : runnerPath.toString()
                    ));
                    List<Map<String, Object>> spiders = resolveSpiderDisplay.apply(project, manifest);
                    if (spiders.isEmpty()) {
                        checks.add(Map.of("name", "spider_loader", "status", "warning", "details", "no spider files discovered"));
                    } else {
                        checks.add(Map.of("name", "spider_loader", "status", "passed", "details", spiders.size() + " spiders discovered"));
                        for (Map<String, Object> spider : spiders) {
                            checks.add(Map.of("name", "spider:" + String.valueOf(spider.get("name")), "status", "passed", "details",
                                String.valueOf(spider.get("path"))
                                    + " runner=" + stringValue(spider.get("runner"), "http")
                                    + " runner_source=" + stringValue(spider.get("runner_source"), "default")
                                    + " url=" + stringValue(spider.get("url"), "")
                                    + " url_source=" + stringValue(spider.get("url_source"), "default")
                                    + " pipelines=" + String.valueOf(spider.get("pipelines"))
                                    + " spider_middlewares=" + String.valueOf(spider.get("spider_middlewares"))
                                    + " downloader_middlewares=" + String.valueOf(spider.get("downloader_middlewares"))));
                        }
                    }
                } catch (RuntimeException exception) {
                    checks.add(Map.of("name", "runtime", "status", "failed", "details", exception.getMessage()));
                }
            }
            Path configPath = Paths.get(project).resolve("spider-framework.yaml");
            checks.add(Map.of("name", "config", "status", Files.exists(configPath) ? "passed" : "warning", "details", configPath.toString()));
            Map<String, Object> projectCfg = Files.exists(configPath) ? readContractConfig(configPath) : defaultContractConfig("java");
            appendDeclarativeComponentChecks(checks, projectCfg);
            Path pluginManifestPath = Paths.get(project).resolve("scrapy-plugins.json");
            if (Files.exists(pluginManifestPath)) {
                try {
                    validateScrapyPluginManifest(pluginManifestPath);
                    checks.add(Map.of("name", "plugin_manifest", "status", "passed", "details", pluginManifestPath.toString()));
                } catch (RuntimeException exception) {
                    checks.add(Map.of("name", "plugin_manifest", "status", "failed", "details", exception.getMessage()));
                }
            } else {
                checks.add(Map.of("name", "plugin_manifest", "status", "warning", "details", pluginManifestPath.toString()));
            }
            Path exportsDir = Paths.get(project).resolve("artifacts").resolve("exports");
            checks.add(Map.of("name", "exports_dir", "status", Files.isDirectory(exportsDir) ? "passed" : "warning", "details", exportsDir.toString()));
            boolean failed = checks.stream().anyMatch(check -> "failed".equals(check.get("status")));
            boolean warning = checks.stream().anyMatch(check -> "warning".equals(check.get("status")));
            String summary = failed ? "failed" : warning ? "warning" : "passed";
            Map<String, Object> payload = new LinkedHashMap<>();
            payload.put("command", "scrapy doctor");
            payload.put("runtime", "java");
            payload.put("project", project);
            payload.put("summary", summary);
            payload.put("checks", checks);
            try {
                System.out.println(new ObjectMapper().writerWithDefaultPrettyPrinter().writeValueAsString(payload));
            } catch (IOException e) {
                throw new RuntimeException(e);
            }
            if (failed) {
                throw new RuntimeException("scrapy project doctor failed");
            }
            return;
        }

        if ("bench".equals(subcommand)) {
            try {
                String source;
                String html;
                double fetchMs = 0.0;
                String resolvedRunner = "http";
                String runnerSource = "default";
                String urlSource = "default";
                if (!project.isBlank()) {
                    Map<String, Object> manifest = readManifest.apply(project);
                    if (!selectedSpider.isBlank()) {
                        List<Map<String, Object>> spiders = resolveSpiderDisplay.apply(project, manifest);
                        Map<String, Object> match = spiders.stream()
                            .filter(spider -> selectedSpider.equals(String.valueOf(spider.get("name"))))
                            .findFirst()
                            .orElse(null);
                        if (match == null) {
                            throw new IllegalArgumentException("unknown spider in " + project + ": " + selectedSpider);
                        }
                        url = stringValue(match.get("url"), url);
                        resolvedRunner = stringValue(match.get("runner"), "http");
                        runnerSource = stringValue(match.get("runner_source"), "default");
                        urlSource = stringValue(match.get("url_source"), "default");
                    } else if (url.isBlank()) {
                        Map<String, Object> cfg = Files.exists(Paths.get(project).resolve("spider-framework.yaml"))
                            ? readContractConfig(Paths.get(project).resolve("spider-framework.yaml"))
                            : defaultContractConfig("java");
                        String[] resolved = resolveScrapyUrlDetail(cfg, "", Map.of(), stringValue(manifest.get("url"), ""));
                        String[] runner = resolveScrapyRunnerDetail(cfg, "", Map.of());
                        url = resolved[0];
                        urlSource = resolved[1];
                        resolvedRunner = runner[0];
                        runnerSource = runner[1];
                    }
                }

                if (!htmlFile.isBlank()) {
                    source = htmlFile;
                    html = Files.readString(Paths.get(htmlFile));
                } else if (!url.isBlank()) {
                    source = url;
                    long fetchStarted = System.nanoTime();
                    html = loadHtmlInput(url, "");
                    fetchMs = (System.nanoTime() - fetchStarted) / 1_000_000.0;
                } else {
                    throw new IllegalArgumentException("scrapy bench 需要 --project、--url 或 --html-file");
                }

                long started = System.nanoTime();
                HtmlParser parser = new HtmlParser(html);
                double elapsedMs = (System.nanoTime() - started) / 1_000_000.0;
                Map<String, Object> payload = new LinkedHashMap<>();
                payload.put("command", "scrapy bench");
                payload.put("runtime", "java");
                payload.put("project", project.isBlank() ? null : project);
                payload.put("spider", selectedSpider.isBlank() ? null : selectedSpider);
                payload.put("source", source);
                payload.put("resolved_runner", resolvedRunner);
                payload.put("runner_source", htmlFile.isBlank() ? runnerSource : "html-fixture");
                payload.put("resolved_url", url);
                payload.put("url_source", htmlFile.isBlank() ? urlSource : "html-fixture");
                payload.put("elapsed_ms", elapsedMs);
                payload.put("fetch_ms", fetchMs == 0.0 ? null : fetchMs);
                payload.put("title", parser.title());
                payload.put("link_count", parser.links().size());
                payload.put("image_count", parser.images().size());
                payload.put("text_length", parser.text().length());
                payload.put("html_length", html.length());
                System.out.println(new ObjectMapper().writerWithDefaultPrettyPrinter().writeValueAsString(payload));
            } catch (IOException e) {
                throw new RuntimeException("scrapy bench 失败", e);
            }
            return;
        }

        if ("export".equals(subcommand)) {
            if (project.isBlank()) {
                System.out.println("scrapy export 需要 --project");
                return;
            }
            Map<String, Object> manifest = readManifest.apply(project);
            if (!selectedSpider.isBlank()) {
                List<Map<String, Object>> spiders = resolveSpiderDisplay.apply(project, manifest);
                boolean found = spiders.stream().anyMatch(spider -> selectedSpider.equals(String.valueOf(spider.get("name"))));
                if (!found) {
                    throw new IllegalArgumentException("unknown spider in " + project + ": " + selectedSpider);
                }
            }
            Path inputPath = resolveProjectOutput.apply(manifest, selectedSpider);
            try {
                String raw = Files.readString(inputPath);
                List<Map<String, String>> items = new ObjectMapper().readValue(raw, new TypeReference<List<Map<String, String>>>() {});
                Path outputPath = "artifacts/exports/javaspider-scrapy-demo.json".equals(output)
                    ? Paths.get(inputPath.toString().replaceFirst("\\.[^.]+$", "." + exportFormat))
                    : Paths.get(output);
                Exporter exporter = new Exporter(outputPath.getParent() != null ? outputPath.getParent().toString() : ".");
                if ("csv".equals(exportFormat)) {
                    exporter.exportCSV(items, outputPath.getFileName().toString());
                } else if ("md".equals(exportFormat)) {
                    exporter.exportMD(items, outputPath.getFileName().toString());
                } else {
                    exporter.exportJSON(items, outputPath.getFileName().toString());
                }
                Map<String, Object> payload = new LinkedHashMap<>();
                payload.put("command", "scrapy export");
                payload.put("runtime", "java");
                payload.put("project", project);
                payload.put("spider", selectedSpider.isBlank() ? null : selectedSpider);
                payload.put("input", inputPath.toString());
                payload.put("output", outputPath.toString());
                payload.put("format", exportFormat);
                System.out.println(new ObjectMapper().writerWithDefaultPrettyPrinter().writeValueAsString(payload));
            } catch (IOException e) {
                throw new RuntimeException("scrapy export 失败", e);
            }
            return;
        }

        if ("validate".equals(subcommand)) {
            if (project.isBlank()) {
                System.out.println("scrapy validate 需要 --project");
                return;
            }
            List<Map<String, Object>> checks = new ArrayList<>();
            Path manifestPath = Paths.get(project).resolve("scrapy-project.json");
            checks.add(Map.of("name", "manifest", "status", Files.exists(manifestPath) ? "passed" : "failed", "details", manifestPath.toString()));
            if (Files.exists(manifestPath)) {
                try {
                    Map<String, Object> manifest = readManifest.apply(project);
                    checks.add(Map.of("name", "runtime", "status", "passed", "details", "java"));
                    Path entryPath = Paths.get(project).resolve(stringValue(manifest.get("entry"), "src/main/java/starter/ScrapyStyleStarter.java"));
                    checks.add(Map.of("name", "entry", "status", Files.exists(entryPath) ? "passed" : "failed", "details", entryPath.toString()));
                    String runner = stringValue(manifest.get("runner"), "");
                    Path runnerPath = runner.isBlank() ? null : Paths.get(project).resolve(runner);
                    checks.add(Map.of(
                        "name", "runner_artifact",
                        "status", runnerPath != null && Files.exists(runnerPath) ? "passed" : "warning",
                        "details", runnerPath == null ? "project runner artifact not configured; built-in metadata runner will be used" : runnerPath.toString()
                    ));
                    for (Map<String, Object> spider : resolveSpiderDisplay.apply(project, manifest)) {
                        checks.add(Map.of("name", "spider:" + String.valueOf(spider.get("name")), "status", "passed", "details",
                            String.valueOf(spider.get("path"))
                                + " runner=" + stringValue(spider.get("runner"), "http")
                                + " runner_source=" + stringValue(spider.get("runner_source"), "default")
                                + " url=" + stringValue(spider.get("url"), "")
                                + " url_source=" + stringValue(spider.get("url_source"), "default")
                                + " pipelines=" + String.valueOf(spider.get("pipelines"))
                                + " spider_middlewares=" + String.valueOf(spider.get("spider_middlewares"))
                                + " downloader_middlewares=" + String.valueOf(spider.get("downloader_middlewares"))));
                    }
                } catch (RuntimeException exception) {
                    checks.add(Map.of("name", "runtime", "status", "failed", "details", exception.getMessage()));
                }
            }
            Path configPath = Paths.get(project).resolve("spider-framework.yaml");
            checks.add(Map.of("name", "config", "status", Files.exists(configPath) ? "passed" : "warning", "details", configPath.toString()));
            Map<String, Object> projectCfg = Files.exists(configPath) ? readContractConfig(configPath) : defaultContractConfig("java");
            appendDeclarativeComponentChecks(checks, projectCfg);
            Path pluginManifestPath = Paths.get(project).resolve("scrapy-plugins.json");
            if (Files.exists(pluginManifestPath)) {
                try {
                    validateScrapyPluginManifest(pluginManifestPath);
                    checks.add(Map.of("name", "plugin_manifest", "status", "passed", "details", pluginManifestPath.toString()));
                } catch (RuntimeException exception) {
                    checks.add(Map.of("name", "plugin_manifest", "status", "failed", "details", exception.getMessage()));
                }
            } else {
                checks.add(Map.of("name", "plugin_manifest", "status", "warning", "details", pluginManifestPath.toString()));
            }
            boolean failed = checks.stream().anyMatch(check -> "failed".equals(check.get("status")));
            try {
                System.out.println(new ObjectMapper().writerWithDefaultPrettyPrinter().writeValueAsString(Map.of(
                    "command", "scrapy validate",
                    "runtime", "java",
                    "project", project,
                    "summary", failed ? "failed" : "passed",
                    "checks", checks
                )));
            } catch (IOException e) {
                throw new RuntimeException(e);
            }
            if (failed) {
                throw new RuntimeException("scrapy project validation failed");
            }
            return;
        }

        if ("genspider".equals(subcommand)) {
            if (project.isBlank()) {
                System.out.println("scrapy genspider 需要 --project");
                return;
            }
            if (spiderName.isBlank() || spiderDomain.isBlank()) {
                System.out.println("scrapy genspider 需要 --name 和 --domain");
                return;
            }
            readManifest.apply(project);
            Path spidersDir = Paths.get(project).resolve("spiders");
            Path target = spidersDir.resolve(spiderName + ".java");
            Path sourceDir = Paths.get(project).resolve("src").resolve("main").resolve("java").resolve("project").resolve("spiders");
            Path sourceTarget = sourceDir.resolve(spiderName.substring(0, 1).toUpperCase() + spiderName.substring(1) + "SpiderFactory.java");
            try {
                Files.createDirectories(spidersDir);
                Files.createDirectories(sourceDir);
                Files.writeString(target, "// scrapy: name=" + spiderName + " url=https://" + spiderDomain + System.lineSeparator() + "// Generated " + (aiTemplate ? "AI " : "") + "spider template for " + spiderDomain + System.lineSeparator());
                String className = spiderName.substring(0, 1).toUpperCase() + spiderName.substring(1) + "SpiderFactory";
                Files.writeString(sourceTarget, aiTemplate ? renderJavaAISpiderTemplate(spiderName, spiderDomain) : """
                    package project.spiders;

                    // scrapy: name=%s url=https://%s

                    import com.javaspider.scrapy.Spider;
                    import com.javaspider.scrapy.item.Item;
                    import com.javaspider.scrapy.project.ProjectRuntime;

                    import java.util.List;

                    public final class %s {
                        private %s() {
                        }

                        public static Spider create() {
                            return new Spider() {
                                {
                                    setName("%s");
                                    addStartUrl("https://%s");
                                }

                                @Override
                                public List<Object> parse(Spider.Response response) {
                                    return List.of(new Item().set("title", response.selector().css("title").firstText()).set("url", response.getUrl()));
                                }
                            };
                        }

                        public static void register() {
                            ProjectRuntime.registerSpider("%s", %s::create);
                        }
                    }
                    """.formatted(spiderName, spiderDomain, className, className, spiderName, spiderDomain, spiderName, className));
                Path registry = Paths.get(project).resolve("src").resolve("main").resolve("java").resolve("project").resolve("Spiders.java");
                if (Files.exists(registry)) {
                    String current = Files.readString(registry);
                    if (!current.contains(className + ".register();")) {
                        current = current.replace("import project.spiders.DemoSpiderFactory;", "import project.spiders.DemoSpiderFactory;\nimport project.spiders." + className + ";");
                        current = current.replace("DemoSpiderFactory.register();", "DemoSpiderFactory.register();\n        " + className + ".register();");
                        Files.writeString(registry, current);
                    }
                }
                System.out.println(new ObjectMapper().writerWithDefaultPrettyPrinter().writeValueAsString(Map.of(
                    "command", "scrapy genspider",
                    "runtime", "java",
                    "project", project,
                    "spider", spiderName,
                    "path", target.toString(),
                    "template", aiTemplate ? "ai" : "standard"
                )));
            } catch (IOException e) {
                throw new RuntimeException("生成 spider 失败", e);
            }
            return;
        }

        if ("init".equals(subcommand)) {
            if (initPath.isBlank()) {
                System.out.println("scrapy init 需要 --path");
                return;
            }
            Path projectRoot = Paths.get(initPath);
            try {
                Files.createDirectories(projectRoot);
                Map<String, Object> config = new LinkedHashMap<>(defaultContractConfig("java"));
                Map<String, Object> projectConfig = new LinkedHashMap<>(nestedMap(config, "project"));
                projectConfig.put("name", projectRoot.getFileName() != null ? projectRoot.getFileName().toString() : "javaspider-project");
                config.put("project", projectConfig);
                Map<String, String> files = new LinkedHashMap<>();
                files.put("scrapy-project.json", new ObjectMapper().writerWithDefaultPrettyPrinter().writeValueAsString(Map.of(
                    "name", projectConfig.get("name"),
                    "runtime", "java",
                    "entry", "src/main/java/project/Main.java",
                    "runner", "build/project-runner.jar",
                    "url", "https://example.com",
                    "output", "artifacts/exports/items.json"
                )));
                files.put("pom.xml", """
                    <project xmlns="http://maven.apache.org/POM/4.0.0"
                             xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                             xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
                      <modelVersion>4.0.0</modelVersion>
                      <groupId>project</groupId>
                      <artifactId>project-runner</artifactId>
                      <version>0.1.0</version>
                      <properties>
                        <maven.compiler.source>17</maven.compiler.source>
                        <maven.compiler.target>17</maven.compiler.target>
                        <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
                      </properties>
                      <dependencies>
                        <dependency>
                          <groupId>com.javaspider</groupId>
                          <artifactId>javaspider</artifactId>
                          <version>1.0.0</version>
                        </dependency>
                      </dependencies>
                    </project>
                    """);
                files.put("src/main/java/project/Main.java", """
                    package project;

                    import com.javaspider.scrapy.CrawlerProcess;
                    import com.javaspider.scrapy.ScrapyPlugin;
                    import com.javaspider.scrapy.Spider;
                    import com.javaspider.scrapy.feed.FeedExporter;
                    import com.javaspider.scrapy.item.Item;
                    import com.javaspider.scrapy.project.ProjectRuntime;

                    import java.util.List;

                    public final class Main {
                        private Main() {
                        }

                        public static void main(String[] args) {
                            Spiders.register();
                            Plugins.register();
                            if (ProjectRuntime.runFromEnv()) {
                                return;
                            }
                            Spider spider = ProjectRuntime.resolveSpider("");
                            List<ScrapyPlugin> plugins = ProjectRuntime.resolvePlugins(List.of());
                            CrawlerProcess process = new CrawlerProcess(spider);
                            for (ScrapyPlugin plugin : plugins) {
                                process.addPlugin(plugin);
                            }
                            List<Item> items = process.crawl();
                            try (FeedExporter exporter = FeedExporter.json("artifacts/exports/items.json")) {
                                exporter.exportItems(items);
                            }
                        }
                    }
                    """);
                files.put("src/main/java/starter/ScrapyStyleStarter.java", """
                    package starter;

                    public final class ScrapyStyleStarter {
                        private ScrapyStyleStarter() {
                        }

                        public static void main(String[] args) {
                            project.Main.main(args);
                        }
                    }
                    """);
                files.put("src/main/java/project/Spiders.java", """
                    package project;

                    import project.spiders.DemoSpiderFactory;

                    public final class Spiders {
                        private Spiders() {
                        }

                        public static void register() {
                            DemoSpiderFactory.register();
                        }
                    }
                    """);
                files.put("src/main/java/project/Plugins.java", """
                    package project;

                    import project.plugins.DefaultPlugin;

                    public final class Plugins {
                        private Plugins() {
                        }

                        public static void register() {
                            DefaultPlugin.register();
                        }
                    }
                    """);
                files.put("src/main/java/project/spiders/DemoSpiderFactory.java", """
                    package project.spiders;

                    // scrapy: name=demo url=https://example.com

                    import com.javaspider.scrapy.Spider;
                    import com.javaspider.scrapy.item.Item;
                    import com.javaspider.scrapy.project.ProjectRuntime;

                    import java.util.List;

                    public final class DemoSpiderFactory {
                        private DemoSpiderFactory() {
                        }

                        public static Spider create() {
                            return new Spider() {
                                {
                                    setName("demo");
                                    addStartUrl("https://example.com");
                                }

                                @Override
                                public List<Object> parse(Spider.Response response) {
                                    return List.of(
                                        new Item()
                                            .set("title", response.selector().css("title").firstText())
                                            .set("url", response.getUrl())
                                            .set("framework", "javaspider")
                                    );
                                }
                            };
                        }

                        public static void register() {
                            ProjectRuntime.registerSpider("demo", DemoSpiderFactory::create);
                        }
                    }
                    """);
                files.put("src/main/java/project/plugins/DefaultPlugin.java", """
                    package project.plugins;

                    import com.javaspider.scrapy.ScrapyPlugin;
                    import com.javaspider.scrapy.item.Item;
                    import com.javaspider.scrapy.project.ProjectRuntime;

                    public final class DefaultPlugin implements ScrapyPlugin {
                        public static DefaultPlugin create() {
                            return new DefaultPlugin();
                        }

                        public static void register() {
                            ProjectRuntime.registerPlugin("project-plugin", DefaultPlugin::create);
                        }

                        @Override
                        public Item processItem(Item item, com.javaspider.scrapy.Spider spider) {
                            return item;
                        }
                    }
                    """);
                files.put("scrapy-plugins.json", """
                    {
                      "plugins": [
                        {
                          "name": "field-injector",
                          "priority": 10,
                          "config": {
                            "fields": {
                              "plugin": "project-plugin"
                            }
                          }
                        }
                      ]
                    }
                    """);
                files.put("spiders/.gitkeep", "");
                files.put("run-scrapy.sh", "#!/usr/bin/env bash\nset -euo pipefail\n\njava com.javaspider.EnhancedSpider scrapy run --project .\n");
                files.put("run-scrapy.ps1", "java com.javaspider.EnhancedSpider scrapy run --project .\n");
                files.put("README.md", "# " + projectConfig.get("name") + "\n\n## Quick Start\n\n```bash\njava com.javaspider.EnhancedSpider scrapy run --project .\njava com.javaspider.EnhancedSpider scrapy run --project . --spider demo\nmvn -q -DskipTests package\ncp target/project-runner-0.1.0.jar build/project-runner.jar\n```\n\n`scrapy run --project` 会优先执行 `scrapy-project.json` 里配置的 project runner artifact；如果 artifact 尚未构建，会回退到 built-in metadata runner。\n\n## AI Starter\n\n```bash\njava com.javaspider.EnhancedSpider ai --url https://example.com --instructions \"提取标题和摘要\" --schema-file ai-schema.json\njava com.javaspider.EnhancedSpider job --file ai-job.json\n```\n\n## Plugin SDK\n\n`src/main/java/project/plugins/` 中的注册型插件用于 project runner artifact，`scrapy-plugins.json` 用于 built-in metadata runner 和内置插件。\n");
                files.put("ai-schema.json", """
                    {
                      "type": "object",
                      "properties": {
                        "title": { "type": "string" },
                        "summary": { "type": "string" },
                        "url": { "type": "string" }
                      }
                    }
                    """);
                files.put("ai-job.json", """
                    {
                      "name": "javaspider-ai-job",
                      "runtime": "ai",
                      "target": { "url": "https://example.com" },
                      "extract": [
                        { "field": "title", "type": "ai" },
                        { "field": "summary", "type": "ai" },
                        { "field": "url", "type": "ai" }
                      ],
                      "output": { "format": "json", "path": "artifacts/exports/ai-job-output.json" },
                      "metadata": { "content": "<title>Demo</title>", "schema_file": "ai-schema.json" }
                    }
                    """);
                files.put("job.json", """
                    {
                      "name": "javaspider-job",
                      "runtime": "browser",
                      "target": { "url": "https://example.com" },
                      "output": { "format": "json", "path": "artifacts/exports/job-output.json" }
                    }
                    """);
                files.put("spider-framework.yaml", new Yaml().dump(config));
                for (Map.Entry<String, String> entry : files.entrySet()) {
                    Path filePath = projectRoot.resolve(entry.getKey());
                    ensureParentDirectory(filePath);
                    Files.writeString(filePath, entry.getValue());
                }
                Map<String, Object> payload = new LinkedHashMap<>();
                payload.put("command", "scrapy init");
                payload.put("runtime", "java");
                payload.put("project", projectRoot.toString());
                System.out.println(new ObjectMapper().writerWithDefaultPrettyPrinter().writeValueAsString(payload));
            } catch (IOException e) {
                throw new RuntimeException("生成 scrapy project 失败", e);
            }
            return;
        }

        if ("run".equals(subcommand)) {
            if (project.isBlank()) {
                System.out.println("scrapy run 需要 --project");
                return;
            }
            Path manifestPath = Paths.get(project).resolve("scrapy-project.json");
            try {
                Map<String, Object> projectConfig = defaultContractConfig("java");
                Path configPath = Paths.get(project).resolve("spider-framework.yaml");
                if (Files.exists(configPath)) {
                    projectConfig = readContractConfig(configPath);
                }
                Map<String, Object> manifest = new ObjectMapper().readValue(
                    Files.readString(manifestPath),
                    new TypeReference<Map<String, Object>>() {}
                );
                Map<String, Object> selectedMetadata = new LinkedHashMap<>();
                if (!"java".equals(stringValue(manifest.get("runtime"), ""))) {
                    throw new IllegalArgumentException("runtime mismatch in " + manifestPath + ": expected 'java'");
                }
                String[] selectedUrlDetail;
                if (!selectedSpider.isBlank()) {
                    List<Map<String, Object>> spiders = resolveSpiderDisplay.apply(project, manifest);
                    Map<String, Object> match = spiders.stream()
                        .filter(spider -> selectedSpider.equals(String.valueOf(spider.get("name"))))
                        .findFirst()
                        .orElse(null);
                    if (match == null) {
                        throw new IllegalArgumentException("unknown spider in " + project + ": " + selectedSpider);
                    }
                    selectedMetadata = match;
                    selectedUrlDetail = new String[]{stringValue(match.get("url"), url), stringValue(match.get("url_source"), "metadata")};
                    url = selectedUrlDetail[0];
                } else {
                    selectedUrlDetail = resolveScrapyUrlDetail(projectConfig, "", selectedMetadata, stringValue(manifest.get("url"), ""));
                    url = selectedUrlDetail[0];
                }
                if ("artifacts/exports/javaspider-scrapy-demo.json".equals(output)) {
                    if (!selectedSpider.isBlank()) {
                        output = Paths.get(project).resolve("artifacts").resolve("exports").resolve(selectedSpider + ".json").toString();
                    } else {
                        output = Paths.get(project).resolve(stringValue(manifest.get("output"), output)).toString();
                    }
                }
                String[] selectedRunnerDetail = resolveScrapyRunnerDetail(projectConfig, selectedSpider, selectedMetadata);
                String selectedRunner = selectedRunnerDetail[0];
                String runner = stringValue(manifest.get("runner"), "");
                if ("http".equals(selectedRunner) && !runner.isBlank()) {
                    Path runnerPath = Paths.get(project).resolve(runner);
                    if (Files.exists(runnerPath)) {
                        runJavaProjectArtifact(runnerPath, project, selectedSpider, url, htmlFile, output);
                        return;
                    }
                }
            } catch (IOException e) {
                throw new RuntimeException("读取 scrapy project 失败", e);
            }
        }

        Spider spider = new Spider() {
            {
                setName("javaspider-scrapy-demo");
            }

            @Override
            public List<Object> parse(Spider.Response response) {
                return List.of(
                    new Item()
                        .set("title", response.selector().css("title").firstText())
                        .set("url", response.getUrl())
                        .set("framework", "javaspider")
                );
            }
        };

        List<Item> items;
        try {
            spider.addStartUrl(url);
            Map<String, Object> runtimeConfig = defaultContractConfig("java");
            if (!project.isBlank()) {
                Path runtimeConfigPath = Paths.get(project).resolve("spider-framework.yaml");
                if (Files.exists(runtimeConfigPath)) {
                    runtimeConfig = readContractConfig(runtimeConfigPath);
                }
            }
            List<ProjectRuntime.PluginSpec> pluginSpecs = project.isBlank()
                ? List.of()
                : ProjectRuntime.loadPluginSpecsFromManifest(Paths.get(project));
            if (pluginSpecs.isEmpty()) {
                pluginSpecs = configuredScrapyPluginSpecs(runtimeConfig);
            }
            List<ScrapyPlugin> plugins = ProjectRuntime.resolvePluginSpecs(pluginSpecs);
            List<String> resolvedPluginNames = pluginSpecs.isEmpty()
                ? ProjectRuntime.pluginNames()
                : enabledPluginSpecNames(pluginSpecs);
            int pipelineCount = buildDeclarativeScrapyPipelines(runtimeConfig, selectedSpider).size()
                + plugins.stream().mapToInt(plugin -> plugin.providePipelines().size()).sum();
            int spiderMiddlewareCount = buildDeclarativeScrapySpiderMiddlewares(runtimeConfig, selectedSpider).size()
                + plugins.stream().mapToInt(plugin -> plugin.provideSpiderMiddlewares().size()).sum();
            int downloaderMiddlewareCount = buildDeclarativeScrapyDownloaderMiddlewares(runtimeConfig, selectedSpider).size()
                + plugins.stream().mapToInt(plugin -> plugin.provideDownloaderMiddlewares().size()).sum();
            String[] selectedRunnerDetail = resolveScrapyRunnerDetail(runtimeConfig, selectedSpider, Map.of());
            String selectedRunner = selectedRunnerDetail[0];
            CrawlerProcess process = new CrawlerProcess(spider).withConfig(Map.of("runner", htmlFile.isBlank() ? selectedRunner : "browser"));
            List<Spider.ItemPipeline> declarativePipelines = buildDeclarativeScrapyPipelines(runtimeConfig, selectedSpider);
            List<SpiderMiddleware> declarativeSpiderMiddlewares = buildDeclarativeScrapySpiderMiddlewares(runtimeConfig, selectedSpider);
            List<DownloaderMiddleware> declarativeDownloaderMiddlewares = buildDeclarativeScrapyDownloaderMiddlewares(runtimeConfig, selectedSpider);
            if (!htmlFile.isBlank()) {
                String fixturePath = htmlFile;
                process.withBrowserFetcher((request, currentSpider) -> {
                    try {
                        return new Spider.Response(
                            request.getUrl(),
                            200,
                            Map.of(),
                            Files.readString(Paths.get(fixturePath)),
                            request
                        );
                    } catch (IOException e) {
                        throw new RuntimeException(e);
                    }
                });
            } else if ("browser".equals(selectedRunner) || "hybrid".equals(selectedRunner)) {
                Map<String, Object> browserRuntimeConfig = runtimeConfig;
                process.withBrowserFetcher((request, currentSpider) -> browserResponseForScrapy(request, browserRuntimeConfig));
            }
            for (ScrapyPlugin plugin : plugins) {
                process.addPlugin(plugin);
            }
            for (Spider.ItemPipeline pipeline : declarativePipelines) {
                process.addPipeline(pipeline);
            }
            for (SpiderMiddleware middleware : declarativeSpiderMiddlewares) {
                process.addSpiderMiddleware(middleware);
            }
            for (DownloaderMiddleware middleware : declarativeDownloaderMiddlewares) {
                process.addDownloaderMiddleware(middleware);
            }
            items = process.crawl();

            try (FeedExporter exporter = FeedExporter.json(output)) {
                exporter.exportItems(items);
            }

            Map<String, Object> payload = new LinkedHashMap<>();
            payload.put("command", "scrapy " + subcommand);
            payload.put("runtime", "java");
            payload.put("spider", selectedSpider.isBlank() ? null : selectedSpider);
            payload.put("project_runner", "built-in-metadata-runner");
            payload.put("runner", selectedRunner);
            Map<String, Object> nodeReverse = nestedMap(runtimeConfig, "node_reverse");
            String reverseUrl = stringValue(nodeReverse.get("base_url"), "");
            if (!reverseUrl.isBlank()) {
                payload.put("reverse", ProjectRuntime.collectReverseSummary(reverseUrl, url, htmlFile));
            }
            payload.put("resolved_runner", selectedRunner);
            payload.put("runner_source", htmlFile.isBlank() ? selectedRunnerDetail[1] : "html-fixture");
            payload.put("resolved_url", url);
            payload.put("url_source", htmlFile.isBlank() ? resolveScrapyUrlDetail(runtimeConfig, selectedSpider, Map.of(), url)[1] : "html-fixture");
            payload.put("settings_source", project.isBlank() ? null : Paths.get(project).resolve("spider-framework.yaml").toString());
            payload.put("plugins", resolvedPluginNames);
            payload.put("pipelines", configuredScrapyPipelines(runtimeConfig, selectedSpider));
            payload.put("spider_middlewares", configuredScrapySpiderMiddlewares(runtimeConfig, selectedSpider));
            payload.put("downloader_middlewares", configuredScrapyDownloaderMiddlewares(runtimeConfig, selectedSpider));
            payload.put("pipeline_count", pipelineCount);
            payload.put("spider_middleware_count", spiderMiddlewareCount);
            payload.put("downloader_middleware_count", downloaderMiddlewareCount);
            payload.put("runtime_features", Map.of(
                "browser", !htmlFile.isBlank() || "browser".equals(selectedRunner) || "hybrid".equals(selectedRunner),
                "anti_bot", boolValue(nestedMap(runtimeConfig, "anti_bot").get("enabled"), true),
                "node_reverse", boolValue(nodeReverse.get("enabled"), true) && !reverseUrl.isBlank(),
                "distributed", true
            ));
            List<String> pipelineNames = configuredScrapyPipelines(runtimeConfig, selectedSpider);
            pipelineNames.addAll(collectJavaPipelineNames(plugins, declarativePipelines));
            List<String> spiderMiddlewareNames = configuredScrapySpiderMiddlewares(runtimeConfig, selectedSpider);
            spiderMiddlewareNames.addAll(collectJavaSpiderMiddlewareNames(plugins, declarativeSpiderMiddlewares));
            List<String> downloaderMiddlewareNames = configuredScrapyDownloaderMiddlewares(runtimeConfig, selectedSpider);
            downloaderMiddlewareNames.addAll(collectJavaDownloaderMiddlewareNames(plugins, declarativeDownloaderMiddlewares));
            payload.put("pipelines", pipelineNames);
            payload.put("spider_middlewares", spiderMiddlewareNames);
            payload.put("downloader_middlewares", downloaderMiddlewareNames);
            payload.put("item_count", items.size());
            payload.put("output", output);
            System.out.println(new ObjectMapper().writerWithDefaultPrettyPrinter().writeValueAsString(payload));
        } catch (IOException e) {
            throw new RuntimeException("scrapy demo 失败", e);
        }
    }

    private static String[] slice(String[] args, int start) {
        if (start >= args.length) {
            return new String[0];
        }
        String[] result = new String[args.length - start];
        System.arraycopy(args, start, result, 0, result.length);
        return result;
    }

    private static boolean contains(String[] args, String target) {
        for (String arg : args) {
            if (target.equals(arg)) {
                return true;
            }
        }
        return false;
    }

    private static String extractOption(String[] args, String... names) {
        for (int i = 0; i < args.length - 1; i++) {
            for (String name : names) {
                if (name.equals(args[i])) {
                    return args[i + 1];
                }
            }
        }
        return null;
    }

    private static List<String> extractOptions(String[] args, String name) {
        List<String> values = new ArrayList<>();
        for (int i = 0; i < args.length - 1; i++) {
            if (name.equals(args[i])) {
                values.add(args[i + 1]);
            }
        }
        return values;
    }

    private static Integer parseIntegerOption(String value) {
        if (value == null || value.isBlank()) {
            return null;
        }
        return Integer.parseInt(value);
    }

    private static boolean isWritableDirectory(Path path) {
        try {
            if (Files.notExists(path)) {
                Files.createDirectories(path);
            }
            Path probe = Files.createTempFile(path, "javaspider-doctor-", ".tmp");
            Files.deleteIfExists(probe);
            return true;
        } catch (IOException ignored) {
            return false;
        }
    }

    private static Map<String, Object> doctorCheck(String name, boolean passed, String details) {
        return doctorCheck(name, passed ? "passed" : "failed", details);
    }

    private static Map<String, Object> doctorCheck(String name, String status, String details) {
        Map<String, Object> check = new LinkedHashMap<>();
        check.put("name", name);
        check.put("status", status);
        check.put("details", details);
        return check;
    }

    private static String doctorSummaryText(List<Map<String, Object>> checks) {
        long passed = checks.stream().filter(check -> "passed".equals(check.get("status"))).count();
        long warning = checks.stream().filter(check -> "warning".equals(check.get("status"))).count();
        long failed = checks.stream().filter(check -> "failed".equals(check.get("status"))).count();
        long skipped = checks.stream().filter(check -> "skipped".equals(check.get("status"))).count();
        return passed + " passed, " + warning + " warning, " + failed + " failed, " + skipped + " skipped";
    }

    private static Map<String, Object> checkNetworkTarget(String target) {
        String normalized = normalizeDialTarget(target);
        if (normalized == null || normalized.isBlank()) {
            return doctorCheck("network:" + target, "failed", "invalid network target");
        }
        try (Socket socket = new Socket()) {
            String host = normalized.substring(0, normalized.lastIndexOf(':'));
            int port = Integer.parseInt(normalized.substring(normalized.lastIndexOf(':') + 1));
            socket.connect(new InetSocketAddress(host, port), 3000);
            return doctorCheck("network:" + target, "passed", normalized);
        } catch (Exception e) {
            return doctorCheck("network:" + target, "failed", e.getMessage());
        }
    }

    private static Map<String, Object> checkRedisTarget(String target) {
        String normalized = normalizeDialTarget(target);
        if (normalized == null || normalized.isBlank()) {
            return doctorCheck("redis", "failed", "invalid redis target");
        }
        try (Socket socket = new Socket()) {
            String host = normalized.substring(0, normalized.lastIndexOf(':'));
            int port = Integer.parseInt(normalized.substring(normalized.lastIndexOf(':') + 1));
            socket.connect(new InetSocketAddress(host, port), 3000);
            socket.getOutputStream().write("*1\r\n$4\r\nPING\r\n".getBytes(StandardCharsets.UTF_8));
            socket.getOutputStream().flush();
            byte[] buffer = socket.getInputStream().readNBytes(64);
            String response = new String(buffer, StandardCharsets.UTF_8);
            if (response.contains("PONG")) {
                return doctorCheck("redis", "passed", normalized);
            }
            return doctorCheck("redis", "failed", response.isBlank() ? "unexpected empty response" : response.trim());
        } catch (Exception e) {
            return doctorCheck("redis", "failed", e.getMessage());
        }
    }

    private static String normalizeDialTarget(String target) {
        if (target == null || target.isBlank()) {
            return "";
        }
        try {
            java.net.URI parsed = target.contains("://") ? java.net.URI.create(target) : null;
            if (parsed != null) {
                String host = stringValue(parsed.getHost(), "");
                int port = parsed.getPort();
                if (host.isBlank()) {
                    return "";
                }
                if (port <= 0) {
                    port = switch (stringValue(parsed.getScheme(), "")) {
                        case "https" -> 443;
                        case "redis" -> 6379;
                        default -> 80;
                    };
                }
                return host + ":" + port;
            }
            if (!target.contains(":")) {
                return target + ":80";
            }
            return target;
        } catch (Exception ignored) {
            return "";
        }
    }

    private static String detectBrowserBinary() {
        for (String candidate : List.of(
            "chrome",
            "chrome.exe",
            "chromium",
            "chromium-browser",
            "msedge",
            "msedge.exe",
            "chromedriver",
            "chromedriver.exe",
            "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
            "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
            "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
            "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe"
        )) {
            if (candidate.contains("\\") || candidate.contains("/")) {
                if (Files.exists(Path.of(candidate))) {
                    return candidate;
                }
                continue;
            }
            try {
                Process process = new ProcessBuilder(candidate, "--version").start();
                if (process.waitFor(3, java.util.concurrent.TimeUnit.SECONDS) && process.exitValue() == 0) {
                    return candidate;
                }
            } catch (Exception ignored) {
            }
        }
        return "";
    }

    private static Map<String, Object> loadContractConfig(String configPath) {
        if (configPath != null && !configPath.isBlank()) {
            Path explicit = Paths.get(configPath);
            if (Files.notExists(explicit)) {
                throw new IllegalArgumentException("config file not found: " + configPath);
            }
            return validateContractConfig(readContractConfig(explicit), "java");
        }

        Path resolved = resolveConfigPath(null);
        if (resolved == null) {
            return validateContractConfig(defaultContractConfig("java"), "java");
        }
        return validateContractConfig(readContractConfig(resolved), "java");
    }

    private static Path resolveConfigPath(String configPath) {
        if (configPath != null && !configPath.isBlank()) {
            Path path = Paths.get(configPath);
            return Files.exists(path) ? path : null;
        }
        for (String candidate : List.of("spider-framework.yaml", "spider-framework.yml", "spider-framework.json", "config.yaml")) {
            Path path = Paths.get(candidate);
            if (Files.exists(path)) {
                return path;
            }
        }
        return null;
    }

    private static Map<String, Object> defaultContractConfig(String runtime) {
        Map<String, Object> root = new LinkedHashMap<>();
        root.put("version", 1);
        root.put("runtime", runtime);
        root.put("project", Map.of("name", runtime + "-project"));
        root.put("crawl", Map.of(
            "urls", List.of("https://example.com"),
            "concurrency", 5,
            "max_requests", 100,
            "max_depth", 3,
            "timeout_seconds", 30
        ));
        root.put("sitemap", Map.of(
            "enabled", false,
            "url", "https://example.com/sitemap.xml",
            "max_urls", 50
        ));
        root.put("browser", Map.of(
            "enabled", true,
            "headless", true,
            "timeout_seconds", 30,
            "user_agent", "",
            "screenshot_path", "artifacts/browser/page.png",
            "html_path", "artifacts/browser/page.html"
        ));
        root.put("anti_bot", Map.of(
            "enabled", true,
            "profile", "chrome-stealth",
            "proxy_pool", "local",
            "session_mode", "sticky",
            "stealth", true,
            "challenge_policy", "browser",
            "captcha_provider", "2captcha",
            "captcha_api_key", ""
        ));
        root.put("node_reverse", Map.of(
            "enabled", true,
            "base_url", "http://localhost:3000"
        ));
        root.put("middleware", Map.of(
            "user_agent_rotation", true,
            "respect_robots_txt", true,
            "min_request_interval_ms", 200
        ));
        root.put("pipeline", Map.of(
            "console", true,
            "dataset", true,
            "jsonl_path", "artifacts/exports/results.jsonl"
        ));
        root.put("auto_throttle", Map.of(
            "enabled", true,
            "start_delay_ms", 200,
            "max_delay_ms", 5000,
            "target_response_time_ms", 2000
        ));
        root.put("frontier", Map.of(
            "enabled", true,
            "autoscale", true,
            "min_concurrency", 1,
            "max_concurrency", 16,
            "lease_ttl_seconds", 30,
            "max_inflight_per_domain", 2,
            "checkpoint_id", "runtime-frontier",
            "checkpoint_dir", "artifacts/checkpoints/frontier"
        ));
        root.put("observability", Map.of(
            "structured_logs", true,
            "metrics", true,
            "trace", true,
            "failure_classification", true,
            "artifact_dir", "artifacts/observability"
        ));
        root.put("cache", Map.of(
            "enabled", true,
            "store_path", "artifacts/cache/incremental.json",
            "delta_fetch", true,
            "revalidate_seconds", 3600
        ));
        root.put("plugins", Map.of(
            "enabled", true,
            "manifest", "contracts/integration-catalog.json"
        ));
        root.put("scrapy", Map.of(
            "runner", "http",
            "plugins", List.of(),
            "pipelines", List.of(),
            "spider_middlewares", List.of(),
            "downloader_middlewares", List.of(),
            "component_config", Map.of(
                "field_injector", Map.of("fields", Map.of()),
                "request_headers", Map.of("headers", Map.of())
            ),
            "spiders", Map.of(
                "demo", Map.of(
                    "runner", "http",
                    "url", "https://example.com",
                    "pipelines", List.of(),
                    "spider_middlewares", List.of(),
                    "downloader_middlewares", List.of(),
                    "component_config", Map.of()
                )
            )
        ));
        root.put("storage", Map.of(
            "checkpoint_dir", "artifacts/checkpoints",
            "dataset_dir", "artifacts/datasets",
            "export_dir", "artifacts/exports"
        ));
        root.put("export", Map.of(
            "format", "json",
            "output_path", "artifacts/exports/results.json"
        ));
        root.put("doctor", Map.of(
            "network_targets", List.of("https://example.com")
        ));
        return root;
    }

    private static void writeContractConfig(Path output, String runtime) throws IOException {
        ensureParentDirectory(output);
        String yaml = new Yaml().dump(defaultContractConfig(runtime));
        Files.writeString(output, yaml);
    }

    private static Map<String, Object> readContractConfig(Path path) {
        Map<String, Object> merged = new LinkedHashMap<>(defaultContractConfig("java"));
        try {
            String content = Files.readString(path);
            Object loaded;
            if (path.toString().endsWith(".json")) {
                loaded = new ObjectMapper().readValue(content, new TypeReference<Map<String, Object>>() {});
            } else {
                loaded = new Yaml().load(content);
            }
            if (!(loaded instanceof Map<?, ?> parsed)) {
                throw new IllegalArgumentException("config root must be an object");
            }
            mergeNestedMap(merged, parsed);
            return merged;
        } catch (IOException e) {
            throw new IllegalArgumentException("failed to read config: " + e.getMessage(), e);
        }
    }

    @SuppressWarnings("unchecked")
    private static void mergeNestedMap(Map<String, Object> target, Map<?, ?> source) {
        for (Map.Entry<?, ?> entry : source.entrySet()) {
            Object key = entry.getKey();
            Object value = entry.getValue();
            if (!(key instanceof String stringKey)) {
                continue;
            }
            Object existing = target.get(stringKey);
            if (existing instanceof Map<?, ?> existingMap && value instanceof Map<?, ?> valueMap) {
                Map<String, Object> nested = new LinkedHashMap<>((Map<String, Object>) existingMap);
                mergeNestedMap(nested, valueMap);
                target.put(stringKey, nested);
            } else {
                target.put(stringKey, value);
            }
        }
    }

    private static Map<String, Object> validateContractConfig(Map<String, Object> cfg, String expectedRuntime) {
        List<String> errors = new ArrayList<>();
        Object version = cfg.get("version");
        if (!(version instanceof Number) || ((Number) version).intValue() < 1) {
            errors.add("version must be an integer >= 1");
        }

        Map<String, Object> project = nestedMap(cfg, "project");
        if (stringValue(project.get("name"), "").isBlank()) {
            errors.add("project.name must be a non-empty string");
        }

        if (!expectedRuntime.equals(cfg.get("runtime"))) {
            errors.add("runtime mismatch: expected '" + expectedRuntime + "', got '" + cfg.get("runtime") + "'");
        }

        Map<String, Object> crawl = nestedMap(cfg, "crawl");
        Object urls = crawl.get("urls");
        if (!(urls instanceof List<?>) || ((List<?>) urls).isEmpty()) {
            errors.add("crawl.urls must be a non-empty string array");
        }
        validateInteger(errors, crawl, "concurrency", 1, "crawl");
        validateInteger(errors, crawl, "max_requests", 1, "crawl");
        validateInteger(errors, crawl, "max_depth", 0, "crawl");
        validateInteger(errors, crawl, "timeout_seconds", 1, "crawl");

        Map<String, Object> browser = nestedMap(cfg, "browser");
        validateBoolean(errors, browser, "enabled", "browser");
        validateBoolean(errors, browser, "headless", "browser");
        validateInteger(errors, browser, "timeout_seconds", 1, "browser");
        validateString(errors, browser, "user_agent", "browser", true);
        validateString(errors, browser, "screenshot_path", "browser", false);
        validateString(errors, browser, "html_path", "browser", false);

        Map<String, Object> antiBot = nestedMap(cfg, "anti_bot");
        validateBoolean(errors, antiBot, "enabled", "anti_bot");
        validateString(errors, antiBot, "profile", "anti_bot", false);
        validateString(errors, antiBot, "proxy_pool", "anti_bot", false);
        validateString(errors, antiBot, "session_mode", "anti_bot", false);
        validateBoolean(errors, antiBot, "stealth", "anti_bot");
        validateString(errors, antiBot, "challenge_policy", "anti_bot", false);
        validateString(errors, antiBot, "captcha_provider", "anti_bot", false);
        validateString(errors, antiBot, "captcha_api_key", "anti_bot", true);

        Map<String, Object> nodeReverse = nestedMap(cfg, "node_reverse");
        validateBoolean(errors, nodeReverse, "enabled", "node_reverse");
        validateString(errors, nodeReverse, "base_url", "node_reverse", false);

        Map<String, Object> storage = nestedMap(cfg, "storage");
        validateString(errors, storage, "checkpoint_dir", "storage", false);
        validateString(errors, storage, "dataset_dir", "storage", false);
        validateString(errors, storage, "export_dir", "storage", false);

        Map<String, Object> export = nestedMap(cfg, "export");
        validateString(errors, export, "output_path", "export", false);
        String exportFormat = stringValue(export.get("format"), "");
        if (!List.of("json", "jsonl", "csv", "md").contains(exportFormat)) {
            errors.add("export.format must be one of [json, jsonl, csv, md]");
        }
        Map<String, Object> frontier = nestedMap(cfg, "frontier");
        validateBoolean(errors, frontier, "enabled", "frontier");
        validateBoolean(errors, frontier, "autoscale", "frontier");
        validateInteger(errors, frontier, "min_concurrency", 1, "frontier");
        validateInteger(errors, frontier, "max_concurrency", 1, "frontier");
        validateInteger(errors, frontier, "lease_ttl_seconds", 1, "frontier");
        validateInteger(errors, frontier, "max_inflight_per_domain", 1, "frontier");
        validateString(errors, frontier, "checkpoint_id", "frontier", false);
        validateString(errors, frontier, "checkpoint_dir", "frontier", false);
        Map<String, Object> observability = nestedMap(cfg, "observability");
        validateBoolean(errors, observability, "structured_logs", "observability");
        validateBoolean(errors, observability, "metrics", "observability");
        validateBoolean(errors, observability, "trace", "observability");
        validateBoolean(errors, observability, "failure_classification", "observability");
        validateString(errors, observability, "artifact_dir", "observability", false);
        Map<String, Object> cache = nestedMap(cfg, "cache");
        validateBoolean(errors, cache, "enabled", "cache");
        validateString(errors, cache, "store_path", "cache", false);
        validateBoolean(errors, cache, "delta_fetch", "cache");
        validateInteger(errors, cache, "revalidate_seconds", 1, "cache");
        Map<String, Object> scrapy = nestedMap(cfg, "scrapy");
        validateStringArray(errors, scrapy.get("plugins"), "scrapy.plugins");
        validateStringArray(errors, scrapy.get("pipelines"), "scrapy.pipelines");
        validateStringArray(errors, scrapy.get("spider_middlewares"), "scrapy.spider_middlewares");
        validateStringArray(errors, scrapy.get("downloader_middlewares"), "scrapy.downloader_middlewares");
        validateAllowedValues(errors, stringListValue(scrapy.get("pipelines")), "scrapy.pipelines", Set.of("field-injector"));
        validateAllowedValues(errors, stringListValue(scrapy.get("spider_middlewares")), "scrapy.spider_middlewares", Set.of("response-context"));
        validateAllowedValues(errors, stringListValue(scrapy.get("downloader_middlewares")), "scrapy.downloader_middlewares", Set.of("request-headers"));
        Object spiderConfigs = scrapy.get("spiders");
        if (spiderConfigs instanceof Map<?, ?> spiderMap) {
            for (Map.Entry<?, ?> entry : spiderMap.entrySet()) {
                if (!(entry.getKey() instanceof String spiderName) || !(entry.getValue() instanceof Map<?, ?> raw)) {
                    continue;
                }
                @SuppressWarnings("unchecked")
                Map<String, Object> typed = (Map<String, Object>) raw;
                String prefix = "scrapy.spiders." + spiderName;
                validateStringArray(errors, typed.get("pipelines"), prefix + ".pipelines");
                validateStringArray(errors, typed.get("spider_middlewares"), prefix + ".spider_middlewares");
                validateStringArray(errors, typed.get("downloader_middlewares"), prefix + ".downloader_middlewares");
                validateAllowedValues(errors, stringListValue(typed.get("pipelines")), prefix + ".pipelines", Set.of("field-injector"));
                validateAllowedValues(errors, stringListValue(typed.get("spider_middlewares")), prefix + ".spider_middlewares", Set.of("response-context"));
                validateAllowedValues(errors, stringListValue(typed.get("downloader_middlewares")), prefix + ".downloader_middlewares", Set.of("request-headers"));
            }
        }

        Object doctor = cfg.get("doctor");
        if (doctor != null && !(doctor instanceof Map<?, ?>)) {
            errors.add("doctor must be an object");
        }

        if (!errors.isEmpty()) {
            throw new IllegalArgumentException(String.join("; ", errors));
        }
        return cfg;
    }

    private static void validateInteger(List<String> errors, Map<String, Object> section, String key, int minimum, String name) {
        Object value = section.get(key);
        if (!(value instanceof Number) || ((Number) value).intValue() < minimum) {
            errors.add(name + "." + key + " must be an integer >= " + minimum);
        }
    }

    private static void validateBoolean(List<String> errors, Map<String, Object> section, String key, String name) {
        if (!(section.get(key) instanceof Boolean)) {
            errors.add(name + "." + key + " must be a boolean");
        }
    }

    private static void validateString(List<String> errors, Map<String, Object> section, String key, String name, boolean allowEmpty) {
        Object value = section.get(key);
        if (!(value instanceof String stringValue)) {
            errors.add(name + "." + key + " must be a string");
            return;
        }
        if (!allowEmpty && stringValue.isBlank()) {
            errors.add(name + "." + key + " must be a non-empty string");
        }
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> nestedMap(Map<String, Object> root, String key) {
        Object value = root.get(key);
        if (value instanceof Map) {
            return (Map<String, Object>) value;
        }
        return new HashMap<>();
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

    private static List<ProjectRuntime.PluginSpec> configuredScrapyPluginSpecs(Map<String, Object> cfg) {
        return stringListValue(nestedMap(cfg, "scrapy").get("plugins")).stream()
            .map(name -> new ProjectRuntime.PluginSpec(name, true, 0, Map.of()))
            .toList();
    }

    private static List<String> configuredScrapyPipelines(Map<String, Object> cfg) {
        return stringListValue(nestedMap(cfg, "scrapy").get("pipelines"));
    }

    private static List<String> configuredScrapyPipelines(Map<String, Object> cfg, String spiderName) {
        return mergeUniqueStrings(
            configuredScrapyPipelines(cfg),
            stringListValue(nestedSpiderScrapyMap(cfg, spiderName).get("pipelines"))
        );
    }

    private static List<String> configuredScrapySpiderMiddlewares(Map<String, Object> cfg) {
        return stringListValue(nestedMap(cfg, "scrapy").get("spider_middlewares"));
    }

    private static List<String> configuredScrapySpiderMiddlewares(Map<String, Object> cfg, String spiderName) {
        return mergeUniqueStrings(
            configuredScrapySpiderMiddlewares(cfg),
            stringListValue(nestedSpiderScrapyMap(cfg, spiderName).get("spider_middlewares"))
        );
    }

    private static List<String> configuredScrapyDownloaderMiddlewares(Map<String, Object> cfg) {
        return stringListValue(nestedMap(cfg, "scrapy").get("downloader_middlewares"));
    }

    private static List<String> configuredScrapyDownloaderMiddlewares(Map<String, Object> cfg, String spiderName) {
        return mergeUniqueStrings(
            configuredScrapyDownloaderMiddlewares(cfg),
            stringListValue(nestedSpiderScrapyMap(cfg, spiderName).get("downloader_middlewares"))
        );
    }

    private static List<String> mergeUniqueStrings(List<String> base, List<String> overlay) {
        LinkedHashSet<String> values = new LinkedHashSet<>();
        for (String value : base) {
            if (value != null && !value.isBlank()) {
                values.add(value.trim());
            }
        }
        for (String value : overlay) {
            if (value != null && !value.isBlank()) {
                values.add(value.trim());
            }
        }
        return new ArrayList<>(values);
    }

    private static Map<String, Object> nestedSpiderScrapyMap(Map<String, Object> cfg, String spiderName) {
        if (spiderName == null || spiderName.isBlank()) {
            return Map.of();
        }
        Object spiders = nestedMap(cfg, "scrapy").get("spiders");
        if (spiders instanceof Map<?, ?> spiderMap) {
            Object value = spiderMap.get(spiderName);
            if (value instanceof Map<?, ?> nested) {
                @SuppressWarnings("unchecked")
                Map<String, Object> typed = (Map<String, Object>) nested;
                return typed;
            }
        }
        return Map.of();
    }

    private static void validateStringArray(List<String> errors, Object value, String name) {
        if (value == null) {
            return;
        }
        if (!(value instanceof List<?> list)) {
            errors.add(name + " must be a string array");
            return;
        }
        for (Object item : list) {
            if (!(item instanceof String stringValue) || stringValue.isBlank()) {
                errors.add(name + " must be a string array");
                break;
            }
        }
    }

    private static void validateAllowedValues(List<String> errors, List<String> values, String name, Set<String> allowed) {
        for (String value : values) {
            if (!allowed.contains(value)) {
                errors.add(name + " contains unsupported component: " + value);
            }
        }
    }

    private static List<String> enabledPluginSpecNames(List<ProjectRuntime.PluginSpec> specs) {
        if (specs == null || specs.isEmpty()) {
            return List.of();
        }
        return specs.stream()
            .filter(ProjectRuntime.PluginSpec::enabled)
            .map(ProjectRuntime.PluginSpec::name)
            .filter(name -> name != null && !name.isBlank())
            .toList();
    }

    private static void appendDeclarativeComponentChecks(List<Map<String, Object>> checks, Map<String, Object> cfg) {
        List<String> pipelines = configuredScrapyPipelines(cfg);
        List<String> spiderMiddlewares = configuredScrapySpiderMiddlewares(cfg);
        List<String> downloaderMiddlewares = configuredScrapyDownloaderMiddlewares(cfg);
        checks.add(Map.of(
            "name", "components",
            "status", "passed",
            "details", "pipelines=" + pipelines.size()
                + " spider_middlewares=" + spiderMiddlewares.size()
                + " downloader_middlewares=" + downloaderMiddlewares.size()
        ));
        for (String name : pipelines) {
            checks.add(Map.of("name", "pipeline:" + name, "status", "passed", "details", "declarative pipeline"));
        }
        for (String name : spiderMiddlewares) {
            checks.add(Map.of("name", "spider_middleware:" + name, "status", "passed", "details", "declarative spider middleware"));
        }
        for (String name : downloaderMiddlewares) {
            checks.add(Map.of("name", "downloader_middleware:" + name, "status", "passed", "details", "declarative downloader middleware"));
        }
    }

    private static String firstConfiguredUrl(Map<String, Object> cfg) {
        Object urls = nestedMap(cfg, "crawl").get("urls");
        if (urls instanceof List && !((List<?>) urls).isEmpty()) {
            return String.valueOf(((List<?>) urls).get(0));
        }
        return null;
    }

    private static String loadHtmlInput(String url, String htmlFile) throws IOException {
        if (htmlFile != null && !htmlFile.isBlank()) {
            return Files.readString(Paths.get(htmlFile));
        }
        if (url == null || url.isBlank()) {
            return "";
        }
        try (InputStream inputStream = new URL(url).openStream()) {
            return new String(inputStream.readAllBytes(), StandardCharsets.UTF_8);
        }
    }

    private static String resolveScrapyRunner(Map<String, Object> cfg, String spiderName, Map<String, Object> metadata) {
        return resolveScrapyRunnerDetail(cfg, spiderName, metadata)[0];
    }

    private static String[] resolveScrapyRunnerDetail(Map<String, Object> cfg, String spiderName, Map<String, Object> metadata) {
        String metadataRunner = normalizeScrapyRunner(stringValue(metadata.get("runner"), ""));
        if (!metadataRunner.isBlank()) {
            return new String[]{metadataRunner, "metadata"};
        }
        Map<String, Object> scrapy = nestedMap(cfg, "scrapy");
        Object spiders = scrapy.get("spiders");
        if (spiders instanceof Map<?, ?> spiderMap && spiderName != null && !spiderName.isBlank()) {
            Object spiderValue = spiderMap.get(spiderName);
            if (spiderValue instanceof Map<?, ?> raw) {
                @SuppressWarnings("unchecked")
                Map<String, Object> typed = (Map<String, Object>) raw;
                String runner = normalizeScrapyRunner(stringValue(typed.get("runner"), ""));
                if (!runner.isBlank()) {
                    return new String[]{runner, "scrapy.spiders"};
                }
            }
        }
        String runner = normalizeScrapyRunner(stringValue(scrapy.get("runner"), ""));
        if (!runner.isBlank()) {
            return new String[]{runner, "scrapy.runner"};
        }
        return new String[]{"http", "default"};
    }

    private static String[] resolveScrapyUrlDetail(Map<String, Object> cfg, String spiderName, Map<String, Object> metadata, String manifestUrl) {
        Map<String, Object> scrapy = nestedMap(cfg, "scrapy");
        Object spiders = scrapy.get("spiders");
        if (spiders instanceof Map<?, ?> spiderMap && spiderName != null && !spiderName.isBlank()) {
            Object spiderValue = spiderMap.get(spiderName);
            if (spiderValue instanceof Map<?, ?> raw) {
                @SuppressWarnings("unchecked")
                Map<String, Object> typed = (Map<String, Object>) raw;
                String configuredUrl = stringValue(typed.get("url"), "");
                if (!configuredUrl.isBlank()) {
                    return new String[]{configuredUrl, "scrapy.spiders"};
                }
            }
        }
        String metadataUrl = stringValue(metadata.get("url"), "");
        if (!metadataUrl.isBlank()) {
            return new String[]{metadataUrl, "metadata"};
        }
        if (manifestUrl != null && !manifestUrl.isBlank()) {
            return new String[]{manifestUrl, "manifest"};
        }
        return new String[]{"https://example.com", "default"};
    }

    private static String normalizeScrapyRunner(String value) {
        String normalized = value == null ? "" : value.trim().toLowerCase();
        return switch (normalized) {
            case "browser", "http", "hybrid" -> normalized;
            default -> "";
        };
    }

    private static Spider.Response browserResponseForScrapy(Spider.Request request, Map<String, Object> cfg) {
        Map<String, Object> merged = new LinkedHashMap<>(cfg);
        Map<String, Object> browser = new LinkedHashMap<>(nestedMap(merged, "browser"));
        Object timeout = request.getMeta().get("browser_timeout_seconds");
        if (timeout instanceof Number number && number.intValue() > 0) {
            browser.put("timeout_seconds", number.intValue());
        }
        Object htmlPath = request.getMeta().get("browser_html_path");
        if (htmlPath instanceof String string && !string.isBlank()) {
            browser.put("html_path", string);
        }
        Object screenshotPath = request.getMeta().get("browser_screenshot_path");
        if (screenshotPath instanceof String string && !string.isBlank()) {
            browser.put("screenshot_path", string);
        }
        Object browserMeta = request.getMeta().get("browser");
        if (browserMeta instanceof Map<?, ?> raw) {
            @SuppressWarnings("unchecked")
            Map<String, Object> typed = (Map<String, Object>) raw;
            browser.putAll(typed);
        }
        merged.put("browser", browser);
        String screenshot = stringValue(browser.get("screenshot_path"), "artifacts/browser/page.png");
        String html = stringValue(browser.get("html_path"), "artifacts/browser/page.html");
        BrowserFetchRunner runner = browserFetchRunnerFactory.get();
        try {
            BrowserFetchResult result = runner.fetch(request.getUrl(), screenshot, html, merged);
            String body = Files.readString(Paths.get(html));
            return new Spider.Response(
                stringValue(result.url, request.getUrl()),
                200,
                Map.of("x-browser-runner", "playwright"),
                body,
                request
            );
        } catch (IOException e) {
            throw new RuntimeException("browser scrapy fetch failed", e);
        } finally {
            runner.close();
        }
    }

    private static List<Spider.ItemPipeline> buildDeclarativeScrapyPipelines(Map<String, Object> cfg, String spiderName) {
        List<Spider.ItemPipeline> pipelines = new ArrayList<>();
        for (String value : configuredScrapyPipelines(cfg, spiderName)) {
            if (!"field-injector".equals(value.trim())) {
                continue;
            }
            Map<String, Object> component = nestedComponentConfig(cfg, spiderName, "field_injector");
            Map<String, Object> fields = nestedMap(component, "fields");
            pipelines.add((item, spider) -> {
                Item current = item;
                for (Map.Entry<String, Object> entry : fields.entrySet()) {
                    current = current.set(entry.getKey(), entry.getValue());
                }
                return current;
            });
        }
        return pipelines;
    }

    private static List<SpiderMiddleware> buildDeclarativeScrapySpiderMiddlewares(Map<String, Object> cfg, String spiderName) {
        List<SpiderMiddleware> middlewares = new ArrayList<>();
        for (String value : configuredScrapySpiderMiddlewares(cfg, spiderName)) {
            if (!"response-context".equals(value.trim())) {
                continue;
            }
            middlewares.add((response, result, spider) -> {
                List<Object> enriched = new ArrayList<>();
                for (Object entry : result) {
                    if (entry instanceof Item item) {
                        enriched.add(item.set("response_url", response.getUrl()).set("response_status", response.getStatusCode()));
                    } else if (entry instanceof Map<?, ?> map) {
                        @SuppressWarnings("unchecked")
                        Map<String, Object> typed = (Map<String, Object>) map;
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
        return middlewares;
    }

    private static List<DownloaderMiddleware> buildDeclarativeScrapyDownloaderMiddlewares(Map<String, Object> cfg, String spiderName) {
        List<DownloaderMiddleware> middlewares = new ArrayList<>();
        for (String value : configuredScrapyDownloaderMiddlewares(cfg, spiderName)) {
            if (!"request-headers".equals(value.trim())) {
                continue;
            }
            Map<String, Object> component = nestedComponentConfig(cfg, spiderName, "request_headers");
            Map<String, Object> headers = nestedMap(component, "headers");
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
        return middlewares;
    }

    private static List<String> collectJavaPipelineNames(List<ScrapyPlugin> plugins, List<Spider.ItemPipeline> declarative) {
        List<String> names = new ArrayList<>();
        for (ScrapyPlugin plugin : plugins) {
            for (Spider.ItemPipeline pipeline : plugin.providePipelines()) {
                names.add(javaComponentName(pipeline));
            }
        }
        return names;
    }

    private static List<String> collectJavaSpiderMiddlewareNames(List<ScrapyPlugin> plugins, List<SpiderMiddleware> declarative) {
        List<String> names = new ArrayList<>();
        for (ScrapyPlugin plugin : plugins) {
            for (SpiderMiddleware middleware : plugin.provideSpiderMiddlewares()) {
                names.add(javaComponentName(middleware));
            }
        }
        return names;
    }

    private static List<String> collectJavaDownloaderMiddlewareNames(List<ScrapyPlugin> plugins, List<DownloaderMiddleware> declarative) {
        List<String> names = new ArrayList<>();
        for (ScrapyPlugin plugin : plugins) {
            for (DownloaderMiddleware middleware : plugin.provideDownloaderMiddlewares()) {
                names.add(javaComponentName(middleware));
            }
        }
        return names;
    }

    private static String javaComponentName(Object value) {
        return value.getClass().getSimpleName().isBlank()
            ? value.getClass().getName()
            : value.getClass().getSimpleName();
    }

    private static List<String> stringList(Object value) {
        List<String> values = new ArrayList<>();
        if (value instanceof List<?> list) {
            for (Object item : list) {
                String stringValue = String.valueOf(item).trim();
                if (!stringValue.isBlank()) {
                    values.add(stringValue);
                }
            }
        }
        return values;
    }

    private static Map<String, Object> nestedComponentConfig(Map<String, Object> cfg, String key) {
        Map<String, Object> scrapy = nestedMap(cfg, "scrapy");
        Object componentConfig = scrapy.get("component_config");
        if (componentConfig instanceof Map<?, ?> map) {
            Object value = map.get(key);
            if (value instanceof Map<?, ?> nested) {
                @SuppressWarnings("unchecked")
                Map<String, Object> typed = (Map<String, Object>) nested;
                return typed;
            }
        }
        return Map.of();
    }

    private static Map<String, Object> nestedComponentConfig(Map<String, Object> cfg, String spiderName, String key) {
        Map<String, Object> merged = new LinkedHashMap<>(nestedComponentConfig(cfg, key));
        Map<String, Object> spiderCfg = nestedSpiderScrapyMap(cfg, spiderName);
        Object spiderComponentConfig = spiderCfg.get("component_config");
        if (spiderComponentConfig instanceof Map<?, ?> map) {
            Object value = map.get(key);
            if (value instanceof Map<?, ?> nested) {
                @SuppressWarnings("unchecked")
                Map<String, Object> typed = (Map<String, Object>) nested;
                mergeObjectMaps(merged, typed);
            }
        }
        return merged;
    }

    @SuppressWarnings("unchecked")
    private static void mergeObjectMaps(Map<String, Object> target, Map<String, Object> overlay) {
        for (Map.Entry<String, Object> entry : overlay.entrySet()) {
            Object existing = target.get(entry.getKey());
            Object value = entry.getValue();
            if (existing instanceof Map<?, ?> existingMap && value instanceof Map<?, ?> valueMap) {
                Map<String, Object> nested = new LinkedHashMap<>((Map<String, Object>) existingMap);
                mergeObjectMaps(nested, (Map<String, Object>) valueMap);
                target.put(entry.getKey(), nested);
            } else {
                target.put(entry.getKey(), value);
            }
        }
    }

    private static List<String> localAntiBotSignals(String html, int statusCode) {
        List<String> signals = new ArrayList<>();
        String lower = html.toLowerCase();
        if (lower.contains("captcha")) {
            signals.add("captcha");
        }
        if (lower.contains("cf-ray") || lower.contains("just a moment")) {
            signals.add("vendor:cloudflare");
        }
        if (lower.contains("datadome")) {
            signals.add("vendor:datadome");
        }
        if (lower.contains("akamai")) {
            signals.add("vendor:akamai");
        }
        if (statusCode == 403) {
            signals.add("status:403");
        }
        if (statusCode == 429) {
            signals.add("status:429");
        }
        if (signals.isEmpty()) {
            signals.add("clear");
        }
        return signals;
    }

    private static Map<String, Object> localSiteProfilePayload(String url, String html) {
        String lower = html.toLowerCase();
        String pageType;
        if (lower.contains("<article") || lower.contains("<h1")) {
            pageType = "detail";
        } else if (lower.contains("<li") || lower.contains("<ul")) {
            pageType = "list";
        } else {
            pageType = "generic";
        }
        List<String> candidateFields = new ArrayList<>();
        if (lower.contains("<title")) candidateFields.add("title");
        if (lower.contains("price")) candidateFields.add("price");
        if (lower.contains("author")) candidateFields.add("author");
        if (lower.contains("date")) candidateFields.add("date");

        List<String> signals = localAntiBotSignals(html, 200);
        String riskLevel = (signals.contains("captcha") || signals.contains("vendor:cloudflare"))
            ? "high"
            : (lower.contains("<form") ? "medium" : "low");
        String recommendedRuntime = "low".equals(riskLevel)
            ? ("detail".equals(pageType) ? "python" : "go")
            : "java";

        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("command", "profile-site");
        payload.put("runtime", "java");
        payload.put("url", url);
        payload.put("page_type", pageType);
        payload.put("candidate_fields", candidateFields);
        payload.put("signals", signals);
        payload.put("risk_level", riskLevel);
        payload.put("recommended_runtime", recommendedRuntime);
        payload.put("anti_bot_recommended", !"low".equals(riskLevel));
        payload.put("node_reverse_recommended", false);
        return payload;
    }

    private static Map<String, Object> schemaFromCandidateFields(List<String> fields) {
        List<String> ordered = new ArrayList<>(List.of("title", "summary", "url"));
        for (String field : fields) {
            if (!ordered.contains(field)) {
                ordered.add(field);
            }
        }
        Map<String, Object> properties = new LinkedHashMap<>();
        for (String field : ordered) {
            String lower = field.toLowerCase();
            if (lower.contains("price") || lower.contains("amount") || lower.contains("score") || lower.contains("rating")) {
                properties.put(field, Map.of("type", "number"));
            } else if (lower.contains("count") || lower.contains("total")) {
                properties.put(field, Map.of("type", "integer"));
            } else if (lower.contains("images") || lower.contains("links") || lower.contains("tags") || lower.contains("items")) {
                properties.put(field, Map.of("type", "array", "items", Map.of("type", "string")));
            } else {
                properties.put(field, Map.of("type", "string"));
            }
        }
        return Map.of("type", "object", "properties", properties);
    }

    private static Map<String, Object> buildJavaAIBlueprint(String resolvedUrl, String spiderName, Map<String, Object> profile, Map<String, Object> schema, String html) {
        @SuppressWarnings("unchecked")
        List<String> candidateFields = new ArrayList<>((List<String>) profile.getOrDefault("candidate_fields", List.of()));
        Map<String, Object> properties = nestedMap(schema, "properties");
        List<String> fieldNames = new ArrayList<>(properties.keySet());
        fieldNames.sort(String::compareTo);
        String lower = stringValue(html, "").toLowerCase();
        Map<String, Object> blueprint = new LinkedHashMap<>();
        blueprint.put("version", 1);
        blueprint.put("spider_name", spiderName);
        blueprint.put("resolved_url", resolvedUrl);
        blueprint.put("page_type", profile.get("page_type"));
        blueprint.put("candidate_fields", candidateFields);
        blueprint.put("schema", schema);
        blueprint.put("extraction_prompt", "请从页面中提取以下字段，并只返回 JSON：" + String.join(", ", fieldNames) + "。缺失字段返回空字符串或空数组。");
        blueprint.put("follow_rules", List.of(Map.of(
            "name", "same-domain-content",
            "enabled", true,
            "description", "优先跟进同域详情页和内容页链接"
        )));
        blueprint.put("pagination", Map.of(
            "enabled", List.of("list", "generic").contains(stringValue(profile.get("page_type"), "generic")) || lower.contains("rel=\"next\"") || lower.contains("pagination") || lower.contains("page=") || lower.contains("next page") || lower.contains("下一页"),
            "strategy", "follow next page or numbered pagination links",
            "selectors", List.of("a[rel='next']", ".next", ".pagination a")
        ));
        boolean authRequired = lower.contains("type=\"password\"") || lower.contains("type='password'") || lower.contains("login") || lower.contains("sign in") || lower.contains("signin") || lower.contains("登录");
        boolean jsRequired = lower.contains("__next_data__") || lower.contains("window.__") || lower.contains("webpack") || lower.contains("fetch(") || lower.contains("graphql") || lower.contains("xhr");
        boolean reverseRequired = lower.contains("crypto") || lower.contains("signature") || lower.contains("token") || lower.contains("webpack") || lower.contains("obfusc") || lower.contains("encrypt") || lower.contains("decrypt");
        blueprint.put("authentication", Map.of(
            "required", authRequired,
            "strategy", authRequired ? "capture session/login flow before crawl" : "not required"
        ));
        blueprint.put("javascript_runtime", Map.of(
            "required", jsRequired,
            "recommended_runner", jsRequired ? "browser" : "http"
        ));
        blueprint.put("reverse_engineering", Map.of(
            "required", reverseRequired,
            "notes", reverseRequired ? "inspect network/API signing or obfuscated scripts" : "not required"
        ));
        blueprint.put("anti_bot_strategy", Map.of(
            "risk_level", profile.get("risk_level"),
            "signals", profile.get("signals"),
            "recommended_runner", "low".equals(stringValue(profile.get("risk_level"), "low")) ? "http" : "browser",
            "notes", "高风险页面建议先走浏览器模式并降低抓取速率"
        ));
        return blueprint;
    }

    private static String deriveDomainFromUrl(String raw) {
        try {
            URI uri = URI.create(raw);
            if (uri.getHost() != null && !uri.getHost().isBlank()) {
                return uri.getHost();
            }
        } catch (Exception ignored) {
        }
        return "example.com";
    }

    private static Map<String, Object> authValidationStatus(String html) {
        String lower = stringValue(html, "").toLowerCase();
        List<String> indicators = new ArrayList<>();
        if (lower.contains("type=\"password\"") || lower.contains("type='password'")) {
            indicators.add("password-input");
        }
        if (lower.contains("login") || lower.contains("sign in") || lower.contains("signin") || lower.contains("登录")) {
            indicators.add("login-marker");
        }
        return Map.of("authenticated", indicators.isEmpty(), "indicators", indicators);
    }

    private static String renderJavaAISpiderTemplate(String spiderName, String spiderDomain) {
        String className = spiderName.substring(0, 1).toUpperCase() + spiderName.substring(1) + "SpiderFactory";
        return """
            package project.spiders;

            // scrapy: name=%s url=https://%s

            import com.fasterxml.jackson.core.type.TypeReference;
            import com.javaspider.ai.AIExtractor;
            import com.javaspider.scrapy.Spider;
            import com.javaspider.scrapy.item.Item;
            import com.javaspider.scrapy.project.ProjectRuntime;

            import java.util.ArrayList;
            import java.util.LinkedHashMap;
            import java.util.List;
            import java.util.Map;

            public final class %s {
                private %s() {
                }

                public static Spider create() {
                    Map<String, Object> assets = ProjectRuntime.loadAIProjectAssets(java.nio.file.Path.of("."));
                    Spider spider = new Spider() {
                        {
                            setName("%s");
                            addStartUrl("https://%s");
                        }

                        @Override
                        public List<Object> parse(Spider.Response response) {
                            Map<String, Object> data = new LinkedHashMap<>();
                            data.put("title", response.selector().css("title").firstText());
                            data.put("summary", response.selector().xpath("//meta[@name='description']/@content").firstText());
                            data.put("url", response.getUrl());
                            try {
                                data = AIExtractor.fromEnv().extractStructured(
                                    response.getBody(),
                                    String.valueOf(assets.get("extraction_prompt")),
                                    (Map<String, Object>) assets.get("schema")
                                );
                            } catch (Exception ignored) {
                            }
                            data.putIfAbsent("url", response.getUrl());
                            data.put("framework", "javaspider-ai");
                            List<Object> outputs = new ArrayList<>();
                            outputs.add(Item.fromMap(data));
                            for (Spider.Request request : ProjectRuntime.collectAIPaginationRequests(response, this::parse, assets)) {
                                outputs.add(request);
                            }
                            return outputs;
                        }
                    };
                    return ProjectRuntime.applyAIStartMeta(spider, assets);
                }

                public static void register() {
                    ProjectRuntime.registerSpider("%s", %s::create);
                }
            }
            """.formatted(spiderName, spiderDomain, className, className, spiderName, spiderDomain, spiderName, className);
    }

    private static String detectAIMode(String instructions, String question, String description, String schemaFile, String schemaJson) {
        if (!description.isBlank()) {
            return "generate-config";
        }
        if (!question.isBlank()) {
            return "understand";
        }
        if (!instructions.isBlank() || !schemaFile.isBlank() || !schemaJson.isBlank()) {
            return "extract";
        }
        return "understand";
    }

    private static Map<String, Object> loadAISchema(String schemaFile, String schemaJson) {
        ObjectMapper mapper = new ObjectMapper();
        try {
            if (!schemaFile.isBlank()) {
                return mapper.readValue(Files.readString(Paths.get(schemaFile)), new TypeReference<>() {});
            }
            if (!schemaJson.isBlank()) {
                return mapper.readValue(schemaJson, new TypeReference<>() {});
            }
        } catch (IOException e) {
            throw new RuntimeException("invalid ai schema", e);
        }
        return defaultAISchema();
    }

    private static Map<String, Object> defaultAISchema() {
        Map<String, Object> schema = new LinkedHashMap<>();
        Map<String, Object> properties = new LinkedHashMap<>();
        properties.put("title", Map.of("type", "string"));
        properties.put("url", Map.of("type", "string"));
        properties.put("summary", Map.of("type", "string"));
        schema.put("type", "object");
        schema.put("properties", properties);
        return schema;
    }

    private static Map<String, Object> heuristicAIExtract(String url, String html, Map<String, Object> schema) {
        Map<String, Object> properties = nestedMap(schema, "properties");
        if (properties.isEmpty()) {
            properties = nestedMap(defaultAISchema(), "properties");
        }
        String text = compactAIText(stripHtmlTags(html));
        Map<String, Object> result = new LinkedHashMap<>();
        for (Map.Entry<String, Object> entry : properties.entrySet()) {
            String fieldName = entry.getKey();
            String expectedType = stringValue(nestedMap(Map.of("spec", entry.getValue()), "spec").get("type"), "string");
            result.put(fieldName, heuristicAIFieldValue(fieldName, expectedType, url, html, text));
        }
        return result;
    }

    private static Object heuristicAIFieldValue(String fieldName, String expectedType, String url, String html, String text) {
        String lower = fieldName.toLowerCase();
        if (lower.contains("title") || lower.contains("headline")) {
            return firstNonEmpty(
                htmlMeta(html, "property", "og:title"),
                htmlTitle(html),
                htmlTagContent(html, "h1")
            );
        }
        if ("url".equals(lower) || lower.contains("link")) {
            return "array".equals(expectedType) ? List.of(url) : url;
        }
        if (lower.contains("summary") || lower.contains("description") || "desc".equals(lower)) {
            return firstNonEmpty(
                htmlMeta(html, "name", "description"),
                htmlMeta(html, "property", "og:description"),
                truncateAIText(text, 220)
            );
        }
        if (lower.contains("content") || lower.contains("body") || "text".equals(lower)) {
            return truncateAIText(text, 1200);
        }
        if (lower.contains("author")) {
            return firstNonEmpty(
                htmlMeta(html, "name", "author"),
                htmlMeta(html, "property", "article:author")
            );
        }
        if (lower.contains("date") || lower.contains("time") || lower.contains("published")) {
            return firstNonEmpty(
                htmlMeta(html, "property", "article:published_time"),
                htmlMeta(html, "name", "pubdate"),
                htmlAttribute(html, "time", "datetime")
            );
        }
        if (lower.contains("image") || lower.contains("thumbnail") || lower.contains("cover")) {
            return firstNonEmpty(
                htmlMeta(html, "property", "og:image"),
                htmlAttribute(html, "img", "src")
            );
        }
        if (lower.contains("price")) {
            return findToken(text, List.of("¥", "￥", "$", "usd", "rmb"));
        }
        return "array".equals(expectedType) ? new ArrayList<>() : "";
    }

    private static Map<String, Object> heuristicAIUnderstand(String url, String html, String question) {
        Map<String, Object> profile = localSiteProfilePayload(url, html);
        Map<String, Object> result = new LinkedHashMap<>();
        result.put(
            "answer",
            "页面类型=" + stringValue(profile.get("page_type"), "generic")
                + "，候选字段=" + profile.get("candidate_fields")
                + "，风险等级=" + stringValue(profile.get("risk_level"), "low")
                + "。问题：" + (question.isBlank() ? "请总结页面类型、核心内容和推荐提取字段。" : question)
        );
        result.put("page_profile", profile);
        return result;
    }

    private static Map<String, Object> heuristicAIGenerateConfig(String description) {
        List<String> fields = new ArrayList<>(List.of("title", "url", "summary"));
        String lower = description.toLowerCase();
        if (lower.contains("price") || description.contains("价格")) {
            fields.add("price");
        }
        if (lower.contains("author") || description.contains("作者")) {
            fields.add("author");
        }
        if (lower.contains("date") || description.contains("时间") || description.contains("日期")) {
            fields.add("published_at");
        }
        if (lower.contains("content") || description.contains("正文")) {
            fields.add("content");
        }
        List<String> startUrls = new ArrayList<>(List.of("https://example.com"));
        for (String token : description.split("\\s+")) {
            String cleaned = token.replaceAll("^[\\s,.;'\"()\\[\\]{}]+|[\\s,.;'\"()\\[\\]{}]+$", "");
            if (cleaned.startsWith("http://") || cleaned.startsWith("https://")) {
                startUrls = new ArrayList<>(List.of(cleaned));
                break;
            }
        }
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("start_urls", startUrls);
        payload.put("rules", List.of(Map.of(
            "name", "auto-generated",
            "pattern", ".*",
            "extract", fields,
            "follow_links", true
        )));
        payload.put("settings", Map.of("concurrency", 3, "max_depth", 2, "delay", 500));
        payload.put("source_description", description);
        return payload;
    }

    private static String htmlTitle(String html) {
        return firstNonEmpty(
            htmlMeta(html, "property", "og:title"),
            htmlTagContent(html, "title"),
            htmlTagContent(html, "h1")
        );
    }

    private static String htmlTagContent(String html, String tag) {
        java.util.regex.Matcher matcher = java.util.regex.Pattern.compile("<" + tag + "[^>]*>(.*?)</" + tag + ">", java.util.regex.Pattern.CASE_INSENSITIVE | java.util.regex.Pattern.DOTALL).matcher(html);
        if (matcher.find()) {
            return compactAIText(matcher.group(1));
        }
        return "";
    }

    private static String htmlMeta(String html, String attr, String name) {
        java.util.regex.Matcher matcher = java.util.regex.Pattern.compile(
            "<meta[^>]*" + attr + "=[\"']" + java.util.regex.Pattern.quote(name) + "[\"'][^>]*content=[\"']([^\"']+)[\"']",
            java.util.regex.Pattern.CASE_INSENSITIVE
        ).matcher(html);
        if (matcher.find()) {
            return matcher.group(1).trim();
        }
        return "";
    }

    private static String htmlAttribute(String html, String tag, String attr) {
        java.util.regex.Matcher matcher = java.util.regex.Pattern.compile(
            "<" + tag + "[^>]*" + attr + "=[\"']([^\"']+)[\"']",
            java.util.regex.Pattern.CASE_INSENSITIVE
        ).matcher(html);
        if (matcher.find()) {
            return matcher.group(1).trim();
        }
        return "";
    }

    private static String stripHtmlTags(String html) {
        return html.replaceAll("<[^>]+>", " ");
    }

    private static String compactAIText(String value) {
        return value == null ? "" : value.replaceAll("\\s+", " ").trim();
    }

    private static String truncateAIText(String value, int limit) {
        String compact = compactAIText(value);
        if (compact.length() <= limit) {
            return compact;
        }
        return compact.substring(0, limit).trim() + "...";
    }

    private static String truncateAIContent(String value, int limit) {
        if (value == null || value.length() <= limit) {
            return value;
        }
        return value.substring(0, limit);
    }

    private static String firstNonEmpty(String... values) {
        for (String value : values) {
            if (value != null && !value.isBlank()) {
                return value.trim();
            }
        }
        return "";
    }

    private static String findToken(String text, List<String> tokens) {
        for (String item : compactAIText(text).toLowerCase().split("\\s+")) {
            for (String token : tokens) {
                if (item.contains(token.toLowerCase())) {
                    return item.replaceAll("^[,.;:!?()\\[\\]{}\"']+|[,.;:!?()\\[\\]{}\"']+$", "");
                }
            }
        }
        return "";
    }

    private static List<String> extractSitemapUrls(String content) {
        List<String> urls = new ArrayList<>();
        java.util.regex.Matcher matcher = java.util.regex.Pattern.compile("<loc>(.*?)</loc>", java.util.regex.Pattern.DOTALL).matcher(content);
        while (matcher.find()) {
            String value = matcher.group(1).trim();
            if (!value.isBlank()) {
                urls.add(value);
            }
        }
        return urls;
    }

    private static List<String> discoverSitemapTargets(String seedUrl, Map<String, Object> sitemap) throws IOException {
        String source = stringValue(sitemap.get("url"), "");
        if (source.isBlank() && !seedUrl.isBlank()) {
            source = seedUrl.replaceAll("/+$", "") + "/sitemap.xml";
        }
        if (source.isBlank()) {
            return List.of();
        }
        String content = loadHtmlInput(source, "");
        List<String> urls = extractSitemapUrls(content);
        int maxUrls = integerValue(sitemap.get("max_urls"), 0);
        if (maxUrls > 0 && urls.size() > maxUrls) {
            return new ArrayList<>(urls.subList(0, maxUrls));
        }
        return urls;
    }

    private static List<String> mergeUniqueTargets(List<String> base, List<String> extra) {
        LinkedHashSet<String> merged = new LinkedHashSet<>();
        merged.addAll(base);
        merged.addAll(extra);
        return new ArrayList<>(merged);
    }

    private static String stringValue(Object value, String defaultValue) {
        if (value == null) {
            return defaultValue;
        }
        String stringValue = String.valueOf(value);
        return stringValue.isBlank() ? defaultValue : stringValue;
    }

    private static int integerValue(Object value, int defaultValue) {
        if (value instanceof Number number) {
            return number.intValue();
        }
        if (value != null) {
            try {
                return Integer.parseInt(String.valueOf(value));
            } catch (NumberFormatException ignored) {
            }
        }
        return defaultValue;
    }

    private static boolean boolValue(Object value, boolean defaultValue) {
        if (value instanceof Boolean bool) {
            return bool;
        }
        if (value instanceof Number number) {
            return number.intValue() != 0;
        }
        if (value != null) {
            String normalized = String.valueOf(value).trim().toLowerCase();
            if (normalized.equals("true") || normalized.equals("yes") || normalized.equals("on") || normalized.equals("1")) {
                return true;
            }
            if (normalized.equals("false") || normalized.equals("no") || normalized.equals("off") || normalized.equals("0")) {
                return false;
            }
        }
        return defaultValue;
    }

    private static void ensureParentDirectory(Path path) throws IOException {
        Path parent = path.getParent();
        if (parent != null && Files.notExists(parent)) {
            Files.createDirectories(parent);
        }
    }

    private static void validateScrapyPluginManifest(Path path) {
        try {
            Object payload = new ObjectMapper().readValue(Files.readString(path), Object.class);
            if (!(payload instanceof Map<?, ?> object)) {
                throw new IllegalArgumentException("plugin manifest must be an object");
            }
            Object version = object.get("version");
            if (version != null) {
                if (!(version instanceof Number number) || number.intValue() < 1) {
                    throw new IllegalArgumentException("plugin manifest version must be an integer >= 1");
                }
            }
            Object plugins = object.get("plugins");
            if (!(plugins instanceof List<?> list)) {
                throw new IllegalArgumentException("plugin manifest must contain a plugins array");
            }
            for (Object item : list) {
                if (item instanceof String name) {
                    if (name.isBlank()) {
                        throw new IllegalArgumentException("plugin name must be a non-empty string");
                    }
                    continue;
                }
                if (!(item instanceof Map<?, ?> pluginObject)) {
                    throw new IllegalArgumentException("plugin entries must be strings or objects");
                }
                Object name = pluginObject.get("name");
                if (!(name instanceof String string) || string.isBlank()) {
                    throw new IllegalArgumentException("plugin object must include a non-empty name");
                }
                Object enabled = pluginObject.get("enabled");
                if (enabled != null && !(enabled instanceof Boolean)) {
                    throw new IllegalArgumentException("plugin enabled must be a boolean");
                }
                Object priority = pluginObject.get("priority");
                if (priority != null && !(priority instanceof Number)) {
                    throw new IllegalArgumentException("plugin priority must be an integer");
                }
                Object config = pluginObject.get("config");
                if (config != null && !(config instanceof Map<?, ?>)) {
                    throw new IllegalArgumentException("plugin config must be an object");
                }
            }
        } catch (IOException e) {
            throw new RuntimeException("failed to read plugin manifest", e);
        }
    }

    private static void runJavaProjectArtifact(Path runnerJar, String project, String spider, String url, String htmlFile, String output) {
        try {
            Path projectRoot = Paths.get(project);
            List<String> javaCommand = new ArrayList<>();
            javaCommand.add("java");
            javaCommand.add("-jar");
            javaCommand.add(runnerJar.toString());
            ProcessBuilder builder = new ProcessBuilder(javaCommand).redirectErrorStream(true);
            Map<String, String> env = builder.environment();
            env.put("JAVASPIDER_SCRAPY_RUNNER", "1");
            env.put("JAVASPIDER_SCRAPY_PROJECT", project);
            env.put("JAVASPIDER_SCRAPY_URL", url);
            env.put("JAVASPIDER_SCRAPY_OUTPUT", output);
            try {
                Map<String, Object> cfg = loadContractConfig(projectRoot.resolve("spider-framework.yaml").toString());
                Map<String, Object> nodeReverse = nestedMap(cfg, "node_reverse");
                String reverseUrl = stringValue(nodeReverse.get("base_url"), "");
                if (!reverseUrl.isBlank()) {
                    env.put("JAVASPIDER_SCRAPY_REVERSE_URL", reverseUrl);
                }
            } catch (Exception ignored) {
            }
            if (spider != null && !spider.isBlank()) {
                env.put("JAVASPIDER_SCRAPY_SPIDER", spider);
            }
            if (htmlFile != null && !htmlFile.isBlank()) {
                env.put("JAVASPIDER_SCRAPY_HTML_FILE", htmlFile);
            }
            Process java = builder.start();
            String javaOutput = new String(java.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
            System.out.print(javaOutput);
            if (java.waitFor() != 0) {
                throw new IOException("project java runner failed: " + javaOutput);
            }
        } catch (IOException | InterruptedException e) {
            if (e instanceof InterruptedException) {
                Thread.currentThread().interrupt();
            }
            throw new RuntimeException("运行 scrapy project 失败", e);
        }
    }

    interface BrowserFetchRunner {
        BrowserFetchResult fetch(String url, String screenshotPath, String htmlPath, Map<String, Object> cfg) throws IOException;
        void close();
    }

    static class BrowserFetchResult {
        public String title;
        public String url;
        public String html_path;
        public String screenshot_path;
    }

    static class DefaultBrowserFetchRunner implements BrowserFetchRunner {
        @Override
        public BrowserFetchResult fetch(String url, String screenshotPath, String htmlPath, Map<String, Object> cfg) throws IOException {
            ensureParentDirectory(Paths.get(screenshotPath));
            ensureParentDirectory(Paths.get(htmlPath));

            List<String> command = new ArrayList<>();
            command.add(resolvePythonCommand());
            command.add(resolveHelperScript());
            command.add("--url");
            command.add(url);
            command.add("--timeout-seconds");
            command.add(String.valueOf(nestedMap(cfg, "browser").getOrDefault("timeout_seconds", 30)));
            if (screenshotPath != null && !screenshotPath.isBlank()) {
                command.add("--screenshot");
                command.add(screenshotPath);
            }
            if (htmlPath != null && !htmlPath.isBlank()) {
                command.add("--html");
                command.add(htmlPath);
            }
            String userAgent = stringValue(nestedMap(cfg, "browser").get("user_agent"), "");
            if (!userAgent.isBlank()) {
                command.add("--user-agent");
                command.add(userAgent);
            }
            String storageState = stringValue(nestedMap(cfg, "browser").get("storage_state_file"), "");
            if (!storageState.isBlank()) {
                if (Files.exists(Paths.get(storageState))) {
                    command.add("--storage-state");
                    command.add(storageState);
                }
                command.add("--save-storage-state");
                command.add(storageState);
            }
            String cookiesFile = stringValue(nestedMap(cfg, "browser").get("cookies_file"), "");
            if (!cookiesFile.isBlank()) {
                if (Files.exists(Paths.get(cookiesFile))) {
                    command.add("--cookies-file");
                    command.add(cookiesFile);
                }
                command.add("--save-cookies-file");
                command.add(cookiesFile);
            }
            String authFile = stringValue(nestedMap(cfg, "browser").get("auth_file"), "");
            if (!authFile.isBlank()) {
                command.add("--auth-file");
                command.add(authFile);
            }
            if (Boolean.TRUE.equals(nestedMap(cfg, "browser").getOrDefault("headless", true))) {
                command.add("--headless");
            }

            Process process = new ProcessBuilder(command).redirectErrorStream(true).start();
            String output = new String(process.getInputStream().readAllBytes(), StandardCharsets.UTF_8).trim();
            try {
                int exitCode = process.waitFor();
                if (exitCode != 0) {
                    throw new IOException("Playwright helper failed: " + output);
                }
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                throw new IOException("Playwright helper interrupted", e);
            }
            return new ObjectMapper().readValue(output, BrowserFetchResult.class);
        }

        @Override
        public void close() {
        }
    }

    static void setBrowserFetchRunnerFactoryForTests(Supplier<BrowserFetchRunner> factory) {
        browserFetchRunnerFactory = factory;
    }

    static void resetBrowserFetchRunnerFactoryForTests() {
        browserFetchRunnerFactory = DefaultBrowserFetchRunner::new;
    }

    private static String resolvePythonCommand() {
        String configured = System.getenv("SPIDER_PYTHON");
        if (configured != null && !configured.isBlank()) {
            return configured;
        }
        for (String candidate : List.of("..\\..\\.venv\\Scripts\\python.exe", "..\\.venv\\Scripts\\python.exe", "python")) {
            if ("python".equals(candidate) || Files.exists(Paths.get(candidate))) {
                return candidate;
            }
        }
        return "python";
    }

    private static String resolveHelperScript() {
        return resolveSharedTool("playwright_fetch.py");
    }

    private static List<Map<String, Object>> defaultAuthActionExamples() {
        return List.of(
            Map.of("type", "goto", "url", "https://example.com/login"),
            Map.of("type", "type", "selector", "#username", "value", "demo"),
            Map.of("type", "type", "selector", "#password", "value", "secret"),
            Map.of(
                "type", "if",
                "when", Map.of("selector_exists", "#otp"),
                "then", List.of(Map.of("type", "mfa_totp", "selector", "#otp", "totp_env", "SPIDER_AUTH_TOTP_SECRET"))
            ),
            Map.of(
                "type", "if",
                "when", Map.of("selector_exists", ".cf-turnstile,[data-sitekey]"),
                "then", List.of(Map.of(
                    "type", "captcha_solve",
                    "challenge", "turnstile",
                    "selector", ".cf-turnstile,[data-sitekey]",
                    "provider", "anticaptcha",
                    "save_as", "captcha_token"
                ))
            ),
            Map.of("type", "submit", "selector", "#password"),
            Map.of("type", "wait_network_idle"),
            Map.of("type", "reverse_profile", "save_as", "reverse_runtime"),
            Map.of("type", "assert", "url_contains", "/dashboard"),
            Map.of("type", "save_as", "value", "url", "save_as", "final_url")
        );
    }

    private static String resolveSharedTool(String name) {
        if ("playwright_fetch.py".equals(name)) {
            for (String envName : List.of("JAVASPIDER_PLAYWRIGHT_HELPER", "SPIDER_PLAYWRIGHT_HELPER")) {
                String configured = System.getenv(envName);
                if (configured != null && !configured.isBlank()) {
                    return configured;
                }
            }
        }
        for (String candidate : List.of("..\\tools\\" + name, "..\\..\\tools\\" + name)) {
            if (Files.exists(Paths.get(candidate))) {
                return candidate;
            }
        }
        return "..\\tools\\" + name;
    }

    private static int runSharedPythonTool(String scriptName, List<String> toolArgs) {
        try {
            List<String> command = new ArrayList<>();
            command.add(resolvePythonCommand());
            command.add(resolveSharedTool(scriptName));
            command.addAll(toolArgs);
            Process process = new ProcessBuilder(command).redirectErrorStream(true).start();
            String output = new String(process.getInputStream().readAllBytes(), StandardCharsets.UTF_8).trim();
            if (!output.isBlank()) {
                System.out.println(output);
            }
            return process.waitFor();
        } catch (IOException e) {
            throw new RuntimeException("运行共享工具失败: " + scriptName, e);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new RuntimeException("共享工具执行被中断: " + scriptName, e);
        }
    }
}
