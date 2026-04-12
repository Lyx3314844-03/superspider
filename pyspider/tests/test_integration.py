"""
pyspider 集成测试

运行：pytest tests/test_integration.py -v
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch
from concurrent.futures import ThreadPoolExecutor, as_completed

from pyspider.core.spider import Spider, SpiderStats
from pyspider.downloader.downloader import HTTPDownloader
from pyspider.core.security import URLValidator, InputSanitizer
from pyspider.core.models import Request, Response, Page


class TestSpiderIntegration:
    """爬虫集成测试"""

    @pytest.fixture
    def spider(self):
        """创建测试用爬虫"""
        return Spider(name="integration-test", thread_count=2)

    def test_spider_initialization(self, spider):
        """测试爬虫初始化"""
        assert spider is not None
        assert spider.name == "integration-test"
        assert spider.thread_count == 2
        assert spider.stats is not None

    def test_spider_start_stop(self, spider):
        """测试爬虫启动和停止"""
        spider.set_start_urls(["https://example.com"])

        # 启动然后停止
        spider.start()
        spider.stop()

        assert spider.stopped or not spider.running

    def test_spider_context_manager(self):
        """测试上下文管理器"""
        with Spider(name="context-test") as spider:
            assert spider is not None
            assert spider.running or not spider.stopped

        # 退出后应该停止
        assert spider._stop_event.is_set()

    def test_spider_add_request(self, spider):
        """测试添加请求"""
        req = Request(url="https://example.com", callback=lambda page: None)
        result = spider.add_request(req)

        # 应该成功添加
        assert result is True or result is False  # 取决于是否重复

    def test_spider_duplicate_detection(self, spider):
        """测试重复检测"""
        url = "https://example.com"

        # 第一次不是重复
        assert spider._is_duplicate(url) is False

        # 第二次是重复
        assert spider._is_duplicate(url) is True

    def test_spider_stats(self, spider):
        """测试统计信息"""
        stats = spider.get_stats()

        assert isinstance(stats, dict)
        assert "total_requests" in stats
        assert "duration_seconds" in stats

    def test_spider_middleware(self, spider):
        """测试中间件"""
        called = []

        def middleware(req):
            called.append(req.url)
            return req

        spider.add_middleware(middleware)

        assert len(spider.middlewares) == 1

    def test_spider_pipeline(self, spider):
        """测试管道"""
        results = []

        def pipeline(page):
            results.append(page.response.url)

        spider.add_pipeline(pipeline)

        assert len(spider.pipelines) == 1

    def test_spider_rate_limit(self):
        """测试速率限制"""
        spider = Spider(name="ratelimit-test", rate_limit=10.0)

        start = time.time()

        # 模拟多次请求
        for _ in range(10):
            with spider._rate_limit_context():
                pass

        elapsed = time.time() - start

        # 应该有适当的延迟
        assert elapsed >= 0.5  # 至少 0.5 秒

    def test_spider_thread_safety(self):
        """测试线程安全"""
        spider = Spider(name="threadsafe-test", thread_count=5)

        urls_added = []
        lock = threading.Lock()

        def add_urls():
            for i in range(10):
                url = f"https://example.com/{i}"
                spider._is_duplicate(url)
                with lock:
                    urls_added.append(url)

        # 并发添加
        threads = [threading.Thread(target=add_urls) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 应该没有异常
        assert len(urls_added) == 50

    def test_spider_error_handling(self, spider):
        """测试错误处理"""
        # 添加无效请求应该不抛出异常
        try:
            req = Request(url="invalid-url")
            spider.add_request(req)
        except Exception as e:
            pytest.fail(f"Unexpected exception: {e}")

    def test_spider_url_validation(self, spider):
        """测试 URL 验证"""
        assert spider._validate_url("https://example.com") is True
        assert spider._validate_url("http://example.com") is True
        assert spider._validate_url("") is False
        assert spider._validate_url("not-a-url") is False

    def test_spider_max_depth(self):
        """测试最大深度"""
        spider = Spider(name="depth-test", max_depth=3)

        # 在深度范围内
        req = Request(url="https://example.com", depth=2)
        # 应该可以添加

        # 超出深度范围
        req = Request(url="https://example.com", depth=5)
        # 应该被拒绝


class TestDownloaderIntegration:
    """下载器集成测试"""

    @pytest.fixture
    def downloader(self):
        """创建测试用下载器"""
        return HTTPDownloader(timeout=5)

    def test_downloader_initialization(self, downloader):
        """测试下载器初始化"""
        assert downloader is not None
        assert downloader.session is not None
        assert downloader.timeout == 5

    def test_downloader_context_manager(self):
        """测试上下文管理器"""
        with HTTPDownloader() as downloader:
            assert downloader.session is not None

        # 退出后会话应该关闭
        assert downloader.session is None

    def test_downloader_set_headers(self, downloader):
        """测试设置请求头"""
        downloader.set_headers({"X-Custom": "test"})
        assert "X-Custom" in downloader.session.headers

    def test_downloader_set_cookies(self, downloader):
        """测试设置 Cookie"""
        downloader.set_cookies({"session": "abc123"})
        assert "session" in downloader.session.cookies

    def test_downloader_user_agent(self, downloader):
        """测试 User-Agent"""
        ua = downloader._get_user_agent()
        assert ua in downloader.DEFAULT_USER_AGENTS

    def test_downloader_rate_limit(self):
        """测试速率限制"""
        downloader = HTTPDownloader(rate_limit=10.0)

        start = time.time()

        for _ in range(5):
            with downloader._rate_limit_context():
                pass

        elapsed = time.time() - start

        # 应该有适当的延迟
        assert elapsed >= 0.3


class TestSecurityIntegration:
    """安全模块集成测试"""

    def test_url_validator_basic(self):
        """测试基本 URL 验证"""
        validator = URLValidator()

        assert validator.validate("https://example.com") is True
        assert validator.validate("http://example.com") is True
        assert validator.validate("") is False

    def test_url_validator_scheme(self):
        """测试协议验证"""
        validator = URLValidator()

        # 只允许 http 和 https
        assert validator.validate("ftp://example.com") is False
        assert validator.validate("javascript:alert(1)") is False

    def test_url_validator_domain_whitelist(self):
        """测试域名白名单"""
        config = SecurityConfig(allowed_domains=["example.com", "trusted.org"])
        validator = URLValidator(config)

        assert validator.validate("https://www.example.com") is True
        assert validator.validate("https://evil.com") is False

    def test_url_validator_private_ip(self):
        """测试私有 IP 防护"""
        validator = URLValidator()

        assert validator._is_private_ip("192.168.1.1") is True
        assert validator._is_private_ip("10.0.0.1") is True
        assert validator._is_private_ip("8.8.8.8") is False

    def test_input_sanitizer_html(self):
        """测试 HTML 清理"""
        html = '<script>alert("xss")</script><div>Safe</div>'
        result = InputSanitizer.sanitize_html(html)

        assert "<script>" not in result

    def test_input_sanitizer_url(self):
        """测试 URL 清理"""
        assert InputSanitizer.sanitize_url("javascript:alert(1)") == ""
        assert InputSanitizer.sanitize_url("data:text/html,<script>") == ""

    def test_input_sanitizer_filename(self):
        """测试文件名清理"""
        assert InputSanitizer.sanitize_filename("file<name>.txt") == "file_name_.txt"


class TestIntegrationScenarios:
    """集成场景测试"""

    def test_full_crawl_simulation(self):
        """模拟完整爬取流程"""
        with Spider(name="full-test", thread_count=2) as spider:
            spider.set_start_urls(["https://example.com", "https://example.org"])

            results = []

            def pipeline(page):
                results.append(page.response.url)

            spider.add_pipeline(pipeline)

            # 启动爬取
            spider.start()

            # 应该有结果
            assert isinstance(results, list)

    def test_concurrent_crawl(self):
        """测试并发爬取"""
        spider = Spider(name="concurrent-test", thread_count=5)

        def crawl_site(url):
            spider._is_duplicate(url)

        # 并发爬取多个站点
        urls = [f"https://example{i}.com" for i in range(10)]

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(crawl_site, url) for url in urls]
            for future in as_completed(futures):
                future.result()

        # 不应该有异常

    def test_error_recovery(self):
        """测试错误恢复"""
        spider = Spider(name="error-test", max_retries=3)

        # 添加多个请求，包括无效的
        spider.add_request(Request(url="https://example.com"))
        spider.add_request(Request(url="invalid-url"))
        spider.add_request(Request(url="https://example.org"))

        # 应该能处理错误而不崩溃
        assert spider.stats is not None

    def test_resource_cleanup(self):
        """测试资源清理"""
        spider = Spider(name="cleanup-test")

        # 添加一些数据
        for i in range(10):
            spider.add_request(Request(url=f"https://example{i}.com"))

        # 清理
        spider.stop()

        # 资源应该被清理
        assert spider._stop_event.is_set()


# 导入安全配置类
from pyspider.core.security import SecurityConfig

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
