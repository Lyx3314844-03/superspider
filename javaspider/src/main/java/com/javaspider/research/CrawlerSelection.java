package com.javaspider.research;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public class CrawlerSelection {
    private final String scenario;
    private final String crawlerType;
    private final String recommendedRunner;
    private final List<String> runnerOrder;
    private final String siteFamily;
    private final String riskLevel;
    private final List<String> capabilities;
    private final List<String> strategyHints;
    private final List<String> jobTemplates;
    private final List<String> fallbackPlan;
    private final List<String> stopConditions;
    private final double confidence;
    private final List<String> reasonCodes;
    private final SiteProfile profile;

    public CrawlerSelection(
        String scenario,
        String crawlerType,
        String recommendedRunner,
        List<String> runnerOrder,
        String siteFamily,
        String riskLevel,
        List<String> capabilities,
        List<String> strategyHints,
        List<String> jobTemplates,
        List<String> fallbackPlan,
        List<String> stopConditions,
        double confidence,
        List<String> reasonCodes,
        SiteProfile profile
    ) {
        this.scenario = scenario;
        this.crawlerType = crawlerType;
        this.recommendedRunner = recommendedRunner;
        this.runnerOrder = new ArrayList<>(runnerOrder);
        this.siteFamily = siteFamily;
        this.riskLevel = riskLevel;
        this.capabilities = new ArrayList<>(capabilities);
        this.strategyHints = new ArrayList<>(strategyHints);
        this.jobTemplates = new ArrayList<>(jobTemplates);
        this.fallbackPlan = new ArrayList<>(fallbackPlan);
        this.stopConditions = new ArrayList<>(stopConditions);
        this.confidence = confidence;
        this.reasonCodes = new ArrayList<>(reasonCodes);
        this.profile = profile;
    }

    public String getScenario() {
        return scenario;
    }

    public String getCrawlerType() {
        return crawlerType;
    }

    public String getRecommendedRunner() {
        return recommendedRunner;
    }

    public List<String> getRunnerOrder() {
        return new ArrayList<>(runnerOrder);
    }

    public String getSiteFamily() {
        return siteFamily;
    }

    public String getRiskLevel() {
        return riskLevel;
    }

    public List<String> getCapabilities() {
        return new ArrayList<>(capabilities);
    }

    public List<String> getStrategyHints() {
        return new ArrayList<>(strategyHints);
    }

    public List<String> getJobTemplates() {
        return new ArrayList<>(jobTemplates);
    }

    public List<String> getFallbackPlan() {
        return new ArrayList<>(fallbackPlan);
    }

    public List<String> getStopConditions() {
        return new ArrayList<>(stopConditions);
    }

    public double getConfidence() {
        return confidence;
    }

    public List<String> getReasonCodes() {
        return new ArrayList<>(reasonCodes);
    }

    public SiteProfile getProfile() {
        return profile;
    }

    public Map<String, Object> toMap() {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("scenario", scenario);
        payload.put("crawler_type", crawlerType);
        payload.put("recommended_runner", recommendedRunner);
        payload.put("runner_order", getRunnerOrder());
        payload.put("site_family", siteFamily);
        payload.put("risk_level", riskLevel);
        payload.put("capabilities", getCapabilities());
        payload.put("strategy_hints", getStrategyHints());
        payload.put("job_templates", getJobTemplates());
        payload.put("fallback_plan", getFallbackPlan());
        payload.put("stop_conditions", getStopConditions());
        payload.put("confidence", confidence);
        payload.put("reason_codes", getReasonCodes());
        payload.put("profile", profile);
        return payload;
    }
}
