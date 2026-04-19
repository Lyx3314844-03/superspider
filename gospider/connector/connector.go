package connector

import (
	"encoding/json"
	"os"
	"path/filepath"
	"sync"
)

// OutputEnvelope is the normalized payload emitted by workflow and job surfaces.
type OutputEnvelope struct {
	JobID     string         `json:"job_id"`
	RunID     string         `json:"run_id"`
	Extracted map[string]any `json:"extracted"`
	Artifacts []string       `json:"artifacts"`
}

// Connector persists or forwards normalized output envelopes.
type Connector interface {
	Write(OutputEnvelope) error
}

// InMemoryConnector stores envelopes in-process for tests and lightweight orchestration.
type InMemoryConnector struct {
	mu        sync.Mutex
	envelopes []OutputEnvelope
}

func (c *InMemoryConnector) Write(envelope OutputEnvelope) error {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.envelopes = append(c.envelopes, cloneEnvelope(envelope))
	return nil
}

// List returns a defensive copy of stored envelopes.
func (c *InMemoryConnector) List() []OutputEnvelope {
	c.mu.Lock()
	defer c.mu.Unlock()
	result := make([]OutputEnvelope, 0, len(c.envelopes))
	for _, envelope := range c.envelopes {
		result = append(result, cloneEnvelope(envelope))
	}
	return result
}

// FileConnector appends envelopes to a JSONL file.
type FileConnector struct {
	path string
	mu   sync.Mutex
}

func NewFileConnector(path string) *FileConnector {
	return &FileConnector{path: path}
}

func (c *FileConnector) Write(envelope OutputEnvelope) error {
	c.mu.Lock()
	defer c.mu.Unlock()

	if err := os.MkdirAll(filepath.Dir(c.path), 0o755); err != nil {
		return err
	}
	file, err := os.OpenFile(c.path, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0o644)
	if err != nil {
		return err
	}
	defer file.Close()

	data, err := json.Marshal(cloneEnvelope(envelope))
	if err != nil {
		return err
	}
	if _, err := file.Write(append(data, '\n')); err != nil {
		return err
	}
	return nil
}

func cloneEnvelope(envelope OutputEnvelope) OutputEnvelope {
	extracted := make(map[string]any, len(envelope.Extracted))
	for key, value := range envelope.Extracted {
		extracted[key] = value
	}
	artifacts := append([]string(nil), envelope.Artifacts...)
	return OutputEnvelope{
		JobID:     envelope.JobID,
		RunID:     envelope.RunID,
		Extracted: extracted,
		Artifacts: artifacts,
	}
}
