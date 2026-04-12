package com.javaspider.cli;

import com.javaspider.audit.InMemoryAuditTrail;
import com.javaspider.connector.InMemoryConnector;
import com.javaspider.session.SessionProfile;
import com.javaspider.workflow.ExecutionPolicy;
import com.javaspider.workflow.FlowJob;
import com.javaspider.workflow.FlowResult;
import com.javaspider.workflow.FlowStep;
import com.javaspider.workflow.FlowStepType;
import com.javaspider.workflow.WorkflowSpider;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;

public final class WorkflowSpiderCLI {
    private WorkflowSpiderCLI() {
    }

    public static void main(String[] args) {
        if (args.length == 0) {
            printUsage();
            return;
        }

        String target = args[0];
        String title = args.length > 1 ? args[1] : "WorkflowSpider Result";
        String screenshot = args.length > 2 ? args[2] : "artifacts/workflow-" + System.currentTimeMillis() + ".png";

        InMemoryAuditTrail auditTrail = new InMemoryAuditTrail();
        InMemoryConnector connector = new InMemoryConnector();
        WorkflowSpider spider = new WorkflowSpider(auditTrail).addConnector(connector);

        List<FlowStep> steps = new ArrayList<>();
        steps.add(new FlowStep("goto", FlowStepType.GOTO, target, null, Map.of("url", target)));
        steps.add(new FlowStep("extract-title", FlowStepType.EXTRACT, "title", title, Map.of(
            "field", "title",
            "value", title
        )));
        steps.add(new FlowStep("capture", FlowStepType.SCREENSHOT, null, screenshot, Map.of(
            "artifact", screenshot
        )));

        FlowJob job = new FlowJob(
            "workflow-" + UUID.randomUUID(),
            "workflow-cli",
            new SessionProfile("session-cli", "local-user", "default", "chrome-stealth", Map.of()),
            steps,
            Map.of("format", "json"),
            new ExecutionPolicy(5000L, 1)
        );

        FlowResult result = spider.execute(job);

        System.out.println("Workflow job completed");
        System.out.println("Job ID: " + result.getJobId());
        System.out.println("Run ID: " + result.getRunId());
        System.out.println("Extracted: " + result.getExtracted());
        System.out.println("Artifacts: " + result.getArtifacts());
        System.out.println("Audit events: " + auditTrail.list().size());
        System.out.println("Connector outputs: " + connector.list().size());
    }

    private static void printUsage() {
        System.out.println("Usage: WorkflowSpiderCLI <target-url> [title] [screenshot-path]");
    }
}
