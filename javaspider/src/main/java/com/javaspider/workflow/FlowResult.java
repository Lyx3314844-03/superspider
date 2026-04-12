package com.javaspider.workflow;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public class FlowResult {
    private final String jobId;
    private final String runId;
    private final Map<String, Object> extracted;
    private final List<String> artifacts;

    public FlowResult(String jobId, String runId, Map<String, Object> extracted, List<String> artifacts) {
        this.jobId = jobId;
        this.runId = runId;
        this.extracted = Collections.unmodifiableMap(new LinkedHashMap<>(extracted));
        this.artifacts = List.copyOf(artifacts);
    }

    public String getJobId() {
        return jobId;
    }

    public String getRunId() {
        return runId;
    }

    public Map<String, Object> getExtracted() {
        return extracted;
    }

    public List<String> getArtifacts() {
        return artifacts;
    }
}
