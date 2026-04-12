package distributed

import "testing"

func TestRunSyntheticSoakProducesStableReport(t *testing.T) {
	report := RunSyntheticSoak(SoakOptions{
		Jobs:            15,
		Workers:         4,
		MaxRetries:      1,
		ExpireEvery:     4,
		RetryEvery:      3,
		DeadLetterEvery: 5,
	})

	if report.Summary != "passed" {
		t.Fatalf("expected passed soak summary, got %s", report.Summary)
	}
	if !report.Stable {
		t.Fatal("expected stable soak report")
	}
	if report.Completed == 0 {
		t.Fatal("expected completed jobs in soak report")
	}
	if report.Retried == 0 {
		t.Fatal("expected retried jobs in soak report")
	}
	if report.Expired == 0 {
		t.Fatal("expected expired jobs in soak report")
	}
	if report.DeadLetters == 0 {
		t.Fatal("expected dead-letter jobs in soak report")
	}
	if report.FinalQueueDepth != 0 || report.FinalLeases != 0 {
		t.Fatalf("expected drained soak queues, got queue=%d leases=%d", report.FinalQueueDepth, report.FinalLeases)
	}
}
