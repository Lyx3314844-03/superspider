package core

import (
	"path/filepath"
	"testing"
	"time"
)

func TestFingerprintForRequestIsStable(t *testing.T) {
	first := &Request{
		URL:      "https://example.com",
		Method:   "GET",
		Headers:  map[string]string{"Accept": "text/html"},
		Meta:     map[string]interface{}{"page": 1},
		Priority: 1,
	}
	second := &Request{
		URL:      "https://example.com",
		Method:   "GET",
		Headers:  map[string]string{"Accept": "text/html"},
		Meta:     map[string]interface{}{"page": 1},
		Priority: 1,
	}

	if FingerprintForRequest(first) != FingerprintForRequest(second) {
		t.Fatal("expected stable request fingerprint")
	}
}

func TestAutoscaledFrontierRespectsBackpressureAndPersists(t *testing.T) {
	frontier, err := NewAutoscaledFrontier(FrontierConfig{
		CheckpointDir:        filepath.Join(t.TempDir(), "checkpoints"),
		CheckpointID:         "demo-frontier",
		Autoscale:            true,
		MinConcurrency:       1,
		MaxConcurrency:       4,
		TargetLatencyMS:      1200,
		LeaseTTLSeconds:      30,
		MaxInflightPerDomain: 1,
	})
	if err != nil {
		t.Fatalf("new frontier: %v", err)
	}

	first := &Request{URL: "https://example.com/a", Method: "GET", Headers: map[string]string{}, Meta: map[string]interface{}{}, Priority: 10}
	second := &Request{URL: "https://example.com/b", Method: "GET", Headers: map[string]string{}, Meta: map[string]interface{}{}, Priority: 5}
	other := &Request{URL: "https://other.example.com/c", Method: "GET", Headers: map[string]string{}, Meta: map[string]interface{}{}, Priority: 1}

	if !frontier.Push(first) || !frontier.Push(second) || !frontier.Push(other) {
		t.Fatal("expected requests to enqueue")
	}

	leasedFirst := frontier.Lease()
	leasedOther := frontier.Lease()
	if leasedFirst == nil || leasedOther == nil {
		t.Fatal("expected two leases")
	}
	if leasedFirst.URL != "https://example.com/a" {
		t.Fatalf("expected first lease from primary domain, got %s", leasedFirst.URL)
	}
	if leasedOther.URL != "https://other.example.com/c" {
		t.Fatalf("expected other-domain request to bypass backpressure, got %s", leasedOther.URL)
	}

	if err := frontier.Persist(); err != nil {
		t.Fatalf("persist frontier: %v", err)
	}

	restored, err := NewAutoscaledFrontier(FrontierConfig{
		CheckpointDir:        frontier.config.CheckpointDir,
		CheckpointID:         frontier.config.CheckpointID,
		Autoscale:            true,
		MinConcurrency:       1,
		MaxConcurrency:       4,
		TargetLatencyMS:      1200,
		LeaseTTLSeconds:      30,
		MaxInflightPerDomain: 1,
	})
	if err != nil {
		t.Fatalf("new restored frontier: %v", err)
	}
	if !restored.Load() {
		t.Fatal("expected checkpoint to load")
	}
	snapshot := restored.Snapshot()
	pending := snapshot["pending"].([]frontierRequest)
	if len(pending) != 1 || pending[0].URL != "https://example.com/b" {
		t.Fatalf("unexpected restored pending queue: %#v", pending)
	}
}

func TestAutoscaledFrontierScalesDownOnFailures(t *testing.T) {
	frontier, err := NewAutoscaledFrontier(DefaultFrontierConfig())
	if err != nil {
		t.Fatalf("new frontier: %v", err)
	}
	request := &Request{URL: "https://example.com/a", Method: "GET", Headers: map[string]string{}, Meta: map[string]interface{}{}}
	if !frontier.Push(request) {
		t.Fatal("expected request to enqueue")
	}
	leased := frontier.Lease()
	if leased == nil {
		t.Fatal("expected lease")
	}
	frontier.Ack(leased, false, 5000, errRateLimited, 429, 3)
	if frontier.RecommendedConcurrency() != 1 {
		t.Fatalf("expected frontier to scale down, got %d", frontier.RecommendedConcurrency())
	}
}

func TestAutoscaledFrontierSyntheticSoakAndRecovery(t *testing.T) {
	frontier, err := NewAutoscaledFrontier(FrontierConfig{
		CheckpointDir:        filepath.Join(t.TempDir(), "checkpoints"),
		CheckpointID:         "soak-frontier",
		Autoscale:            true,
		MinConcurrency:       1,
		MaxConcurrency:       8,
		TargetLatencyMS:      1200,
		LeaseTTLSeconds:      30,
		MaxInflightPerDomain: 2,
	})
	if err != nil {
		t.Fatalf("new frontier: %v", err)
	}

	for idx := 0; idx < 24; idx++ {
		request := &Request{
			URL:      "https://example.com/item/" + string(rune('a'+idx)),
			Method:   "GET",
			Headers:  map[string]string{},
			Meta:     map[string]interface{}{"mode": map[bool]string{true: "dead-letter", false: "success"}[idx%7 == 0]},
			Priority: idx % 3,
		}
		if !frontier.Push(request) {
			t.Fatalf("expected request %d to enqueue", idx)
		}
	}

	processed := 0
	failed := 0
	for idx := 0; idx < 80; idx++ {
		leased := frontier.Lease()
		if leased == nil {
			break
		}
		if leased.Meta["mode"] == "dead-letter" {
			failed++
			frontier.Ack(leased, false, 1800, errRateLimited, 408, 1)
			continue
		}
		processed++
		frontier.Ack(leased, true, 40, nil, 200, 1)
	}

	if err := frontier.Persist(); err != nil {
		t.Fatalf("persist frontier: %v", err)
	}
	restored, err := NewAutoscaledFrontier(FrontierConfig{
		CheckpointDir:        frontier.config.CheckpointDir,
		CheckpointID:         frontier.config.CheckpointID,
		Autoscale:            true,
		MinConcurrency:       1,
		MaxConcurrency:       8,
		TargetLatencyMS:      1200,
		LeaseTTLSeconds:      30,
		MaxInflightPerDomain: 2,
	})
	if err != nil {
		t.Fatalf("new restored frontier: %v", err)
	}
	if !restored.Load() {
		t.Fatal("expected frontier checkpoint to load")
	}
	if processed == 0 || failed == 0 {
		t.Fatalf("expected both processed and failed requests, got processed=%d failed=%d", processed, failed)
	}
	if frontier.DeadLetterCount() == 0 {
		t.Fatal("expected at least one dead-lettered request")
	}
	if restored.RecommendedConcurrency() < 1 || restored.RecommendedConcurrency() > 8 {
		t.Fatalf("unexpected recommended concurrency: %d", restored.RecommendedConcurrency())
	}
}

func TestIncrementalCrawlerPersistsDeltaState(t *testing.T) {
	crawler := NewIncrementalCrawler(true, time.Hour)
	path := filepath.Join(t.TempDir(), "incremental.json")

	if changed := crawler.UpdateCache("https://example.com/a", "etag-1", "Sat, 11 Apr 2026 00:00:00 GMT", []byte("alpha"), 200); !changed {
		t.Fatal("expected first update to mark content as changed")
	}
	token := crawler.DeltaToken("https://example.com/a")
	if token == "" {
		t.Fatal("expected delta token")
	}
	if err := crawler.Save(path); err != nil {
		t.Fatalf("save incremental state: %v", err)
	}

	restored := NewIncrementalCrawler(true, time.Hour)
	if err := restored.Load(path); err != nil {
		t.Fatalf("load incremental state: %v", err)
	}
	if restored.DeltaToken("https://example.com/a") != token {
		t.Fatal("expected restored delta token to match")
	}
	headers := restored.GetConditionalHeaders("https://example.com/a")
	if headers["If-None-Match"] != "etag-1" {
		t.Fatalf("unexpected conditional headers: %#v", headers)
	}
}

func TestObservabilityAndArtifactsCaptureEvidence(t *testing.T) {
	store := NewFileArtifactStore(t.TempDir())
	record, err := store.PutBytes("frontier", "json", []byte("{}"), nil)
	if err != nil {
		t.Fatalf("put artifact: %v", err)
	}
	collector := NewObservabilityCollector()
	traceID := collector.StartTrace("crawl")
	classification := collector.RecordResult(
		&Request{URL: "https://example.com", Method: "GET"},
		42,
		403,
		errorsNew("captcha challenge"),
		traceID,
	)
	collector.EndTrace(traceID, map[string]interface{}{"artifact": record.Path})

	if classification != "blocked" {
		t.Fatalf("unexpected classification: %s", classification)
	}
	summary := collector.Summary()
	if summary["traces"].(int) != 1 {
		t.Fatalf("unexpected summary: %#v", summary)
	}
}

var errRateLimited = errorsNew("rate limit")

func errorsNew(message string) error {
	return &runtimeContractError{message: message}
}

type runtimeContractError struct {
	message string
}

func (e *runtimeContractError) Error() string { return e.message }
