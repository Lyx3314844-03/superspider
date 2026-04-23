package com.javaspider;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.PrintStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.concurrent.atomic.AtomicInteger;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class EnhancedSpiderContractTest {

    @AfterEach
    void resetBrowserFactory() {
        EnhancedSpider.resetBrowserFetchRunnerFactoryForTests();
    }

    @Test
    void configInitWritesSharedContract() throws Exception {
        Path output = Files.createTempDirectory("java-contract").resolve("spider-framework.yaml");

        String stdout = captureStdout(() ->
            EnhancedSpider.main(new String[]{"config", "init", "--output", output.toString()})
        );

        assertTrue(stdout.contains("Wrote shared config"));
        String content = Files.readString(output);
        assertTrue(content.contains("runtime: java"));
        assertTrue(content.contains("checkpoint_dir: artifacts/checkpoints"));
        assertTrue(content.contains("network_targets"));
        assertTrue(content.contains("anti_bot"));
        assertTrue(content.contains("node_reverse"));
    }

    @Test
    void browserFetchUsesInjectedSession() throws Exception {
        Path dir = Files.createTempDirectory("java-browser-contract");
        Path screenshot = dir.resolve("page.png");
        Path html = dir.resolve("page.html");

        EnhancedSpider.setBrowserFetchRunnerFactoryForTests(() -> new EnhancedSpider.BrowserFetchRunner() {
            @Override
            public EnhancedSpider.BrowserFetchResult fetch(String url, String screenshotPath, String htmlPath, java.util.Map<String, Object> cfg) {
                try {
                    Files.writeString(Path.of(screenshotPath), "png");
                    Files.writeString(Path.of(htmlPath), "<html>fake</html>");
                } catch (Exception e) {
                    throw new RuntimeException(e);
                }
                EnhancedSpider.BrowserFetchResult result = new EnhancedSpider.BrowserFetchResult();
                result.title = "Fake Title";
                result.url = "https://example.com";
                result.html_path = htmlPath;
                result.screenshot_path = screenshotPath;
                return result;
            }

            @Override
            public void close() {
            }
        });

        String stdout = captureStdout(() ->
            EnhancedSpider.main(new String[]{
                "browser", "fetch",
                "--url", "https://example.com",
                "--screenshot", screenshot.toString(),
                "--html", html.toString()
            })
        );

        assertTrue(stdout.contains("title: Fake Title"));
        assertEquals("png", Files.readString(screenshot));
        assertEquals("<html>fake</html>", Files.readString(html));
    }

    @Test
    void doctorJsonUsesUnifiedContract() throws Exception {
        String stdout = captureStdout(() ->
            EnhancedSpider.main(new String[]{"doctor", "--json"})
        );

        ObjectMapper mapper = new ObjectMapper();
        java.util.Map<String, Object> payload = mapper.readValue(stdout, new TypeReference<java.util.Map<String, Object>>() {});

        assertEquals("doctor", payload.get("command"));
        assertEquals("java", payload.get("runtime"));
        assertTrue(payload.containsKey("exit_code"));
        assertTrue(payload.containsKey("summary_text"));

        @SuppressWarnings("unchecked")
        java.util.List<java.util.Map<String, Object>> checks = (java.util.List<java.util.Map<String, Object>>) payload.get("checks");
        assertFalse(checks.isEmpty());
        assertTrue(checks.stream().allMatch(check -> check.containsKey("name")));
        assertTrue(checks.stream().allMatch(check -> check.containsKey("status")));
        assertTrue(checks.stream().allMatch(check -> check.containsKey("details")));
    }

    @Test
    void invalidRuntimeConfigIsRejected() throws Exception {
        Path output = Files.createTempFile("java-invalid-runtime", ".yaml");
        Files.writeString(
            output,
            """
            version: 1
            project:
              name: bad-runtime
            runtime: python
            crawl:
              urls:
                - https://example.com
            """.strip()
        );

        IllegalArgumentException error = assertThrows(
            IllegalArgumentException.class,
            () -> EnhancedSpider.main(new String[]{"doctor", "--config", output.toString()})
        );

        assertTrue(error.getMessage().contains("runtime mismatch"));
    }

    @Test
    void jobCommandDelegatesToCompatibilityCli() throws Exception {
        Path dir = Files.createTempDirectory("java-enhanced-job");
        Path outputPath = dir.resolve("job-output.json");
        Path path = dir.resolve("job.json");
        Files.writeString(path, """
            {
              "name": "java-enhanced-job",
              "runtime": "browser",
              "target": { "url": "https://example.com" },
              "extract": [
                { "field": "title", "type": "css", "expr": "title" }
              ],
              "output": { "format": "json", "path": "%s" },
              "metadata": {
                "mock_extract": { "title": "Enhanced Job Title" }
              }
            }
            """.formatted(outputPath.toString().replace("\\", "\\\\")));

        String stdout = captureStdout(() ->
            EnhancedSpider.main(new String[]{"job", "--file", path.toString()})
        );

        assertTrue(stdout.contains("\"state\" : \"succeeded\""));
        assertTrue(stdout.contains("Enhanced Job Title"));
        assertTrue(Files.readString(outputPath).contains("Enhanced Job Title"));
    }

    @Test
    void helpMentionsUltimateCommand() {
        String stdout = captureStdout(() ->
            EnhancedSpider.main(new String[]{"help"})
        );

        assertTrue(stdout.contains("ultimate"));
        assertTrue(stdout.contains("scrapy"));
        assertTrue(stdout.contains("jobdir"));
        assertTrue(stdout.contains("http-cache"));
        assertTrue(stdout.contains("console"));
        assertTrue(stdout.contains("node-reverse"));
        assertTrue(stdout.contains("anti-bot"));
    }

    @Test
    void capabilitiesCommandReportsSharedContractFields() throws Exception {
        String stdout = captureStdout(() ->
            EnhancedSpider.main(new String[]{"capabilities"})
        );

        ObjectMapper mapper = new ObjectMapper();
        java.util.Map<String, Object> payload = mapper.readValue(stdout, new TypeReference<java.util.Map<String, Object>>() {});
        assertEquals("capabilities", payload.get("command"));
        assertEquals("java", payload.get("runtime"));
        assertTrue(payload.containsKey("shared_contracts"));
        assertTrue(payload.containsKey("kernel_contracts"));
        assertTrue(payload.containsKey("feature_gates"));
        assertTrue(payload.containsKey("operator_products"));
        assertTrue(payload.containsKey("browser_compatibility"));
        assertTrue(payload.containsKey("observability"));
        assertTrue(stdout.contains("\"jobdir\""));
        assertTrue(stdout.contains("\"http-cache\""));
        assertTrue(stdout.contains("\"console\""));
    }

    @Test
    void nodeReverseHealthCommandUsesFrameworkCliSurface() throws Exception {
        HttpServer reverseServer = HttpServer.create(new InetSocketAddress(0), 0);
        reverseServer.createContext("/health", exchange -> writeJson(exchange, 200, "{\"status\":\"ok\"}", "application/json"));
        reverseServer.start();

        try {
            String stdout = captureStdout(() ->
                EnhancedSpider.main(new String[]{
                    "node-reverse",
                    "health",
                    "--base-url",
                    "http://127.0.0.1:" + reverseServer.getAddress().getPort()
                })
            );
            assertTrue(stdout.contains("\"command\" : \"node-reverse health\""));
            assertTrue(stdout.contains("\"healthy\" : true"));
        } finally {
            reverseServer.stop(0);
        }
    }

    @Test
    void nodeReverseDetectCommandUsesFrameworkCliSurface() throws Exception {
        HttpServer reverseServer = HttpServer.create(new InetSocketAddress(0), 0);
        reverseServer.createContext("/api/anti-bot/detect", exchange -> writeJson(exchange, 200,
            "{\"success\":true,\"signals\":[\"vendor:cloudflare\"],\"level\":\"high\"}",
            "application/json"));
        reverseServer.start();

        try {
            Path htmlFile = Files.createTempFile("java-node-reverse-detect", ".html");
            Files.writeString(htmlFile, "<html><body>blocked</body></html>");
            String stdout = captureStdout(() ->
                EnhancedSpider.main(new String[]{
                    "node-reverse",
                    "detect",
                    "--base-url",
                    "http://127.0.0.1:" + reverseServer.getAddress().getPort(),
                    "--html-file",
                    htmlFile.toString(),
                    "--status-code",
                    "403"
                })
            );
            assertTrue(stdout.contains("vendor:cloudflare"));
            assertTrue(stdout.contains("\"level\" : \"high\""));
        } finally {
            reverseServer.stop(0);
        }
    }

    @Test
    void nodeReverseFingerprintSpoofCommandUsesFrameworkCliSurface() throws Exception {
        HttpServer reverseServer = HttpServer.create(new InetSocketAddress(0), 0);
        reverseServer.createContext("/api/fingerprint/spoof", exchange -> writeJson(exchange, 200,
            "{\"success\":true,\"browser\":\"chrome\",\"platform\":\"windows\",\"fingerprint\":{\"userAgent\":\"mock\"}}",
            "application/json"));
        reverseServer.start();

        try {
            String stdout = captureStdout(() ->
                EnhancedSpider.main(new String[]{
                    "node-reverse",
                    "fingerprint-spoof",
                    "--base-url",
                    "http://127.0.0.1:" + reverseServer.getAddress().getPort(),
                    "--browser",
                    "chrome",
                    "--platform",
                    "windows"
                })
            );
            assertTrue(stdout.contains("\"browser\" : \"chrome\""));
            assertTrue(stdout.contains("\"platform\" : \"windows\""));
        } finally {
            reverseServer.stop(0);
        }
    }

    @Test
    void nodeReverseTlsFingerprintCommandUsesFrameworkCliSurface() throws Exception {
        HttpServer reverseServer = HttpServer.create(new InetSocketAddress(0), 0);
        reverseServer.createContext("/api/tls/fingerprint", exchange -> writeJson(exchange, 200,
            "{\"success\":true,\"browser\":\"chrome\",\"version\":\"120\",\"fingerprint\":{\"ja3\":\"mock-ja3\"}}",
            "application/json"));
        reverseServer.start();

        try {
            String stdout = captureStdout(() ->
                EnhancedSpider.main(new String[]{
                    "node-reverse",
                    "tls-fingerprint",
                    "--base-url",
                    "http://127.0.0.1:" + reverseServer.getAddress().getPort(),
                    "--browser",
                    "chrome",
                    "--version",
                    "120"
                })
            );
            assertTrue(stdout.contains("\"version\" : \"120\""));
            assertTrue(stdout.contains("mock-ja3"));
        } finally {
            reverseServer.stop(0);
        }
    }

    @Test
    void nodeReverseCanvasFingerprintCommandUsesFrameworkCliSurface() throws Exception {
        HttpServer reverseServer = HttpServer.create(new InetSocketAddress(0), 0);
        reverseServer.createContext("/api/canvas/fingerprint", exchange -> writeJson(exchange, 200,
            "{\"success\":true,\"hash\":\"mock-canvas\"}",
            "application/json"));
        reverseServer.start();

        try {
            String stdout = captureStdout(() ->
                EnhancedSpider.main(new String[]{
                    "node-reverse",
                    "canvas-fingerprint",
                    "--base-url",
                    "http://127.0.0.1:" + reverseServer.getAddress().getPort()
                })
            );
            assertTrue(stdout.contains("mock-canvas"));
        } finally {
            reverseServer.stop(0);
        }
    }

    @Test
    void nodeReverseSignatureReverseCommandUsesFrameworkCliSurface() throws Exception {
        HttpServer reverseServer = HttpServer.create(new InetSocketAddress(0), 0);
        reverseServer.createContext("/api/signature/reverse", exchange -> writeJson(exchange, 200,
            "{\"success\":true,\"functionName\":\"sign\"}",
            "application/json"));
        reverseServer.start();

        try {
            Path codeFile = Files.createTempFile("java-node-reverse-signature", ".js");
            Files.writeString(codeFile, "function sign(v){return v;}");
            String stdout = captureStdout(() ->
                EnhancedSpider.main(new String[]{
                    "node-reverse",
                    "signature-reverse",
                    "--base-url",
                    "http://127.0.0.1:" + reverseServer.getAddress().getPort(),
                    "--code-file",
                    codeFile.toString(),
                    "--input-data",
                    "left",
                    "--expected-output",
                    "left"
                })
            );
            assertTrue(stdout.contains("\"functionName\" : \"sign\""));
        } finally {
            reverseServer.stop(0);
        }
    }

    @Test
    void nodeReverseWebpackCommandUsesFrameworkCliSurface() throws Exception {
        HttpServer reverseServer = HttpServer.create(new InetSocketAddress(0), 0);
        reverseServer.createContext("/api/webpack/analyze", exchange -> writeJson(exchange, 200,
            "{\"success\":true,\"entrypoints\":[\"main\"]}",
            "application/json"));
        reverseServer.start();

        try {
            Path codeFile = Files.createTempFile("java-node-reverse-webpack", ".js");
            Files.writeString(codeFile, "__webpack_require__(1)");
            String stdout = captureStdout(() ->
                EnhancedSpider.main(new String[]{
                    "node-reverse",
                    "webpack",
                    "--base-url",
                    "http://127.0.0.1:" + reverseServer.getAddress().getPort(),
                    "--code-file",
                    codeFile.toString()
                })
            );

            assertTrue(stdout.contains("\"entrypoints\" : [ \"main\" ]") || stdout.contains("\"entrypoints\" : ["));
            assertTrue(stdout.contains("main"));
        } finally {
            reverseServer.stop(0);
        }
    }

    @Test
    void nodeReverseFunctionCallCommandUsesFrameworkCliSurface() throws Exception {
        HttpServer reverseServer = HttpServer.create(new InetSocketAddress(0), 0);
        reverseServer.createContext("/api/function/call", exchange -> writeJson(exchange, 200,
            "{\"success\":true,\"result\":\"left|right\"}",
            "application/json"));
        reverseServer.start();

        try {
            Path codeFile = Files.createTempFile("java-node-reverse-function", ".js");
            Files.writeString(codeFile, "function sign(a,b){return a+'|'+b;}");
            String stdout = captureStdout(() ->
                EnhancedSpider.main(new String[]{
                    "node-reverse",
                    "function-call",
                    "--base-url",
                    "http://127.0.0.1:" + reverseServer.getAddress().getPort(),
                    "--code-file",
                    codeFile.toString(),
                    "--function-name",
                    "sign",
                    "--arg",
                    "left",
                    "--arg",
                    "right"
                })
            );

            assertTrue(stdout.contains("left|right"));
        } finally {
            reverseServer.stop(0);
        }
    }

    @Test
    void nodeReverseBrowserSimulateCommandUsesFrameworkCliSurface() throws Exception {
        HttpServer reverseServer = HttpServer.create(new InetSocketAddress(0), 0);
        reverseServer.createContext("/api/browser/simulate", exchange -> writeJson(exchange, 200,
            "{\"success\":true,\"result\":{\"ok\":true},\"cookies\":\"session=1\"}",
            "application/json"));
        reverseServer.start();

        try {
            Path codeFile = Files.createTempFile("java-node-reverse-browser", ".js");
            Files.writeString(codeFile, "navigator.userAgent");
            String stdout = captureStdout(() ->
                EnhancedSpider.main(new String[]{
                    "node-reverse",
                    "browser-simulate",
                    "--base-url",
                    "http://127.0.0.1:" + reverseServer.getAddress().getPort(),
                    "--code-file",
                    codeFile.toString()
                })
            );

            assertTrue(stdout.contains("session=1"));
        } finally {
            reverseServer.stop(0);
        }
    }

    @Test
    void antiBotProfileCommandDetectsBlockedFixture() throws Exception {
        Path htmlFile = Files.createTempFile("java-antibot", ".html");
        Files.writeString(htmlFile, "<html><title>Blocked</title><body>Access denied captcha</body></html>");

        String stdout = captureStdout(() ->
            EnhancedSpider.main(new String[]{
                "anti-bot",
                "profile",
                "--html-file",
                htmlFile.toString(),
                "--status-code",
                "403"
            })
        );

        assertTrue(stdout.contains("\"command\" : \"anti-bot profile\""));
        assertTrue(stdout.contains("\"blocked\" : true"));
        assertTrue(stdout.contains("captcha"));
    }

    @Test
    void profileSiteCommandBuildsProfile() throws Exception {
        Path htmlFile = Files.createTempFile("java-profile-site", ".html");
        Files.writeString(htmlFile, "<html><title>X</title><article>author price</article></html>");

        HttpServer reverseServer = HttpServer.create(new InetSocketAddress(0), 0);
        reverseServer.createContext("/api/anti-bot/detect", exchange -> writeJson(exchange, 200,
            "{\"success\":true,\"signals\":[\"vendor:test\"]}",
            "application/json"));
        reverseServer.createContext("/api/anti-bot/profile", exchange -> writeJson(exchange, 200,
            "{\"success\":true,\"signals\":[\"vendor:test\"],\"level\":\"medium\"}",
            "application/json"));
        reverseServer.createContext("/api/fingerprint/spoof", exchange -> writeJson(exchange, 200,
            "{\"success\":true,\"browser\":\"chrome\"}",
            "application/json"));
        reverseServer.createContext("/api/tls/fingerprint", exchange -> writeJson(exchange, 200,
            "{\"success\":true,\"fingerprint\":{\"ja3\":\"mock-ja3\"}}",
            "application/json"));
        reverseServer.createContext("/api/canvas/fingerprint", exchange -> writeJson(exchange, 200,
            "{\"success\":true,\"hash\":\"mock-canvas\"}",
            "application/json"));
        reverseServer.createContext("/api/crypto/analyze", exchange -> writeJson(exchange, 200,
            "{\"success\":true,\"cryptoTypes\":[{\"name\":\"AES\"}],\"analysis\":{\"keyFlowChains\":[{\"variable\":\"sessionKey\",\"source\":{\"kind\":\"storage.localStorage\",\"expression\":\"localStorage.getItem('session-key')\"},\"derivations\":[{\"variable\":\"derivedKey\",\"kind\":\"hash\",\"expression\":\"sha256(sessionKey)\"}],\"sinks\":[\"crypto.subtle.encrypt\"],\"confidence\":0.87}]}}",
            "application/json"));
        reverseServer.start();

        try {
            String stdout = captureStdout(() ->
                EnhancedSpider.main(new String[]{
                    "profile-site",
                    "--html-file",
                    htmlFile.toString(),
                    "--base-url",
                    "http://127.0.0.1:" + reverseServer.getAddress().getPort()
                })
            );

            assertTrue(stdout.contains("\"command\" : \"profile-site\""));
            assertTrue(stdout.contains("\"page_type\" : \"detail\""));
            assertTrue(stdout.contains("\"framework\" : \"javaspider\""));
            assertTrue(stdout.contains("\"crawler_type\" : \"static_detail\""));
            assertTrue(stdout.contains("\"runner_order\""));
            assertTrue(stdout.contains("\"job_templates\""));
            assertTrue(stdout.contains("\"reverse\""));
            assertTrue(stdout.contains("mock-ja3"));
            assertTrue(stdout.contains("mock-canvas"));
            assertTrue(stdout.contains("\"canvas_fingerprint\""));
            assertTrue(stdout.contains("\"crypto_analysis\""));
            assertTrue(stdout.contains("AES"));
            assertTrue(stdout.contains("\"reverse_focus\""));
            assertTrue(stdout.contains("sessionKey"));
            assertTrue(stdout.contains("crypto.subtle.encrypt"));
        } finally {
            reverseServer.stop(0);
        }
    }

    @Test
    void sitemapDiscoverCommandReadsLocalFile() throws Exception {
        Path sitemapFile = Files.createTempFile("java-sitemap", ".xml");
        Files.writeString(sitemapFile, "<?xml version=\"1.0\"?><urlset><url><loc>https://example.com/a</loc></url><url><loc>https://example.com/b</loc></url></urlset>");

        String stdout = captureStdout(() ->
            EnhancedSpider.main(new String[]{
                "sitemap-discover",
                "--sitemap-file",
                sitemapFile.toString()
            })
        );

        assertTrue(stdout.contains("\"command\" : \"sitemap-discover\""));
        assertTrue(stdout.contains("\"url_count\" : 2"));
    }

    @Test
    void pluginsListCommandReadsManifest() throws Exception {
        Path manifest = Files.createTempFile("java-plugins", ".json");
        Files.writeString(manifest, "{\"entrypoints\":[{\"id\":\"shared-cli\"}]}");

        String stdout = captureStdout(() ->
            EnhancedSpider.main(new String[]{
                "plugins",
                "list",
                "--manifest",
                manifest.toString()
            })
        );

        assertTrue(stdout.contains("\"command\" : \"plugins list\""));
        assertTrue(stdout.contains("shared-cli"));
    }

    @Test
    void pluginsRunDispatchesBuiltInPlugin() throws Exception {
        Path htmlFile = Files.createTempFile("java-plugin-selector", ".html");
        Files.writeString(htmlFile, "<html><title>Demo</title></html>");

        String stdout = captureStdout(() ->
            EnhancedSpider.main(new String[]{
                "plugins",
                "run",
                "--plugin",
                "selector-studio",
                "--",
                "--html-file",
                htmlFile.toString(),
                "--type",
                "css",
                "--expr",
                "title"
            })
        );

        assertTrue(stdout.contains("\"command\" : \"selector-studio\""));
        assertTrue(stdout.contains("\"count\" : 1"));
        assertTrue(stdout.contains("\"framework\" : \"javaspider\""));
        assertTrue(stdout.contains("\"suggested_xpaths\""));
    }

    @Test
    void selectorStudioCommandExtractsValues() throws Exception {
        Path htmlFile = Files.createTempFile("java-selector", ".html");
        Files.writeString(htmlFile, "<html><title>Demo</title><article><h1>Title</h1></article></html>");

        String stdout = captureStdout(() ->
            EnhancedSpider.main(new String[]{
                "selector-studio",
                "--html-file",
                htmlFile.toString(),
                "--type",
                "css",
                "--expr",
                "title"
            })
        );

        assertTrue(stdout.contains("\"command\" : \"selector-studio\""));
        assertTrue(stdout.contains("\"count\" : 1"));
        assertTrue(stdout.contains("\"suggested_xpaths\""));
    }

    @Test
    void scrapyDemoCommandExportsResults() throws Exception {
        Path htmlFile = Files.createTempFile("java-scrapy-demo", ".html");
        Path outputFile = Files.createTempFile("java-scrapy-demo-output", ".json");
        Files.writeString(htmlFile, "<html><title>Demo</title></html>");

        String stdout = captureStdout(() ->
            EnhancedSpider.main(new String[]{
                "scrapy",
                "demo",
                "--url",
                "https://example.com",
                "--html-file",
                htmlFile.toString(),
                "--output",
                outputFile.toString()
            })
        );

        assertTrue(stdout.contains("\"command\" : \"scrapy demo\""));
        assertTrue(Files.readString(outputFile).contains("Demo"));
    }

    @Test
    void scrapyRunCommandReadsProjectManifest() throws Exception {
        Path projectDir = Files.createTempDirectory("java-scrapy-project");
        Path htmlFile = projectDir.resolve("page.html");
        Path outputFile = projectDir.resolve("artifacts").resolve("exports").resolve("items.json");
        Files.createDirectories(outputFile.getParent());
        Files.writeString(htmlFile, "<html><title>Manifest Demo</title></html>");
        Files.writeString(
            projectDir.resolve("scrapy-project.json"),
            """
            {
              "name": "demo-project",
              "runtime": "java",
              "entry": "src/main/java/starter/ScrapyStyleStarter.java",
              "runner": "build/project-runner.jar",
              "url": "https://example.com",
              "output": "artifacts/exports/items.json"
            }
            """
        );

        String stdout = captureStdout(() ->
            EnhancedSpider.main(new String[]{
                "scrapy",
                "run",
                "--project",
                projectDir.toString(),
                "--html-file",
                htmlFile.toString()
            })
        );

        assertTrue(stdout.contains("\"command\" : \"scrapy run\""));
        assertTrue(stdout.contains("\"command\" : \"scrapy run\""));
        assertTrue(Files.readString(outputFile).contains("Manifest Demo"));
    }

    @Test
    void scrapyInitCommandCreatesProject() throws Exception {
        Path projectDir = Files.createTempDirectory("java-scrapy-init");

        String stdout = captureStdout(() ->
            EnhancedSpider.main(new String[]{
                "scrapy",
                "init",
                "--path",
                projectDir.toString()
            })
        );

        assertTrue(stdout.contains("\"command\" : \"scrapy init\""));
        assertTrue(Files.exists(projectDir.resolve("scrapy-project.json")));
        assertTrue(Files.exists(projectDir.resolve("src").resolve("main").resolve("java").resolve("starter").resolve("ScrapyStyleStarter.java")));
        assertTrue(Files.exists(projectDir.resolve("pom.xml")));
        assertTrue(Files.exists(projectDir.resolve("spider-framework.yaml")));
    }

    @Test
    void scrapyListValidateAndGenspiderCommandsWork() throws Exception {
        Path projectDir = Files.createTempDirectory("java-scrapy-project-tools");
        EnhancedSpider.main(new String[]{"scrapy", "init", "--path", projectDir.toString()});

        String listOutput = captureStdout(() ->
            EnhancedSpider.main(new String[]{"scrapy", "list", "--project", projectDir.toString()})
        );
        assertTrue(listOutput.contains("\"command\" : \"scrapy list\""));
        assertTrue(listOutput.contains("\"runner\" : \"http\""));

        String validateOutput = captureStdout(() ->
            EnhancedSpider.main(new String[]{"scrapy", "validate", "--project", projectDir.toString()})
        );
        assertTrue(validateOutput.contains("\"summary\" : \"passed\""));

        String genspiderOutput = captureStdout(() ->
            EnhancedSpider.main(new String[]{"scrapy", "genspider", "--name", "news", "--domain", "example.com", "--project", projectDir.toString()})
        );
        assertTrue(genspiderOutput.contains("\"command\" : \"scrapy genspider\""));
        assertTrue(Files.exists(projectDir.resolve("spiders").resolve("news.java")));

        Path htmlFile = projectDir.resolve("page.html");
        Files.writeString(htmlFile, "<html><title>Selected Spider</title></html>");
        String runOutput = captureStdout(() ->
            EnhancedSpider.main(new String[]{"scrapy", "run", "--project", projectDir.toString(), "--spider", "news", "--html-file", htmlFile.toString()})
        );
        assertTrue(runOutput.contains("\"spider\" : \"news\""));
        assertTrue(runOutput.contains("\"project_runner\" : \"built-in-metadata-runner\""));
        assertTrue(runOutput.contains("\"runner\" : \"http\""));
        assertTrue(runOutput.contains("\"resolved_runner\" : \"http\""));
        assertTrue(runOutput.contains("\"url_source\" : \"html-fixture\""));
        assertTrue(runOutput.contains("\"plugins\" : ["));
        assertTrue(runOutput.contains("field-injector"));
        assertTrue(runOutput.contains("\"settings_source\" : "));
    }

    @Test
    void scrapyShellCommandExtractsValues() throws Exception {
        Path htmlFile = Files.createTempFile("java-scrapy-shell", ".html");
        Files.writeString(htmlFile, "<html><title>Shell Demo</title></html>");

        String stdout = captureStdout(() ->
            EnhancedSpider.main(new String[]{
                "scrapy",
                "shell",
                "--html-file",
                htmlFile.toString(),
                "--type",
                "css",
                "--expr",
                "title"
            })
        );

        assertTrue(stdout.contains("\"command\" : \"scrapy shell\""));
        assertTrue(stdout.contains("Shell Demo"));
    }

    @Test
    void scrapyExportCommandUsesProjectOutput() throws Exception {
        Path projectDir = Files.createTempDirectory("java-scrapy-export");
        Path outputDir = projectDir.resolve("artifacts").resolve("exports");
        Files.createDirectories(outputDir);
        Files.writeString(
            projectDir.resolve("scrapy-project.json"),
            """
            {
              "name": "demo-project",
              "runtime": "java",
              "entry": "src/main/java/starter/ScrapyStyleStarter.java",
              "runner": "build/project-runner.jar",
              "url": "https://example.com",
              "output": "artifacts/exports/items.json"
            }
            """
        );
        Files.writeString(outputDir.resolve("items.json"), "[{\"title\":\"Demo\",\"url\":\"https://example.com\"}]");

        String stdout = captureStdout(() ->
            EnhancedSpider.main(new String[]{
                "scrapy",
                "export",
                "--project",
                projectDir.toString(),
                "--format",
                "csv"
            })
        );

        assertTrue(stdout.contains("\"command\" : \"scrapy export\""));
        assertTrue(Files.exists(outputDir.resolve("items.csv")));
    }

    @Test
    void scrapyProfileCommandUsesProjectAndSpider() throws Exception {
        Path projectDir = Files.createTempDirectory("java-scrapy-profile");
        Path spidersDir = projectDir.resolve("spiders");
        Files.createDirectories(spidersDir);
        Files.writeString(
            projectDir.resolve("scrapy-project.json"),
            """
            {
              "name": "demo-project",
              "runtime": "java",
              "entry": "src/main/java/starter/ScrapyStyleStarter.java",
              "runner": "build/project-runner.jar",
              "url": "https://example.com",
              "output": "artifacts/exports/items.json"
            }
            """
        );
        Files.writeString(spidersDir.resolve("news.java"), "// scrapy: url=https://example.com/news\n");
        Path htmlFile = projectDir.resolve("page.html");
        Files.writeString(htmlFile, "<html><title>Profile Demo</title><a href='/a'>A</a><img src='x.png'></html>");

        String stdout = captureStdout(() ->
            EnhancedSpider.main(new String[]{
                "scrapy",
                "profile",
                "--project",
                projectDir.toString(),
                "--spider",
                "news",
                "--html-file",
                htmlFile.toString()
            })
        );

        assertTrue(stdout.contains("\"command\" : \"scrapy profile\""));
        assertTrue(stdout.contains("\"spider\" : \"news\""));
        assertTrue(stdout.contains("\"link_count\" : 1"));
        assertTrue(stdout.contains("\"url_source\" : \"html-fixture\""));
    }

    @Test
    void scrapyBenchCommandUsesHtmlFixture() throws Exception {
        Path htmlFile = Files.createTempFile("java-scrapy-bench", ".html");
        Files.writeString(htmlFile, "<html><title>Bench Demo</title><a href='/a'>A</a></html>");

        String stdout = captureStdout(() ->
            EnhancedSpider.main(new String[]{
                "scrapy",
                "bench",
                "--html-file",
                htmlFile.toString()
            })
        );

        assertTrue(stdout.contains("\"command\" : \"scrapy bench\""));
        assertTrue(stdout.contains("Bench Demo"));
        assertTrue(stdout.contains("\"url_source\" : \"html-fixture\""));
    }

    @Test
    void scrapyDoctorCommandReportsProjectHealth() throws Exception {
        Path projectDir = Files.createTempDirectory("java-scrapy-doctor");
        Path spidersDir = projectDir.resolve("spiders");
        Files.createDirectories(spidersDir);
        Files.writeString(
            projectDir.resolve("scrapy-project.json"),
            """
            {
              "name": "demo-project",
              "runtime": "java",
              "entry": "src/main/java/starter/ScrapyStyleStarter.java",
              "runner": "build/project-runner.jar",
              "url": "https://example.com",
              "output": "artifacts/exports/items.json"
            }
            """
        );
        Files.writeString(spidersDir.resolve("demo.java"), "// scrapy: url=https://example.com\n");

        String stdout = captureStdout(() ->
            EnhancedSpider.main(new String[]{
                "scrapy",
                "doctor",
                "--project",
                projectDir.toString()
            })
        );

        assertTrue(stdout.contains("\"command\" : \"scrapy doctor\""));
    }

    @Test
    void javaProjectRunnerLoadsRegisteredPlugin() throws Exception {
        Path projectDir = Files.createTempDirectory("java-scrapy-project-plugin");
        EnhancedSpider.main(new String[]{"scrapy", "init", "--path", projectDir.toString()});
        Files.writeString(
            projectDir.resolve("scrapy-plugins.json"),
            """
            {
              "plugins": [
                {
                  "name": "field-injector",
                  "priority": 5,
                  "config": {
                    "fields": {
                      "plugin": "yes"
                    }
                  }
                }
              ]
            }
            """
        );
        Path htmlFile = projectDir.resolve("page.html");
        Files.writeString(htmlFile, "<html><title>Plugin Demo</title></html>");

        String stdout = captureStdout(() ->
            EnhancedSpider.main(new String[]{
                "scrapy",
                "run",
                "--project",
                projectDir.toString(),
                "--spider",
                "demo",
                "--html-file",
                htmlFile.toString()
            })
        );

        assertTrue(stdout.contains("\"command\" : \"scrapy run\""));
        Path output = projectDir.resolve("artifacts").resolve("exports").resolve("demo.json");
        String exported = Files.readString(output);
        assertTrue(exported.contains("\"plugin\""));
        assertTrue(exported.contains("yes"));
    }

    @Test
    void javaProjectRunnerAppliesDeclarativeComponents() throws Exception {
        Path projectDir = Files.createTempDirectory("java-scrapy-project-components");
        EnhancedSpider.main(new String[]{"scrapy", "init", "--path", projectDir.toString()});

        Path configPath = projectDir.resolve("spider-framework.yaml");
        Files.writeString(
            configPath,
            Files.readString(configPath) + "\nscrapy:\n  runner: http\n  pipelines:\n    - field-injector\n  spider_middlewares:\n    - response-context\n  component_config:\n    field_injector:\n      fields:\n        component: configured\n"
        );
        Path htmlFile = projectDir.resolve("page.html");
        Files.writeString(htmlFile, "<html><title>Component Demo</title></html>");

        String stdout = captureStdout(() ->
            EnhancedSpider.main(new String[]{
                "scrapy",
                "run",
                "--project",
                projectDir.toString(),
                "--spider",
                "demo",
                "--html-file",
                htmlFile.toString()
            })
        );

        assertTrue(stdout.contains("\"resolved_runner\" : \"http\""));
        assertTrue(stdout.contains("field-injector"));
        assertTrue(stdout.contains("response-context"));
        String exported = Files.readString(projectDir.resolve("artifacts").resolve("exports").resolve("demo.json"));
        assertTrue(exported.contains("\"component\" : \"configured\""));
        assertTrue(exported.contains("\"response_url\" : \"https://example.com\""));
    }

    @Test
    void javaProjectRunnerAppliesSpiderSpecificDeclarativeOverrides() throws Exception {
        Path projectDir = Files.createTempDirectory("java-scrapy-project-spider-components");
        EnhancedSpider.main(new String[]{"scrapy", "init", "--path", projectDir.toString()});

        Path configPath = projectDir.resolve("spider-framework.yaml");
        Files.writeString(
            configPath,
            """
            scrapy:
              runner: http
              pipelines:
                - field-injector
              component_config:
                field_injector:
                  fields:
                    scope: global
              spiders:
                demo:
                  runner: http
                  url: https://example.com
                  spider_middlewares:
                    - response-context
                  component_config:
                    field_injector:
                      fields:
                        scope: demo
                        spider_only: demo-only
            """
        );
        Path htmlFile = projectDir.resolve("page.html");
        Files.writeString(htmlFile, "<html><title>Spider Override Demo</title></html>");

        String stdout = captureStdout(() ->
            EnhancedSpider.main(new String[]{
                "scrapy",
                "run",
                "--project",
                projectDir.toString(),
                "--spider",
                "demo",
                "--html-file",
                htmlFile.toString()
            })
        );

        assertTrue(stdout.contains("field-injector"), stdout);
        assertTrue(stdout.contains("response-context"), stdout);

        String listOutput = captureStdout(() ->
            EnhancedSpider.main(new String[]{
                "scrapy",
                "list",
                "--project",
                projectDir.toString()
            })
        );
        assertTrue(listOutput.contains("\"pipelines\" : ["), listOutput);
        assertTrue(listOutput.contains("\"spider_middlewares\" : ["), listOutput);

        String exported = Files.readString(projectDir.resolve("artifacts").resolve("exports").resolve("demo.json"));
        assertTrue(exported.contains("\"scope\" : \"demo\""), exported);
        assertTrue(exported.contains("\"spider_only\" : \"demo-only\""), exported);
        assertTrue(exported.contains("\"response_url\" : \"https://example.com\""), exported);
    }

    @Test
    void javaProjectRunnerIncludesReverseSummaryWhenConfigured() throws Exception {
        Path projectDir = Files.createTempDirectory("java-scrapy-project-reverse");
        EnhancedSpider.main(new String[]{"scrapy", "init", "--path", projectDir.toString()});

        HttpServer reverseServer = HttpServer.create(new InetSocketAddress(0), 0);
        reverseServer.createContext("/api/anti-bot/detect", exchange -> writeJson(exchange, 200,
            "{\"success\":true,\"signals\":[\"vendor:test\"]}",
            "application/json"));
        reverseServer.createContext("/api/anti-bot/profile", exchange -> writeJson(exchange, 200,
            "{\"success\":true,\"signals\":[\"vendor:test\"],\"level\":\"medium\"}",
            "application/json"));
        reverseServer.createContext("/api/fingerprint/spoof", exchange -> writeJson(exchange, 200,
            "{\"success\":true,\"browser\":\"chrome\"}",
            "application/json"));
        reverseServer.createContext("/api/tls/fingerprint", exchange -> writeJson(exchange, 200,
            "{\"success\":true,\"fingerprint\":{\"ja3\":\"mock-ja3\"}}",
            "application/json"));
        reverseServer.start();

        Path configPath = projectDir.resolve("spider-framework.yaml");
        Files.writeString(
            configPath,
            Files.readString(configPath).replace("http://localhost:3000", "http://127.0.0.1:" + reverseServer.getAddress().getPort())
        );
        Path htmlFile = projectDir.resolve("page.html");
        Files.writeString(htmlFile, "<html><title>Reverse Demo</title></html>");

        try {
            String stdout = captureStdout(() ->
                EnhancedSpider.main(new String[]{
                    "scrapy",
                    "run",
                    "--project",
                    projectDir.toString(),
                    "--spider",
                    "demo",
                    "--html-file",
                    htmlFile.toString()
                })
            );

            assertTrue(stdout.contains("\"command\" : \"scrapy run\""), stdout);
            assertTrue(stdout.contains("\"project_runner\" : \"built-in-metadata-runner\""), stdout);
            assertTrue(stdout.contains("\"runner\" : \"http\""), stdout);
            assertTrue(stdout.contains("\"reverse\""), stdout);
        } finally {
            reverseServer.stop(0);
        }
    }

    @Test
    void javaSourceProjectAppliesDeclarativeComponentsFromProjectConfig() throws Exception {
        Path projectDir = Files.createTempDirectory("java-scrapy-project-components");
        EnhancedSpider.main(new String[]{"scrapy", "init", "--path", projectDir.toString()});

        Path configPath = projectDir.resolve("spider-framework.yaml");
        Files.writeString(
            configPath,
            """
            scrapy:
              runner: http
              pipelines:
                - field-injector
              spider_middlewares:
                - response-context
              component_config:
                field_injector:
                  fields:
                    component: configured
            """
        );

        String listOutput = captureStdout(() ->
            EnhancedSpider.main(new String[]{
                "scrapy",
                "list",
                "--project",
                projectDir.toString()
            })
        );
        assertTrue(listOutput.contains("\"pipelines\" : ["), listOutput);
        assertTrue(listOutput.contains("field-injector"), listOutput);
        assertTrue(listOutput.contains("\"spider_middlewares\" : ["), listOutput);
        assertTrue(listOutput.contains("response-context"), listOutput);

        String validateOutput = captureStdout(() ->
            EnhancedSpider.main(new String[]{
                "scrapy",
                "validate",
                "--project",
                projectDir.toString()
            })
        );
        assertTrue(validateOutput.contains("\"summary\" : \"passed\""), validateOutput);
        assertTrue(validateOutput.contains("pipeline:field-injector"), validateOutput);
        assertTrue(validateOutput.contains("spider_middleware:response-context"), validateOutput);

        Path htmlFile = projectDir.resolve("page.html");
        Files.writeString(htmlFile, "<html><title>Component Demo</title></html>");

        String stdout = captureStdout(() ->
            EnhancedSpider.main(new String[]{
                "scrapy",
                "run",
                "--project",
                projectDir.toString(),
                "--spider",
                "demo",
                "--html-file",
                htmlFile.toString()
            })
        );

        assertTrue(stdout.contains("\"project_runner\" : \"built-in-metadata-runner\""), stdout);
        assertTrue(stdout.contains("\"runner\" : \"http\""), stdout);
        assertTrue(stdout.contains("\"pipeline_count\" : 1"), stdout);
        assertTrue(stdout.contains("\"spider_middleware_count\" : 1"), stdout);
        Path output = projectDir.resolve("artifacts").resolve("exports").resolve("demo.json");
        String exported = Files.readString(output);
        assertTrue(exported.contains("\"component\" : \"configured\""), exported);
        assertTrue(exported.contains("\"response_url\" : \"https://example.com\""), exported);
    }

    @Test
    void ultimateCommandRunsAgainstMockServices() throws Exception {
        AtomicInteger reverseHits = new AtomicInteger();
        HttpServer pageServer = HttpServer.create(new InetSocketAddress(0), 0);
        pageServer.createContext("/", exchange -> {
            writeJson(
                exchange,
                200,
                "<html><title>Ultimate Java</title><script>navigator.userAgent; CryptoJS.AES.encrypt('x','y')</script></html>",
                "text/html; charset=utf-8"
            );
        });
        pageServer.start();

        HttpServer reverseServer = HttpServer.create(new InetSocketAddress(0), 0);
        reverseServer.createContext("/health", exchange -> {
            reverseHits.incrementAndGet();
            writeJson(exchange, 200, "{\"status\":\"ok\"}", "application/json");
        });
        reverseServer.createContext("/api/anti-bot/profile", exchange -> {
            reverseHits.incrementAndGet();
            writeJson(
                exchange,
                200,
                "{\"success\":true,\"signals\":[\"vendor:test\"],\"level\":\"medium\",\"score\":7,\"vendors\":[],\"challenges\":[],\"recommendations\":[\"keep cookies\"],\"requestBlueprint\":{},\"mitigationPlan\":{}}",
                "application/json"
            );
        });
        reverseServer.createContext("/api/anti-bot/detect", exchange -> {
            reverseHits.incrementAndGet();
            writeJson(exchange, 200, "{\"success\":true,\"signals\":[\"vendor:test\"],\"level\":\"medium\",\"detection\":{\"hasCloudflare\":true}}", "application/json");
        });
        reverseServer.createContext("/api/tls/fingerprint", exchange -> {
            reverseHits.incrementAndGet();
            writeJson(exchange, 200, "{\"success\":true,\"ja3\":\"mock-ja3\"}", "application/json");
        });
        reverseServer.createContext("/api/fingerprint/spoof", exchange -> {
            reverseHits.incrementAndGet();
            writeJson(exchange, 200, "{\"success\":true,\"browser\":\"chrome\",\"platform\":\"windows\",\"fingerprint\":{\"userAgent\":\"mock\"}}", "application/json");
        });
        reverseServer.createContext("/api/canvas/fingerprint", exchange -> {
            reverseHits.incrementAndGet();
            writeJson(exchange, 200, "{\"success\":true,\"hash\":\"mock-canvas\"}", "application/json");
        });
        reverseServer.createContext("/api/browser/simulate", exchange -> {
            reverseHits.incrementAndGet();
            writeJson(exchange, 200, "{\"success\":true,\"result\":{\"ok\":true},\"cookies\":\"session=1\"}", "application/json");
        });
        reverseServer.createContext("/api/crypto/analyze", exchange -> {
            reverseHits.incrementAndGet();
            writeJson(
                exchange,
                200,
                "{\"success\":true,\"cryptoTypes\":[{\"name\":\"AES\",\"confidence\":0.9,\"modes\":[\"CBC\"]}],\"keys\":[\"secret\"],\"ivs\":[\"iv\"]}",
                "application/json"
            );
        });
        reverseServer.start();

        try {
            Path checkpointDir = Files.createTempDirectory("java-ultimate-checkpoints");
            String stdout = captureStdout(() ->
                EnhancedSpider.main(new String[]{
                    "ultimate",
                    "http://127.0.0.1:" + pageServer.getAddress().getPort() + "/",
                    "--reverse-service-url",
                    "http://127.0.0.1:" + reverseServer.getAddress().getPort(),
                    "--checkpoint-dir",
                    checkpointDir.toString()
                })
            );

            assertTrue(stdout.contains("启动 Java Spider 终极增强版"));
            assertTrue(stdout.contains("\"command\" : \"ultimate\""));
            assertTrue(stdout.contains("\"runtime\" : \"java\""));
            assertTrue(stdout.contains("\"summary\" : \"passed\""));
            assertTrue(stdout.contains("\"reverse\""));
            assertTrue(stdout.contains("mock-ja3"));
            assertTrue(stdout.contains("mock-canvas"));
            assertTrue(stdout.contains("\"canvas_fingerprint\""));
            assertTrue(stdout.contains("\"crypto_analysis\""));
            assertTrue(stdout.contains("AES"));
            assertTrue(reverseHits.get() > 0);
        } finally {
            pageServer.stop(0);
            reverseServer.stop(0);
        }
    }

    private String captureStdout(Runnable runnable) {
        PrintStream originalOut = System.out;
        ByteArrayOutputStream buffer = new ByteArrayOutputStream();

        try (PrintStream capture = new PrintStream(buffer, true, StandardCharsets.UTF_8)) {
            System.setOut(capture);
            runnable.run();
        } finally {
            System.setOut(originalOut);
        }

        return buffer.toString(StandardCharsets.UTF_8);
    }

    private static void writeJson(HttpExchange exchange, int status, String body, String contentType) throws IOException {
        byte[] payload = body.getBytes(StandardCharsets.UTF_8);
        exchange.getResponseHeaders().set("Content-Type", contentType);
        exchange.sendResponseHeaders(status, payload.length);
        exchange.getResponseBody().write(payload);
        exchange.close();
    }
}
