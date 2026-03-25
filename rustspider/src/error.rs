//! 错误处理模块
//! 统一的异常体系和错误处理机制

use std::error::Error;
use std::fmt;

/// 错误级别
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum ErrorLevel {
    Debug,
    Info,
    Warning,
    Error,
    Critical,
}

/// 错误类型
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum ErrorType {
    NetworkError,
    TimeoutError,
    ConnectionError,
    HttpError,
    ParseError,
    DownloadError,
    ProxyError,
    ConfigError,
    QueueError,
    UnknownError,
}

/// 爬虫错误
#[derive(Debug, Clone)]
pub struct SpiderError {
    pub message: String,
    pub error_type: ErrorType,
    pub level: ErrorLevel,
    pub url: Option<String>,
    pub status_code: Option<u16>,
    pub retry_count: i32,
    pub source: Option<String>,
}

impl SpiderError {
    pub fn new(message: &str) -> Self {
        Self {
            message: message.to_string(),
            error_type: ErrorType::UnknownError,
            level: ErrorLevel::Error,
            url: None,
            status_code: None,
            retry_count: 0,
            source: None,
        }
    }

    pub fn with_type(message: &str, error_type: ErrorType) -> Self {
        Self {
            message: message.to_string(),
            error_type,
            level: ErrorLevel::Error,
            ..Self::default()
        }
    }

    pub fn with_url(mut self, url: &str) -> Self {
        self.url = Some(url.to_string());
        self
    }

    pub fn with_status_code(mut self, status_code: u16) -> Self {
        self.status_code = Some(status_code);
        self
    }

    pub fn with_retry_count(mut self, retry_count: i32) -> Self {
        self.retry_count = retry_count;
        self
    }
}

impl Default for SpiderError {
    fn default() -> Self {
        Self::new("Unknown error")
    }
}

impl fmt::Display for SpiderError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "[{:?}] {}", self.error_type, self.message)
    }
}

impl Error for SpiderError {}

/// 网络错误
#[derive(Debug)]
pub struct NetworkError {
    pub message: String,
    pub url: Option<String>,
}

impl NetworkError {
    pub fn new(message: &str) -> Self {
        Self {
            message: message.to_string(),
            url: None,
        }
    }
}

impl fmt::Display for NetworkError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "Network error: {}", self.message)
    }
}

impl Error for NetworkError {}

/// HTTP 错误
#[derive(Debug)]
pub struct HttpError {
    pub status_code: u16,
    pub message: String,
    pub url: Option<String>,
}

impl HttpError {
    pub fn new(status_code: u16, message: &str) -> Self {
        Self {
            status_code,
            message: message.to_string(),
            url: None,
        }
    }
}

impl fmt::Display for HttpError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "HTTP {}: {}", self.status_code, self.message)
    }
}

impl Error for HttpError {}

/// 错误处理器
pub struct ErrorHandler {
    error_count: std::sync::Mutex<std::collections::HashMap<String, usize>>,
    max_error_count: usize,
    fatal_errors: std::sync::Mutex<Vec<SpiderError>>,
}

impl ErrorHandler {
    pub fn new(max_error_count: usize) -> Self {
        Self {
            error_count: std::sync::Mutex::new(std::collections::HashMap::new()),
            max_error_count,
            fatal_errors: std::sync::Mutex::new(Vec::new()),
        }
    }

    pub fn handle(&self, error: &SpiderError) -> bool {
        // 记录错误
        {
            let mut counts = self.error_count.lock().unwrap();
            let key = format!("{:?}:{}", error.error_type, error.message);
            *counts.entry(key).or_insert(0) += 1;
        }

        // 检查是否应该停止
        if self.should_stop(error) {
            self.fatal_errors.lock().unwrap().push(error.clone());
            log::error!("达到最大错误数，停止爬虫：{}", error);
            return false;
        }

        // 日志记录
        self.log_error(error);

        true
    }

    fn should_stop(&self, error: &SpiderError) -> bool {
        // 致命错误立即停止
        if error.level == ErrorLevel::Critical {
            return true;
        }

        // 错误数过多停止
        let counts = self.error_count.lock().unwrap();
        let total: usize = counts.values().sum();
        if total >= self.max_error_count {
            return true;
        }

        false
    }

    fn log_error(&self, error: &SpiderError) {
        match error.level {
            ErrorLevel::Debug => log::debug!("{}", error),
            ErrorLevel::Info => log::info!("{}", error),
            ErrorLevel::Warning => log::warn!("{}", error),
            ErrorLevel::Error => log::error!("{}", error),
            ErrorLevel::Critical => log::error!("{}", error),
        }
    }

    pub fn get_error_summary(&self) -> ErrorSummary {
        let counts = self.error_count.lock().unwrap();
        let total: usize = counts.values().sum();
        let fatal_count = self.fatal_errors.lock().unwrap().len();

        ErrorSummary {
            total_errors: total,
            fatal_errors: fatal_count,
        }
    }

    pub fn clear(&self) {
        self.error_count.lock().unwrap().clear();
        self.fatal_errors.lock().unwrap().clear();
    }
}

/// 错误摘要
#[derive(Debug, Clone)]
pub struct ErrorSummary {
    pub total_errors: usize,
    pub fatal_errors: usize,
}

/// 安全执行函数
pub fn safe_execute<F, T>(func: F, default: T) -> T
where
    F: FnOnce() -> Result<T, Box<dyn Error + Send + Sync>>,
{
    match func() {
        Ok(result) => result,
        Err(e) => {
            log::error!("安全执行失败：{}", e);
            default
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_spider_error() {
        let mut error = SpiderError::new("Test error");
        error.error_type = ErrorType::NetworkError;
        error.url = Some("https://example.com".to_string());

        assert_eq!(error.error_type, ErrorType::NetworkError);
        assert_eq!(error.url, Some("https://example.com".to_string()));
    }

    #[test]
    fn test_error_handler() {
        let handler = ErrorHandler::new(100);
        let error = SpiderError::new("Test");

        assert!(handler.handle(&error));
    }
}
