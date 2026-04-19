package com.javaspider.research;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public class ResearchJob {
    private final List<String> seedUrls;
    private final Map<String, Object> siteProfile;
    private final Map<String, Object> extractSchema;
    private final List<Map<String, Object>> extractSpecs;
    private final Map<String, Object> policy;
    private final Map<String, Object> output;

    public ResearchJob(List<String> seedUrls) {
        this(seedUrls, Map.of(), Map.of(), List.of(), Map.of(), Map.of());
    }

    public ResearchJob(
        List<String> seedUrls,
        Map<String, Object> siteProfile,
        Map<String, Object> extractSchema,
        List<Map<String, Object>> extractSpecs,
        Map<String, Object> policy,
        Map<String, Object> output
    ) {
        this.seedUrls = new ArrayList<>(seedUrls);
        this.siteProfile = new LinkedHashMap<>(siteProfile);
        this.extractSchema = new LinkedHashMap<>(extractSchema);
        this.extractSpecs = new ArrayList<>(extractSpecs);
        this.policy = new LinkedHashMap<>(policy);
        this.output = new LinkedHashMap<>(output);
    }

    public List<String> getSeedUrls() {
        return new ArrayList<>(seedUrls);
    }

    public Map<String, Object> getSiteProfile() {
        return new LinkedHashMap<>(siteProfile);
    }

    public Map<String, Object> getExtractSchema() {
        return new LinkedHashMap<>(extractSchema);
    }

    public List<Map<String, Object>> getExtractSpecs() {
        return new ArrayList<>(extractSpecs);
    }

    public Map<String, Object> getPolicy() {
        return new LinkedHashMap<>(policy);
    }

    public Map<String, Object> getOutput() {
        return new LinkedHashMap<>(output);
    }
}
