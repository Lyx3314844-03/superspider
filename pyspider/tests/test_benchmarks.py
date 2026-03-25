"""
pyspider 性能基准测试

运行：pytest tests/test_benchmarks.py --benchmark
"""

import pytest
import time
from unittest.mock import Mock, patch

from pyspider.core.spider_enhanced import Spider, SpiderStats
from pyspider.downloader.downloader_enhanced import HTTPDownloader
from pyspider.core.security import URLValidator, InputSanitizer


class TestSpiderBenchmarks:
    """爬虫性能基准测试"""
    
    @pytest.mark.benchmark
    def test_spider_initialization(self, benchmark):
        """测试爬虫初始化性能"""
        def create_spider():
            return Spider(name="bench", thread_count=5)
        
        result = benchmark(create_spider)
        assert result is not None
    
    @pytest.mark.benchmark
    def test_url_validation(self, benchmark):
        """测试 URL 验证性能"""
        validator = URLValidator()
        url = "https://www.example.com/page"
        
        result = benchmark(validator.validate, url)
        assert result is True
    
    @pytest.mark.benchmark
    def test_url_hash_generation(self, benchmark):
        """测试 URL 哈希生成性能"""
        spider = Spider()
        url = "https://www.example.com/page"
        
        result = benchmark(spider._url_hash, url)
        assert len(result) == 32
    
    @pytest.mark.benchmark
    def test_duplicate_detection(self, benchmark):
        """测试重复检测性能"""
        spider = Spider()
        url = "https://www.example.com"
        
        # 第一次不是重复
        benchmark(spider._is_duplicate, url)
        
        # 第二次是重复
        result = benchmark(spider._is_duplicate, url)
        assert result is True
    
    @pytest.mark.benchmark
    def test_stats_to_dict(self, benchmark):
        """测试统计转换性能"""
        stats = SpiderStats()
        stats.total_requests = 1000
        stats.successful_requests = 950
        stats.failed_requests = 50
        
        result = benchmark(stats.to_dict)
        assert 'total_requests' in result


class TestDownloaderBenchmarks:
    """下载器性能基准测试"""
    
    @pytest.mark.benchmark
    def test_downloader_creation(self, benchmark):
        """测试下载器创建性能"""
        def create_downloader():
            return HTTPDownloader()
        
        result = benchmark(create_downloader)
        assert result is not None
    
    @pytest.mark.benchmark
    def test_user_agent_rotation(self, benchmark):
        """测试 UA 轮换性能"""
        downloader = HTTPDownloader(random_ua=True)
        
        result = benchmark(downloader._get_user_agent)
        assert result in downloader.DEFAULT_USER_AGENTS
    
    @pytest.mark.benchmark
    def test_rate_limit_context(self, benchmark):
        """测试速率限制性能"""
        downloader = HTTPDownloader(rate_limit=100.0)
        
        @benchmark
        def check_rate_limit():
            with downloader._rate_limit_context():
                pass
        
        assert check_rate_limit is None
    
    @pytest.mark.benchmark
    def test_header_setting(self, benchmark):
        """测试设置请求头性能"""
        downloader = HTTPDownloader()
        
        @benchmark
        def set_headers():
            downloader.set_headers({'X-Test': 'value'})
        
        assert 'X-Test' in downloader.session.headers


class TestSecurityBenchmarks:
    """安全模块性能基准测试"""
    
    @pytest.mark.benchmark
    def test_url_validator_creation(self, benchmark):
        """测试 URL 验证器创建性能"""
        def create_validator():
            return URLValidator()
        
        result = benchmark(create_validator)
        assert result is not None
    
    @pytest.mark.benchmark
    def test_private_ip_check(self, benchmark):
        """测试私有 IP 检查性能"""
        validator = URLValidator()
        ip = "192.168.1.1"
        
        result = benchmark(validator._is_private_ip, ip)
        assert result is True
    
    @pytest.mark.benchmark
    def test_html_sanitization(self, benchmark):
        """测试 HTML 清理性能"""
        html = '<script>alert("xss")</script><div class="content">Safe content</div>'
        
        result = benchmark(InputSanitizer.sanitize_html, html)
        assert '<script>' not in result
    
    @pytest.mark.benchmark
    def test_url_sanitization(self, benchmark):
        """测试 URL 清理性能"""
        url = 'javascript:alert("xss")'
        
        result = benchmark(InputSanitizer.sanitize_url, url)
        assert result == ''
    
    @pytest.mark.benchmark
    def test_filename_sanitization(self, benchmark):
        """测试文件名清理性能"""
        filename = 'file<name>:"/\\|？*.txt'
        
        result = benchmark(InputSanitizer.sanitize_filename, filename)
        assert '<' not in result
        assert '>' not in result


class TestConcurrencyBenchmarks:
    """并发性能基准测试"""
    
    @pytest.mark.benchmark
    def test_thread_safe_url_check(self, benchmark):
        """测试线程安全 URL 检查"""
        import threading
        
        spider = Spider()
        urls = [f"https://example.com/{i}" for i in range(100)]
        
        def check_urls():
            for url in urls:
                spider._is_duplicate(url)
        
        threads = [threading.Thread(target=check_urls) for _ in range(5)]
        
        @benchmark
        def run_threads():
            for t in threads:
                t.start()
            for t in threads:
                t.join()
        
        assert run_threads is None


class TestObjectPoolBenchmarks:
    """对象池性能基准测试（针对 javaspider 风格）"""
    
    @pytest.mark.benchmark
    def test_set_operations(self, benchmark):
        """测试集合操作性能"""
        visited = set()
        
        @benchmark
        def add_and_check():
            for i in range(1000):
                url = f"https://example.com/{i}"
                url_hash = hash(url)
                if url_hash in visited:
                    pass
                visited.add(url_hash)
        
        assert len(visited) == 1000
    
    @pytest.mark.benchmark
    def test_queue_operations(self, benchmark):
        """测试队列操作性能"""
        import queue
        
        q = queue.PriorityQueue()
        
        @benchmark
        def push_pop():
            for i in range(100):
                q.put((i, f"item_{i}"))
            for _ in range(100):
                q.get()
        
        assert q.empty()


class TestMemoryBenchmarks:
    """内存使用基准测试"""
    
    @pytest.mark.benchmark
    def test_spider_memory_usage(self, benchmark):
        """测试爬虫内存使用"""
        import tracemalloc
        
        tracemalloc.start()
        
        spider = Spider(name="mem_test", thread_count=5)
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # 内存应该小于 50MB
        assert peak < 50 * 1024 * 1024
        
        benchmark.pedantic(
            lambda: Spider(name="bench", thread_count=5),
            iterations=10,
            rounds=3
        )
    
    @pytest.mark.benchmark
    def test_downloader_memory_usage(self, benchmark):
        """测试下载器内存使用"""
        import tracemalloc
        
        tracemalloc.start()
        
        downloader = HTTPDownloader()
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # 内存应该小于 10MB
        assert peak < 10 * 1024 * 1024
        
        benchmark.pedantic(
            lambda: HTTPDownloader(),
            iterations=10,
            rounds=3
        )


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--benchmark'])
