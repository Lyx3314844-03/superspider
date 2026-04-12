package distributed

import (
	"testing"

	"gospider/core"
)

func TestTaskToJobSpecCompilesMediaTask(t *testing.T) {
	task := &CrawlTask{
		ID:       "task-1",
		URL:      "https://cdn.example.com/video.mp4",
		Type:     "video",
		Priority: 10,
	}

	job, err := taskToJobSpec(task, "downloads")
	if err != nil {
		t.Fatalf("unexpected compile error: %v", err)
	}
	if job.Runtime != core.RuntimeMedia {
		t.Fatalf("expected media runtime, got %s", job.Runtime)
	}
	if job.Metadata["task_id"] != "task-1" {
		t.Fatalf("expected task metadata to be propagated")
	}
}

func TestTaskToJobSpecPreservesNormalizedJob(t *testing.T) {
	task := &CrawlTask{
		ID: "task-2",
		Job: &core.JobSpec{
			Name:    "embedded-job",
			Runtime: core.RuntimeAI,
			Target:  core.TargetSpec{URL: "https://example.com"},
			Output:  core.OutputSpec{Format: "json"},
			Metadata: map[string]interface{}{
				"mock_extract": map[string]interface{}{"title": "x"},
			},
		},
	}

	job, err := taskToJobSpec(task, "downloads")
	if err != nil {
		t.Fatalf("unexpected compile error: %v", err)
	}
	if job.Runtime != core.RuntimeAI {
		t.Fatalf("expected ai runtime, got %s", job.Runtime)
	}
	if job.Metadata["task_id"] != "task-2" {
		t.Fatalf("expected embedded job metadata to include task id")
	}
}

func TestMergeResultIntoTaskPersistsNormalizedFields(t *testing.T) {
	task := &CrawlTask{
		ID:   "task-3",
		Data: map[string]interface{}{},
	}

	result := core.NewJobResult(core.JobSpec{
		Name:    "task-3",
		Runtime: core.RuntimeMedia,
		Target:  core.TargetSpec{URL: "https://cdn.example.com/video.mp4"},
	}, core.StateSucceeded)
	result.StatusCode = 200
	result.AddMediaArtifact(core.MediaArtifact{
		Type: "video",
		URL:  "https://cdn.example.com/video.mp4",
		Path: "downloads/task-3.mp4",
	})
	result.SetExtractField("title", "demo")
	result.Finalize()

	mergeResultIntoTask(task, result)

	if task.Data["runtime"] != string(core.RuntimeMedia) {
		t.Fatalf("expected runtime to be mirrored into task data")
	}
	if task.Data["output_file"] != "downloads/task-3.mp4" {
		t.Fatalf("expected output file to be populated")
	}
	if _, ok := task.Data["extract"]; !ok {
		t.Fatalf("expected extract payload to be persisted")
	}
	if _, ok := task.Data["artifacts"]; !ok {
		t.Fatalf("expected artifacts list to be mirrored into task data")
	}
}

func TestMergeResultIntoTaskPersistsGraphArtifactRefs(t *testing.T) {
	task := &CrawlTask{
		ID:   "task-graph",
		Data: map[string]interface{}{},
	}

	result := core.NewJobResult(core.JobSpec{
		Name:    "task-graph",
		Runtime: core.RuntimeHTTP,
		Target:  core.TargetSpec{URL: "https://example.com"},
	}, core.StateSucceeded)
	result.SetArtifact("graph", core.ArtifactRef{
		Kind: "graph",
		Path: "artifacts/runtime/graphs/task-graph.json",
		Metadata: map[string]interface{}{
			"root_id": "document",
		},
	})
	result.Finalize()

	mergeResultIntoTask(task, result)

	artifactRefs, ok := task.Data["artifact_refs"]
	if !ok {
		t.Fatalf("expected artifact refs to be mirrored")
	}
	artifacts, ok := task.Data["artifacts"]
	if !ok {
		t.Fatalf("expected artifacts list to be mirrored")
	}
	if artifactRefs == nil || artifacts == nil {
		t.Fatalf("expected non-empty graph artifact mirrors")
	}
}
