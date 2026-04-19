package monitor

import (
	"strings"
	"testing"
	"time"
)

func TestPrometheusTextIncludesQueueAndHealthMetrics(t *testing.T) {
	mon := &Monitor{
		stats: &SystemStats{
			Timestamp:            time.Now(),
			Queues:               map[string]int64{"queued": 5, "running": 2, "dead_letter": 1},
			WorkersTotal:         4,
			WorkersActive:        3,
			TasksTotal:           20,
			TasksCompleted:       12,
			TasksFailed:          3,
			DeadLetters:          1,
			QueueBacklog:         7,
			Throughput:           1.5,
			QPS:                  1.5,
			LatencyP95MS:         220,
			LatencyP99MS:         380,
			SuccessRate:          80,
			FailureRate:          20,
			WorkerUtilizationPct: 75,
			QueuePressure:        2.3333,
		},
		startTime: time.Now().Add(-time.Minute),
	}

	text := mon.PrometheusText("gospider")
	if !strings.Contains(text, "gospider_dead_letters 1") {
		t.Fatalf("expected dead letter metric, got %s", text)
	}
	if !strings.Contains(text, `gospider_queue_depth{state="queued"} 5`) {
		t.Fatalf("expected queued depth metric, got %s", text)
	}
	if !strings.Contains(text, "gospider_worker_utilization_pct 75") {
		t.Fatalf("expected worker utilization metric, got %s", text)
	}
	if !strings.Contains(text, "gospider_latency_p95_ms 220") || !strings.Contains(text, "gospider_latency_p99_ms 380") {
		t.Fatalf("expected latency percentile metrics, got %s", text)
	}
}

func TestOTELPayloadIncludesQueuePressureMetric(t *testing.T) {
	mon := &Monitor{
		stats: &SystemStats{
			Timestamp:     time.Now(),
			Queues:        map[string]int64{"queued": 9},
			QueuePressure: 4.5,
			TasksTotal:    9,
			QPS:           2.5,
			LatencyP95MS:  210,
			LatencyP99MS:  350,
		},
		startTime: time.Now().Add(-time.Minute),
	}

	payload := mon.OTELPayload("monitor-test")
	if payload["scope"] != "gospider/monitor" {
		t.Fatalf("unexpected otel scope: %#v", payload)
	}
	metrics, ok := payload["metrics"].([]map[string]interface{})
	if !ok || len(metrics) == 0 {
		t.Fatalf("expected metrics in otel payload: %#v", payload)
	}
	var foundQueuePressure bool
	var foundLatencyP95 bool
	for _, metric := range metrics {
		if metric["name"] == "queue_pressure" && metric["value"] == 4.5 {
			foundQueuePressure = true
		}
		if metric["name"] == "latency_p95_ms" && metric["value"] == 210.0 {
			foundLatencyP95 = true
		}
	}
	if !foundQueuePressure {
		t.Fatalf("expected queue_pressure metric in otel payload: %#v", payload)
	}
	if !foundLatencyP95 {
		t.Fatalf("expected latency_p95_ms metric in otel payload: %#v", payload)
	}
}
