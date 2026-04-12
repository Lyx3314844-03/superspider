package distributed

import (
	"time"

	"gospider/core"
)

type LeaseTransitionInput struct {
	Job         core.JobSpec
	WorkerID    string
	LeaseID     string
	Attempt     int
	HeartbeatAt time.Time
	ExpiresAt   time.Time
	Reason      string
	MaxRetries  int
	Expired     bool
}

type LeaseTransitionResult struct {
	Record     JobRecord
	DeadLetter *DeadLetterRecord
	Requeue    bool
}

func EvaluateLeaseTransition(input LeaseTransitionInput) LeaseTransitionResult {
	maxRetries := input.MaxRetries
	if maxRetries < 0 {
		maxRetries = 0
	}
	record := JobRecord{
		Job:            input.Job,
		LeaseID:        input.LeaseID,
		Attempts:       input.Attempt,
		LastError:      input.Reason,
		LastWorkerID:   input.WorkerID,
		LastHeartbeat:  input.HeartbeatAt,
		LeaseExpiresAt: input.ExpiresAt,
		UpdatedAt:      time.Now(),
	}
	maxAttempts := maxRetries + 1
	if input.Attempt >= maxAttempts {
		record.State = core.StateFailed
		return LeaseTransitionResult{
			Record: record,
			DeadLetter: &DeadLetterRecord{
				Job:        input.Job,
				WorkerID:   input.WorkerID,
				LeaseID:    input.LeaseID,
				Attempts:   input.Attempt,
				Reason:     input.Reason,
				DeadAt:     record.UpdatedAt,
				FinalState: core.StateFailed,
			},
			Requeue: false,
		}
	}

	if input.Expired {
		record.State = core.StateExpired
	} else {
		record.State = core.StateRetryScheduled
	}
	return LeaseTransitionResult{
		Record:  record,
		Requeue: true,
	}
}
