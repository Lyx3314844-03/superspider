package com.javaspider.research;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public class SiteProfile {
    private final String url;
    private final String pageType;
    private final Map<String, Boolean> signals;
    private final List<String> candidateFields;
    private final String riskLevel;

    public SiteProfile(
        String url,
        String pageType,
        Map<String, Boolean> signals,
        List<String> candidateFields,
        String riskLevel
    ) {
        this.url = url;
        this.pageType = pageType;
        this.signals = new LinkedHashMap<>(signals);
        this.candidateFields = new ArrayList<>(candidateFields);
        this.riskLevel = riskLevel;
    }

    public String getUrl() {
        return url;
    }

    public String getPageType() {
        return pageType;
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
}
