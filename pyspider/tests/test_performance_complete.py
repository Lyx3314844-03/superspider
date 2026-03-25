"""
PySpider 性能模块完整测试

测试覆盖率目标：>95%
"""

import pytest
import time
import asyncio
from unittest.mock import patch, MagicMock

from pyspider.performance.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    CircuitBreakerOpen,
)
from pyspider.performance.limiter import (
    RateLimiter,
    ContentFingerprinter,
)
from pyspider.core.spider_async_v3 import (
    TokenBucket,
)


class TestCircuitBreaker:
    """熔断器测试"""
    
    def test_initial_state(self):
        """测试初始状态"""
        cb = CircuitBreaker(failure_threshold=5, success_threshold=3, timeout=60)
        
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
        assert cb.success_count == 0
    
    def test_allow_request_closed(self):
        """测试关闭状态允许请求"""
        cb = CircuitBreaker()
        
        assert cb.allow_request() is True
    
    def test_allow_request_open(self):
        """测试打开状态拒绝请求"""
        cb = CircuitBreaker(failure_threshold=1, timeout=60)
        
        # 触发熔断
        cb.record_failure()
        
        assert cb.state == CircuitState.OPEN
        assert cb.allow_request() is False
    
    def test_allow_request_half_open(self):
        """测试半开状态允许请求"""
        cb = CircuitBreaker(failure_threshold=1, timeout=1)
        
        # 触发熔断
        cb.record_failure()
        
        # 等待超时
        time.sleep(1.5)
        
        assert cb.state == CircuitState.HALF_OPEN
        assert cb.allow_request() is True
    
    def test_record_success_closed(self):
        """测试关闭状态记录成功"""
        cb = CircuitBreaker()
        
        cb.record_success()
        
        assert cb.failure_count == 0
    
    def test_record_success_half_open(self):
        """测试半开状态记录成功"""
        cb = CircuitBreaker(failure_threshold=1, success_threshold=2, timeout=1)
        
        # 触发熔断
        cb.record_failure()
        time.sleep(1.5)
        
        # 记录成功
        cb.record_success()
        assert cb.state == CircuitState.HALF_OPEN
        
        cb.record_success()
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
        assert cb.success_count == 0
    
    def test_record_failure_closed(self):
        """测试关闭状态记录失败"""
        cb = CircuitBreaker(failure_threshold=3)
        
        cb.record_failure()
        assert cb.failure_count == 1
        assert cb.state == CircuitState.CLOSED
        
        cb.record_failure()
        assert cb.failure_count == 2
        assert cb.state == CircuitState.CLOSED
        
        cb.record_failure()
        assert cb.failure_count == 3
        assert cb.state == CircuitState.OPEN
    
    def test_record_failure_half_open(self):
        """测试半开状态记录失败"""
        cb = CircuitBreaker(failure_threshold=1, success_threshold=1, timeout=1)
        
        # 触发熔断
        cb.record_failure()
        time.sleep(1.5)
        
        # 记录失败
        cb.record_failure()
        
        assert cb.state == CircuitState.OPEN
        assert cb.success_count == 0
    
    def test_reset(self):
        """测试重置"""
        cb = CircuitBreaker(failure_threshold=1, timeout=60)
        
        # 触发熔断
        cb.record_failure()
        
        # 重置
        cb.reset()
        
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
        assert cb.success_count == 0
    
    def test_get_stats(self):
        """测试获取统计"""
        cb = CircuitBreaker(name="test")
        
        cb.record_failure()
        cb.record_failure()
        
        stats = cb.get_stats()
        
        assert stats['name'] == "test"
        assert stats['state'] == "closed"
        assert stats['failure_count'] == 2
    
    def test_concurrent_access(self):
        """测试并发访问"""
        import threading
        
        cb = CircuitBreaker(failure_threshold=100)
        results = []
        
        def record():
            for _ in range(10):
                cb.record_success()
                results.append(cb.state)
        
        threads = [threading.Thread(target=record) for _ in range(5)]
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        assert len(results) == 50
        assert all(s == CircuitState.CLOSED for s in results)
    
    def test_timeout_transition(self):
        """测试超时转换"""
        cb = CircuitBreaker(failure_threshold=1, timeout=1)
        
        # 触发熔断
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        
        # 等待超时
        time.sleep(1.5)
        
        # 应该转换到半开
        assert cb.allow_request() is True
        assert cb.state == CircuitState.HALF_OPEN
    
    def test_custom_thresholds(self):
        """测试自定义阈值"""
        cb = CircuitBreaker(failure_threshold=10, success_threshold=5, timeout=120)
        
        assert cb.failure_threshold == 10
        assert cb.success_threshold == 5
        assert cb.timeout == 120


class TestRateLimiter:
    """速率限制器测试"""
    
    def test_initial_state(self):
        """测试初始状态"""
        limiter = RateLimiter(rate=100.0)
        
        assert limiter.rate == 100.0
        assert limiter.tokens == 100.0
    
    def test_acquire_token(self):
        """测试获取令牌"""
        limiter = RateLimiter(rate=100.0)
        
        limiter.acquire()
        
        assert limiter.tokens < 100.0
    
    def test_rate_limiting(self):
        """测试速率限制"""
        limiter = RateLimiter(rate=10.0)  # 10 请求/秒
        
        # 快速消耗令牌
        for _ in range(10):
            limiter.acquire()
        
        # 第 11 次应该需要等待
        start = time.monotonic()
        limiter.acquire()
        elapsed = time.monotonic() - start
        
        assert elapsed > 0.05  # 至少等待 50ms
    
    def test_token_refill(self):
        """测试令牌补充"""
        limiter = RateLimiter(rate=100.0)
        
        # 消耗令牌
        for _ in range(50):
            limiter.acquire()
        
        initial_tokens = limiter.tokens
        
        # 等待补充
        time.sleep(0.5)
        
        limiter._refill()
        
        assert limiter.tokens > initial_tokens
    
    def test_max_capacity(self):
        """测试最大容量"""
        limiter = RateLimiter(rate=100.0)
        
        # 等待补充
        time.sleep(0.5)
        
        limiter._refill()
        
        assert limiter.tokens <= limiter.capacity


class TestTokenBucket:
    """令牌桶测试"""
    
    def test_initial_state(self):
        """测试初始状态"""
        bucket = TokenBucket(capacity=100, refill_rate=10)
        
        assert bucket.capacity == 100
        assert bucket.refill_rate == 10
        assert bucket.tokens == 100
    
    def test_consume(self):
        """测试消费"""
        bucket = TokenBucket(capacity=100, refill_rate=10)
        
        assert bucket.consume(10) is True
        assert bucket.tokens == 90
    
    def test_consume_insufficient(self):
        """测试令牌不足"""
        bucket = TokenBucket(capacity=100, refill_rate=10)
        
        # 消耗所有令牌
        bucket.consume(100)
        
        # 应该失败
        assert bucket.consume(10) is False
    
    def test_wait_for_tokens(self):
        """测试等待令牌"""
        bucket = TokenBucket(capacity=100, refill_rate=100)
        
        # 消耗所有令牌
        bucket.consume(100)
        
        # 等待补充
        time.sleep(0.5)
        
        # 现在应该有足够的令牌
        assert bucket.consume(50) is True


class TestContentFingerprinter:
    """内容指纹测试"""
    
    def test_fingerprint_generation(self):
        """测试指纹生成"""
        fingerprinter = ContentFingerprinter()
        
        content = "test content"
        fp1 = fingerprinter.generate(content)
        fp2 = fingerprinter.generate(content)
        
        assert fp1 == fp2
    
    def test_different_content(self):
        """测试不同内容"""
        fingerprinter = ContentFingerprinter()
        
        fp1 = fingerprinter.generate("content 1")
        fp2 = fingerprinter.generate("content 2")
        
        assert fp1 != fp2
    
    def test_is_duplicate(self):
        """测试重复检测"""
        fingerprinter = ContentFingerprinter()
        
        content = "test content"
        
        # 第一次不是重复
        assert fingerprinter.is_duplicate(content) is False
        
        # 第二次是重复
        assert fingerprinter.is_duplicate(content) is True
    
    def test_clear(self):
        """测试清除"""
        fingerprinter = ContentFingerprinter()
        
        content = "test content"
        fingerprinter.generate(content)
        
        fingerprinter.clear()
        
        assert fingerprinter.is_duplicate(content) is False
    
    def test_similar_content(self):
        """测试相似内容"""
        fingerprinter = ContentFingerprinter()
        
        content1 = "This is a test content with some words"
        content2 = "This is a test content with different words"
        
        fp1 = fingerprinter.generate(content1)
        fp2 = fingerprinter.generate(content2)
        
        # 相似内容可能有不同的指纹
        assert fp1 != fp2
    
    def test_empty_content(self):
        """测试空内容"""
        fingerprinter = ContentFingerprinter()
        
        fp = fingerprinter.generate("")
        
        assert fp is not None
    
    def test_large_content(self):
        """测试大内容"""
        fingerprinter = ContentFingerprinter()
        
        content = "a" * 1000000  # 1MB
        
        fp = fingerprinter.generate(content)
        
        assert fp is not None
        assert len(fp) == 32  # MD5 指纹长度
    
    def test_unicode_content(self):
        """测试 Unicode 内容"""
        fingerprinter = ContentFingerprinter()
        
        content = "中文测试 日本語テスト 한국어 테스트"
        
        fp = fingerprinter.generate(content)
        
        assert fp is not None
    
    def test_concurrent_fingerprinting(self):
        """测试并发指纹生成"""
        import threading
        
        fingerprinter = ContentFingerprinter()
        results = []
        
        def generate():
            for i in range(10):
                fp = fingerprinter.generate(f"content {i}")
                results.append(fp)
        
        threads = [threading.Thread(target=generate) for _ in range(5)]
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        assert len(results) == 50
        assert len(set(results)) == 50  # 所有指纹都不同


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short', '--cov=pyspider.performance', '--cov-report=term-missing'])
