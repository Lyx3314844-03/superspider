"""
PySpider 熔断器实现
"""

import time
import threading
from enum import Enum
from typing import Optional


class CircuitState(Enum):
    CLOSED = "closed"  # 正常状态
    OPEN = "open"  # 熔断状态
    HALF_OPEN = "half_open"  # 半开状态


class CircuitBreaker:
    """
    熔断器实现

    使用示例:
        breaker = CircuitBreaker(failure_threshold=5, success_threshold=3, timeout=60)

        def make_request():
            if not breaker.allow_request():
                raise Exception("Circuit is open")
            try:
                result = do_something()
                breaker.record_success()
                return result
            except Exception as e:
                breaker.record_failure()
                raise
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 3,
        timeout: float = 60.0,
        name: Optional[str] = None,
    ):
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout = timeout
        self.name = name or "circuit_breaker"

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._lock = threading.Lock()

    @property
    def state(self) -> CircuitState:
        with self._lock:
            if self._state == CircuitState.OPEN and self._last_failure_time is not None:
                if time.time() - self._last_failure_time > self.timeout:
                    self._state = CircuitState.HALF_OPEN
                    self._success_count = 0
        return self._state

    @property
    def failure_count(self) -> int:
        return self._failure_count

    @property
    def success_count(self) -> int:
        return self._success_count

    def allow_request(self) -> bool:
        """检查是否允许请求通过"""
        with self._lock:
            if self._state == CircuitState.OPEN:
                # 检查是否超过超时时间
                if self._last_failure_time is None:
                    return True

                elapsed = time.time() - self._last_failure_time
                if elapsed > self.timeout:
                    # 转换为半开状态
                    self._state = CircuitState.HALF_OPEN
                    self._success_count = 0
                    return True
                return False

            return True

    def record_success(self):
        """记录成功请求"""
        with self._lock:
            if self._state == CircuitState.OPEN and self._last_failure_time is not None:
                if time.time() - self._last_failure_time > self.timeout:
                    self._state = CircuitState.HALF_OPEN
                    self._success_count = 0
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.success_threshold:
                    # 恢复到关闭状态
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._success_count = 0
            elif self._state == CircuitState.CLOSED:
                self._failure_count = 0

    def record_failure(self):
        """记录失败请求"""
        with self._lock:
            self._last_failure_time = time.time()

            if self._state == CircuitState.HALF_OPEN:
                # 回到熔断状态
                self._state = CircuitState.OPEN
                self._success_count = 0
            elif self._state == CircuitState.CLOSED:
                self._failure_count += 1
                if self._failure_count >= self.failure_threshold:
                    # 进入熔断状态
                    self._state = CircuitState.OPEN

    def reset(self):
        """重置熔断器"""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._last_failure_time = None

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "last_failure_time": self._last_failure_time,
        }

    def __repr__(self) -> str:
        return (
            f"CircuitBreaker(state={self._state.value}, failures={self._failure_count})"
        )


class CircuitBreakerOpen(Exception):
    """熔断器打开异常"""

    pass
