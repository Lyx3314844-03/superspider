package com.javaspider.cli;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;

public class WorkflowSpiderCLITest {

    @Test
    void workflowCliRunsWithoutThrowing() {
        assertDoesNotThrow(() -> WorkflowSpiderCLI.main(new String[]{
            "https://example.com",
            "CLI Title",
            "artifacts/test-cli.png"
        }));
    }
}
