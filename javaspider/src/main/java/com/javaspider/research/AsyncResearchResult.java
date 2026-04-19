package com.javaspider.research;

import java.util.LinkedHashMap;
import java.util.Map;

public record AsyncResearchResult(
    String seed,
    SiteProfile profile,
    Map<String, Object> extract,
    double durationMs,
    Map<String, Object> dataset,
    String error
) {
    public AsyncResearchResult {
        extract = extract == null ? Map.of() : new LinkedHashMap<>(extract);
        dataset = dataset == null ? Map.of() : new LinkedHashMap<>(dataset);
        error = error == null ? "" : error;
    }
}
