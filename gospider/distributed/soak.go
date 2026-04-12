package distributed

import (
	"fmt"
	"time"

	"gospider/core"
)

// SoakOptions controls the synthetic distributed soak harness.
type SoakOptions struct {
	Jobs            int
	Workers         int
	MaxRetries      int
	LeaseTTL        time.Duration
	ExpireEvery     int
	RetryEvery      int
	DeadLetterEvery int
}

// SoakReport summarizes a synthetic distributed soak run.
type SoakReport struct {
	Summary          string        `json:"summary"`
	JobsSubmitted    int           `json:"jobs_submitted"`
	Iterations       int           `json:"iterations"`
	Completed        int           `json:"completed"`
	Retried          int           `json:"retried"`
	Expired          int           `json:"expired"`
	DeadLetters      int           `json:"dead_letters"`
	PeakQueueDepth   int           `json:"peak_queue_depth"`
	PeakActiveLeases int           `json:"peak_active_leases"`
	FinalQueueDepth  int           `json:"final_queue_depth"`
	FinalLeases      int           `json:"final_leases"`
	MaxRetries       int           `json:"max_retries"`
	LeaseTTL         time.Duration `json:"lease_ttl"`
	Stable           bool          `json:"stable"`
}

// RunSyntheticSoak executes a deterministic in-memory soak simulation for lease, retry, expiry, and dead-letter paths.
func RunSyntheticSoak(opts SoakOptions) SoakReport {
	if opts.Jobs <= 0 {
		opts.Jobs = 12
	}
	if opts.Workers <= 0 {
		opts.Workers = 3
	}
	if opts.MaxRetries < 0 {
		opts.MaxRetries = 0
	}
	if opts.LeaseTTL <= 0 {
		opts.LeaseTTL = 15 * time.Millisecond
	}
	if opts.ExpireEvery <= 0 {
		opts.ExpireEvery = 4
	}
	if opts.RetryEvery <= 0 {
		opts.RetryEvery = 3
	}
	if opts.DeadLetterEvery <= 0 {
		opts.DeadLetterEvery = 5
	}

	service := NewDistributedServiceWithOptions(ServiceOptions{
		DefaultLeaseTTL: opts.LeaseTTL,
		MaxRetries:      opts.MaxRetries,
	})

	for idx := 0; idx < opts.Jobs; idx++ {
		job := core.JobSpec{
			Name:     fmt.Sprintf("soak-job-%02d", idx),
			Runtime:  core.RuntimeHTTP,
			Priority: idx % 3,
			Target:   core.TargetSpec{URL: fmt.Sprintf("https://example.com/soak/%02d", idx)},
			Output:   core.OutputSpec{Format: "json"},
			Metadata: map[string]interface{}{},
		}
		switch {
		case idx%opts.DeadLetterEvery == 0:
			job.Metadata["soak_mode"] = "dead-letter"
		case idx%opts.ExpireEvery == 0:
			job.Metadata["soak_mode"] = "expire-once"
		case idx%opts.RetryEvery == 0:
			job.Metadata["soak_mode"] = "retry-once"
		default:
			job.Metadata["soak_mode"] = "success"
		}
		_ = service.Submit(job)
	}

	report := SoakReport{
		JobsSubmitted: opts.Jobs,
		MaxRetries:    opts.MaxRetries,
		LeaseTTL:      opts.LeaseTTL,
	}

	limit := opts.Jobs * (opts.MaxRetries + 4)
	for iteration := 0; iteration < limit; iteration++ {
		if service.QueueLen() == 0 && service.ActiveLeases() == 0 {
			break
		}

		lease, err := service.Lease(fmt.Sprintf("worker-%d", iteration%opts.Workers), opts.LeaseTTL)
		if err != nil || lease == nil {
			continue
		}

		report.Iterations++
		if stats := service.Stats(); stats.PeakQueueDepth > report.PeakQueueDepth {
			report.PeakQueueDepth = stats.PeakQueueDepth
		}
		if active := service.ActiveLeases(); active > report.PeakActiveLeases {
			report.PeakActiveLeases = active
		}

		mode, _ := lease.Job.Metadata["soak_mode"].(string)
		switch mode {
		case "dead-letter":
			report.Expired++
			_ = service.ReapExpiredLeases(lease.ExpiresAt.Add(time.Millisecond))
		case "expire-once":
			if lease.Attempt == 1 {
				report.Expired++
				_ = service.ReapExpiredLeases(lease.ExpiresAt.Add(time.Millisecond))
				continue
			}
			_ = service.Heartbeat(lease.LeaseID, opts.LeaseTTL)
			_ = service.Ack(lease.LeaseID)
			report.Completed++
		case "retry-once":
			if lease.Attempt == 1 {
				report.Retried++
				_ = service.RetryWithError(lease.LeaseID, "synthetic retry")
				continue
			}
			_ = service.Heartbeat(lease.LeaseID, opts.LeaseTTL)
			_ = service.Ack(lease.LeaseID)
			report.Completed++
		default:
			_ = service.Heartbeat(lease.LeaseID, opts.LeaseTTL)
			_ = service.Ack(lease.LeaseID)
			report.Completed++
		}
	}

	stats := service.Stats()
	report.FinalQueueDepth = stats.Queued
	report.FinalLeases = stats.ActiveLeases
	report.DeadLetters = len(service.DeadLetters())
	report.PeakQueueDepth = max(report.PeakQueueDepth, stats.PeakQueueDepth)
	report.PeakActiveLeases = max(report.PeakActiveLeases, stats.PeakActiveLeases)
	report.Stable = report.FinalQueueDepth == 0 &&
		report.FinalLeases == 0 &&
		report.Completed+report.DeadLetters == report.JobsSubmitted
	if report.Stable {
		report.Summary = "passed"
	} else {
		report.Summary = "failed"
	}
	return report
}
