package core

import (
	"fmt"
	"hash/fnv"
	"sync"
	"time"
)

// ContentDeduplicator 内容去重器
type ContentDeduplicator struct {
	hashes map[uint64]bool
	mu     sync.RWMutex
}

// NewContentDeduplicator 创建内容去重器
func NewContentDeduplicator() *ContentDeduplicator {
	return &ContentDeduplicator{
		hashes: make(map[uint64]bool),
	}
}

// IsDuplicate 检查内容是否重复
func (cd *ContentDeduplicator) IsDuplicate(content []byte) bool {
	if len(content) == 0 {
		return false
	}

	hash := hashContent(content)

	cd.mu.RLock()
	exists := cd.hashes[hash]
	cd.mu.RUnlock()

	if exists {
		return true
	}

	cd.mu.Lock()
	cd.hashes[hash] = true
	cd.mu.Unlock()

	return false
}

// Clear 清除所有哈希
func (cd *ContentDeduplicator) Clear() {
	cd.mu.Lock()
	defer cd.mu.Unlock()
	cd.hashes = make(map[uint64]bool)
}

// Count 返回已存储的哈希数量
func (cd *ContentDeduplicator) Count() int {
	cd.mu.RLock()
	defer cd.mu.RUnlock()
	return len(cd.hashes)
}

// hashContent 计算内容哈希 (修复: 使用 FNV-1a 代替截断MD5)
func hashContent(content []byte) uint64 {
	h := fnv.New64a()
	h.Write(content)
	return h.Sum64()
}

// RateLimiter 速率限制器 (令牌桶算法)
type RateLimiter struct {
	tokens         float64
	maxTokens      float64
	refillRate     float64 // tokens per second
	lastRefillTime time.Time
	mu             sync.Mutex
}

// NewRateLimiter 创建速率限制器
// maxTokens: 最大令牌数 (burst size)
// refillRate: 每秒补充的令牌数
func NewRateLimiter(maxTokens float64, refillRate float64) *RateLimiter {
	return &RateLimiter{
		tokens:         maxTokens,
		maxTokens:      maxTokens,
		refillRate:     refillRate,
		lastRefillTime: time.Now(),
	}
}

// Wait 等待直到获取到令牌
func (rl *RateLimiter) Wait() {
	for {
		if rl.tryAcquire() {
			return
		}
		time.Sleep(10 * time.Millisecond)
	}
}

// tryAcquire 尝试获取令牌
func (rl *RateLimiter) tryAcquire() bool {
	rl.mu.Lock()
	defer rl.mu.Unlock()

	// 补充令牌
	now := time.Now()
	elapsed := now.Sub(rl.lastRefillTime).Seconds()
	rl.tokens += elapsed * rl.refillRate
	if rl.tokens > rl.maxTokens {
		rl.tokens = rl.maxTokens
	}
	rl.lastRefillTime = now

	// 尝试获取
	if rl.tokens >= 1.0 {
		rl.tokens -= 1.0
		return true
	}

	return false
}

// SetRate 动态调整速率
func (rl *RateLimiter) SetRate(refillRate float64) {
	rl.mu.Lock()
	defer rl.mu.Unlock()
	rl.refillRate = refillRate
}

// String 返回当前状态
func (rl *RateLimiter) String() string {
	rl.mu.Lock()
	defer rl.mu.Unlock()
	return fmt.Sprintf("RateLimiter{tokens: %.2f, max: %.2f, rate: %.2f/s}",
		rl.tokens, rl.maxTokens, rl.refillRate)
}
