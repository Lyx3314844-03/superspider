package com.javaspider.workflow;

import java.util.List;
import java.util.Map;

public interface WorkflowExecutionContext extends AutoCloseable {
    void gotoUrl(String url);
    void waitFor(long timeoutMillis);
    void click(String selector);
    void type(String selector, String value);
    default void select(String selector, String value, Map<String, Object> options) {
    }
    default void hover(String selector) {
    }
    default void scroll(String selector, Map<String, Object> options) {
    }
    default Object evaluate(String script) {
        return null;
    }
    default List<Map<String, Object>> listenNetwork(Map<String, Object> options) {
        return List.of();
    }
    String captureHtml();
    void captureScreenshot(String artifactPath);
    String currentUrl();
    String title();
    boolean challengeDetected();
    boolean captchaDetected();
    default CaptchaRecoveryResult recoverCaptcha(Map<String, Object> options) {
        return CaptchaRecoveryResult.notAttempted();
    }
    String proxyHealth();
    @Override
    void close();
}
