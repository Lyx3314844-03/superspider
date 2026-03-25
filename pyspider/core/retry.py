"""
重试机制模块
支持指数退避、自定义重试策略
"""

import time
import random
import threading
from typing import Optional, Callable, Any, List, Type, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import logging


logger = logging.getLogger(__name__)


class RetryStrategy(Enum):
    """重试策略"""
    FIXED = "fixed"  # 固定延迟
    LINEAR = "linear"  # 线性退避
    EXPONENTIAL = "exponential"  # 指数退避
    EXPONENTIAL_JITTER = "exponential_jitter"  # 指数退避 + 抖动


@dataclass
class RetryConfig:
    """重试配置"""
    max_retries: int = 3
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_JITTER
    base_delay: float = 1.0  # 基础延迟（秒）
    max_delay: float = 60.0  # 最大延迟（秒）
    jitter_factor: float = 0.1  # 抖动因子（0-1）
    retry_on_exceptions: List[Type[Exception]] = field(default_factory=list)
    retry_on_status_codes: List[int] = field(default_factory=lambda: [429, 500, 502, 503, 504])
    
    @classmethod
    def default(cls) -> 'RetryConfig':
        """默认配置"""
        return cls(
            max_retries=3,
            strategy=RetryStrategy.EXPONENTIAL_JITTER,
            base_delay=1.0,
            max_delay=60.0,
            jitter_factor=0.1,
            retry_on_exceptions=[
                ConnectionError,
                TimeoutError,
            ],
            retry_on_status_codes=[429, 500, 502, 503, 504],
        )
    
    @classmethod
    def aggressive(cls) -> 'RetryConfig':
        """激进重试（更多次数，更短延迟）"""
        return cls(
            max_retries=5,
            strategy=RetryStrategy.EXPONENTIAL,
            base_delay=0.5,
            max_delay=30.0,
            jitter_factor=0.05,
        )
    
    @classmethod
    def conservative(cls) -> 'RetryConfig':
        """保守重试（更少次数，更长延迟）"""
        return cls(
            max_retries=2,
            strategy=RetryStrategy.EXPONENTIAL_JITTER,
            base_delay=2.0,
            max_delay=120.0,
            jitter_factor=0.2,
        )


@dataclass
class RetryResult:
    """重试结果"""
    success: bool
    attempts: int
    total_time: float
    last_error: Optional[Exception] = None
    last_status_code: Optional[int] = None
    delays: List[float] = field(default_factory=list)


class RetryHandler:
    """重试处理器"""
    
    def __init__(self, config: RetryConfig = None):
        self.config = config or RetryConfig.default()
        self._lock = threading.RLock()
        self._stats = {
            "total_retries": 0,
            "successful_retries": 0,
            "failed_retries": 0,
            "total_attempts": 0,
        }
    
    def calculate_delay(self, attempt: int) -> float:
        """
        计算延迟时间
        
        Args:
            attempt: 当前尝试次数（从 0 开始）
            
        Returns:
            延迟时间（秒）
        """
        if self.config.strategy == RetryStrategy.FIXED:
            delay = self.config.base_delay
            
        elif self.config.strategy == RetryStrategy.LINEAR:
            delay = self.config.base_delay * (attempt + 1)
            
        elif self.config.strategy == RetryStrategy.EXPONENTIAL:
            delay = self.config.base_delay * (2 ** attempt)
            
        elif self.config.strategy == RetryStrategy.EXPONENTIAL_JITTER:
            # 指数退避 + 抖动
            delay = self.config.base_delay * (2 ** attempt)
            jitter = delay * self.config.jitter_factor * random.random()
            delay += jitter
        
        else:
            delay = self.config.base_delay
        
        # 限制最大延迟
        return min(delay, self.config.max_delay)
    
    def should_retry(
        self, 
        exception: Optional[Exception] = None,
        status_code: Optional[int] = None
    ) -> bool:
        """
        判断是否应该重试
        
        Args:
            exception: 抛出的异常
            status_code: HTTP 状态码
            
        Returns:
            是否重试
        """
        # 检查异常类型
        if exception:
            for exc_type in self.config.retry_on_exceptions:
                if isinstance(exception, exc_type):
                    return True
        
        # 检查状态码
        if status_code and status_code in self.config.retry_on_status_codes:
            return True
        
        return False
    
    def execute_with_retry(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> RetryResult:
        """
        执行函数，带重试机制
        
        Args:
            func: 要执行的函数
            *args: 函数参数
            **kwargs: 函数关键字参数
            
        Returns:
            RetryResult: 重试结果
        """
        start_time = time.time()
        last_error = None
        last_status_code = None
        delays = []
        
        for attempt in range(self.config.max_retries + 1):
            try:
                # 执行函数
                result = func(*args, **kwargs)
                
                # 检查是否需要重试（基于返回值）
                if hasattr(result, 'status_code'):
                    last_status_code = result.status_code
                    if self.should_retry(status_code=last_status_code):
                        if attempt < self.config.max_retries:
                            delay = self.calculate_delay(attempt)
                            delays.append(delay)
                            logger.warning(
                                f"请求返回状态码 {last_status_code}，{delay:.2f}秒后重试 "
                                f"(尝试 {attempt + 1}/{self.config.max_retries + 1})"
                            )
                            time.sleep(delay)
                            continue
                
                # 成功
                with self._lock:
                    self._stats["successful_retries"] += 1
                    self._stats["total_attempts"] += attempt + 1
                
                return RetryResult(
                    success=True,
                    attempts=attempt + 1,
                    total_time=time.time() - start_time,
                    last_error=None,
                    last_status_code=last_status_code,
                    delays=delays
                )
                
            except Exception as e:
                last_error = e
                
                # 检查是否应该重试
                if not self.should_retry(exception=e):
                    logger.error(f"遇到不可重试的错误：{e}")
                    break
                
                if attempt < self.config.max_retries:
                    delay = self.calculate_delay(attempt)
                    delays.append(delay)
                    logger.warning(
                        f"请求失败：{e}，{delay:.2f}秒后重试 "
                        f"(尝试 {attempt + 1}/{self.config.max_retries + 1})"
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"达到最大重试次数：{e}")
        
        # 失败
        with self._lock:
            self._stats["failed_retries"] += 1
            self._stats["total_attempts"] += self.config.max_retries + 1
        
        return RetryResult(
            success=False,
            attempts=self.config.max_retries + 1,
            total_time=time.time() - start_time,
            last_error=last_error,
            last_status_code=last_status_code,
            delays=delays
        )
    
    async def execute_with_retry_async(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> RetryResult:
        """
        异步执行函数，带重试机制
        
        Args:
            func: 要执行的异步函数
            *args: 函数参数
            **kwargs: 函数关键字参数
            
        Returns:
            RetryResult: 重试结果
        """
        import asyncio
        
        start_time = time.time()
        last_error = None
        last_status_code = None
        delays = []
        
        for attempt in range(self.config.max_retries + 1):
            try:
                # 执行异步函数
                result = await func(*args, **kwargs)
                
                # 检查是否需要重试
                if hasattr(result, 'status_code'):
                    last_status_code = result.status_code
                    if self.should_retry(status_code=last_status_code):
                        if attempt < self.config.max_retries:
                            delay = self.calculate_delay(attempt)
                            delays.append(delay)
                            logger.warning(
                                f"请求返回状态码 {last_status_code}，{delay:.2f}秒后重试 "
                                f"(尝试 {attempt + 1}/{self.config.max_retries + 1})"
                            )
                            await asyncio.sleep(delay)
                            continue
                
                # 成功
                with self._lock:
                    self._stats["successful_retries"] += 1
                    self._stats["total_attempts"] += attempt + 1
                
                return RetryResult(
                    success=True,
                    attempts=attempt + 1,
                    total_time=time.time() - start_time,
                    last_error=None,
                    last_status_code=last_status_code,
                    delays=delays
                )
                
            except Exception as e:
                last_error = e
                
                # 检查是否应该重试
                if not self.should_retry(exception=e):
                    logger.error(f"遇到不可重试的错误：{e}")
                    break
                
                if attempt < self.config.max_retries:
                    delay = self.calculate_delay(attempt)
                    delays.append(delay)
                    logger.warning(
                        f"请求失败：{e}，{delay:.2f}秒后重试 "
                        f"(尝试 {attempt + 1}/{self.config.max_retries + 1})"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"达到最大重试次数：{e}")
        
        # 失败
        with self._lock:
            self._stats["failed_retries"] += 1
            self._stats["total_attempts"] += self.config.max_retries + 1
        
        return RetryResult(
            success=False,
            attempts=self.config.max_retries + 1,
            total_time=time.time() - start_time,
            last_error=last_error,
            last_status_code=last_status_code,
            delays=delays
        )
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        with self._lock:
            stats = self._stats.copy()
            if stats["total_attempts"] > 0:
                stats["success_rate"] = stats["successful_retries"] / stats["total_attempts"]
            else:
                stats["success_rate"] = 0
            return stats
    
    def reset_stats(self):
        """重置统计信息"""
        with self._lock:
            self._stats = {
                "total_retries": 0,
                "successful_retries": 0,
                "failed_retries": 0,
                "total_attempts": 0,
            }


class CircuitBreakerError(Exception):
    """熔断器错误"""
    pass


class CircuitBreaker:
    """熔断器（防止雪崩）"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout: float = 60.0,
        half_open_max_calls: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout = timeout
        self.half_open_max_calls = half_open_max_calls
        
        self._failure_count = 0
        self._success_count = 0
        self._state = "closed"  # closed, open, half-open
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0
        self._lock = threading.RLock()
    
    @property
    def state(self) -> str:
        """获取当前状态"""
        with self._lock:
            if self._state == "open":
                # 检查是否应该切换到 half-open
                if self._last_failure_time and \
                   (time.time() - self._last_failure_time) > self.timeout:
                    self._state = "half-open"
                    self._half_open_calls = 0
            return self._state
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        通过熔断器调用函数
        
        Args:
            func: 要执行的函数
            
        Returns:
            函数执行结果
            
        Raises:
            CircuitBreakerError: 熔断器打开时抛出
        """
        current_state = self.state
        
        if current_state == "open":
            raise CircuitBreakerError(
                f"熔断器已打开，拒绝执行。失败计数：{self._failure_count}"
            )
        
        if current_state == "half-open":
            with self._lock:
                self._half_open_calls += 1
                if self._half_open_calls > self.half_open_max_calls:
                    raise CircuitBreakerError(
                        f"半开状态达到最大调用次数：{self.half_open_max_calls}"
                    )
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        """成功回调"""
        with self._lock:
            if self._state == "half-open":
                self._success_count += 1
                if self._success_count >= self.success_threshold:
                    self._state = "closed"
                    self._failure_count = 0
                    self._success_count = 0
            elif self._state == "closed":
                self._failure_count = 0
    
    def _on_failure(self):
        """失败回调"""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            
            if self._state == "half-open":
                self._state = "open"
                self._success_count = 0
            elif self._state == "closed":
                if self._failure_count >= self.failure_threshold:
                    self._state = "open"
    
    def reset(self):
        """重置熔断器"""
        with self._lock:
            self._state = "closed"
            self._failure_count = 0
            self._success_count = 0
            self._half_open_calls = 0
            self._last_failure_time = None
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        with self._lock:
            return {
                "state": self._state,
                "failure_count": self._failure_count,
                "success_count": self._success_count,
                "half_open_calls": self._half_open_calls,
                "last_failure_time": self._last_failure_time,
            }


# 使用示例
if __name__ == "__main__":
    import requests
    
    # 配置重试
    config = RetryConfig(
        max_retries=3,
        strategy=RetryStrategy.EXPONENTIAL_JITTER,
        base_delay=1.0,
    )
    
    handler = RetryHandler(config)
    
    # 示例：带重试的 HTTP 请求
    def make_request(url: str) -> requests.Response:
        return requests.get(url, timeout=10)
    
    # 执行
    result = handler.execute_with_retry(make_request, "https://httpbin.org/status/500")
    
    print(f"成功：{result.success}")
    print(f"尝试次数：{result.attempts}")
    print(f"总耗时：{result.total_time:.2f}秒")
    print(f"延迟列表：{result.delays}")
    print(f"统计信息：{handler.get_stats()}")
    
    # 熔断器示例
    breaker = CircuitBreaker(failure_threshold=3, timeout=10)
    
    try:
        breaker.call(make_request, "https://httpbin.org/status/500")
    except CircuitBreakerError as e:
        print(f"熔断器触发：{e}")
    
    print(f"熔断器状态：{breaker.get_stats()}")
