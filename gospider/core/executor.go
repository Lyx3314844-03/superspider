package core

import (
	"context"
	"fmt"
	"sync"
)

// Executor is the normalized execution seam used to avoid hard package coupling
// between core scheduling code and concrete runtime implementations.
type Executor interface {
	Execute(ctx context.Context, job JobSpec) (*JobResult, error)
}

// RoutingExecutor dispatches jobs to per-runtime executors.
type RoutingExecutor struct {
	mu       sync.RWMutex
	routes   map[Runtime]Executor
	fallback Executor
}

// NewRoutingExecutor creates an empty runtime router.
func NewRoutingExecutor() *RoutingExecutor {
	return &RoutingExecutor{
		routes: make(map[Runtime]Executor),
	}
}

// Register associates a runtime with a concrete executor.
func (r *RoutingExecutor) Register(runtime Runtime, executor Executor) *RoutingExecutor {
	if r == nil || executor == nil {
		return r
	}
	r.mu.Lock()
	defer r.mu.Unlock()
	r.routes[runtime] = executor
	return r
}

// SetFallback configures an executor used when a runtime route is missing.
func (r *RoutingExecutor) SetFallback(executor Executor) *RoutingExecutor {
	if r == nil {
		return r
	}
	r.mu.Lock()
	defer r.mu.Unlock()
	r.fallback = executor
	return r
}

// Execute dispatches the job to a registered runtime executor.
func (r *RoutingExecutor) Execute(ctx context.Context, job JobSpec) (*JobResult, error) {
	if err := job.Validate(); err != nil {
		return nil, err
	}

	r.mu.RLock()
	executor, ok := r.routes[job.Runtime]
	fallback := r.fallback
	r.mu.RUnlock()

	if ok && executor != nil {
		return executor.Execute(ctx, job)
	}
	if fallback != nil {
		return fallback.Execute(ctx, job)
	}
	return nil, fmt.Errorf("no executor registered for runtime %q", job.Runtime)
}
