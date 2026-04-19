package workflow

import (
	"fmt"
	"os"
	"path/filepath"
	"time"

	"gospider/connector"
	"gospider/events"
)

type FlowStepType string

const (
	StepGoto          FlowStepType = "goto"
	StepWait          FlowStepType = "wait"
	StepClick         FlowStepType = "click"
	StepType          FlowStepType = "type"
	StepSelect        FlowStepType = "select"
	StepHover         FlowStepType = "hover"
	StepScroll        FlowStepType = "scroll"
	StepEval          FlowStepType = "eval"
	StepListenNetwork FlowStepType = "listen_network"
	StepExtract       FlowStepType = "extract"
	StepDownload      FlowStepType = "download"
	StepScreenshot    FlowStepType = "screenshot"
)

type FlowStep struct {
	ID       string         `json:"id"`
	Type     FlowStepType   `json:"type"`
	Selector string         `json:"selector,omitempty"`
	Value    string         `json:"value,omitempty"`
	Metadata map[string]any `json:"metadata,omitempty"`
}

type ExecutionPolicy struct {
	StepTimeoutMillis int64 `json:"step_timeout_millis,omitempty"`
	MaxRetries        int   `json:"max_retries,omitempty"`
}

type FlowJob struct {
	ID             string         `json:"id"`
	Name           string         `json:"name"`
	Steps          []FlowStep     `json:"steps"`
	OutputContract map[string]any `json:"output_contract,omitempty"`
	Policy         ExecutionPolicy `json:"policy,omitempty"`
}

type FlowResult struct {
	JobID     string         `json:"job_id"`
	RunID     string         `json:"run_id"`
	Extracted map[string]any `json:"extracted"`
	Artifacts []string       `json:"artifacts"`
}

type ExecutionContext interface {
	GotoURL(string)
	WaitFor(int64)
	Click(string)
	Type(string, string)
	Select(string, string, map[string]any)
	Hover(string)
	Scroll(string, map[string]any)
	Evaluate(string) any
	ListenNetwork(map[string]any) []map[string]any
	CaptureHTML() string
	CaptureScreenshot(string)
	CurrentURL() string
	Title() string
	Close() error
}

type MemoryExecutionContext struct {
	currentURL    string
	title         string
	html          string
	evaluations   map[string]any
	networkEvents []map[string]any
	interactions  []string
}

func NewMemoryExecutionContext() *MemoryExecutionContext {
	return &MemoryExecutionContext{
		title:       "workflow",
		html:        "<html><title>workflow</title></html>",
		evaluations: map[string]any{},
		networkEvents: []map[string]any{
			{"url": "https://example.com/api", "method": "GET", "status": 200},
		},
		interactions: make([]string, 0),
	}
}

func (c *MemoryExecutionContext) GotoURL(url string) { c.currentURL = url }
func (c *MemoryExecutionContext) WaitFor(timeoutMillis int64) {
	if timeoutMillis > 0 {
		time.Sleep(time.Duration(timeoutMillis) * time.Millisecond)
	}
}
func (c *MemoryExecutionContext) Click(selector string) { c.interactions = append(c.interactions, "click:"+selector) }
func (c *MemoryExecutionContext) Type(selector, value string) {
	c.interactions = append(c.interactions, "type:"+selector+"="+value)
}
func (c *MemoryExecutionContext) Select(selector, value string, _ map[string]any) {
	c.interactions = append(c.interactions, "select:"+selector+"="+value)
}
func (c *MemoryExecutionContext) Hover(selector string) { c.interactions = append(c.interactions, "hover:"+selector) }
func (c *MemoryExecutionContext) Scroll(selector string, _ map[string]any) {
	c.interactions = append(c.interactions, "scroll:"+selector)
}
func (c *MemoryExecutionContext) Evaluate(script string) any {
	if value, ok := c.evaluations[script]; ok {
		return value
	}
	return script
}
func (c *MemoryExecutionContext) ListenNetwork(_ map[string]any) []map[string]any {
	return append([]map[string]any(nil), c.networkEvents...)
}
func (c *MemoryExecutionContext) CaptureHTML() string { return c.html }
func (c *MemoryExecutionContext) CaptureScreenshot(path string) {
	_ = writeArtifact(path, []byte("workflow-screenshot"))
}
func (c *MemoryExecutionContext) CurrentURL() string { return c.currentURL }
func (c *MemoryExecutionContext) Title() string      { return c.title }
func (c *MemoryExecutionContext) Close() error       { return nil }

func (c *MemoryExecutionContext) SetTitle(title string) { c.title = title }
func (c *MemoryExecutionContext) SetHTML(html string)   { c.html = html }
func (c *MemoryExecutionContext) SetEvaluation(script string, value any) {
	c.evaluations[script] = value
}

type WorkflowSpider struct {
	connectors              []connector.Connector
	eventBus                events.Bus
	executionContextFactory func() ExecutionContext
}

func New(eventBus events.Bus) *WorkflowSpider {
	return &WorkflowSpider{
		connectors:              make([]connector.Connector, 0),
		eventBus:                eventBus,
		executionContextFactory: func() ExecutionContext { return NewMemoryExecutionContext() },
	}
}

func (w *WorkflowSpider) AddConnector(sink connector.Connector) *WorkflowSpider {
	w.connectors = append(w.connectors, sink)
	return w
}

func (w *WorkflowSpider) SetExecutionContextFactory(factory func() ExecutionContext) *WorkflowSpider {
	if factory != nil {
		w.executionContextFactory = factory
	}
	return w
}

func (w *WorkflowSpider) Execute(job FlowJob) (FlowResult, error) {
	if job.ID == "" {
		job.ID = job.Name
	}
	runID := fmt.Sprintf("%s-%d", job.ID, time.Now().UnixNano())
	extracted := map[string]any{}
	artifacts := make([]string, 0)

	if w.eventBus != nil {
		_ = w.eventBus.Publish(events.New("workflow.job.started", map[string]any{
			"job_id":     job.ID,
			"run_id":     runID,
			"step_count": len(job.Steps),
		}))
	}

	ctx := w.executionContextFactory()
	defer ctx.Close()

	for _, step := range job.Steps {
		if step.Metadata == nil {
			step.Metadata = map[string]any{}
		}
		stepID := step.ID
		if stepID == "" {
			stepID = string(step.Type)
		}
		if w.eventBus != nil {
			_ = w.eventBus.Publish(events.New("workflow.step.started", map[string]any{
				"job_id":  job.ID,
				"run_id":  runID,
				"step_id": stepID,
				"type":    step.Type,
			}))
		}
		if err := executeStep(ctx, step, extracted, &artifacts); err != nil {
			if w.eventBus != nil {
				_ = w.eventBus.Publish(events.New("workflow.step.failed", map[string]any{
					"job_id":  job.ID,
					"run_id":  runID,
					"step_id": stepID,
					"type":    step.Type,
					"error":   err.Error(),
				}))
			}
			return FlowResult{}, err
		}
		if w.eventBus != nil {
			_ = w.eventBus.Publish(events.New("workflow.step.succeeded", map[string]any{
				"job_id":  job.ID,
				"run_id":  runID,
				"step_id": stepID,
				"type":    step.Type,
			}))
		}
	}

	result := FlowResult{
		JobID:     job.ID,
		RunID:     runID,
		Extracted: extracted,
		Artifacts: artifacts,
	}
	envelope := connector.OutputEnvelope{
		JobID:     result.JobID,
		RunID:     result.RunID,
		Extracted: result.Extracted,
		Artifacts: result.Artifacts,
	}
	for _, sink := range w.connectors {
		if err := sink.Write(envelope); err != nil {
			return FlowResult{}, err
		}
	}
	if w.eventBus != nil {
		_ = w.eventBus.Publish(events.New("workflow.job.completed", map[string]any{
			"job_id":    job.ID,
			"run_id":    runID,
			"artifacts": len(artifacts),
			"fields":    keys(extracted),
		}))
	}
	return result, nil
}

func executeStep(ctx ExecutionContext, step FlowStep, extracted map[string]any, artifacts *[]string) error {
	switch step.Type {
	case StepGoto:
		url := metadataString(step.Metadata, "url", step.Selector)
		if url != "" {
			ctx.GotoURL(url)
		}
	case StepWait:
		ctx.WaitFor(metadataInt64(step.Metadata, "timeout_ms", 0))
	case StepClick:
		if step.Selector != "" {
			ctx.Click(step.Selector)
		}
	case StepType:
		ctx.Type(step.Selector, step.Value)
	case StepSelect:
		ctx.Select(step.Selector, step.Value, step.Metadata)
	case StepHover:
		ctx.Hover(step.Selector)
	case StepScroll:
		ctx.Scroll(step.Selector, step.Metadata)
	case StepEval:
		field := metadataString(step.Metadata, "field", metadataString(step.Metadata, "save_as", "eval"))
		extracted[field] = ctx.Evaluate(step.Value)
	case StepListenNetwork:
		field := metadataString(step.Metadata, "field", metadataString(step.Metadata, "save_as", "network_requests"))
		extracted[field] = ctx.ListenNetwork(step.Metadata)
	case StepExtract:
		field := metadataString(step.Metadata, "field", step.Selector)
		if field == "" {
			field = "value"
		}
		if value, ok := step.Metadata["value"]; ok {
			extracted[field] = value
			return nil
		}
		switch field {
		case "title":
			extracted[field] = ctx.Title()
		case "url":
			extracted[field] = ctx.CurrentURL()
		case "html", "dom":
			extracted[field] = ctx.CaptureHTML()
		default:
			extracted[field] = step.Value
		}
	case StepScreenshot:
		artifact := metadataString(step.Metadata, "artifact", step.Value)
		if artifact == "" {
			artifact = fmt.Sprintf("%s.png", step.ID)
		}
		ctx.CaptureScreenshot(artifact)
		*artifacts = append(*artifacts, artifact)
	case StepDownload:
		artifact := metadataString(step.Metadata, "artifact", step.Value)
		if artifact == "" {
			artifact = fmt.Sprintf("%s.bin", step.ID)
		}
		if err := writeArtifact(artifact, []byte("workflow-artifact")); err != nil {
			return err
		}
		*artifacts = append(*artifacts, artifact)
	default:
		return fmt.Errorf("unsupported workflow step: %s", step.Type)
	}
	return nil
}

func metadataString(metadata map[string]any, key, fallback string) string {
	if metadata == nil {
		return fallback
	}
	if value, ok := metadata[key]; ok {
		return fmt.Sprint(value)
	}
	return fallback
}

func metadataInt64(metadata map[string]any, key string, fallback int64) int64 {
	if metadata == nil {
		return fallback
	}
	switch value := metadata[key].(type) {
	case int:
		return int64(value)
	case int64:
		return value
	case float64:
		return int64(value)
	default:
		return fallback
	}
}

func writeArtifact(path string, data []byte) error {
	if path == "" {
		return nil
	}
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	return os.WriteFile(path, data, 0o644)
}

func keys(values map[string]any) []string {
	result := make([]string, 0, len(values))
	for key := range values {
		result = append(result, key)
	}
	return result
}
