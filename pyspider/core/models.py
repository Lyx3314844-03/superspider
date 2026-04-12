"""
pyspider - Python Web Crawler Framework
核心模块
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional


@dataclass
class Request:
    """爬虫请求"""

    url: str
    method: str = "GET"
    headers: Dict[str, str] = field(default_factory=dict)
    cookies: Dict[str, str] = field(default_factory=dict)
    body: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)
    callback: Optional[Callable] = None
    priority: int = 0
    depth: int = 0

    def set_header(self, key: str, value: str) -> "Request":
        """设置请求头"""
        self.headers[key] = value
        return self

    def set_meta(self, key: str, value: Any) -> "Request":
        """设置元数据"""
        self.meta[key] = value
        return self

    def set_method(self, method: str) -> "Request":
        """设置请求方法"""
        self.method = method
        return self

    def set_body(self, body: str) -> "Request":
        """设置请求体"""
        self.body = body
        return self

    def set_priority(self, priority: int) -> "Request":
        """设置优先级"""
        self.priority = priority
        return self


@dataclass
class Response:
    """爬虫响应"""

    url: str
    status_code: int
    headers: Dict[str, str]
    content: bytes
    text: str
    request: Optional[Request] = None
    duration: float = 0.0
    error: Optional[Exception] = None


@dataclass
class Page:
    """页面对象"""

    response: Response
    data: Dict[str, Any] = field(default_factory=dict)

    def set_data(self, key: str, value: Any):
        """设置数据"""
        self.data[key] = value

    def get_data(self, key: str) -> Any:
        """获取数据"""
        return self.data.get(key)
