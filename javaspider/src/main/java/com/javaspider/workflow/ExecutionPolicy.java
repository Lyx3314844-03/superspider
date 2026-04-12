package com.javaspider.workflow;

public class ExecutionPolicy {
    private final long stepTimeoutMillis;
    private final int maxRetries;

    public ExecutionPolicy(long stepTimeoutMillis, int maxRetries) {
        this.stepTimeoutMillis = stepTimeoutMillis;
        this.maxRetries = maxRetries;
    }

    public long getStepTimeoutMillis() {
        return stepTimeoutMillis;
    }

    public int getMaxRetries() {
        return maxRetries;
    }
}
