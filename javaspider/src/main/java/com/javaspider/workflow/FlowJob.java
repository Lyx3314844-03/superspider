package com.javaspider.workflow;

import com.javaspider.session.SessionProfile;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public class FlowJob {
    private final String id;
    private final String name;
    private final SessionProfile sessionProfile;
    private final List<FlowStep> steps;
    private final Map<String, Object> outputContract;
    private final ExecutionPolicy policy;

    public FlowJob(String id,
                   String name,
                   SessionProfile sessionProfile,
                   List<FlowStep> steps,
                   Map<String, Object> outputContract,
                   ExecutionPolicy policy) {
        this.id = id;
        this.name = name;
        this.sessionProfile = sessionProfile;
        this.steps = List.copyOf(steps);
        this.outputContract = outputContract == null
            ? Collections.emptyMap()
            : Collections.unmodifiableMap(new LinkedHashMap<>(outputContract));
        this.policy = policy;
    }

    public String getId() {
        return id;
    }

    public String getName() {
        return name;
    }

    public SessionProfile getSessionProfile() {
        return sessionProfile;
    }

    public List<FlowStep> getSteps() {
        return steps;
    }

    public Map<String, Object> getOutputContract() {
        return outputContract;
    }

    public ExecutionPolicy getPolicy() {
        return policy;
    }
}
