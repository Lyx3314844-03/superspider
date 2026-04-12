"""
性能优化模块
包含速率限制、熔断器、连接池等
"""

import time
import threading
from typing import Dict, Optional
from datetime import datetime


class RateLimiter:
    """速率限制器（令牌桶算法）"""

    def __init__(self, rate: int, interval: float = 1.0):
        """
        Args:
            rate: 每秒请求数
            interval: 时间间隔（秒）
        """
        self.rate = rate
        self.interval = interval
        self.capacity = float(rate)
        self.tokens = float(rate)
        self.last_refill = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self):
        """获取令牌"""
        while True:
            with self._lock:
                self._refill()
                if self.tokens >= 1:
                    self.tokens -= 1
                    return
                wait_time = max((1 - self.tokens) / float(self.rate or 1), 0.01)
            time.sleep(wait_time)

    def wait(self):
        """兼容旧接口"""
        self.acquire()

    def _refill(self):
        """补充令牌"""
        now = time.monotonic()
        elapsed = now - self.last_refill
        tokens_to_add = elapsed * (float(self.rate) / float(self.interval or 1))
        if tokens_to_add > 0:
            self.tokens = min(self.capacity, self.tokens + tokens_to_add)
            self.last_refill = now


class TokenBucket:
    """通用令牌桶，替代旧的 spider_async_v3 实现。"""

    def __init__(
        self,
        rate: Optional[float] = None,
        capacity: Optional[float] = None,
        refill_rate: Optional[float] = None,
    ):
        resolved_refill_rate = (
            refill_rate
            if refill_rate is not None
            else (rate if rate is not None else 1.0)
        )
        resolved_capacity = capacity if capacity is not None else resolved_refill_rate

        self.capacity = float(resolved_capacity)
        self.refill_rate = float(resolved_refill_rate)
        self.rate = self.refill_rate
        self.tokens = float(resolved_capacity)
        self.last_update = time.monotonic()
        self._lock = threading.Lock()

    def _refill(self):
        now = time.monotonic()
        elapsed = now - self.last_update
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_update = now

    def consume(self, amount: float = 1) -> bool:
        with self._lock:
            self._refill()
            if self.tokens >= amount:
                self.tokens -= amount
                return True
            return False


class CircuitBreaker:
    """熔断器"""

    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 3,
        timeout: float = 60.0,
    ):
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout = timeout

        self.failures = 0
        self.successes = 0
        self.state = "closed"  # closed, open, half-open
        self.last_failure: Optional[datetime] = None
        self._lock = threading.Lock()

    def allow(self) -> bool:
        """检查是否允许请求"""
        with self._lock:
            if self.state == "open":
                if (
                    self.last_failure
                    and (datetime.now() - self.last_failure).total_seconds()
                    > self.timeout
                ):
                    self.state = "half-open"
                    return True
                return False
            return True

    def record_success(self):
        """记录成功"""
        with self._lock:
            if self.state == "half-open":
                self.successes += 1
                if self.successes >= self.success_threshold:
                    self.state = "closed"
                    self.failures = 0
                    self.successes = 0
            elif self.state == "closed":
                self.failures = 0

    def record_failure(self):
        """记录失败"""
        with self._lock:
            self.failures += 1
            self.last_failure = datetime.now()

            if self.state == "half-open" or self.failures >= self.failure_threshold:
                self.state = "open"
                self.successes = 0

    def get_state(self) -> str:
        """获取状态"""
        with self._lock:
            return self.state


class ConnectionPool:
    """连接池"""

    def __init__(self, max_connections: int = 100):
        self.max_connections = max_connections
        self.current = 0
        self._lock = threading.Lock()
        self._available = threading.Semaphore(max_connections)

    def acquire(self):
        """获取连接"""
        self._available.acquire()
        with self._lock:
            self.current += 1

    def release(self):
        """释放连接"""
        with self._lock:
            self.current -= 1
        self._available.release()

    def stats(self) -> Dict:
        """获取统计"""
        with self._lock:
            return {
                "current": self.current,
                "max": self.max_connections,
                "available": self.max_connections - self.current,
            }


class AdaptiveRateLimiter:
    """自适应速率限制器（类似 Scrapy AutoThrottle）"""

    def __init__(
        self,
        initial_delay: float = 1.0,
        min_delay: float = 0.1,
        max_delay: float = 60.0,
        target_response_time: float = 2.0,
    ):
        self.initial_delay = initial_delay
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.target_response_time = target_response_time

        self.domain_delays: Dict[str, float] = {}
        self.domain_last_request: Dict[str, float] = {}
        self._lock = threading.Lock()

    def wait(self, url: str):
        """等待"""
        domain = self._extract_domain(url)

        with self._lock:
            delay = self.domain_delays.get(domain, self.initial_delay)
            last_request = self.domain_last_request.get(domain, 0)

            # 等待域延迟
            elapsed = time.time() - last_request
            if elapsed < delay:
                time.sleep(delay - elapsed)

            self.domain_last_request[domain] = time.time()

    def adjust(self, url: str, response_time: float, status_code: int):
        """调整延迟"""
        domain = self._extract_domain(url)

        with self._lock:
            current_delay = self.domain_delays.get(domain, self.initial_delay)
            new_delay = current_delay

            # 根据响应时间调整
            if response_time < self.target_response_time:
                new_delay = current_delay * 0.9
            elif response_time > self.target_response_time * 2:
                new_delay = current_delay * 1.5

            # 根据状态码调整
            if status_code in (429, 503):
                new_delay = current_delay * 2.0
            elif status_code >= 500:
                new_delay = current_delay * 1.2

            # 应用限制
            new_delay = max(self.min_delay, min(self.max_delay, new_delay))

            if abs(new_delay - current_delay) > 0.1:
                self.domain_delays[domain] = new_delay

    def _extract_domain(self, url: str) -> str:
        """提取域名"""
        from urllib.parse import urlparse

        parsed = urlparse(url)
        return parsed.netloc


class ContentFingerprinter:
    """内容指纹（去重）"""

    def __init__(self):
        self.seen_hashes = set()
        self._lock = threading.Lock()

    def generate(self, content: str) -> str:
        import hashlib

        return hashlib.md5(content.encode()).hexdigest()

    def is_duplicate(self, content: str) -> bool:
        """检查是否重复"""
        fingerprint = self.generate(content)

        with self._lock:
            if fingerprint in self.seen_hashes:
                return True
            self.seen_hashes.add(fingerprint)
            return False

    def clear(self):
        """清空"""
        with self._lock:
            self.seen_hashes.clear()
