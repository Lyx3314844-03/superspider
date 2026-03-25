//! 性能优化模块
//! 包含速率限制、熔断器、连接池等

use parking_lot::Mutex;
use std::collections::hash_map::DefaultHasher;
use std::collections::HashMap;
use std::hash::{Hash, Hasher};
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;
use std::thread;
use std::time::{Duration, Instant};

/// 速率限制器（令牌桶算法）
pub struct RateLimiter {
    rate: usize,
    interval: Duration,
    tokens: AtomicUsize,
    last_refill: Mutex<Instant>,
}

impl RateLimiter {
    /// 创建速率限制器
    pub fn new(rate: usize, interval_secs: u64) -> Self {
        RateLimiter {
            rate,
            interval: Duration::from_secs(interval_secs),
            tokens: AtomicUsize::new(rate),
            last_refill: Mutex::new(Instant::now()),
        }
    }

    /// 等待获取令牌
    pub fn wait(&self) {
        loop {
            self.refill();

            let current = self.tokens.load(Ordering::SeqCst);
            if current > 0 {
                if self
                    .tokens
                    .compare_exchange(current, current - 1, Ordering::SeqCst, Ordering::SeqCst)
                    .is_ok()
                {
                    break;
                }
            } else {
                thread::sleep(Duration::from_millis(100));
            }
        }
    }

    fn refill(&self) {
        let mut last_refill = self.last_refill.lock();
        let now = Instant::now();
        let elapsed = now.duration_since(*last_refill);

        let tokens_to_add =
            (elapsed.as_secs_f64() / self.interval.as_secs_f64()) as usize * self.rate;

        if tokens_to_add > 0 {
            let current = self.tokens.load(Ordering::SeqCst);
            self.tokens.store(
                std::cmp::min(self.rate, current + tokens_to_add),
                Ordering::SeqCst,
            );
            *last_refill = now;
        }
    }
}

/// 熔断器状态
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum CircuitState {
    Closed,
    Open,
    HalfOpen,
}

/// 熔断器
pub struct CircuitBreaker {
    failure_threshold: usize,
    success_threshold: usize,
    timeout: Duration,

    failures: AtomicUsize,
    successes: AtomicUsize,
    state: Mutex<CircuitState>,
    last_failure: Mutex<Option<Instant>>,
}

impl CircuitBreaker {
    /// 创建熔断器
    pub fn new(failure_threshold: usize, success_threshold: usize, timeout_secs: u64) -> Self {
        CircuitBreaker {
            failure_threshold,
            success_threshold,
            timeout: Duration::from_secs(timeout_secs),
            failures: AtomicUsize::new(0),
            successes: AtomicUsize::new(0),
            state: Mutex::new(CircuitState::Closed),
            last_failure: Mutex::new(None),
        }
    }

    /// 检查是否允许请求
    pub fn allow(&self) -> bool {
        let mut state = self.state.lock();

        match *state {
            CircuitState::Open => {
                if let Some(last_failure) = *self.last_failure.lock() {
                    if last_failure.elapsed() > self.timeout {
                        *state = CircuitState::HalfOpen;
                        return true;
                    }
                }
                false
            }
            _ => true,
        }
    }

    /// 记录成功
    pub fn record_success(&self) {
        let mut state = self.state.lock();

        if *state == CircuitState::HalfOpen {
            let successes = self.successes.fetch_add(1, Ordering::SeqCst) + 1;
            if successes >= self.success_threshold {
                *state = CircuitState::Closed;
                self.failures.store(0, Ordering::SeqCst);
                self.successes.store(0, Ordering::SeqCst);
            }
        } else if *state == CircuitState::Closed {
            self.failures.store(0, Ordering::SeqCst);
        }
    }

    /// 记录失败
    pub fn record_failure(&self) {
        let mut state = self.state.lock();
        let failures = self.failures.fetch_add(1, Ordering::SeqCst) + 1;

        *self.last_failure.lock() = Some(Instant::now());

        if *state == CircuitState::HalfOpen || failures >= self.failure_threshold {
            *state = CircuitState::Open;
            self.successes.store(0, Ordering::SeqCst);
        }
    }

    /// 获取状态
    pub fn state(&self) -> CircuitState {
        *self.state.lock()
    }
}

/// 连接池
pub struct ConnectionPool {
    max_connections: usize,
    current: AtomicUsize,
    semaphore: Arc<Semaphore>,
}

impl ConnectionPool {
    /// 创建连接池
    pub fn new(max_connections: usize) -> Self {
        ConnectionPool {
            max_connections,
            current: AtomicUsize::new(0),
            semaphore: Arc::new(Semaphore::new(max_connections)),
        }
    }

    /// 获取连接
    pub fn acquire(&self) -> Option<ConnectionPermit<'_>> {
        if self.semaphore.acquire() {
            self.current.fetch_add(1, Ordering::SeqCst);
            Some(ConnectionPermit { pool: self })
        } else {
            None
        }
    }

    /// 释放连接
    fn release(&self) {
        self.current.fetch_sub(1, Ordering::SeqCst);
        self.semaphore.release();
    }

    /// 获取统计
    pub fn stats(&self) -> ConnectionStats {
        ConnectionStats {
            current: self.current.load(Ordering::SeqCst),
            max: self.max_connections,
            available: self.max_connections - self.current.load(Ordering::SeqCst),
        }
    }
}

/// 连接许可
pub struct ConnectionPermit<'a> {
    pool: &'a ConnectionPool,
}

impl<'a> Drop for ConnectionPermit<'a> {
    fn drop(&mut self) {
        self.pool.release();
    }
}

/// 连接统计
pub struct ConnectionStats {
    pub current: usize,
    pub max: usize,
    pub available: usize,
}

/// 信号量
struct Semaphore {
    count: AtomicUsize,
}

impl Semaphore {
    fn new(count: usize) -> Self {
        Semaphore {
            count: AtomicUsize::new(count),
        }
    }

    fn acquire(&self) -> bool {
        loop {
            let current = self.count.load(Ordering::SeqCst);
            if current == 0 {
                return false;
            }
            if self
                .count
                .compare_exchange(current, current - 1, Ordering::SeqCst, Ordering::SeqCst)
                .is_ok()
            {
                return true;
            }
        }
    }

    fn release(&self) {
        self.count.fetch_add(1, Ordering::SeqCst);
    }
}

/// 自适应速率限制器
pub struct AdaptiveRateLimiter {
    initial_delay: f64,
    min_delay: f64,
    max_delay: f64,
    target_response_time: f64,
    domain_delays: Mutex<HashMap<String, f64>>,
    domain_last_request: Mutex<HashMap<String, f64>>,
}

impl AdaptiveRateLimiter {
    /// 创建自适应速率限制器
    pub fn new(
        initial_delay: f64,
        min_delay: f64,
        max_delay: f64,
        target_response_time: f64,
    ) -> Self {
        AdaptiveRateLimiter {
            initial_delay,
            min_delay,
            max_delay,
            target_response_time,
            domain_delays: Mutex::new(HashMap::new()),
            domain_last_request: Mutex::new(HashMap::new()),
        }
    }

    /// 等待
    pub fn wait(&self, url: &str) {
        let domain = self.extract_domain(url);

        let delays = self.domain_delays.lock();
        let mut last_requests = self.domain_last_request.lock();

        let delay = delays.get(&domain).copied().unwrap_or(self.initial_delay);
        let last_request = last_requests.get(&domain).copied().unwrap_or(0.0);

        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_secs_f64();

        let elapsed = now - last_request;
        if elapsed < delay {
            thread::sleep(Duration::from_secs_f64(delay - elapsed));
        }

        last_requests.insert(domain.clone(), now);
    }

    /// 调整延迟
    pub fn adjust(&self, url: &str, response_time: f64, status_code: u16) {
        let domain = self.extract_domain(url);

        let mut delays = self.domain_delays.lock();
        let current_delay = delays.get(&domain).copied().unwrap_or(self.initial_delay);
        let mut new_delay = current_delay;

        // 根据响应时间调整
        if response_time < self.target_response_time {
            new_delay = current_delay * 0.9;
        } else if response_time > self.target_response_time * 2.0 {
            new_delay = current_delay * 1.5;
        }

        // 根据状态码调整
        match status_code {
            429 | 503 => new_delay = current_delay * 2.0,
            500..=599 => new_delay = current_delay * 1.2,
            _ => {}
        }

        // 应用限制
        new_delay = new_delay.max(self.min_delay).min(self.max_delay);

        if (new_delay - current_delay).abs() > 0.1 {
            delays.insert(domain, new_delay);
        }
    }

    fn extract_domain(&self, url: &str) -> String {
        if let Ok(parsed) = url::Url::parse(url) {
            parsed.host_str().unwrap_or("").to_string()
        } else {
            String::new()
        }
    }
}

/// 内容指纹（去重）
pub struct ContentFingerprinter {
    seen_hashes: Mutex<std::collections::HashSet<u64>>,
}

impl ContentFingerprinter {
    /// 创建内容指纹
    pub fn new() -> Self {
        ContentFingerprinter {
            seen_hashes: Mutex::new(std::collections::HashSet::new()),
        }
    }

    /// 检查是否重复
    pub fn is_duplicate(&self, content: &str) -> bool {
        let hash = self.hash(content);
        let mut seen = self.seen_hashes.lock();

        if seen.contains(&hash) {
            true
        } else {
            seen.insert(hash);
            false
        }
    }

    fn hash(&self, content: &str) -> u64 {
        let mut hasher = DefaultHasher::new();
        content.hash(&mut hasher);
        hasher.finish()
    }

    /// 清空
    pub fn clear(&self) {
        self.seen_hashes.lock().clear();
    }
}

impl Default for ContentFingerprinter {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_rate_limiter() {
        let limiter = RateLimiter::new(5, 1);
        limiter.wait();
        limiter.wait();
    }

    #[test]
    fn test_circuit_breaker() {
        let cb = CircuitBreaker::new(3, 2, 60);

        assert!(cb.allow());
        cb.record_failure();
        cb.record_failure();
        cb.record_failure();

        assert!(!cb.allow()); // 应该打开
    }

    #[test]
    fn test_fingerprinter() {
        let fp = ContentFingerprinter::new();

        assert!(!fp.is_duplicate("test"));
        assert!(fp.is_duplicate("test"));
    }
}
