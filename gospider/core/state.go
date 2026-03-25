package core

import "fmt"

// TaskState is the normalized lifecycle state for a job.
type TaskState string

const (
	StateCreated        TaskState = "created"
	StateQueued         TaskState = "queued"
	StateLeased         TaskState = "leased"
	StateRunning        TaskState = "running"
	StateWaiting        TaskState = "waiting"
	StateRetryScheduled TaskState = "retry_scheduled"
	StateSucceeded      TaskState = "succeeded"
	StatePartiallyDone  TaskState = "partially_succeeded"
	StateFailed         TaskState = "failed"
	StateCancelled      TaskState = "cancelled"
	StateExpired        TaskState = "expired"
)

var validTransitions = map[TaskState]map[TaskState]struct{}{
	StateCreated: {
		StateQueued: {},
	},
	StateQueued: {
		StateLeased:    {},
		StateCancelled: {},
	},
	StateLeased: {
		StateRunning:        {},
		StateRetryScheduled: {},
		StateExpired:        {},
	},
	StateRunning: {
		StateWaiting:        {},
		StateRetryScheduled: {},
		StateSucceeded:      {},
		StatePartiallyDone:  {},
		StateFailed:         {},
		StateCancelled:      {},
	},
	StateWaiting: {
		StateRunning:        {},
		StateRetryScheduled: {},
		StateFailed:         {},
	},
	StateRetryScheduled: {
		StateQueued: {},
	},
	StateExpired: {
		StateQueued: {},
	},
}

// CanTransitionTo validates whether a state change is allowed.
func (s TaskState) CanTransitionTo(next TaskState) error {
	if s == next {
		return nil
	}
	if nextStates, ok := validTransitions[s]; ok {
		if _, ok := nextStates[next]; ok {
			return nil
		}
	}
	return fmt.Errorf("invalid transition from %s to %s", s, next)
}
