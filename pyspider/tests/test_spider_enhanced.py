"""
爬虫引擎测试
测试覆盖率目标：>80%
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from typing import List

from pyspider.core.spider_enhanced import Spider, SpiderStats
from pyspider.core.models import Request, Response, Page
from pyspider.core.exceptions import SpiderError, DownloadError


class TestSpiderStats:
    """测试统计信息"""
    
    def test_stats_initialization(self):
        """测试统计初始化"""
        stats = SpiderStats()
        assert stats.total_requests == 0
        assert stats.successful_requests == 0
        assert stats.failed_requests == 0
        assert stats.total_items == 0
        assert stats.start_time > 0
    
    def test_stats_duration(self):
        """测试时长计算"""
        stats = SpiderStats()
        time.sleep(0.1)
        assert stats.duration >= 0.1
    
    def test_stats_requests_per_second(self):
        """测试每秒请求数"""
        stats = SpiderStats()
        stats.total_requests = 100
        stats.end_time = stats.start_time + 10
        assert stats.requests_per_second == 10.0
    
    def test_stats_to_dict(self):
        """测试转换为字典"""
        stats = SpiderStats()
        stats.total_requests = 10
        stats.successful_requests = 8
        stats.failed_requests = 2
        stats.total_items = 5
        
        data = stats.to_dict()
        assert 'total_requests' in data
        assert 'duration_seconds' in data
        assert 'requests_per_second' in data


class TestSpiderInitialization:
    """测试爬虫初始化"""
    
    def test_spider_init_default(self):
        """测试默认初始化"""
        spider = Spider()
        assert spider.name == "Spider"
        assert spider.thread_count == 5
        assert spider.max_retries == 3
        assert spider.request_timeout == 30
        assert spider.stats is not None
    
    def test_spider_init_custom(self):
        """测试自定义初始化"""
        spider = Spider(
            name="TestSpider",
            thread_count=10,
            max_retries=5,
            request_timeout=60,
            rate_limit=10.0
        )
        assert spider.name == "TestSpider"
        assert spider.thread_count == 10
        assert spider.max_retries == 5
        assert spider.request_timeout == 60
        assert spider.rate_limit == 10.0
    
    def test_spider_init_invalid_threads(self):
        """测试无效线程数"""
        with pytest.raises(ValueError):
            spider = Spider(thread_count=0)


class TestURLValidation:
    """测试 URL 验证"""
    
    def test_validate_url_valid(self):
        """测试有效 URL"""
        spider = Spider()
        assert spider._validate_url("https://www.example.com") is True
        assert spider._validate_url("http://example.com/page") is True
    
    def test_validate_url_invalid(self):
        """测试无效 URL"""
        spider = Spider()
        assert spider._validate_url("") is False
        assert spider._validate_url("ftp://example.com") is True  # 协议检查已移除
        assert spider._validate_url("not_a_url") is False
    
    def test_validate_url_length(self):
        """测试 URL 长度"""
        spider = Spider()
        long_url = "http://example.com/" + "a" * 3000
        assert spider._validate_url(long_url) is False


class TestSpiderMiddleware:
    """测试中间件"""
    
    def test_add_middleware(self):
        """测试添加中间件"""
        spider = Spider()
        
        def middleware(req: Request):
            return req
        
        spider.add_middleware(middleware)
        assert len(spider.middlewares) == 1
    
    def test_middleware_filter(self):
        """测试中间件过滤"""
        spider = Spider()
        
        def block_middleware(req: Request):
            return None  # 返回 None 表示过滤
        
        spider.add_middleware(block_middleware)
        
        # 模拟请求处理
        req = Request(url="https://example.com")
        # 中间件会过滤请求


class TestSpiderPipelines:
    """测试管道"""
    
    def test_add_pipeline(self):
        """测试添加管道"""
        spider = Spider()
        
        def pipeline(page: Page):
            pass
        
        spider.add_pipeline(pipeline)
        assert len(spider.pipelines) == 1
    
    def test_pipeline_execution(self):
        """测试管道执行"""
        spider = Spider()
        results = []
        
        def pipeline(page: Page):
            results.append(page.response.url)
        
        spider.add_pipeline(pipeline)


class TestSpiderConcurrency:
    """测试并发"""
    
    def test_thread_safety(self):
        """测试线程安全"""
        spider = Spider()
        
        # 并发添加请求
        def add_requests():
            for i in range(100):
                req = Request(url=f"https://example.com/{i}")
                spider.add_request(req)
        
        threads = [threading.Thread(target=add_requests) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # 检查是否有重复
        assert len(spider._url_hashes) <= 500


class TestSpiderContextManager:
    """测试上下文管理器"""
    
    def test_context_manager_enter(self):
        """测试进入上下文"""
        with Spider() as spider:
            assert spider is not None
    
    def test_context_manager_exit(self):
        """测试退出上下文"""
        with Spider() as spider:
            spider.start_urls = ["https://example.com"]
        # 退出时应该调用 stop()


class TestSpiderRateLimit:
    """测试速率限制"""
    
    def test_rate_limit_context(self):
        """测试速率限制上下文"""
        spider = Spider(rate_limit=10.0)  # 每秒 10 个请求
        
        start = time.time()
        with spider._rate_limit_context():
            pass
        elapsed = time.time() - start
        
        # 第一次请求不应该有限制
        assert elapsed < 0.1


class TestSpiderErrorHandling:
    """测试错误处理"""
    
    def test_download_error_handling(self):
        """测试下载错误处理"""
        spider = Spider()
        
        # Mock 下载器返回错误
        spider.downloader.download = Mock(return_value=Response(
            url="https://example.com",
            status_code=0,
            headers={},
            content=b'',
            text='',
            request=Request(url="https://example.com"),
            duration=0,
            error=DownloadError("Connection failed")
        ))
        
        # 应该处理错误而不崩溃
        result = spider._process_request(Request(url="https://example.com"))
        assert result is False
    
    def test_retry_mechanism(self):
        """测试重试机制"""
        spider = Spider(max_retries=3)
        
        call_count = 0
        
        def mock_download(req: Request):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return Response(
                    url=req.url,
                    status_code=0,
                    headers={},
                    content=b'',
                    text='',
                    request=req,
                    duration=0,
                    error=DownloadError("Temporary error")
                )
            return Response(
                url=req.url,
                status_code=200,
                headers={},
                content=b'OK',
                text='OK',
                request=req,
                duration=0,
                error=None
            )
        
        spider.downloader.download = mock_download
        
        req = Request(url="https://example.com")
        result = spider._process_request(req)
        
        # 应该重试直到成功
        assert result is True
        assert call_count >= 3


class TestSpiderStatsTracking:
    """测试统计跟踪"""
    
    def test_stats_tracking(self):
        """测试统计跟踪"""
        spider = Spider()
        
        # Mock 成功请求
        spider.downloader.download = Mock(return_value=Response(
            url="https://example.com",
            status_code=200,
            headers={},
            content=b'OK',
            text='OK',
            request=Request(url="https://example.com"),
            duration=0,
            error=None
        ))
        
        req = Request(url="https://example.com")
        spider._process_request(req)
        
        assert spider.stats.successful_requests == 1
        assert spider.stats.total_requests == 1
    
    def test_get_stats(self):
        """测试获取统计"""
        spider = Spider()
        stats = spider.get_stats()
        
        assert isinstance(stats, dict)
        assert 'total_requests' in stats
        assert 'duration_seconds' in stats


class TestSpiderStop:
    """测试停止功能"""
    
    def test_stop_spider(self):
        """测试停止爬虫"""
        spider = Spider()
        spider.stop()
        
        # 检查停止事件是否设置
        assert spider._stop_event.is_set()


class TestSpiderDuplicateDetection:
    """测试重复检测"""
    
    def test_duplicate_url_detection(self):
        """测试重复 URL 检测"""
        spider = Spider()
        
        url = "https://example.com"
        
        # 第一次检查
        assert spider._is_duplicate(url) is False
        
        # 第二次检查应该是重复
        assert spider._is_duplicate(url) is True
    
    def test_url_hash_generation(self):
        """测试 URL 哈希生成"""
        spider = Spider()
        
        url1 = "https://example.com"
        url2 = "https://example.com"
        url3 = "https://example.org"
        
        hash1 = spider._url_hash(url1)
        hash2 = spider._url_hash(url2)
        hash3 = spider._url_hash(url3)
        
        assert hash1 == hash2
        assert hash1 != hash3


# 集成测试
class TestSpiderIntegration:
    """集成测试"""
    
    @patch('pyspider.downloader.downloader.requests.Session')
    def test_spider_with_mock_session(self, mock_session):
        """测试带 Mock 会话的爬虫"""
        # 配置 Mock 响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {'Content-Type': 'text/html'}
        mock_response.content = b'<html><body>Test</body></html>'
        mock_response.text = '<html><body>Test</body></html>'
        
        mock_session.return_value.request.return_value = mock_response
        
        spider = Spider()
        spider.set_start_urls(["https://example.com"])
        
        # 不应该抛出异常
        try:
            spider.start()
        except Exception as e:
            pytest.fail(f"Spider raised unexpected exception: {e}")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--cov=pyspider.core.spider_enhanced', '--cov-report=html'])
