//! 重试机制模块
//! 支持指数退避、自定义重试策略

use rand::Rng;
use std::error::Error;
use std::time::Duration;

/// 重试策略
#[derive(Debug, Clone, Copy)]
pub enum RetryStrategy {
    /// 固定延迟
    Fixed,
    /// 线性退避
    Linear,
    /// 指数退避
    Exponential,
    /// 指数退避 + 抖动
    ExponentialJitter,
}

/// 重试配置
#[derive(Debug, Clone)]
pub struct RetryConfig {
    pub max_retries: usize,
    pub strategy: RetryStrategy,
    pub base_delay: Duration,
    pub max_delay: Duration,
    pub jitter_factor: f64,
    pub retry_on_status_codes: Vec<u16>,
}

impl Default for RetryConfig {
    fn default() -> Self {
        Self {
            max_retries: 3,
            strategy: RetryStrategy::ExponentialJitter,
            base_delay: Duration::from_secs(1),
            max_delay: Duration::from_secs(60),
            jitter_factor: 0.1,
            retry_on_status_codes: vec![429, 500, 502, 503, 504],
        }
    }
}

impl RetryConfig {
    /// 激进重试（更多次数，更短延迟）
    pub fn aggressive() -> Self {
        Self {
            max_retries: 5,
            strategy: RetryStrategy::Exponential,
            base_delay: Duration::from_millis(500),
            max_delay: Duration::from_secs(30),
            jitter_factor: 0.05,
            retry_on_status_codes: vec![429, 500, 502, 503, 504],
        }
    }

    /// 保守重试（更少次数，更长延迟）
    pub fn conservative() -> Self {
        Self {
            max_retries: 2,
            strategy: RetryStrategy::ExponentialJitter,
            base_delay: Duration::from_secs(2),
            max_delay: Duration::from_secs(120),
            jitter_factor: 0.2,
            retry_on_status_codes: vec![429, 500, 502, 503, 504],
        }
    }
}

/// 重试结果
#[derive(Debug)]
pub struct RetryResult<T> {
    pub success: bool,
    pub attempts: usize,
    pub total_time: Duration,
    pub result: Option<T>,
    pub last_error: Option<String>,
    pub last_status_code: Option<u16>,
    pub delays: Vec<Duration>,
}

/// 重试处理器
pub struct RetryHandler {
    config: RetryConfig,
    total_retries: std::sync::atomic::AtomicUsize,
    successful_retries: std::sync::atomic::AtomicUsize,
    failed_retries: std::sync::atomic::AtomicUsize,
}

impl RetryHandler {
    pub fn new(config: RetryConfig) -> Self {
        Self {
            config,
            total_retries: std::sync::atomic::AtomicUsize::new(0),
            successful_retries: std::sync::atomic::AtomicUsize::new(0),
            failed_retries: std::sync::atomic::AtomicUsize::new(0),
        }
    }

    pub fn with_default_config() -> Self {
        Self::new(RetryConfig::default())
    }

    /// 计算延迟时间
    pub fn calculate_delay(&self, attempt: usize) -> Duration {
        let delay = match self.config.strategy {
            RetryStrategy::Fixed => self.config.base_delay,
            RetryStrategy::Linear => self.config.base_delay * (attempt as u32 + 1),
            RetryStrategy::Exponential => {
                self.config.base_delay * (1 << attempt.min(30)) // 防止溢出
            }
            RetryStrategy::ExponentialJitter => {
                let mut rng = rand::thread_rng();
                let base = self.config.base_delay * (1 << attempt.min(30));
                let jitter = base.mul_f64(self.config.jitter_factor * rng.gen::<f64>());
                base + jitter
            }
        };

        // 限制最大延迟
        delay.min(self.config.max_delay)
    }

    /// 判断是否应该重试
    pub fn should_retry(&self, status_code: Option<u16>) -> bool {
        if let Some(code) = status_code {
            self.config.retry_on_status_codes.contains(&code)
        } else {
            false
        }
    }

    /// 执行函数，带重试机制
    pub fn execute_with_retry<F, T, E>(&self, mut func: F) -> RetryResult<T>
    where
        F: FnMut() -> Result<T, E>,
        E: std::fmt::Display,
    {
        let start_time = std::time::Instant::now();
        let mut last_error: Option<String> = None;
        let last_status_code: Option<u16> = None;
        let mut delays = Vec::new();

        for attempt in 0..=self.config.max_retries {
            match func() {
                Ok(result) => {
                    self.successful_retries
                        .fetch_add(1, std::sync::atomic::Ordering::SeqCst);
                    return RetryResult {
                        success: true,
                        attempts: attempt + 1,
                        total_time: start_time.elapsed(),
                        result: Some(result),
                        last_error: None,
                        last_status_code,
                        delays,
                    };
                }
                Err(e) => {
                    last_error = Some(e.to_string());
                    self.total_retries
                        .fetch_add(1, std::sync::atomic::Ordering::SeqCst);

                    if attempt < self.config.max_retries {
                        let delay = self.calculate_delay(attempt);
                        delays.push(delay);
                        log::warn!(
                            "请求失败：{}, {:.2?} 后重试 (尝试 {}/{})",
                            e,
                            delay,
                            attempt + 1,
                            self.config.max_retries + 1
                        );
                        std::thread::sleep(delay);
                    } else {
                        log::error!("达到最大重试次数：{}", e);
                    }
                }
            }
        }

        self.failed_retries
            .fetch_add(1, std::sync::atomic::Ordering::SeqCst);

        RetryResult {
            success: false,
            attempts: self.config.max_retries + 1,
            total_time: start_time.elapsed(),
            result: None,
            last_error,
            last_status_code,
            delays,
        }
    }

    /// 异步执行函数，带重试机制
    pub async fn execute_with_retry_async<F, Fut, T, E>(&self, mut func: F) -> RetryResult<T>
    where
        F: FnMut() -> Fut,
        Fut: std::future::Future<Output = Result<T, E>>,
        E: std::fmt::Display,
    {
        let start_time = std::time::Instant::now();
        let mut last_error: Option<String> = None;
        let last_status_code: Option<u16> = None;
        let mut delays = Vec::new();

        for attempt in 0..=self.config.max_retries {
            match func().await {
                Ok(result) => {
                    self.successful_retries
                        .fetch_add(1, std::sync::atomic::Ordering::SeqCst);
                    return RetryResult {
                        success: true,
                        attempts: attempt + 1,
                        total_time: start_time.elapsed(),
                        result: Some(result),
                        last_error: None,
                        last_status_code,
                        delays,
                    };
                }
                Err(e) => {
                    last_error = Some(e.to_string());
                    self.total_retries
                        .fetch_add(1, std::sync::atomic::Ordering::SeqCst);

                    if attempt < self.config.max_retries {
                        let delay = self.calculate_delay(attempt);
                        delays.push(delay);
                        log::warn!(
                            "请求失败：{}, {:.2?} 后重试 (尝试 {}/{})",
                            e,
                            delay,
                            attempt + 1,
                            self.config.max_retries + 1
                        );
                        tokio::time::sleep(delay).await;
                    } else {
                        log::error!("达到最大重试次数：{}", e);
                    }
                }
            }
        }

        self.failed_retries
            .fetch_add(1, std::sync::atomic::Ordering::SeqCst);

        RetryResult {
            success: false,
            attempts: self.config.max_retries + 1,
            total_time: start_time.elapsed(),
            result: None,
            last_error,
            last_status_code,
            delays,
        }
    }

    /// 获取统计信息
    pub fn get_stats(&self) -> RetryStats {
        RetryStats {
            total_retries: self.total_retries.load(std::sync::atomic::Ordering::SeqCst),
            successful_retries: self
                .successful_retries
                .load(std::sync::atomic::Ordering::SeqCst),
            failed_retries: self
                .failed_retries
                .load(std::sync::atomic::Ordering::SeqCst),
        }
    }

    /// 重置统计
    pub fn reset_stats(&self) {
        self.total_retries
            .store(0, std::sync::atomic::Ordering::SeqCst);
        self.successful_retries
            .store(0, std::sync::atomic::Ordering::SeqCst);
        self.failed_retries
            .store(0, std::sync::atomic::Ordering::SeqCst);
    }
}

/// 重试统计
#[derive(Debug, Clone)]
pub struct RetryStats {
    pub total_retries: usize,
    pub successful_retries: usize,
    pub failed_retries: usize,
}

impl std::fmt::Display for RetryStats {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        let success_rate = if self.total_retries > 0 {
            self.successful_retries as f64 / self.total_retries as f64
        } else {
            0.0
        };
        write!(
            f,
            "RetryStats {{ total: {}, success: {}, failed: {}, success_rate: {:.2}% }}",
            self.total_retries,
            self.successful_retries,
            self.failed_retries,
            success_rate * 100.0
        )
    }
}

/// 熔断器
pub struct CircuitBreaker {
    failure_threshold: usize,
    success_threshold: usize,
    timeout: Duration,
    half_open_max_calls: usize,
    state: std::sync::Mutex<CircuitState>,
    failure_count: std::sync::atomic::AtomicUsize,
    success_count: std::sync::atomic::AtomicUsize,
    last_failure_time: std::sync::Mutex<Option<std::time::Instant>>,
    half_open_calls: std::sync::atomic::AtomicUsize,
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum CircuitState {
    Closed,
    Open,
    HalfOpen,
}

impl CircuitBreaker {
    pub fn new(failure_threshold: usize, success_threshold: usize, timeout: Duration) -> Self {
        Self {
            failure_threshold,
            success_threshold,
            timeout,
            half_open_max_calls: 3,
            state: std::sync::Mutex::new(CircuitState::Closed),
            failure_count: std::sync::atomic::AtomicUsize::new(0),
            success_count: std::sync::atomic::AtomicUsize::new(0),
            last_failure_time: std::sync::Mutex::new(None),
            half_open_calls: std::sync::atomic::AtomicUsize::new(0),
        }
    }

    pub fn state(&self) -> CircuitState {
        let mut state = self.state.lock().unwrap();

        if *state == CircuitState::Open {
            if let Some(last_failure) = *self.last_failure_time.lock().unwrap() {
                if last_failure.elapsed() > self.timeout {
                    *state = CircuitState::HalfOpen;
                    self.half_open_calls
                        .store(0, std::sync::atomic::Ordering::SeqCst);
                }
            }
        }

        *state
    }

    pub fn call<F, T>(&self, func: F) -> Result<T, CircuitBreakerError>
    where
        F: FnOnce() -> Result<T, Box<dyn Error + Send + Sync>>,
    {
        let current_state = self.state();

        if current_state == CircuitState::Open {
            return Err(CircuitBreakerError::new("熔断器已打开"));
        }

        if current_state == CircuitState::HalfOpen {
            let current_calls = self
                .half_open_calls
                .fetch_add(1, std::sync::atomic::Ordering::SeqCst);
            if current_calls >= self.half_open_max_calls {
                return Err(CircuitBreakerError::new("半开状态达到最大调用次数"));
            }
        }

        match func() {
            Ok(result) => {
                self.on_success();
                Ok(result)
            }
            Err(e) => {
                self.on_failure();
                Err(CircuitBreakerError::new(&e.to_string()))
            }
        }
    }

    fn on_success(&self) {
        let mut state = self.state.lock().unwrap();

        if *state == CircuitState::HalfOpen {
            let successes = self
                .success_count
                .fetch_add(1, std::sync::atomic::Ordering::SeqCst)
                + 1;
            if successes >= self.success_threshold {
                *state = CircuitState::Closed;
                self.failure_count
                    .store(0, std::sync::atomic::Ordering::SeqCst);
                self.success_count
                    .store(0, std::sync::atomic::Ordering::SeqCst);
            }
        } else if *state == CircuitState::Closed {
            self.failure_count
                .store(0, std::sync::atomic::Ordering::SeqCst);
        }
    }

    fn on_failure(&self) {
        let mut state = self.state.lock().unwrap();
        let failures = self
            .failure_count
            .fetch_add(1, std::sync::atomic::Ordering::SeqCst)
            + 1;

        *self.last_failure_time.lock().unwrap() = Some(std::time::Instant::now());

        if *state == CircuitState::HalfOpen {
            *state = CircuitState::Open;
            self.success_count
                .store(0, std::sync::atomic::Ordering::SeqCst);
        } else if *state == CircuitState::Closed && failures >= self.failure_threshold {
            *state = CircuitState::Open;
        }
    }

    pub fn reset(&self) {
        *self.state.lock().unwrap() = CircuitState::Closed;
        self.failure_count
            .store(0, std::sync::atomic::Ordering::SeqCst);
        self.success_count
            .store(0, std::sync::atomic::Ordering::SeqCst);
        self.half_open_calls
            .store(0, std::sync::atomic::Ordering::SeqCst);
        *self.last_failure_time.lock().unwrap() = None;
    }

    pub fn get_stats(&self) -> CircuitBreakerStats {
        CircuitBreakerStats {
            state: self.state(),
            failure_count: self.failure_count.load(std::sync::atomic::Ordering::SeqCst),
            success_count: self.success_count.load(std::sync::atomic::Ordering::SeqCst),
        }
    }
}

#[derive(Debug)]
pub struct CircuitBreakerError {
    message: String,
}

impl CircuitBreakerError {
    pub fn new(message: &str) -> Self {
        Self {
            message: message.to_string(),
        }
    }
}

impl std::fmt::Display for CircuitBreakerError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.message)
    }
}

impl std::error::Error for CircuitBreakerError {}

#[derive(Debug)]
pub struct CircuitBreakerStats {
    pub state: CircuitState,
    pub failure_count: usize,
    pub success_count: usize,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_retry_handler() {
        let handler = RetryHandler::with_default_config();

        let mut attempts = 0;
        let result = handler.execute_with_retry(|| {
            attempts += 1;
            if attempts < 3 {
                Err::<(), _>("Temporary error")
            } else {
                Ok(())
            }
        });

        assert!(result.success);
        assert_eq!(result.attempts, 3);
    }

    #[test]
    fn test_circuit_breaker() {
        let cb = CircuitBreaker::new(3, 2, Duration::from_secs(1));

        assert_eq!(cb.state(), CircuitState::Closed);

        // 连续失败 3 次
        for _ in 0..3 {
            let _ = cb.call(|| Err::<(), _>(Box::new(std::io::Error::other("error"))));
        }

        assert_eq!(cb.state(), CircuitState::Open);
    }
}
