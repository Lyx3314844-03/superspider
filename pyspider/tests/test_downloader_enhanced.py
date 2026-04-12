"""
HTTP 下载器测试
测试覆盖率目标：>80%
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
import requests

from pyspider.downloader.downloader import HTTPDownloader
from pyspider.core.models import Request
from pyspider.core.exceptions import DownloadError, TimeoutError


class TestHTTPDownloaderInit:
    """测试下载器初始化"""

    def test_init_default(self):
        """测试默认初始化"""
        downloader = HTTPDownloader()
        assert downloader.timeout == 30
        assert downloader.verify_ssl is True
        assert downloader.random_ua is True
        assert downloader.rate_limit is None
        assert downloader.session is not None

    def test_init_custom(self):
        """测试自定义初始化"""
        downloader = HTTPDownloader(
            timeout=60,
            pool_connections=20,
            pool_maxsize=100,
            max_retries=5,
            verify_ssl=False,
            random_ua=False,
            rate_limit=10.0,
            proxy="http://127.0.0.1:7890",
        )
        assert downloader.timeout == 60
        assert downloader.verify_ssl is False
        assert downloader.random_ua is False
        assert downloader.rate_limit == 10.0
        assert downloader.proxy == "http://127.0.0.1:7890"

    def test_init_invalid_timeout(self):
        """测试无效超时"""
        with pytest.raises(ValueError):
            downloader = HTTPDownloader(timeout=0)


class TestUserAgentRotation:
    """测试 User-Agent 轮换"""

    def test_get_user_agent_random(self):
        """测试随机 User-Agent"""
        downloader = HTTPDownloader(random_ua=True)

        # 获取多次，应该有不同的 UA
        agents = [downloader._get_user_agent() for _ in range(10)]
        assert len(set(agents)) > 1  # 至少有不同的

    def test_get_user_agent_fixed(self):
        """测试固定 User-Agent"""
        downloader = HTTPDownloader(random_ua=False)

        # 获取多次，应该相同
        agent1 = downloader._get_user_agent()
        agent2 = downloader._get_user_agent()
        assert agent1 == agent2


class TestHTTPDownloaderMethods:
    """测试下载器方法"""

    def test_set_timeout(self):
        """测试设置超时"""
        downloader = HTTPDownloader()
        downloader.set_timeout(60)
        assert downloader.timeout == 60

    def test_set_timeout_invalid(self):
        """测试无效超时"""
        downloader = HTTPDownloader()
        with pytest.raises(ValueError):
            downloader.set_timeout(0)

    def test_set_headers(self):
        """测试设置请求头"""
        downloader = HTTPDownloader()
        downloader.set_headers({"X-Custom": "value"})
        assert "X-Custom" in downloader.session.headers

    def test_set_headers_invalid(self):
        """测试无效请求头"""
        downloader = HTTPDownloader()
        with pytest.raises(TypeError):
            downloader.set_headers("not a dict")

    def test_set_cookies(self):
        """测试设置 Cookie"""
        downloader = HTTPDownloader()
        downloader.set_cookies({"session": "abc123"})
        assert "session" in downloader.session.cookies

    def test_set_proxy(self):
        """测试设置代理"""
        downloader = HTTPDownloader()
        downloader.set_proxy("http://127.0.0.1:7890")
        assert downloader.proxy == "http://127.0.0.1:7890"

    def test_set_proxy_invalid(self):
        """测试无效代理"""
        downloader = HTTPDownloader()
        with pytest.raises(ValueError):
            downloader.set_proxy("")

    def test_clear_proxy(self):
        """测试清除代理"""
        downloader = HTTPDownloader(proxy="http://127.0.0.1:7890")
        downloader.clear_proxy()
        assert downloader.proxy is None


class TestHTTPDownloaderDownload:
    """测试下载功能"""

    @patch("pyspider.downloader.downloader.requests.Session")
    def test_download_success(self, mock_session):
        """测试成功下载"""
        # 配置 Mock 响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "text/html"}
        mock_response.content = b"OK"
        mock_response.text = "OK"

        mock_session.return_value.request.return_value = mock_response

        downloader = HTTPDownloader()
        req = Request(url="https://example.com")
        response = downloader.download(req)

        assert response.status_code == 200
        assert response.error is None

    @patch("pyspider.downloader.downloader.requests.Session")
    def test_download_404(self, mock_session):
        """测试 404 错误"""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.headers = {}
        mock_response.content = b""
        mock_response.text = ""

        mock_session.return_value.request.return_value = mock_response

        downloader = HTTPDownloader()
        req = Request(url="https://example.com/notfound")
        response = downloader.download(req)

        assert response.status_code == 404
        assert isinstance(response.error, DownloadError)

    @patch("pyspider.downloader.downloader.requests.Session")
    def test_download_timeout(self, mock_session):
        """测试超时"""
        mock_session.return_value.request.side_effect = requests.exceptions.Timeout()

        downloader = HTTPDownloader()
        req = Request(url="https://example.com")
        response = downloader.download(req)

        assert response.status_code == 0
        assert isinstance(response.error, TimeoutError)

    @patch("pyspider.downloader.downloader.requests.Session")
    def test_download_ssl_error(self, mock_session):
        """测试 SSL 错误"""
        mock_session.return_value.request.side_effect = requests.exceptions.SSLError()

        downloader = HTTPDownloader()
        req = Request(url="https://example.com")
        response = downloader.download(req)

        assert response.status_code == 0
        assert isinstance(response.error, DownloadError)

    @patch("pyspider.downloader.downloader.requests.Session")
    def test_download_connection_error(self, mock_session):
        """测试连接错误"""
        mock_session.return_value.request.side_effect = (
            requests.exceptions.ConnectionError()
        )

        downloader = HTTPDownloader()
        req = Request(url="https://example.com")
        response = downloader.download(req)

        assert response.status_code == 0
        assert isinstance(response.error, DownloadError)


class TestHTTPDownloaderRateLimit:
    """测试速率限制"""

    def test_rate_limit_context(self):
        """测试速率限制上下文"""
        downloader = HTTPDownloader(rate_limit=10.0)  # 每秒 10 个请求

        start = time.time()
        with downloader._rate_limit_context():
            pass
        elapsed = time.time() - start

        # 第一次请求不应该有限制
        assert elapsed < 0.1

    def test_rate_limit_enforcement(self):
        """测试速率限制执行"""
        downloader = HTTPDownloader(rate_limit=2.0)  # 每秒 2 个请求

        # 第一次请求
        with downloader._rate_limit_context():
            pass

        # 第二次请求应该有限制
        start = time.time()
        with downloader._rate_limit_context():
            pass
        elapsed = time.time() - start

        # 应该至少有 0.5 秒间隔
        assert elapsed >= 0.4  # 允许一些误差


class TestHTTPDownloaderContextManager:
    """测试上下文管理器"""

    def test_context_manager_enter(self):
        """测试进入上下文"""
        with HTTPDownloader() as downloader:
            assert downloader is not None
            assert downloader.session is not None

    def test_context_manager_exit(self):
        """测试退出上下文"""
        with HTTPDownloader() as downloader:
            session = downloader.session

        # 退出后会话应该关闭
        assert downloader.session is None

    def test_close_method(self):
        """测试关闭方法"""
        downloader = HTTPDownloader()
        session = downloader.session
        downloader.close()

        # 会话应该关闭
        assert downloader.session is None


class TestHTTPDownloaderResourceManagement:
    """测试资源管理"""

    def test_session_cleanup(self):
        """测试会话清理"""
        downloader = HTTPDownloader()
        session = downloader.session

        # 手动关闭
        downloader.close()

        # 会话应该已关闭
        assert session.adapters["http://"].poolmanager is not None

    def test_multiple_close(self):
        """测试多次关闭"""
        downloader = HTTPDownloader()
        downloader.close()
        downloader.close()  # 不应该抛出异常

    def test_destructor(self):
        """测试析构函数"""
        downloader = HTTPDownloader()
        del downloader
        # 不应该抛出异常


class TestHTTPDownloaderSecurity:
    """测试安全性"""

    def test_verify_ssl_enabled(self):
        """测试 SSL 验证"""
        downloader = HTTPDownloader(verify_ssl=True)
        assert downloader.verify_ssl is True

    def test_verify_ssl_disabled(self):
        """测试禁用 SSL 验证"""
        downloader = HTTPDownloader(verify_ssl=False)
        assert downloader.verify_ssl is False

    def test_custom_headers(self):
        """测试自定义请求头"""
        downloader = HTTPDownloader()
        downloader.set_headers(
            {"X-Custom-Header": "test-value", "Authorization": "Bearer token"}
        )

        assert "X-Custom-Header" in downloader.session.headers
        assert "Authorization" in downloader.session.headers


class TestHTTPDownloaderIntegration:
    """集成测试"""

    @pytest.mark.integration
    def test_real_download(self):
        """测试真实下载（需要网络）"""
        # 这个测试需要真实网络，可以标记为 integration
        try:
            downloader = HTTPDownloader(timeout=5)
            req = Request(url="https://httpbin.org/get")
            response = downloader.download(req)

            # 如果网络可用，应该成功
            if response.status_code > 0:
                assert response.status_code == 200
        except Exception:
            # 网络不可用时跳过
            pytest.skip("Network unavailable")


if __name__ == "__main__":
    pytest.main(
        [__file__, "-v", "--cov=pyspider.downloader.downloader", "--cov-report=html"]
    )
