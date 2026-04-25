package com.javaspider.research;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;

public class CrawlerSelector {
    private final ResearchRuntime runtime;

    public CrawlerSelector() {
        this(new ResearchRuntime());
    }

    public CrawlerSelector(ResearchRuntime runtime) {
        this.runtime = runtime;
    }

    public CrawlerSelection select(CrawlerSelectionRequest request) {
        String content = request.getContent().isBlank()
            ? "<title>" + request.getUrl() + "</title>"
            : request.getContent();
        SiteProfile profile = runtime.profile(request.getUrl(), content);
        String scenario = request.getScenarioHint().isBlank()
            ? scenario(profile)
            : request.getScenarioHint();
        List<String> runnerOrder = profile.getRunnerOrder().isEmpty()
            ? List.of("http", "browser")
            : profile.getRunnerOrder();

        return new CrawlerSelection(
            scenario,
            profile.getCrawlerType(),
            runnerOrder.get(0),
            runnerOrder,
            profile.getSiteFamily(),
            profile.getRiskLevel(),
            capabilities(profile, runnerOrder),
            profile.getStrategyHints(),
            profile.getJobTemplates(),
            fallbackPlan(profile, runnerOrder),
            stopConditions(profile),
            confidence(profile),
            reasonCodes(profile),
            profile
        );
    }

    public CrawlerSelection select(String url, String content) {
        return select(new CrawlerSelectionRequest(url, content));
    }

    private String scenario(SiteProfile profile) {
        return switch (profile.getCrawlerType()) {
            case "login_session" -> "authenticated_session";
            case "infinite_scroll_listing" -> "infinite_scroll_listing";
            case "ecommerce_search" -> "ecommerce_listing";
            case "ecommerce_detail" -> "ecommerce_detail";
            case "hydrated_spa" -> "javascript_hydrated_page";
            case "api_bootstrap" -> "embedded_api_or_bootstrap_json";
            case "search_results" -> "search_results";
            case "static_listing" -> "static_listing";
            case "static_detail" -> "static_detail";
            default -> "generic_page";
        };
    }

    private List<String> capabilities(SiteProfile profile, List<String> runnerOrder) {
        Map<String, Boolean> signals = profile.getSignals();
        List<String> capabilities = new ArrayList<>();
        if (runnerOrder.contains("http")) capabilities.add("http_fetch");
        if (runnerOrder.contains("browser")) capabilities.add("browser_rendering");
        if (Boolean.TRUE.equals(signals.get("has_pagination"))) capabilities.add("pagination");
        if (Boolean.TRUE.equals(signals.get("has_infinite_scroll"))) capabilities.add("scroll_automation");
        if (Boolean.TRUE.equals(signals.get("has_login"))) capabilities.add("session_cookies");
        if (Boolean.TRUE.equals(signals.get("has_api_bootstrap")) || Boolean.TRUE.equals(signals.get("has_graphql"))) {
            capabilities.add("network_or_bootstrap_json");
        }
        if (Boolean.TRUE.equals(signals.get("has_price")) || Boolean.TRUE.equals(signals.get("has_product_schema"))) {
            capabilities.add("commerce_fields");
        }
        if (Boolean.TRUE.equals(signals.get("has_captcha"))) capabilities.add("anti_bot_evidence");
        if ("detail".equals(profile.getPageType())) capabilities.add("detail_extraction");
        if ("list".equals(profile.getPageType())) capabilities.add("listing_extraction");
        return unique(capabilities);
    }

    private List<String> fallbackPlan(SiteProfile profile, List<String> runnerOrder) {
        Map<String, Boolean> signals = profile.getSignals();
        List<String> plan = "browser".equals(runnerOrder.get(0))
            ? new ArrayList<>(List.of(
                "render with browser and save DOM, screenshot, and network artifacts",
                "promote stable JSON/API responses into HTTP replay jobs",
                "fall back to DOM selectors only after bootstrap/network data is empty"
            ))
            : new ArrayList<>(List.of(
                "start with HTTP fetch and schema/meta/bootstrap extraction",
                "fall back to browser rendering when required fields are missing",
                "persist raw HTML and normalized fields for selector regression tests"
            ));
        if (Boolean.TRUE.equals(signals.get("has_captcha"))) {
            plan.add("stop on captcha/challenge pages and return evidence instead of bypassing blindly");
        }
        if ("login_session".equals(profile.getCrawlerType())) {
            plan.add("establish authenticated storage state before queueing follow-up URLs");
        }
        return plan;
    }

    private List<String> stopConditions(SiteProfile profile) {
        if ("infinite_scroll_listing".equals(profile.getCrawlerType())) {
            return List.of(
                "stop after two unchanged DOM or item-count snapshots",
                "stop when network responses repeat without new item IDs",
                "respect configured max pages/items/time budget"
            );
        }
        if ("list".equals(profile.getPageType())) {
            return List.of(
                "stop when next-page URL repeats or disappears",
                "stop when item URLs no longer add new fingerprints",
                "respect configured max pages/items/time budget"
            );
        }
        if ("login_session".equals(profile.getCrawlerType())) {
            return List.of(
                "stop if post-login page still contains password or captcha signals",
                "stop when authenticated session storage cannot be established"
            );
        }
        return List.of(
            "stop after required fields are present and normalized",
            "stop when HTTP and browser surfaces both produce empty required fields"
        );
    }

    private double confidence(SiteProfile profile) {
        double score = 0.55;
        if (!"generic_http".equals(profile.getCrawlerType())) score += 0.15;
        if (!"generic".equals(profile.getSiteFamily())) score += 0.1;
        if (!profile.getCandidateFields().isEmpty()) score += 0.05;
        if (profile.getRunnerOrder().size() > 1) score += 0.05;
        if ("medium".equals(profile.getRiskLevel())) score -= 0.05;
        if ("high".equals(profile.getRiskLevel())) score -= 0.15;
        return Math.round(Math.max(0.2, Math.min(0.95, score)) * 100.0) / 100.0;
    }

    private List<String> reasonCodes(SiteProfile profile) {
        List<String> reasons = new ArrayList<>(List.of(
            "crawler_type:" + profile.getCrawlerType(),
            "page_type:" + profile.getPageType(),
            "site_family:" + profile.getSiteFamily(),
            "risk:" + profile.getRiskLevel()
        ));
        for (Map.Entry<String, Boolean> entry : profile.getSignals().entrySet()) {
            if (Boolean.TRUE.equals(entry.getValue())) {
                reasons.add("signal:" + entry.getKey());
            }
        }
        return unique(reasons);
    }

    private List<String> unique(List<String> values) {
        return new ArrayList<>(new LinkedHashSet<>(values));
    }
}
