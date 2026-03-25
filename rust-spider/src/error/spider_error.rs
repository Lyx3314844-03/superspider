//! Spider 错误类型
//! 
//! 定义爬虫框架的统一错误类型

use std::fmt;
use std::time::Duration;

/// Spider 错误类型
#[derive(Debug)]
pub enum SpiderError {
    /// 网络错误
    NetworkError {
        url: String,
        source: Box<dyn std::error::Error + Send + Sync>,
    },
    
    /// 解析错误
    ParseError {
        url: String,
        reason: String,
    },
    
    /// 速率限制错误
    RateLimitError {
        retry_after: Duration,
        message: String,
    },
    
    /// 队列错误
    QueueError {
        message: String,
    },
    
    /// 配置错误
    ConfigError {
        field: String,
        message: String,
    },
    
    /// 运行时错误
    RuntimeError {
        message: String,
        context: Vec<String>,
    },
    
    /// 致命错误
    FatalError {
        reason: String,
        recoverable: bool,
    },
    
    /// 外部依赖错误
    ExternalError {
        source: Box<dyn std::error::Error + Send + Sync>,
    },
}

impl SpiderError {
    /// 创建网络错误
    pub fn network(url: impl Into<String>, source: impl std::error::Error + Send + Sync + 'static) -> Self {
        Self::NetworkError {
            url: url.into(),
            source: Box::new(source),
        }
    }
    
    /// 创建解析错误
    pub fn parse(url: impl Into<String>, reason: impl Into<String>) -> Self {
        Self::ParseError {
            url: url.into(),
            reason: reason.into(),
        }
    }
    
    /// 创建速率限制错误
    pub fn rate_limit(retry_after: Duration, message: impl Into<String>) -> Self {
        Self::RateLimitError {
            retry_after,
            message: message.into(),
        }
    }
    
    /// 创建队列错误
    pub fn queue(message: impl Into<String>) -> Self {
        Self::QueueError {
            message: message.into(),
        }
    }
    
    /// 创建配置错误
    pub fn config(field: impl Into<String>, message: impl Into<String>) -> Self {
        Self::ConfigError {
            field: field.into(),
            message: message.into(),
        }
    }
    
    /// 创建运行时错误
    pub fn runtime(message: impl Into<String>) -> Self {
        Self::RuntimeError {
            message: message.into(),
            context: Vec::new(),
        }
    }
    
    /// 创建致命错误
    pub fn fatal(reason: impl Into<String>, recoverable: bool) -> Self {
        Self::FatalError {
            reason: reason.into(),
            recoverable,
        }
    }
    
    /// 添加上下文信息
    pub fn with_context(mut self, context: impl Into<String>) -> Self {
        if let SpiderError::RuntimeError { ref mut context, .. } = self {
            context.push(context.into());
        }
        self
    }
    
    /// 检查是否可恢复
    pub fn is_recoverable(&self) -> bool {
        match self {
            SpiderError::FatalError { recoverable, .. } => *recoverable,
            SpiderError::NetworkError { .. } => true,
            SpiderError::RateLimitError { .. } => true,
            _ => false,
        }
    }
    
    /// 获取错误类型名称
    pub fn error_type(&self) -> &'static str {
        match self {
            SpiderError::NetworkError { .. } => "NetworkError",
            SpiderError::ParseError { .. } => "ParseError",
            SpiderError::RateLimitError { .. } => "RateLimitError",
            SpiderError::QueueError { .. } => "QueueError",
            SpiderError::ConfigError { .. } => "ConfigError",
            SpiderError::RuntimeError { .. } => "RuntimeError",
            SpiderError::FatalError { .. } => "FatalError",
            SpiderError::ExternalError { .. } => "ExternalError",
        }
    }
}

impl fmt::Display for SpiderError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            SpiderError::NetworkError { url, source } => {
                write!(f, "Network error while crawling {}: {}", url, source)
            }
            SpiderError::ParseError { url, reason } => {
                write!(f, "Parse error for {}: {}", url, reason)
            }
            SpiderError::RateLimitError { retry_after, message } => {
                write!(f, "Rate limited: {} (retry after {:?})", message, retry_after)
            }
            SpiderError::QueueError { message } => {
                write!(f, "Queue error: {}", message)
            }
            SpiderError::ConfigError { field, message } => {
                write!(f, "Config error in {}: {}", field, message)
            }
            SpiderError::RuntimeError { message, context } => {
                write!(f, "Runtime error: {}", message)?;
                if !context.is_empty() {
                    write!(f, " [Context: {}]", context.join(", "))?;
                }
                Ok(())
            }
            SpiderError::FatalError { reason, .. } => {
                write!(f, "Fatal error: {}", reason)
            }
            SpiderError::ExternalError { source } => {
                write!(f, "External error: {}", source)
            }
        }
    }
}

impl std::error::Error for SpiderError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            SpiderError::NetworkError { source, .. } => Some(source.as_ref()),
            SpiderError::ExternalError { source } => Some(source.as_ref()),
            _ => None,
        }
    }
}

impl From<reqwest::Error> for SpiderError {
    fn from(err: reqwest::Error) -> Self {
        SpiderError::ExternalError {
            source: Box::new(err),
        }
    }
}

impl From<serde_json::Error> for SpiderError {
    fn from(err: serde_json::Error) -> Self {
        SpiderError::ExternalError {
            source: Box::new(err),
        }
    }
}

impl From<std::io::Error> for SpiderError {
    fn from(err: std::io::Error) -> Self {
        SpiderError::ExternalError {
            source: Box::new(err),
        }
    }
}

/// 结果类型别名
pub type SpiderResult<T> = Result<T, SpiderError>;

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_error_display() {
        let err = SpiderError::network("https://example.com", reqwest::Error::builder().build());
        assert!(err.to_string().contains("https://example.com"));
    }
    
    #[test]
    fn test_error_is_recoverable() {
        let network_err = SpiderError::network("https://example.com", std::io::Error::new(std::io::ErrorKind::ConnectionRefused, "refused"));
        assert!(network_err.is_recoverable());
        
        let fatal_err = SpiderError::fatal("critical failure", false);
        assert!(!fatal_err.is_recoverable());
    }
    
    #[test]
    fn test_error_with_context() {
        let err = SpiderError::runtime("something went wrong")
            .with_context("additional context");
        
        match err {
            SpiderError::RuntimeError { context, .. } => {
                assert_eq!(context.len(), 1);
                assert_eq!(context[0], "additional context");
            }
            _ => panic!("Wrong error type"),
        }
    }
}
