package core

import (
	"testing"
	"time"

	"gospider/queue"
)

func TestRateLimiterNew(t *testing.T) {
	limiter := NewRateLimiter(100.0, 50.0)

	if limiter.tokens != 100.0 {
		t.Fatalf("expected 100 initial tokens, got %f", limiter.tokens)
	}
	if limiter.maxTokens != 100.0 {
		t.Fatalf("expected max tokens to be 100, got %f", limiter.maxTokens)
	}
	if limiter.refillRate != 50.0 {
		t.Fatalf("expected refill rate to be 50, got %f", limiter.refillRate)
	}
}

func TestRateLimiterWaitAndRefill(t *testing.T) {
	limiter := NewRateLimiter(1.0, 20.0)
	limiter.Wait()

	start := time.Now()
	limiter.Wait()
	elapsed := time.Since(start)

	if elapsed < 30*time.Millisecond {
		t.Fatalf("expected limiter to wait, got %v", elapsed)
	}
}

func TestRateLimiterSetRate(t *testing.T) {
	limiter := NewRateLimiter(10.0, 10.0)
	limiter.SetRate(25.0)

	if limiter.refillRate != 25.0 {
		t.Fatalf("expected refill rate to update, got %f", limiter.refillRate)
	}
}

func TestContentDeduplicatorTracksDuplicates(t *testing.T) {
	deduplicator := NewContentDeduplicator()
	content := []byte("duplicate-content")

	if deduplicator.IsDuplicate(content) {
		t.Fatal("first occurrence should not be duplicate")
	}
	if !deduplicator.IsDuplicate(content) {
		t.Fatal("second occurrence should be duplicate")
	}
	if deduplicator.Count() != 1 {
		t.Fatalf("expected single stored fingerprint, got %d", deduplicator.Count())
	}

	deduplicator.Clear()
	if deduplicator.Count() != 0 {
		t.Fatalf("expected clear to remove all fingerprints, got %d", deduplicator.Count())
	}
}

func TestHashContentIsDeterministic(t *testing.T) {
	first := hashContent([]byte("same"))
	second := hashContent([]byte("same"))
	third := hashContent([]byte("different"))

	if first != second {
		t.Fatal("expected deterministic hash for same content")
	}
	if first == third {
		t.Fatal("expected different content to produce different hash")
	}
}

func TestSpiderCurrentConfigAndStats(t *testing.T) {
	config := DefaultSpiderConfig()
	config.Name = "test-current-spider"
	spider := NewSpider(config)

	if spider == nil {
		t.Fatal("spider should not be nil")
	}
	if spider.config != config {
		t.Fatal("expected spider to use provided config")
	}

	stats := spider.GetStats()
	if stats == nil {
		t.Fatal("stats should not be nil")
	}
	if stats["name"] != "test-current-spider" {
		t.Fatalf("expected spider name in stats, got %#v", stats["name"])
	}
}

func TestSpiderCurrentAddRequest(t *testing.T) {
	spider := NewSpider(DefaultSpiderConfig())
	req := &queue.Request{
		URL: "http://example.com",
	}

	if err := spider.AddRequest(req); err != nil {
		t.Fatalf("expected request to be accepted: %v", err)
	}
}

func BenchmarkRateLimiterWait(b *testing.B) {
	limiter := NewRateLimiter(1000.0, 1000.0)
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		limiter.Wait()
	}
}

func BenchmarkContentDeduplicatorIsDuplicate(b *testing.B) {
	deduplicator := NewContentDeduplicator()
	content := []byte("benchmark-content")
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		deduplicator.IsDuplicate(content)
	}
}
