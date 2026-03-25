package performance

import (
	"sync"
	"time"
)

// CircuitState - 熔断器状态
type CircuitState string

const (
	StateClosed   CircuitState = "closed"    // 正常状态
	StateOpen     CircuitState = "open"      // 熔断状态
	StateHalfOpen CircuitState = "half_open" // 半开状态
)

// CircuitBreaker - 熔断器
type CircuitBreaker struct {
	mu sync.Mutex

	failureThreshold int           // 失败阈值
	successThreshold int           // 成功阈值
	timeout          time.Duration // 超时时间

	state         CircuitState
	failureCount  int
	successCount  int
	lastFailureAt time.Time

	name string
}

// NewCircuitBreaker - 创建熔断器
func NewCircuitBreaker(opts ...func(*CircuitBreaker)) *CircuitBreaker {
	cb := &CircuitBreaker{
		failureThreshold: 5,
		successThreshold: 3,
		timeout:          time.Minute,
		state:            StateClosed,
		name:             "default",
	}

	for _, opt := range opts {
		opt(cb)
	}

	return cb
}

// WithFailureThreshold - 设置失败阈值
func WithFailureThreshold(n int) func(*CircuitBreaker) {
	return func(cb *CircuitBreaker) {
		cb.failureThreshold = n
	}
}

// WithSuccessThreshold - 设置成功阈值
func WithSuccessThreshold(n int) func(*CircuitBreaker) {
	return func(cb *CircuitBreaker) {
		cb.successThreshold = n
	}
}

// WithTimeout - 设置超时时间
func WithTimeout(d time.Duration) func(*CircuitBreaker) {
	return func(cb *CircuitBreaker) {
		cb.timeout = d
	}
}

// WithName - 设置名称
func WithName(name string) func(*CircuitBreaker) {
	return func(cb *CircuitBreaker) {
		cb.name = name
	}
}

// AllowRequest - 检查是否允许请求通过
func (cb *CircuitBreaker) AllowRequest() bool {
	cb.mu.Lock()
	defer cb.mu.Unlock()

	if cb.state == StateOpen {
		// 检查是否超过超时时间
		if time.Since(cb.lastFailureAt) > cb.timeout {
			cb.state = StateHalfOpen
			cb.successCount = 0
			return true
		}
		return false
	}

	return true
}

// RecordSuccess - 记录成功请求
func (cb *CircuitBreaker) RecordSuccess() {
	cb.mu.Lock()
	defer cb.mu.Unlock()

	if cb.state == StateHalfOpen {
		cb.successCount++
		if cb.successCount >= cb.successThreshold {
			cb.state = StateClosed
			cb.failureCount = 0
			cb.successCount = 0
		}
	} else if cb.state == StateClosed {
		cb.failureCount = 0
	}
}

// RecordFailure - 记录失败请求
func (cb *CircuitBreaker) RecordFailure() {
	cb.mu.Lock()
	defer cb.mu.Unlock()

	cb.lastFailureAt = time.Now()

	if cb.state == StateHalfOpen {
		cb.state = StateOpen
		cb.successCount = 0
	} else if cb.state == StateClosed {
		cb.failureCount++
		if cb.failureCount >= cb.failureThreshold {
			cb.state = StateOpen
		}
	}
}

// State - 获取当前状态
func (cb *CircuitBreaker) State() CircuitState {
	cb.mu.Lock()
	defer cb.mu.Unlock()
	return cb.state
}

// Reset - 重置熔断器
func (cb *CircuitBreaker) Reset() {
	cb.mu.Lock()
	defer cb.mu.Unlock()

	cb.state = StateClosed
	cb.failureCount = 0
	cb.successCount = 0
	cb.lastFailureAt = time.Time{}
}

// Stats - 获取统计信息
func (cb *CircuitBreaker) Stats() map[string]interface{} {
	cb.mu.Lock()
	defer cb.mu.Unlock()

	return map[string]interface{}{
		"name":          cb.name,
		"state":         string(cb.state),
		"failure_count": cb.failureCount,
		"success_count": cb.successCount,
		"last_failure":  cb.lastFailureAt,
	}
}

// String - 字符串表示
func (cb *CircuitBreaker) String() string {
	cb.mu.Lock()
	defer cb.mu.Unlock()
	return string(cb.state)
}
