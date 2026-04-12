package dispatch

import (
	"context"
	"fmt"
	"net/url"
	"strings"
	"time"

	"gospider/core"
)

type policyExecutor struct {
	inner core.Executor
}

func (e *policyExecutor) Execute(ctx context.Context, job core.JobSpec) (*core.JobResult, error) {
	if err := job.Validate(); err != nil {
		return nil, err
	}
	if err := validateJobPolicy(job); err != nil {
		result := core.NewJobResult(job, core.StateFailed)
		result.Error = err.Error()
		result.Metadata["policy_stage"] = "preflight"
		result.FinishedAt = time.Now()
		result.Finalize()
		return result, err
	}

	if delay := rateLimitDelay(job); delay > 0 {
		timer := time.NewTimer(delay)
		defer timer.Stop()
		select {
		case <-ctx.Done():
			result := core.NewJobResult(job, core.StateFailed)
			result.Error = ctx.Err().Error()
			result.Metadata["policy_stage"] = "rate_limit"
			result.FinishedAt = time.Now()
			result.Finalize()
			return result, ctx.Err()
		case <-timer.C:
		}
	}

	startedAt := time.Now()
	result, err := e.inner.Execute(ctx, job)
	if result == nil {
		return nil, err
	}

	if policyErr := enforceResultBudget(job, result, time.Since(startedAt)); policyErr != nil {
		result.State = core.StateFailed
		result.Error = policyErr.Error()
		result.Metadata["policy_stage"] = "postflight"
		result.FinishedAt = time.Now()
		result.Finalize()
		return result, policyErr
	}

	return result, err
}

func validateJobPolicy(job core.JobSpec) error {
	allowedDomains := effectiveAllowedDomains(job)
	if len(allowedDomains) == 0 {
		return nil
	}
	parsed, err := url.Parse(job.Target.URL)
	if err != nil {
		return fmt.Errorf("invalid target.url: %w", err)
	}
	host := strings.TrimSpace(parsed.Hostname())
	if host == "" {
		return fmt.Errorf("target.url is missing host")
	}
	for _, allowed := range allowedDomains {
		normalized := strings.ToLower(strings.TrimSpace(allowed))
		if normalized == "" {
			continue
		}
		hostLower := strings.ToLower(host)
		if hostLower == normalized || strings.HasSuffix(hostLower, "."+normalized) {
			return nil
		}
	}
	return fmt.Errorf("target host %s is outside allowed_domains", host)
}

func effectiveAllowedDomains(job core.JobSpec) []string {
	if len(job.Target.AllowedDomains) > 0 {
		return append([]string(nil), job.Target.AllowedDomains...)
	}
	if !job.Policy.SameDomainOnly {
		return nil
	}
	parsed, err := url.Parse(job.Target.URL)
	if err != nil || parsed.Hostname() == "" {
		return nil
	}
	return []string{parsed.Hostname()}
}

func rateLimitDelay(job core.JobSpec) time.Duration {
	if job.Resources.RateLimitPerSec <= 0 {
		return 0
	}
	return time.Duration(float64(time.Second) / job.Resources.RateLimitPerSec)
}

func enforceResultBudget(job core.JobSpec, result *core.JobResult, elapsed time.Duration) error {
	budget := job.Policy.Budget
	usedWallTime := elapsed.Milliseconds()
	if result != nil && result.Metrics != nil && result.Metrics.LatencyMS > usedWallTime {
		usedWallTime = result.Metrics.LatencyMS
	}
	if budget.WallTimeMS > 0 && usedWallTime > budget.WallTimeMS {
		return fmt.Errorf(
			"job exceeded budget.wall_time_ms: used=%d limit=%d",
			usedWallTime,
			budget.WallTimeMS,
		)
	}
	if budget.BytesIn > 0 {
		bytesIn := resultBytesIn(result)
		if bytesIn > budget.BytesIn {
			return fmt.Errorf("job exceeded budget.bytes_in: used=%d limit=%d", bytesIn, budget.BytesIn)
		}
	}
	return nil
}

func resultBytesIn(result *core.JobResult) int64 {
	if result == nil {
		return 0
	}
	if result.Metrics != nil && result.Metrics.BytesIn > 0 {
		return result.Metrics.BytesIn
	}
	if len(result.Body) > 0 {
		return int64(len(result.Body))
	}
	if result.Text != "" {
		return int64(len(result.Text))
	}
	return 0
}
