package com.javaspider.cli;

import org.junit.jupiter.api.Test;

import java.io.ByteArrayOutputStream;
import java.io.PrintStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

import com.sun.net.httpserver.HttpServer;
import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class SuperSpiderCLITest {

    @Test
    void capabilitiesCommandPrintsIntegratedModules() {
        String output = captureStdout(() ->
            SuperSpiderCLI.main(new String[]{"capabilities"})
        );

        assertTrue(output.contains("\"framework\""));
        assertTrue(output.contains("workflow.WorkflowSpider"));
        assertTrue(output.contains("CurlToJavaConverter"));
        assertTrue(output.contains("\"media\""));
        assertTrue(output.contains("\"curl\""));
        assertTrue(output.contains("\"ultimate\""));
        assertTrue(output.contains("\"scrapy\""));
        assertTrue(output.contains("\"jobdir\""));
        assertTrue(output.contains("\"http-cache\""));
        assertTrue(output.contains("\"console\""));
        assertTrue(output.contains("\"audit\""));
        assertTrue(output.contains("\"preflight\""));
        assertTrue(output.contains("\"run\""));
        assertTrue(output.contains("\"async-job\""));
        assertTrue(output.contains("\"api\""));
        assertTrue(output.contains("\"web\""));
        assertTrue(output.contains("\"research\""));
        assertTrue(output.contains("research.ResearchRuntime"));
        assertTrue(output.contains("\"queue_backends\""));
        assertTrue(output.contains("\"native_driver\""));
        assertTrue(output.contains("\"browser_compatibility\""));
        assertTrue(output.contains("\"feature_gates\""));
        assertTrue(output.contains("\"night_mode\""));
        assertTrue(output.contains("\"node_discovery\""));
        assertTrue(output.contains("\"security\""));
        assertTrue(output.contains("\"event_system\""));
        assertTrue(output.contains("bridge.CrawleeBridgeClient"));
        assertTrue(output.contains("\"crawlee_bridge\""));
        assertTrue(output.contains("\"connectors\""));
    }

    @Test
    void jobCommandExecutesNormalizedSpec() throws Exception {
        Path path = Files.createTempFile("superspider-job", ".json");
        Files.writeString(path, """
            {
              "name": "java-job",
              "runtime": "browser",
              "target": { "url": "https://example.com" },
              "extract": [
                { "field": "title", "type": "css", "expr": "title" }
              ],
              "output": { "format": "json", "path": "artifacts/java-job.png" },
              "metadata": {
                "mock_extract": { "title": "Java Job Title" }
              }
            }
            """);

        String output = captureStdout(() ->
            SuperSpiderCLI.main(new String[]{"job", "--file", path.toString()})
        );

        assertTrue(output.contains("\"runtime\" : \"browser\""));
        assertTrue(output.contains("\"state\" : \"succeeded\""));
        assertTrue(output.contains("\"url\" : \"https://example.com\""));
        assertTrue(output.contains("\"error\" : \"\""));
        assertTrue(output.contains("\"latency_ms\""));
        assertTrue(output.contains("Java Job Title"));
        assertTrue(output.contains("artifacts/java-job.png"));
    }

    @Test
    void jobCommandPersistsEnvelopeWhenJsonOutputRequested() throws Exception {
        Path dir = Files.createTempDirectory("superspider-json");
        Path outputPath = dir.resolve("job-output.json");
        Path path = dir.resolve("job.json");
        Files.writeString(path, """
            {
              "name": "java-job-json",
              "runtime": "browser",
              "target": { "url": "https://example.com" },
              "extract": [
                { "field": "title", "type": "css", "expr": "title" }
              ],
              "output": { "format": "json", "path": "%s" },
              "metadata": {
                "mock_extract": { "title": "Java JSON Title" }
              }
            }
            """.formatted(outputPath.toString().replace("\\", "\\\\")));

        captureStdout(() ->
            SuperSpiderCLI.main(new String[]{"job", "--file", path.toString()})
        );

        String persisted = Files.readString(outputPath);
        assertTrue(persisted.contains("Java JSON Title"));
        assertTrue(persisted.contains("\"state\" : \"succeeded\""));
        assertTrue(persisted.contains("-graph.json"));
        assertTrue(Files.exists(dir.resolve("control-plane").resolve("results.jsonl")));
        assertTrue(Files.exists(dir.resolve("control-plane").resolve("events.jsonl")));
        assertTrue(Files.exists(dir.resolve("control-plane").resolve("java-job-json-audit.jsonl")));
        assertTrue(Files.exists(dir.resolve("control-plane").resolve("java-job-json-connector.jsonl")));
        assertTrue(Files.readString(dir.resolve("control-plane").resolve("results.jsonl")).contains("-graph.json"));
    }

    @Test
    void jobCommandSupportsFailureInjection() throws Exception {
        Path path = Files.createTempFile("superspider-fail", ".json");
        Files.writeString(path, """
            {
              "name": "java-job-fail",
              "runtime": "browser",
              "target": { "url": "https://example.com" },
              "output": { "format": "json" },
              "metadata": {
                "fail_job": "synthetic failure"
              }
            }
            """);

        RuntimeException error = assertThrows(RuntimeException.class, () ->
            SuperSpiderCLI.main(new String[]{"job", "--file", path.toString()})
        );
        assertTrue(error.getMessage().contains("job execution failed"));
        String output = captureStdout(() -> assertThrows(RuntimeException.class, () ->
            SuperSpiderCLI.main(new String[]{"job", "--file", path.toString()})
        ));
        assertTrue(output.contains("\"state\" : \"failed\""));
        assertTrue(output.contains("synthetic failure"));
    }

    @Test
    void jobCommandRejectsBlockedAllowedDomain() throws Exception {
        Path path = Files.createTempFile("superspider-domain-fail", ".json");
        Files.writeString(path, """
            {
              "name": "java-job-domain-fail",
              "runtime": "browser",
              "target": {
                "url": "https://example.com",
                "allowed_domains": ["blocked.com"]
              },
              "output": { "format": "json" }
            }
            """);

        String output = captureStdout(() -> assertThrows(RuntimeException.class, () ->
            SuperSpiderCLI.main(new String[]{"job", "--file", path.toString()})
        ));
        assertTrue(output.contains("\"state\" : \"failed\""));
        assertTrue(output.contains("allowed_domains"));
    }

    @Test
    void jobCommandRejectsByteBudgetOverflow() throws Exception {
        Path path = Files.createTempFile("superspider-budget-fail", ".json");
        Files.writeString(path, """
            {
              "name": "java-job-budget-fail",
              "runtime": "browser",
              "target": { "url": "https://example.com" },
              "policy": {
                "budget": { "bytes_in": 8 }
              },
              "output": { "format": "json" },
              "metadata": {
                "mock_html": "<html><title>Budget Overflow</title></html>"
              }
            }
            """);

        String output = captureStdout(() -> assertThrows(RuntimeException.class, () ->
            SuperSpiderCLI.main(new String[]{"job", "--file", path.toString()})
        ));
        assertTrue(output.contains("\"state\" : \"failed\""));
        assertTrue(output.contains("budget.bytes_in"));
    }

    @Test
    void workflowCommandDelegates() {
        assertDoesNotThrow(() ->
            SuperSpiderCLI.main(new String[]{"workflow", "https://example.com"})
        );
    }

    @Test
    void sharedFrameworkCommandsDelegateToEnhancedSpider() throws Exception {
        Path output = Files.createTempDirectory("superspider-config").resolve("spider-framework.yaml");

        String stdout = captureStdout(() ->
            SuperSpiderCLI.main(new String[]{"config", "init", "--output", output.toString()})
        );

        assertTrue(stdout.contains("Wrote shared config"));
        assertTrue(Files.readString(output).contains("runtime: java"));
    }

    @Test
    void nodeReverseCommandDelegatesToEnhancedSpider() throws Exception {
        HttpServer reverseServer = HttpServer.create(new InetSocketAddress(0), 0);
        reverseServer.createContext("/health", exchange -> {
            byte[] body = "{\"status\":\"ok\"}".getBytes(StandardCharsets.UTF_8);
            exchange.getResponseHeaders().add("Content-Type", "application/json");
            exchange.sendResponseHeaders(200, body.length);
            exchange.getResponseBody().write(body);
            exchange.close();
        });
        reverseServer.start();

        try {
            String stdout = captureStdout(() ->
                SuperSpiderCLI.main(new String[]{
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
    void curlConvertCommandUsesUnifiedFrameworkSurface() {
        String output = captureStdout(() ->
            SuperSpiderCLI.main(new String[]{
                "curl",
                "convert",
                "--command",
                "curl -X POST \"https://example.com/api\" -H \"Accept: application/json\"",
                "--target",
                "okhttp",
            })
        );

        assertTrue(output.contains("\"command\" : \"curl convert\""));
        assertTrue(output.contains("\"runtime\" : \"java\""));
        assertTrue(output.contains("\"target\" : \"okhttp\""));
        assertTrue(output.contains("OkHttpClient"));
        assertTrue(output.contains("https://example.com/api"));
    }

    @Test
    void versionCommandUsesUnifiedFrameworkSurface() {
        String output = captureStdout(() ->
            SuperSpiderCLI.main(new String[]{"version"})
        );

        assertTrue(output.contains("JavaSpider Framework CLI v"));
    }

    @Test
    void researchCommandRunsAsyncAndSoak() {
        String runOutput = captureStdout(() ->
            SuperSpiderCLI.main(new String[]{
                "research",
                "run",
                "--url",
                "https://example.com",
                "--schema-json",
                "{\"properties\":{\"title\":{\"type\":\"string\"}}}",
                "--content",
                "<title>Research Demo</title>"
            })
        );
        assertTrue(runOutput.contains("Research Demo"));

        String asyncOutput = captureStdout(() ->
            SuperSpiderCLI.main(new String[]{
                "research",
                "async",
                "--url",
                "https://example.com/1",
                "--url",
                "https://example.com/2",
                "--schema-json",
                "{\"properties\":{\"title\":{\"type\":\"string\"}}}",
                "--content",
                "<title>Async Research</title>"
            })
        );
        assertTrue(asyncOutput.contains("\"command\" : \"research async\""));

        String soakOutput = captureStdout(() ->
            SuperSpiderCLI.main(new String[]{
                "research",
                "soak",
                "--url",
                "https://example.com/1",
                "--url",
                "https://example.com/2",
                "--schema-json",
                "{\"properties\":{\"title\":{\"type\":\"string\"}}}",
                "--content",
                "<title>Soak Research</title>",
                "--rounds",
                "2"
            })
        );
        assertTrue(soakOutput.contains("\"results\" : 4"));
    }

    @Test
    void jobCommandSurfacesExtendedContractFieldsAndBrowserCaptureWarnings() throws Exception {
        Path dir = Files.createTempDirectory("superspider-extended");
        Path outputPath = dir.resolve("job-output.json");
        Path path = dir.resolve("job.json");
        Files.writeString(path, """
            {
              "name": "java-extended-job",
              "runtime": "browser",
              "target": {
                "url": "https://example.com",
                "cookies": { "session": "abc" },
                "allowed_domains": ["example.com"]
              },
              "browser": {
                "profile": "chrome-stealth",
                "actions": [
                  { "type": "wait", "timeout_ms": 25 },
                  { "type": "click", "selector": "#submit" },
                  { "type": "type", "selector": "#query", "value": "ultraman" },
                  { "type": "hover", "selector": "#hoverable" },
                  { "type": "scroll", "selector": "#submit" },
                  { "type": "select", "selector": "#mode", "value": "fast" },
                  { "type": "eval", "value": "return document.readyState", "save_as": "page_state" },
                  { "type": "listen_network", "save_as": "network_events" }
                ],
                "capture": ["html", "console"]
              },
              "extract": [
                { "field": "title", "type": "css", "expr": "title" }
              ],
              "resources": {
                "timeout_ms": 1500,
                "retries": 3
              },
              "anti_bot": {
                "session_mode": "sticky",
                "stealth": true,
                "proxy_pool": "residential"
              },
              "policy": {
                "same_domain_only": true,
                "budget": { "requests": 5 }
              },
              "schedule": {
                "mode": "queued",
                "queue_name": "critical",
                "delay_seconds": 5
              },
              "output": { "format": "json", "path": "%s" },
              "metadata": {
                "mock_html": "<html><title>Extended Title</title><body><button id='submit'>Go</button><input id='query'/><div id='hoverable'></div><select id='mode'><option value='fast'>fast</option></select></body></html>",
                "mock_eval_result": "complete",
                "mock_network_requests": [
                  { "name": "https://cdn.example.com/app.js", "type": "script" },
                  { "name": "https://api.example.com/items", "type": "fetch" }
                ],
                "mock_extract": { "title": "Extended Title" }
              }
            }
            """.formatted(outputPath.toString().replace("\\", "\\\\")));

        String output = captureStdout(() ->
            SuperSpiderCLI.main(new String[]{"job", "--file", path.toString()})
        );

        assertTrue(output.contains("\"session_mode\" : \"sticky\""));
        assertTrue(output.contains("\"same_domain_only\" : true"));
        assertTrue(output.contains("\"queue_name\" : \"critical\""));
        assertTrue(output.contains("\"page_state\" : \"complete\""));
        assertTrue(output.contains("\"network_events\""));
        assertTrue(output.contains("cdn.example.com/app.js"));
        assertTrue(output.contains("Extended Title"));
        assertTrue(output.contains("unsupported browser.capture value in JavaSpider job runtime: console"));
        assertTrue(Files.readString(outputPath).contains("\"retries\" : 3"));
    }

    @Test
    void jobCommandExtractsJsonPathAndSchemaValidatedFields() throws Exception {
        Path path = Files.createTempFile("superspider-json-extract", ".json");
        Files.writeString(path, """
            {
              "name": "java-json-extract",
              "runtime": "ai",
              "target": { "url": "https://example.com", "body": "{\\"product\\":{\\"name\\":\\"Capsule\\",\\"price\\":199}}" },
              "extract": [
                { "field": "name", "type": "json_path", "path": "product.name", "required": true, "schema": { "type": "string" } },
                { "field": "price", "type": "json_path", "path": "product.price", "required": true, "schema": { "type": "number" } }
              ],
              "output": { "format": "json" }
            }
            """);

        String output = captureStdout(() ->
            SuperSpiderCLI.main(new String[]{"job", "--file", path.toString()})
        );

        assertTrue(output.contains("\"name\" : \"Capsule\""));
        assertTrue(output.contains("\"price\" : 199"));
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
}
