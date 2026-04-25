package com.javaspider.research;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class CrawlerSelectorTest {
    private static final ObjectMapper MAPPER = new ObjectMapper();

    @Test
    void selectorRecommendsBrowserForEcommerceListing() {
        CrawlerSelection selection = new CrawlerSelector().select(new CrawlerSelectionRequest(
            "https://shop.example.com/search?q=phone",
            "<html><script>window.__NEXT_DATA__ = {\"items\":[]}</script><body>"
                + "<input type=\"search\"><div class=\"product-list\"><div class=\"sku-item\">SKU-1</div>"
                + "<span class=\"price\">￥10</span><button>加入购物车</button></div></body></html>"
        ));

        assertEquals("ecommerce_listing", selection.getScenario());
        assertEquals("ecommerce_search", selection.getCrawlerType());
        assertEquals("browser", selection.getRecommendedRunner());
        assertTrue(selection.getCapabilities().contains("commerce_fields"));
        assertTrue(selection.getReasonCodes().contains("signal:has_price"));
        assertTrue(selection.getConfidence() >= 0.7);
        Map<String, Object> payload = selection.toMap();
        assertEquals("browser", payload.get("recommended_runner"));
        assertEquals("ecommerce_search", ((SiteProfile) payload.get("profile")).getCrawlerType());
    }

    @Test
    void selectorCapturesLoginRisk() {
        CrawlerSelection selection = new CrawlerSelector().select(
            "https://secure.example.com/login",
            "<form><input type=\"password\"><div>验证码</div></form>"
        );

        assertEquals("authenticated_session", selection.getScenario());
        assertEquals("high", selection.getRiskLevel());
        assertTrue(selection.getCapabilities().contains("session_cookies"));
        assertTrue(selection.getCapabilities().contains("anti_bot_evidence"));
        assertTrue(selection.getFallbackPlan().stream().anyMatch(item -> item.toLowerCase().contains("captcha")));
    }

    @Test
    void selectorMatchesSharedEcommerceGoldenContract() throws Exception {
        Path root = Path.of("..").toAbsolutePath().normalize();
        String html = Files.readString(
            root.resolve("examples/crawler-selection/ecommerce-search-input.html"),
            StandardCharsets.UTF_8
        );
        @SuppressWarnings("unchecked")
        Map<String, Object> golden = MAPPER.readValue(
            root.resolve("examples/crawler-selection/ecommerce-search-selection.json").toFile(),
            Map.class
        );

        Map<String, Object> payload = new CrawlerSelector()
            .select("https://shop.example.com/search?q=phone", html)
            .toMap();

        for (String field : new String[] {
            "scenario",
            "crawler_type",
            "recommended_runner",
            "runner_order",
            "site_family",
            "risk_level",
            "confidence"
        }) {
            assertEquals(golden.get(field), payload.get(field), field);
        }
        @SuppressWarnings("unchecked")
        Iterable<String> capabilities = (Iterable<String>) golden.get("capabilities");
        for (String capability : capabilities) {
            assertTrue(((Iterable<?>) payload.get("capabilities")).iterator().hasNext());
            assertTrue(((java.util.List<?>) payload.get("capabilities")).contains(capability), capability);
        }
    }
}
