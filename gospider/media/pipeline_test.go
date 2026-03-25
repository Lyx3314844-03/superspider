package media

import (
	"testing"

	"gospider/core"
)

func TestMediaPipelineAttachesArtifactsToJobResult(t *testing.T) {
	pipeline := NewPipeline("downloads")
	result := &core.JobResult{
		JobName: "media-job",
		Runtime: core.RuntimeBrowser,
		State:   core.StateSucceeded,
		URL:     "https://example.com",
		Text:    `<html><img src="https://cdn.example.com/cover.jpg"><a href="https://cdn.example.com/playlist.m3u8">stream</a></html>`,
	}

	if err := pipeline.Apply(result, core.MediaSpec{Enabled: true}); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(result.MediaRecord) == 0 {
		t.Fatal("expected discovered media artifacts")
	}
}
