package com.javaspider;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.assertTrue;

class ScaffoldAIContractTest {

    @TempDir
    Path tempDir;

    @AfterEach
    void resetBrowserFactory() {
        EnhancedSpider.resetBrowserFetchRunnerFactoryForTests();
    }

    @Test
    void scaffoldAIProducesBlueprintSchemaPromptAndSpider() throws Exception {
        Path project = tempDir.resolve("project");
        Files.createDirectories(project);
        Files.writeString(
            project.resolve("scrapy-project.json"),
            "{\"name\":\"project\",\"runtime\":\"java\",\"entry\":\"src/main/java/project/Main.java\",\"url\":\"https://example.com\"}",
            StandardCharsets.UTF_8
        );
        Files.writeString(
            project.resolve("ai-auth.json"),
            "{\"actions\":[{\"type\":\"assert\",\"url_contains\":\"/dashboard\"},{\"type\":\"save_as\",\"value\":\"url\",\"save_as\":\"final_url\"}]}",
            StandardCharsets.UTF_8
        );
        Path html = project.resolve("page.html");
        Files.writeString(
            html,
            "<html><head><title>Java Scaffold</title><meta name=\"description\" content=\"Java scaffold summary\"></head><body><article>hello</article></body></html>",
            StandardCharsets.UTF_8
        );

        EnhancedSpider.main(new String[]{
            "scrapy",
            "scaffold-ai",
            "--project", project.toString(),
            "--html-file", html.toString(),
            "--name", "scaffold_ai"
        });

        assertTrue(Files.exists(project.resolve("ai-plan.json")));
        assertTrue(Files.exists(project.resolve("ai-schema.json")));
        assertTrue(Files.exists(project.resolve("ai-blueprint.json")));
        assertTrue(Files.exists(project.resolve("ai-extract-prompt.txt")));
        assertTrue(Files.exists(project.resolve("ai-auth.json")));
        assertTrue(Files.exists(project.resolve("src").resolve("main").resolve("java").resolve("project").resolve("spiders").resolve("Scaffold_aiSpiderFactory.java")));
    }

    @Test
    void authCaptureProducesAuthAssets() throws Exception {
        Path project = tempDir.resolve("auth-project");
        Files.createDirectories(project);
        Files.writeString(
            project.resolve("scrapy-project.json"),
            "{\"name\":\"project\",\"runtime\":\"java\",\"entry\":\"src/main/java/project/Main.java\",\"url\":\"https://example.com\"}",
            StandardCharsets.UTF_8
        );
        Files.writeString(
            project.resolve("ai-auth.json"),
            "{\"actions\":[{\"type\":\"assert\",\"url_contains\":\"/dashboard\"},{\"type\":\"save_as\",\"value\":\"url\",\"save_as\":\"final_url\"}]}",
            StandardCharsets.UTF_8
        );

        EnhancedSpider.setBrowserFetchRunnerFactoryForTests(() -> new EnhancedSpider.BrowserFetchRunner() {
            @Override
            public EnhancedSpider.BrowserFetchResult fetch(String url, String screenshotPath, String htmlPath, java.util.Map<String, Object> cfg) {
                try {
                    @SuppressWarnings("unchecked")
                    java.util.Map<String, Object> browser = (java.util.Map<String, Object>) cfg.get("browser");
                    java.nio.file.Path state = java.nio.file.Paths.get(String.valueOf(browser.get("storage_state_file")));
                    java.nio.file.Path cookies = java.nio.file.Paths.get(String.valueOf(browser.get("cookies_file")));
                    Files.createDirectories(state.getParent());
                    Files.writeString(state, "{}", StandardCharsets.UTF_8);
                    Files.writeString(cookies, "[]", StandardCharsets.UTF_8);
                } catch (Exception e) {
                    throw new RuntimeException(e);
                }
                EnhancedSpider.BrowserFetchResult result = new EnhancedSpider.BrowserFetchResult();
                result.title = "Capture";
                result.url = url;
                result.html_path = htmlPath;
                result.screenshot_path = screenshotPath;
                return result;
            }

            @Override
            public void close() {
            }
        });

        EnhancedSpider.main(new String[]{
            "scrapy",
            "auth-capture",
            "--project", project.toString(),
            "--url", "https://example.com"
        });

        assertTrue(Files.exists(project.resolve("ai-auth.json")));
        assertTrue(Files.exists(project.resolve("artifacts").resolve("auth").resolve("auth-state.json")));
        assertTrue(Files.exists(project.resolve("artifacts").resolve("auth").resolve("auth-cookies.json")));
        String authPayload = Files.readString(project.resolve("ai-auth.json"));
        assertTrue(authPayload.contains("\"actions\""));
        assertTrue(authPayload.contains("\"action_examples\""));
        assertTrue(authPayload.contains("\"final_url\""));
    }
}
