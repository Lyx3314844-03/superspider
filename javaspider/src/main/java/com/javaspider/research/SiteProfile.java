package com.javaspider.research;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public class SiteProfile {
    private final String url;
    private final String pageType;
    private final String siteFamily;
    private final Map<String, Boolean> signals;
    private final List<String> candidateFields;
    private final String riskLevel;
    private final String crawlerType;
    private final List<String> runnerOrder;
    private final List<String> strategyHints;
    private final List<String> jobTemplates;

    public SiteProfile(
        String url,
        String pageType,
        String siteFamily,
        Map<String, Boolean> signals,
        List<String> candidateFields,
        String riskLevel,
        String crawlerType,
        List<String> runnerOrder,
        List<String> strategyHints,
        List<String> jobTemplates
    ) {
        this.url = url;
        this.pageType = pageType;
        this.siteFamily = siteFamily;
        this.signals = new LinkedHashMap<>(signals);
        this.candidateFields = new ArrayList<>(candidateFields);
        this.riskLevel = riskLevel;
        this.crawlerType = crawlerType;
        this.runnerOrder = new ArrayList<>(runnerOrder);
        this.strategyHints = new ArrayList<>(strategyHints);
        this.jobTemplates = new ArrayList<>(jobTemplates);
    }

    public String getUrl() {
        return url;
    }

    public String getPageType() {
        return pageType;
    }

    public String getSiteFamily() {
        return siteFamily;
    }

    public Map<String, Boolean> getSignals() {
        return new LinkedHashMap<>(signals);
    }

    public List<String> getCandidateFields() {
        return new ArrayList<>(candidateFields);
    }

    public String getRiskLevel() {
        return riskLevel;
    }

    public String getCrawlerType() {
        return crawlerType;
    }

    public List<String> getRunnerOrder() {
        return new ArrayList<>(runnerOrder);
    }

    public List<String> getStrategyHints() {
        return new ArrayList<>(strategyHints);
    }

    public List<String> getJobTemplates() {
        return new ArrayList<>(jobTemplates);
    }
}
