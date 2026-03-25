package core

import "context"

// Executor is the normalized execution seam used to avoid hard package coupling
// between core scheduling code and concrete runtime implementations.
type Executor interface {
	Execute(ctx context.Context, job JobSpec) (*JobResult, error)
}
