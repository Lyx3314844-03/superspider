package com.javaspider.workflow;

import com.javaspider.audit.InMemoryAuditTrail;
import com.javaspider.connector.InMemoryConnector;
import com.javaspider.session.SessionProfile;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

public class WorkflowSpiderTest {

    @Test
    void workflowSpiderProducesAuditOutputAndExecutesSteps() {
        InMemoryAuditTrail auditTrail = new InMemoryAuditTrail();
        InMemoryConnector connector = new InMemoryConnector();
        FakeWorkflowExecutionContext context = new FakeWorkflowExecutionContext();
        WorkflowSpider spider = new WorkflowSpider(auditTrail)
            .addConnector(connector)
            .setExecutionContextFactory(session -> context);

        FlowJob job = new FlowJob(
            "job-1",
            "browser-flow",
            new SessionProfile("session-1", "account-1", "residential", "chrome-stealth", Map.of()),
            List.of(
                new FlowStep("step-1", FlowStepType.GOTO, "https://example.com", null, Map.of()),
                new FlowStep("step-2", FlowStepType.TYPE, "#search", "workflow", Map.of()),
                new FlowStep("step-3", FlowStepType.CLICK, "#submit", null, Map.of()),
                new FlowStep("step-4", FlowStepType.EXTRACT, "title", "ignored", Map.of("field", "title")),
                new FlowStep("step-5", FlowStepType.SCREENSHOT, null, "artifacts/job-1.png", Map.of())
            ),
            Map.of("format", "json"),
            new ExecutionPolicy(5_000L, 1)
        );

        FlowResult result = spider.execute(job);

        assertEquals("Fake Title", result.getExtracted().get("title"));
        assertEquals(1, result.getArtifacts().size());
        assertFalse(auditTrail.list().isEmpty());
        assertEquals(1, connector.list().size());
        assertEquals(
            List.of(
                "goto:https://example.com",
                "type:#search=workflow",
                "click:#submit",
                "shot:artifacts/job-1.png"
            ),
            context.actions
        );
        List<String> signalTypes = auditTrail.list().stream()
            .map(event -> event.getType())
            .filter(type -> type.contains(".detected") || type.equals("proxy.health"))
            .toList();
        assertFalse(signalTypes.isEmpty());
        assertTrue(signalTypes.contains("proxy.health"));
        assertTrue(signalTypes.contains("challenge.detected"));
        assertTrue(signalTypes.contains("captcha.detected"));
    }

    @Test
    void workflowSpiderAttemptsCaptchaRecoveryWhenConfigured() {
        InMemoryAuditTrail auditTrail = new InMemoryAuditTrail();
        FakeWorkflowExecutionContext context = new FakeWorkflowExecutionContext();
        context.recoveryResult = CaptchaRecoveryResult.solved("mock", true, 4);

        WorkflowSpider spider = new WorkflowSpider(auditTrail)
            .setExecutionContextFactory(session -> context);

        FlowJob job = new FlowJob(
            "job-2",
            "captcha-flow",
            new SessionProfile("session-1", "account-1", "residential", "chrome-stealth", Map.of()),
            List.of(
                new FlowStep("goto", FlowStepType.GOTO, "https://example.com", null, Map.of())
            ),
            Map.of(
                "captcha", Map.of(
                    "auto_solve", true,
                    "mock_solution", "1234",
                    "submit_selector", "#continue"
                )
            ),
            new ExecutionPolicy(5_000L, 1)
        );

        spider.execute(job);

        assertEquals(1, context.recoveryOptions.size());
        assertEquals("1234", context.recoveryOptions.get(0).get("mock_solution"));
        assertTrue(auditTrail.list().stream().anyMatch(event -> event.getType().equals("captcha.solved")));
    }

    @Test
    void workflowSpiderFailsWhenCaptchaRecoveryIsRequiredButUnsolved() {
        InMemoryAuditTrail auditTrail = new InMemoryAuditTrail();
        FakeWorkflowExecutionContext context = new FakeWorkflowExecutionContext();
        context.recoveryResult = CaptchaRecoveryResult.failed("mock", "solver exhausted");

        WorkflowSpider spider = new WorkflowSpider(auditTrail)
            .setExecutionContextFactory(session -> context);

        FlowJob job = new FlowJob(
            "job-3",
            "captcha-failure",
            new SessionProfile("session-1", "account-1", "residential", "chrome-stealth", Map.of()),
            List.of(
                new FlowStep("goto", FlowStepType.GOTO, "https://example.com", null, Map.of())
            ),
            Map.of("captcha_auto_solve", true),
            new ExecutionPolicy(5_000L, 1)
        );

        IllegalStateException error = assertThrows(IllegalStateException.class, () -> spider.execute(job));
        assertTrue(error.getMessage().contains("solver exhausted"));
        assertTrue(auditTrail.list().stream().anyMatch(event -> event.getType().equals("captcha.failed")));
    }

    static final class FakeWorkflowExecutionContext implements WorkflowExecutionContext {
        private final List<String> actions = new ArrayList<>();
        private final List<Map<String, Object>> recoveryOptions = new ArrayList<>();
        private CaptchaRecoveryResult recoveryResult = CaptchaRecoveryResult.notAttempted();

        @Override
        public void gotoUrl(String url) {
            actions.add("goto:" + url);
        }

        @Override
        public void waitFor(long timeoutMillis) {
            actions.add("wait:" + timeoutMillis);
        }

        @Override
        public void click(String selector) {
            actions.add("click:" + selector);
        }

        @Override
        public void type(String selector, String value) {
            actions.add("type:" + selector + "=" + value);
        }

        @Override
        public String captureHtml() {
            return "<html>fake</html>";
        }

        @Override
        public void captureScreenshot(String artifactPath) {
            actions.add("shot:" + artifactPath);
        }

        @Override
        public String currentUrl() {
            return "https://example.com";
        }

        @Override
        public String title() {
            return "Fake Title";
        }

        @Override
        public boolean challengeDetected() {
            return true;
        }

        @Override
        public boolean captchaDetected() {
            return true;
        }

        @Override
        public CaptchaRecoveryResult recoverCaptcha(Map<String, Object> options) {
            recoveryOptions.add(options);
            return recoveryResult;
        }

        @Override
        public String proxyHealth() {
            return "healthy";
        }

        @Override
        public void close() {
        }
    }
}
