package com.javaspider.research;

public record AsyncResearchConfig(
    int maxConcurrent,
    double timeoutSeconds,
    boolean enableStreaming
) {
    public AsyncResearchConfig() {
        this(5, 30.0, false);
    }
}
