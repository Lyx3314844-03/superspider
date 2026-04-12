package com.javaspider.workflow;

import com.javaspider.audit.AuditEvent;
import com.javaspider.audit.AuditTrail;
import com.javaspider.connector.Connector;
import com.javaspider.connector.OutputEnvelope;
import com.javaspider.session.SessionProfile;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

public class WorkflowSpider implements FlowExecutor {
    @FunctionalInterface
    public interface WorkflowExecutionContextFactory {
        WorkflowExecutionContext create(SessionProfile sessionProfile);
    }

    private final AuditTrail auditTrail;
    private final List<Connector> connectors = new ArrayList<>();
    private WorkflowExecutionContextFactory executionContextFactory = SeleniumWorkflowExecutionContext::new;

    public WorkflowSpider(AuditTrail auditTrail) {
        this.auditTrail = auditTrail;
    }

    public WorkflowSpider addConnector(Connector connector) {
        this.connectors.add(connector);
        return this;
    }

    public WorkflowSpider setExecutionContextFactory(WorkflowExecutionContextFactory factory) {
        this.executionContextFactory = factory;
        return this;
    }

    @Override
    public FlowResult execute(FlowJob job) {
        String runId = UUID.randomUUID().toString();
        Map<String, Object> extracted = new LinkedHashMap<>();
        List<String> artifacts = new ArrayList<>();

        auditTrail.append(new AuditEvent(job.getId(), "job", "job.created", Map.of(
            "run_id", runId,
            "step_count", job.getSteps().size()
        )));

        try (WorkflowExecutionContext context = executionContextFactory.create(job.getSessionProfile())) {
            for (FlowStep step : job.getSteps()) {
                auditTrail.append(new AuditEvent(job.getId(), step.getId(), "step.started", Map.of(
                    "type", step.getType().name()
                )));

                executeStep(step, context, extracted, artifacts);
                emitSecuritySignals(job, step, context);

                auditTrail.append(new AuditEvent(job.getId(), step.getId(), "step.succeeded", Map.of(
                    "type", step.getType().name()
                )));
            }
        }

        FlowResult result = new FlowResult(job.getId(), runId, extracted, artifacts);
        OutputEnvelope envelope = new OutputEnvelope(job.getId(), runId, extracted, artifacts);
        for (Connector connector : connectors) {
            connector.write(envelope);
        }
        auditTrail.append(new AuditEvent(job.getId(), "job", "job.completed", Map.of(
            "run_id", runId,
            "artifacts", artifacts.size(),
            "fields", extracted.keySet()
        )));
        return result;
    }

    private void executeStep(
        FlowStep step,
        WorkflowExecutionContext context,
        Map<String, Object> extracted,
        List<String> artifacts
    ) {
        switch (step.getType()) {
            case GOTO -> handleGoto(step, context);
            case WAIT -> handleWait(step, context);
            case CLICK -> handleClick(step, context);
            case TYPE -> handleType(step, context);
            case SELECT -> handleSelect(step, context);
            case HOVER -> handleHover(step, context);
            case SCROLL -> handleScroll(step, context);
            case EVAL -> handleEval(step, context, extracted);
            case LISTEN_NETWORK -> handleListenNetwork(step, context, extracted);
            case EXTRACT -> handleExtract(step, context, extracted);
            case SCREENSHOT -> handleScreenshot(step, context, artifacts);
            case DOWNLOAD -> handleArtifact(step, artifacts);
        }
    }

    private void handleGoto(FlowStep step, WorkflowExecutionContext context) {
        String url = metadataString(step, "url", step.getSelector());
        if (url != null && !url.isBlank()) {
            context.gotoUrl(url);
        }
    }

    private void handleWait(FlowStep step, WorkflowExecutionContext context) {
        Object timeout = step.getMetadata().get("timeout_ms");
        long waitFor = timeout instanceof Number ? ((Number) timeout).longValue() : 500L;
        context.waitFor(waitFor);
    }

    private void handleClick(FlowStep step, WorkflowExecutionContext context) {
        if (step.getSelector() != null && !step.getSelector().isBlank()) {
            context.click(step.getSelector());
        }
    }

    private void handleType(FlowStep step, WorkflowExecutionContext context) {
        if (step.getSelector() != null && !step.getSelector().isBlank()) {
            context.type(step.getSelector(), step.getValue() == null ? "" : step.getValue());
        }
    }

    private void handleSelect(FlowStep step, WorkflowExecutionContext context) {
        if (step.getSelector() != null && !step.getSelector().isBlank()) {
            context.select(step.getSelector(), step.getValue() == null ? "" : step.getValue(), step.getMetadata());
        }
    }

    private void handleHover(FlowStep step, WorkflowExecutionContext context) {
        if (step.getSelector() != null && !step.getSelector().isBlank()) {
            context.hover(step.getSelector());
        }
    }

    private void handleScroll(FlowStep step, WorkflowExecutionContext context) {
        context.scroll(step.getSelector(), step.getMetadata());
    }

    private void handleEval(FlowStep step, WorkflowExecutionContext context, Map<String, Object> extracted) {
        String script = step.getValue() == null ? "" : step.getValue();
        if (script.isBlank()) {
            return;
        }
        Object value = context.evaluate(script);
        Object field = step.getMetadata().getOrDefault("field", step.getMetadata().get("save_as"));
        if (field != null && value != null) {
            extracted.put(String.valueOf(field), value);
        }
    }

    private void handleListenNetwork(FlowStep step, WorkflowExecutionContext context, Map<String, Object> extracted) {
        String field = metadataString(step, "field", metadataString(step, "save_as", "network_requests"));
        extracted.put(field, context.listenNetwork(step.getMetadata()));
    }

    private void handleExtract(FlowStep step, WorkflowExecutionContext context, Map<String, Object> extracted) {
        Object field = step.getMetadata().getOrDefault("field", step.getSelector());
        Object defaultValue = switch (String.valueOf(field)) {
            case "title" -> context.title();
            case "url" -> context.currentUrl();
            case "html" -> context.captureHtml();
            case "dom" -> context.captureHtml();
            default -> step.getValue();
        };
        Object value = step.getMetadata().getOrDefault("value", defaultValue);
        if (field != null && value != null) {
            extracted.put(String.valueOf(field), value);
        }
    }

    private void handleScreenshot(FlowStep step, WorkflowExecutionContext context, List<String> artifacts) {
        String artifactPath = metadataString(step, "artifact", step.getValue());
        if (artifactPath != null && !artifactPath.isBlank()) {
            context.captureScreenshot(artifactPath);
            artifacts.add(artifactPath);
            return;
        }
        handleArtifact(step, artifacts);
    }

    private void handleArtifact(FlowStep step, List<String> artifacts) {
        Object artifact = step.getMetadata().get("artifact");
        if (artifact != null) {
            artifacts.add(String.valueOf(artifact));
        } else if (step.getValue() != null && !step.getValue().isBlank()) {
            artifacts.add(step.getValue());
        } else {
            artifacts.add(step.getId() + ".bin");
        }
    }

    private String metadataString(FlowStep step, String key, String fallback) {
        Object value = step.getMetadata().get(key);
        if (value != null) {
            return String.valueOf(value);
        }
        return fallback;
    }

    private void emitSecuritySignals(FlowJob job, FlowStep step, WorkflowExecutionContext context) {
        String proxyHealth = context.proxyHealth();
        if (!"not-configured".equals(proxyHealth)) {
            auditTrail.append(new AuditEvent(job.getId(), step.getId(), "proxy.health", Map.of(
                "status", proxyHealth
            )));
        }
        if (context.challengeDetected()) {
            auditTrail.append(new AuditEvent(job.getId(), step.getId(), "challenge.detected", Map.of(
                "url", context.currentUrl()
            )));
        }
        if (context.captchaDetected()) {
            auditTrail.append(new AuditEvent(job.getId(), step.getId(), "captcha.detected", Map.of(
                "url", context.currentUrl()
            )));
            handleCaptchaRecovery(job, step, context);
        }
    }

    private void handleCaptchaRecovery(FlowJob job, FlowStep step, WorkflowExecutionContext context) {
        Map<String, Object> options = captchaOptions(job, step);
        boolean shouldAttempt = shouldAttemptCaptchaRecovery(options);
        if (!shouldAttempt) {
            return;
        }

        CaptchaRecoveryResult recovery = context.recoverCaptcha(options);
        if (recovery == null) {
            recovery = CaptchaRecoveryResult.failed(stringValue(options.get("solver")), "captcha recovery returned null result");
        }

        if (recovery.attempted() && recovery.solved()) {
            auditTrail.append(new AuditEvent(job.getId(), step.getId(), "captcha.solved", Map.of(
                "solver", blankOrDefault(recovery.solver(), "unknown"),
                "continued", recovery.continued(),
                "solution_length", recovery.solutionLength()
            )));
            return;
        }

        Map<String, Object> details = new LinkedHashMap<>();
        details.put("solver", blankOrDefault(recovery.solver(), blankOrDefault(stringValue(options.get("solver")), "unknown")));
        details.put("reason", blankOrDefault(recovery.reason(), "captcha recovery did not complete"));
        details.put("attempted", recovery.attempted());
        auditTrail.append(new AuditEvent(job.getId(), step.getId(), "captcha.failed", details));

        if (shouldFailOnUnsolvedCaptcha(options)) {
            throw new IllegalStateException(blankOrDefault(recovery.reason(), "captcha recovery failed"));
        }
    }

    private Map<String, Object> captchaOptions(FlowJob job, FlowStep step) {
        Map<String, Object> options = new LinkedHashMap<>();
        mergeCaptchaOptions(options, job.getOutputContract());
        mergeCaptchaOptions(options, mapValue(job.getOutputContract().get("captcha")));
        mergeCaptchaOptions(options, step.getMetadata());
        mergeCaptchaOptions(options, mapValue(step.getMetadata().get("captcha")));
        return options;
    }

    private void mergeCaptchaOptions(Map<String, Object> target, Map<String, Object> source) {
        if (source == null || source.isEmpty()) {
            return;
        }
        putIfPresent(target, "auto_solve", source.get("auto_solve"));
        putIfPresent(target, "auto_solve", source.get("captcha_auto_solve"));
        putIfPresent(target, "fail_on_unsolved", source.get("fail_on_unsolved"));
        putIfPresent(target, "fail_on_unsolved", source.get("captcha_fail_on_unsolved"));
        putIfPresent(target, "solver", source.get("solver"));
        putIfPresent(target, "solver", source.get("captcha_solver"));
        putIfPresent(target, "api_key", source.get("api_key"));
        putIfPresent(target, "api_key", source.get("captcha_api_key"));
        putIfPresent(target, "api_secret", source.get("api_secret"));
        putIfPresent(target, "api_secret", source.get("captcha_api_secret"));
        putIfPresent(target, "mock_solution", source.get("mock_solution"));
        putIfPresent(target, "mock_solution", source.get("captcha_mock_solution"));
        putIfPresent(target, "image_selector", source.get("image_selector"));
        putIfPresent(target, "image_selector", source.get("captcha_image_selector"));
        putIfPresent(target, "image_url", source.get("image_url"));
        putIfPresent(target, "image_url", source.get("captcha_image_url"));
        putIfPresent(target, "image_base64", source.get("image_base64"));
        putIfPresent(target, "image_base64", source.get("captcha_image_base64"));
        putIfPresent(target, "input_selector", source.get("input_selector"));
        putIfPresent(target, "input_selector", source.get("captcha_input_selector"));
        putIfPresent(target, "submit_selector", source.get("submit_selector"));
        putIfPresent(target, "submit_selector", source.get("captcha_submit_selector"));
        putIfPresent(target, "continue_selector", source.get("continue_selector"));
        putIfPresent(target, "continue_selector", source.get("captcha_continue_selector"));
        putIfPresent(target, "wait_after_submit_ms", source.get("wait_after_submit_ms"));
        putIfPresent(target, "wait_after_submit_ms", source.get("captcha_wait_after_submit_ms"));
    }

    private boolean shouldAttemptCaptchaRecovery(Map<String, Object> options) {
        if (options.isEmpty()) {
            return false;
        }
        if (truthy(options.get("auto_solve"))) {
            return true;
        }
        return options.containsKey("solver")
            || options.containsKey("mock_solution")
            || options.containsKey("image_selector")
            || options.containsKey("image_url")
            || options.containsKey("image_base64");
    }

    private boolean shouldFailOnUnsolvedCaptcha(Map<String, Object> options) {
        if (options.containsKey("fail_on_unsolved")) {
            return truthy(options.get("fail_on_unsolved"));
        }
        return shouldAttemptCaptchaRecovery(options);
    }

    private boolean truthy(Object value) {
        if (value instanceof Boolean bool) {
            return bool;
        }
        if (value instanceof Number number) {
            return number.intValue() != 0;
        }
        return value != null && Boolean.parseBoolean(String.valueOf(value));
    }

    private void putIfPresent(Map<String, Object> target, String key, Object value) {
        if (value == null) {
            return;
        }
        if (value instanceof String text && text.isBlank()) {
            return;
        }
        target.put(key, value);
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> mapValue(Object value) {
        if (value instanceof Map<?, ?> map) {
            return (Map<String, Object>) map;
        }
        return Map.of();
    }

    private String stringValue(Object value) {
        return value == null ? "" : String.valueOf(value);
    }

    private String blankOrDefault(String value, String fallback) {
        return value == null || value.isBlank() ? fallback : value;
    }
}
