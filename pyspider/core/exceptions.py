"""
异常处理模块 - 修复版
提供统一的异常类型和错误处理
"""

from typing import Optional, Any, Dict


class SpiderError(Exception):
    """爬虫基础异常"""

    def __init__(
        self,
        message: str,
        url: Optional[str] = None,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.url = url
        self.status_code = status_code
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "url": self.url,
            "status_code": self.status_code,
            "details": self.details,
        }


class DownloadError(SpiderError):
    """下载错误"""

    pass


class TimeoutError(DownloadError):
    """超时错误"""

    pass


class ParseError(SpiderError):
    """解析错误"""

    pass


class ValidationError(SpiderError):
    """验证错误"""

    pass


class MaxRetriesExceeded(SpiderError):
    """超过最大重试次数"""

    pass


class CrawlError(SpiderError):
    """爬取错误"""

    pass


class ConfigurationError(SpiderError):
    """配置错误"""

    pass


class PipelineError(SpiderError):
    """管道错误"""

    pass


class MiddlewareError(SpiderError):
    """中间件错误"""

    pass


class RateLimitError(SpiderError):
    """速率限制错误"""

    pass


class ProxyError(SpiderError):
    """代理错误"""

    pass


class AuthenticationError(SpiderError):
    """认证错误"""

    pass


class CaptchaError(SpiderError):
    """验证码错误"""

    pass


class BlockedError(SpiderError):
    """被封禁错误"""

    pass


class DataError(SpiderError):
    """数据错误"""

    pass
