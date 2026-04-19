package com.javaspider.research;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public record ExperimentRecord(
    String id,
    String name,
    double timestamp,
    List<String> urls,
    Map<String, Object> schema,
    List<Map<String, Object>> results,
    Map<String, Object> metadata
) {
    public ExperimentRecord {
        urls = new ArrayList<>(urls);
        schema = new LinkedHashMap<>(schema);
        List<Map<String, Object>> copiedResults = new ArrayList<>();
        for (Map<String, Object> result : results) {
            copiedResults.add(new LinkedHashMap<>(result));
        }
        results = copiedResults;
        metadata = new LinkedHashMap<>(metadata);
    }
}
