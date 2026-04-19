package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"gospider/connector"
	"gospider/events"
	"gospider/workflow"
)

func workflowCommand(args []string) int {
	if len(args) == 0 || args[0] != "run" {
		fmt.Fprintln(os.Stderr, "usage: gospider workflow run --file <workflow.json>")
		return 2
	}

	cmd := flag.NewFlagSet("workflow run", flag.ContinueOnError)
	filePath := cmd.String("file", "", "workflow JSON spec path")
	if err := cmd.Parse(args[1:]); err != nil {
		return 2
	}
	if strings.TrimSpace(*filePath) == "" {
		fmt.Fprintln(os.Stderr, "gospider workflow run requires --file")
		return 2
	}

	data, err := os.ReadFile(*filePath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "read workflow spec failed: %v\n", err)
		return 1
	}
	var job workflow.FlowJob
	if err := json.Unmarshal(data, &job); err != nil {
		fmt.Fprintf(os.Stderr, "parse workflow spec failed: %v\n", err)
		return 1
	}
	if strings.TrimSpace(job.Name) == "" {
		job.Name = "workflow"
	}
	if strings.TrimSpace(job.ID) == "" {
		job.ID = job.Name
	}

	controlPlaneDir := filepath.Join(filepath.Dir(*filePath), "artifacts", "control-plane")
	eventPath := filepath.Join(controlPlaneDir, fmt.Sprintf("%s-workflow-events.jsonl", job.Name))
	connectorPath := filepath.Join(controlPlaneDir, fmt.Sprintf("%s-workflow-connector.jsonl", job.Name))

	spider := workflow.New(events.NewFileBus(eventPath)).
		AddConnector(connector.NewFileConnector(connectorPath))
	result, err := spider.Execute(job)
	if err != nil {
		fmt.Fprintf(os.Stderr, "workflow execution failed: %v\n", err)
		return 1
	}

	payload := map[string]any{
		"command":        "workflow run",
		"runtime":        "go",
		"job_id":         result.JobID,
		"run_id":         result.RunID,
		"extract":        result.Extracted,
		"artifacts":      result.Artifacts,
		"events_path":    eventPath,
		"connector_path": connectorPath,
	}
	encoded, _ := json.MarshalIndent(payload, "", "  ")
	fmt.Println(string(encoded))
	return 0
}
