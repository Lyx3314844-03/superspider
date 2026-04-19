package workflow

import (
	"path/filepath"
	"testing"

	"gospider/connector"
	"gospider/events"
)

func TestWorkflowSpiderExecutesStepsAndPersistsOutputs(t *testing.T) {
	eventBus := events.NewMemoryBus(32)
	connectorSink := &connector.InMemoryConnector{}
	spider := New(eventBus).AddConnector(connectorSink)

	ctx := NewMemoryExecutionContext()
	ctx.SetTitle("Go Workflow")
	ctx.SetHTML("<html><title>Go Workflow</title></html>")
	spider.SetExecutionContextFactory(func() ExecutionContext { return ctx })

	result, err := spider.Execute(FlowJob{
		ID:   "workflow-go",
		Name: "workflow-go",
		Steps: []FlowStep{
			{ID: "goto", Type: StepGoto, Selector: "https://example.com"},
			{ID: "extract-url", Type: StepExtract, Selector: "url"},
			{ID: "extract-title", Type: StepExtract, Selector: "title"},
			{ID: "shot", Type: StepScreenshot, Value: filepath.Join(t.TempDir(), "workflow.png")},
		},
	})
	if err != nil {
		t.Fatalf("expected workflow to succeed: %v", err)
	}
	if result.Extracted["url"] != "https://example.com" {
		t.Fatalf("unexpected extracted url: %#v", result.Extracted)
	}
	if result.Extracted["title"] != "Go Workflow" {
		t.Fatalf("unexpected extracted title: %#v", result.Extracted)
	}
	if len(result.Artifacts) != 1 {
		t.Fatalf("expected screenshot artifact, got %#v", result.Artifacts)
	}
	if got := connectorSink.List(); len(got) != 1 {
		t.Fatalf("expected connector envelope, got %#v", got)
	}
	if got := eventBus.List(10, "workflow.job.completed"); len(got) != 1 {
		t.Fatalf("expected workflow completion event, got %#v", got)
	}
}
