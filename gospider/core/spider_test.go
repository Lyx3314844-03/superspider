package core

import (
	"context"
	"testing"

	"gospider/queue"
)

type stubExecutor struct {
	job   JobSpec
	calls int
}

func (s *stubExecutor) Execute(ctx context.Context, job JobSpec) (*JobResult, error) {
	s.calls++
	s.job = job
	return &JobResult{
		JobName:    job.Name,
		Runtime:    job.Runtime,
		State:      StateSucceeded,
		URL:        job.Target.URL,
		StatusCode: 200,
		Metadata:   map[string]interface{}{},
	}, nil
}

func TestSpiderExecuteRequestUsesInjectedExecutor(t *testing.T) {
	spider := NewSpider(nil)
	executor := &stubExecutor{}
	spider.SetHTTPExecutor(executor)

	req := &queue.Request{
		URL:      "https://example.com",
		Method:   "GET",
		Headers:  map[string]string{},
		Priority: 4,
		Meta:     map[string]interface{}{},
	}

	spider.executeRequest(0, req)

	if executor.calls != 1 {
		t.Fatalf("expected executor to be called once, got %d", executor.calls)
	}
	if executor.job.Target.URL != req.URL {
		t.Fatalf("expected job url %s, got %s", req.URL, executor.job.Target.URL)
	}
	if executor.job.Priority != req.Priority {
		t.Fatalf("expected priority %d, got %d", req.Priority, executor.job.Priority)
	}
	if executor.job.Runtime != RuntimeHTTP {
		t.Fatalf("expected runtime %s, got %s", RuntimeHTTP, executor.job.Runtime)
	}
}

func TestSpiderRunUsesFrontierBackedScheduling(t *testing.T) {
	config := DefaultSpiderConfig()
	config.Name = "frontier-runner"
	config.Concurrency = 1
	config.MaxRequests = 1
	config.RespectRobots = false

	spider := NewSpider(config)
	executor := &stubExecutor{}
	spider.SetHTTPExecutor(executor)

	req := &queue.Request{
		URL:      "https://example.com",
		Method:   "GET",
		Headers:  map[string]string{},
		Priority: 3,
		Meta:     map[string]interface{}{},
	}
	if err := spider.AddRequest(req); err != nil {
		t.Fatalf("expected request to be accepted: %v", err)
	}

	if err := spider.Run(); err != nil {
		t.Fatalf("run should succeed: %v", err)
	}

	if executor.calls != 1 {
		t.Fatalf("expected executor to be called once, got %d", executor.calls)
	}
	stats := spider.GetStats()
	if stats["handled"] != 1 {
		t.Fatalf("expected handled count to be 1, got %#v", stats["handled"])
	}
	frontier := stats["frontier"].(map[string]interface{})
	if frontier["pending"] != 0 {
		t.Fatalf("expected pending frontier items to be 0, got %#v", frontier["pending"])
	}
}
