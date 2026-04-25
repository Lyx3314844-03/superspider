package com.javaspider.examples.ecommerce;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.javaspider.browser.BrowserManager;
import org.openqa.selenium.By;

import java.net.URI;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public final class EcommerceSeleniumCrawler {
    private EcommerceSeleniumCrawler() {
    }

    public static Map<String, Object> capture(String siteFamily, String mode, Path outputDir) throws Exception {
        EcommerceSiteProfiles.Profile profile = EcommerceSiteProfiles.profileFor(siteFamily);
        String normalizedMode = switch (mode) {
            case "detail" -> "detail";
            case "review" -> "review";
            default -> "catalog";
        };
        String targetUrl = switch (normalizedMode) {
            case "detail" -> profile.detailUrl;
            case "review" -> profile.reviewUrl;
            default -> profile.catalogUrl;
        };

        Files.createDirectories(outputDir);
        String prefix = "javaspider-" + siteFamily + "-" + normalizedMode;
        Path htmlPath = outputDir.resolve(prefix + ".html");
        Path jsonPath = outputDir.resolve(prefix + ".json");
        Path screenshotPath = outputDir.resolve(prefix + ".png");
        boolean highFrictionSite = isHighFrictionSite(siteFamily);
        boolean headless = envBool("ECOM_BROWSER_HEADLESS", !highFrictionSite);
        int manualSeconds = envInt("ECOM_BROWSER_MANUAL_SECONDS", highFrictionSite ? 180 : 0);
        int attempts = envInt("ECOM_BROWSER_ATTEMPTS", highFrictionSite ? 2 : 1);
        String userAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36";
        String userDataDir = envString(
            "ECOM_BROWSER_PROFILE",
            outputDir.resolve("profiles").resolve("javaspider-" + siteFamily).toString()
        );

        BrowserManager browser = new BrowserManager(
            BrowserManager.BrowserType.CHROME,
            headless,
            false,
            userAgent,
            "",
            userDataDir,
            List.of("--disable-blink-features=AutomationControlled")
        );
        try {
            browser.init();
            browser.applyEcommerceRuntimeProfile(userAgent);
            Map<String, Object> accessChallenge = Map.of("blocked", false, "signals", List.of());
            for (int attempt = 1; attempt <= Math.max(1, attempts); attempt++) {
                browser.warmup(originUrl(targetUrl));
                browser.navigate(targetUrl);
                browser.waitForPageLoad();
                waitForEcommerceReady(browser, "catalog".equals(normalizedMode) ? 8 : 4);
                accessChallenge = browser.detectAccessChallenge();
                if (!Boolean.TRUE.equals(accessChallenge.get("blocked"))) {
                    break;
                }
                if (!headless && manualSeconds > 0) {
                    System.out.println("Access challenge detected. Complete login/verification in the opened browser within " + manualSeconds + "s.");
                    browser.waitForManualAccess(Duration.ofSeconds(manualSeconds));
                    waitForEcommerceReady(browser, "catalog".equals(normalizedMode) ? 4 : 2);
                    accessChallenge = browser.detectAccessChallenge();
                    if (!Boolean.TRUE.equals(accessChallenge.get("blocked"))) {
                        break;
                    }
                }
                if (attempt < Math.max(1, attempts)) {
                    Thread.sleep(4000L * attempt);
                }
            }
            String html = browser.getPageSource();
            Files.writeString(htmlPath, html);
            browser.screenshotToFile(screenshotPath.toString());

            List<String> links = EcommerceSiteProfiles.collectMatches(html, List.of("<a[^>]+href=[\"']([^\"']+)[\"']"), 100);
            List<String> images = EcommerceSiteProfiles.collectMatches(html, List.of("<img[^>]+(?:src|data-src|data-lazy-img)=[\"']([^\"']+)[\"']"), 100);
            List<String> apiCandidates = EcommerceSiteProfiles.extractApiCandidates(html, 30);
            List<String> skuCandidates = EcommerceSiteProfiles.collectMatches(html, profile.itemIdPatterns, 20);

            Map<String, Object> result = new LinkedHashMap<>();
            result.put("kind", "ecommerce_browser_capture");
            result.put("site_family", siteFamily);
            result.put("mode", normalizedMode);
            result.put("url", browser.getCurrentUrl());
            result.put("title", browser.getTitle());
            result.put("runtime", Map.of(
                "headless", headless,
                "user_data_dir", userDataDir,
                "attempts", attempts
            ));
            result.put("detector", UniversalEcommerceDetector.detect(browser.getCurrentUrl(), html).toMap());
            result.put("product_link_candidates", EcommerceSiteProfiles.collectProductLinks(browser.getCurrentUrl(), links, profile, 30));
            result.put("sku_candidates", skuCandidates);
            result.put("image_candidates", EcommerceSiteProfiles.collectImageLinks(browser.getCurrentUrl(), images, 30));
            result.put("image_gallery", EcommerceSiteProfiles.extractImageGallery(browser.getCurrentUrl(), images));
            result.put("json_ld_products", EcommerceSiteProfiles.extractJsonLdProducts(html, 10));
            result.put("bootstrap_products", EcommerceSiteProfiles.extractBootstrapProducts(html, 10));
            result.put("embedded_json_blocks", EcommerceSiteProfiles.extractEmbeddedJsonBlocks(html, 5, 2000));
            result.put("api_candidates", apiCandidates);
            result.put("api_job_templates", EcommerceSiteProfiles.buildApiJobTemplates(browser.getCurrentUrl(), siteFamily, apiCandidates, skuCandidates, 20));
            result.put("access_challenge", accessChallenge);
            result.put("parameter_table", EcommerceSiteProfiles.extractParameterTable(html));
            result.put("coupons_promotions", EcommerceSiteProfiles.detectCouponsPromotions(html));
            result.put("stock_status", EcommerceSiteProfiles.extractStockStatus(html));
            result.put("artifacts", Map.of("html", htmlPath.toString(), "json", jsonPath.toString(), "screenshot", screenshotPath.toString()));

            new ObjectMapper().writerWithDefaultPrettyPrinter().writeValue(jsonPath.toFile(), result);
            return result;
        } finally {
            browser.close();
        }
    }

    private static boolean isHighFrictionSite(String siteFamily) {
        return switch (siteFamily.toLowerCase()) {
            case "jd", "taobao", "tmall", "pdd", "amazon" -> true;
            default -> false;
        };
    }

    private static boolean envBool(String name, boolean fallback) {
        String value = System.getenv(name);
        if (value == null || value.isBlank()) {
            return fallback;
        }
        return switch (value.trim().toLowerCase()) {
            case "1", "true", "yes", "on" -> true;
            default -> false;
        };
    }

    private static int envInt(String name, int fallback) {
        String value = System.getenv(name);
        if (value == null || value.isBlank()) {
            return fallback;
        }
        try {
            return Integer.parseInt(value.trim());
        } catch (NumberFormatException ignored) {
            return fallback;
        }
    }

    private static String envString(String name, String fallback) {
        String value = System.getenv(name);
        return value == null || value.isBlank() ? fallback : value;
    }

    private static String originUrl(String rawUrl) {
        try {
            URI uri = URI.create(rawUrl);
            if (uri.getScheme() == null || uri.getHost() == null) {
                return "";
            }
            return uri.getScheme() + "://" + uri.getHost() + "/";
        } catch (Exception ignored) {
            return "";
        }
    }

    private static void waitForEcommerceReady(BrowserManager browser, int scrollRounds) {
        for (String selector : List.of("[data-sku]", "[data-product-id]", ".gl-item", ".product", ".product-item", "[itemtype*='Product']")) {
            try {
                browser.waitForElement(selector, By.cssSelector(selector));
                break;
            } catch (Exception ignored) {
            }
        }
        browser.scrollToBottomHumanized(Math.max(1, scrollRounds));
        try {
            Thread.sleep(800);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }

    public static void main(String[] args) throws Exception {
        String siteFamily = args.length > 0 ? args[0] : EcommerceSiteProfiles.DEFAULT_SITE_FAMILY;
        String mode = args.length > 1 ? args[1] : "catalog";
        Map<String, Object> result = capture(siteFamily, mode, Path.of("artifacts", "browser"));
        System.out.println(new ObjectMapper().writeValueAsString(Map.of("artifacts", result.get("artifacts"))));
    }
}
