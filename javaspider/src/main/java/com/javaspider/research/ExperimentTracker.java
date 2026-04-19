package com.javaspider.research;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

public class ExperimentTracker {
    private final List<ExperimentRecord> experiments = new ArrayList<>();

    public List<ExperimentRecord> getExperiments() {
        return new ArrayList<>(experiments);
    }

    public ExperimentRecord record(
        String name,
        List<String> urls,
        List<Map<String, Object>> results,
        Map<String, Object> schema,
        Map<String, Object> metadata
    ) {
        ExperimentRecord record = new ExperimentRecord(
            "exp-%03d".formatted(experiments.size() + 1),
            name,
            System.currentTimeMillis() / 1000.0,
            urls,
            schema == null ? Map.of() : schema,
            results == null ? List.of() : results,
            metadata == null ? Map.of() : metadata
        );
        experiments.add(record);
        return record;
    }

    public Optional<ExperimentRecord> getExperiment(String name) {
        return experiments.stream().filter(item -> item.name().equals(name)).findFirst();
    }

    public Map<String, Object> compare() {
        List<Map<String, Object>> summaries = new ArrayList<>();
        int totalUrls = 0;
        int totalResults = 0;
        for (ExperimentRecord experiment : experiments) {
            totalUrls += experiment.urls().size();
            totalResults += experiment.results().size();
            summaries.add(Map.of(
                "id", experiment.id(),
                "name", experiment.name(),
                "urls_count", experiment.urls().size(),
                "results_count", experiment.results().size(),
                "success_rate", calculateSuccessRate(experiment.results()),
                "avg_extract_time", averageExtractTime(experiment.results())
            ));
        }
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("experiments", summaries);
        payload.put("summary", Map.of(
            "total_experiments", experiments.size(),
            "total_urls", totalUrls,
            "total_results", totalResults
        ));
        return payload;
    }

    public List<Map<String, Object>> toRows() {
        List<Map<String, Object>> rows = new ArrayList<>();
        for (ExperimentRecord experiment : experiments) {
            for (Map<String, Object> result : experiment.results()) {
                rows.add(Map.of(
                    "experiment_id", experiment.id(),
                    "experiment_name", experiment.name(),
                    "seed", result.get("seed"),
                    "extract", result.get("extract"),
                    "duration_ms", result.get("duration_ms"),
                    "error", result.getOrDefault("error", "")
                ));
            }
        }
        return rows;
    }

    private double calculateSuccessRate(List<Map<String, Object>> results) {
        if (results.isEmpty()) {
            return 0.0;
        }
        long success = results.stream()
            .filter(result -> String.valueOf(result.getOrDefault("error", "")).isBlank())
            .count();
        return success * 100.0 / results.size();
    }

    private double averageExtractTime(List<Map<String, Object>> results) {
        return results.stream()
            .map(result -> result.get("duration_ms"))
            .filter(Number.class::isInstance)
            .map(Number.class::cast)
            .mapToDouble(Number::doubleValue)
            .average()
            .orElse(0.0);
    }
}
