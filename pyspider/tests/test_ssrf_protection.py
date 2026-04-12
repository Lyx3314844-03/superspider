"""
PySpider SSRF 防护模块测试

测试覆盖率目标：>90%
"""

import pytest
from unittest.mock import patch, MagicMock
import socket

from pyspider.core.ssrf_protection import (
    SSRFProtection,
    SSRFAwareSession,
    is_safe_url,
    filter_safe_urls,
    get_url_info,
)


class TestSSRFProtection:
    """SSRF 防护测试类"""

    def test_safe_url_http(self):
        """测试安全的 HTTP URL"""
        assert SSRFProtection.is_safe_url("http://example.com") is True
        assert SSRFProtection.is_safe_url("http://www.example.com/path?query=1") is True

    def test_safe_url_https(self):
        """测试安全的 HTTPS URL"""
        assert SSRFProtection.is_safe_url("https://example.com") is True
        assert SSRFProtection.is_safe_url("https://www.google.com") is True

    def test_unsafe_url_protocol(self):
        """测试不安全的协议"""
        assert SSRFProtection.is_safe_url("ftp://example.com") is False
        assert SSRFProtection.is_safe_url("file:///etc/passwd") is False
        assert SSRFProtection.is_safe_url("gopher://example.com") is False

    def test_unsafe_url_private_ip_v4(self):
        """测试 IPv4 私有地址"""
        # Class A 私有
        assert SSRFProtection.is_safe_url("http://10.0.0.1") is False
        assert SSRFProtection.is_safe_url("http://10.255.255.255") is False

        # Class B 私有
        assert SSRFProtection.is_safe_url("http://172.16.0.1") is False
        assert SSRFProtection.is_safe_url("http://172.31.255.255") is False

        # Class C 私有
        assert SSRFProtection.is_safe_url("http://192.168.0.1") is False
        assert SSRFProtection.is_safe_url("http://192.168.255.255") is False

    def test_unsafe_url_localhost(self):
        """测试本地回环地址"""
        assert SSRFProtection.is_safe_url("http://127.0.0.1") is False
        assert SSRFProtection.is_safe_url("http://127.1.2.3") is False
        assert SSRFProtection.is_safe_url("http://localhost") is False

    def test_unsafe_url_link_local(self):
        """测试链路本地地址"""
        assert SSRFProtection.is_safe_url("http://169.254.0.1") is False
        assert SSRFProtection.is_safe_url("http://169.254.255.255") is False

    def test_unsafe_url_multicast(self):
        """测试组播地址"""
        assert SSRFProtection.is_safe_url("http://224.0.0.1") is False
        assert SSRFProtection.is_safe_url("http://239.255.255.255") is False

    def test_unsafe_url_metadata_endpoints(self):
        """测试云服务商元数据端点"""
        # AWS
        assert SSRFProtection.is_safe_url("http://169.254.169.254") is False
        # Azure
        assert SSRFProtection.is_safe_url("http://168.63.129.16") is False

    def test_unsafe_url_no_hostname(self):
        """测试缺少主机名的 URL"""
        assert SSRFProtection.is_safe_url("http://") is False
        assert SSRFProtection.is_safe_url("http:///path") is False

    def test_url_too_long(self):
        """测试过长的 URL"""
        long_url = "http://example.com/" + "a" * 2049
        assert SSRFProtection.is_safe_url(long_url) is False

    def test_url_dangerous_characters(self):
        """测试包含危险字符的 URL"""
        # 控制字符
        assert SSRFProtection.is_safe_url("http://example.com/\x00") is False
        # HTML 特殊字符
        assert SSRFProtection.is_safe_url("http://example.com/<script>") is False
        # 换行符 (日志注入)
        assert SSRFProtection.is_safe_url("http://example.com/\r\n") is False

    def test_filter_safe_urls(self):
        """测试批量过滤 URL"""
        urls = [
            "https://example.com",
            "http://10.0.0.1",  # 私有 IP
            "https://google.com",
            "ftp://example.com",  # 不支持的协议
            "http://192.168.1.1",  # 私有 IP
        ]

        safe_urls = SSRFProtection.filter_safe_urls(urls)
        assert len(safe_urls) == 2
        assert "https://example.com" in safe_urls
        assert "https://google.com" in safe_urls

    def test_validate_redirect_chain_safe(self):
        """测试安全的重定向链"""
        initial = "http://example.com"
        redirects = [
            "http://example.com/page1",
            "http://example.com/page2",
        ]

        assert SSRFProtection.validate_redirect_chain(initial, redirects) is True

    def test_validate_redirect_chain_unsafe(self):
        """测试不安全的重定向链"""
        initial = "http://example.com"
        redirects = [
            "http://10.0.0.1",  # 私有 IP
        ]

        assert SSRFProtection.validate_redirect_chain(initial, redirects) is False

    def test_validate_redirect_chain_too_many(self):
        """测试重定向次数过多"""
        initial = "http://example.com"
        redirects = ["http://example.com/{}".format(i) for i in range(10)]

        assert SSRFProtection.validate_redirect_chain(initial, redirects) is False

    def test_get_url_info(self):
        """测试获取 URL 信息"""
        info = SSRFProtection.get_url_info("https://example.com:8080/path?query=1")

        assert info["url"] == "https://example.com:8080/path?query=1"
        assert info["scheme"] == "https"
        assert info["hostname"] == "example.com"
        assert info["port"] == 8080
        assert info["path"] == "/path?query=1"
        assert "ip_addresses" in info

    def test_get_url_info_error(self):
        """测试获取 URL 信息失败"""
        info = SSRFProtection.get_url_info("invalid-url")

        assert "error" in info or info["is_safe"] is False

    def test_lru_cache(self):
        """测试 LRU 缓存"""
        # 第一次调用会解析 DNS
        result1 = SSRFProtection.is_safe_url("https://example.com")

        # 第二次调用应该使用缓存
        result2 = SSRFProtection.is_safe_url("https://example.com")

        assert result1 == result2

    @patch("socket.getaddrinfo")
    def test_dns_resolution_failure(self, mock_getaddrinfo):
        """测试 DNS 解析失败"""
        mock_getaddrinfo.side_effect = socket.gaierror("DNS resolution failed")

        assert SSRFProtection.is_safe_url("http://nonexistent.invalid") is False

    @patch("socket.getaddrinfo")
    def test_mixed_ip_addresses(self, mock_getaddrinfo):
        """测试混合 IP 地址（包含安全和不安全）"""
        # 模拟返回多个 IP，其中一个不安全
        mock_getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 0)),  # 安全
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.1", 0)),  # 不安全
        ]

        assert SSRFProtection.is_safe_url("http://example.com") is False


class TestSSRAwareSession:
    """SSRF 安全 Session 测试"""

    def test_session_init(self):
        """测试 Session 初始化"""
        session = SSRFAwareSession(max_redirects=5)
        assert session._session.max_redirects == 5

    def test_session_get_safe(self):
        """测试安全的 GET 请求"""
        session = SSRFAwareSession()

        # Mock 请求
        with patch.object(session._session, "request") as mock_request:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_request.return_value = mock_response

            response = session.get("https://example.com")

            assert response is not None
            assert response.status_code == 200

    def test_session_get_unsafe(self):
        """测试不安全的 GET 请求"""
        session = SSRFAwareSession()

        # 私有 IP 应该被阻止
        response = session.get("http://10.0.0.1")

        assert response is None

    def test_session_post(self):
        """测试 POST 请求"""
        session = SSRFAwareSession()

        with patch.object(session._session, "request") as mock_request:
            mock_response = MagicMock()
            mock_request.return_value = mock_response

            response = session.post("https://example.com", data={"key": "value"})

            assert response is not None

    def test_session_head(self):
        """测试 HEAD 请求"""
        session = SSRFAwareSession()

        with patch.object(session._session, "request") as mock_request:
            mock_response = MagicMock()
            mock_request.return_value = mock_response

            response = session.head("https://example.com")

            assert response is not None

    def test_session_context_manager(self):
        """测试上下文管理器"""
        with SSRFAwareSession() as session:
            assert session is not None

        # 退出上下文后 session 应该关闭

    def test_session_redirect_hook(self):
        """测试重定向钩子"""
        session = SSRFAwareSession()

        # Mock 响应
        mock_response = MagicMock()
        mock_response.headers = {"Location": "http://10.0.0.1"}
        mock_response.status_code = 302

        # 调用钩子函数
        for hook in session._session.hooks["response"]:
            result = hook(mock_response)

            # 不安全的重定向应该返回 403
            assert result.status_code == 403
            assert "SSRF Protection" in result.reason

    def test_session_too_many_redirects(self):
        """测试重定向次数过多"""
        session = SSRFAwareSession()

        # 添加多个重定向到历史记录
        for i in range(10):
            session._redirect_history.append(f"http://example.com/{i}")

        mock_response = MagicMock()
        mock_response.headers = {"Location": "http://example.com/next"}
        mock_response.status_code = 302

        for hook in session._session.hooks["response"]:
            result = hook(mock_response)

            # 重定向次数过多应该返回 403
            assert result.status_code == 403
            assert "Too many redirects" in result.reason


class TestConvenienceFunctions:
    """便捷函数测试"""

    def test_is_safe_url(self):
        """测试 is_safe_url 函数"""
        assert is_safe_url("https://example.com") is True
        assert is_safe_url("http://10.0.0.1") is False

    def test_filter_safe_urls(self):
        """测试 filter_safe_urls 函数"""
        urls = ["https://a.com", "http://10.0.0.1", "https://b.com"]
        safe = filter_safe_urls(urls)

        assert len(safe) == 2
        assert "https://a.com" in safe
        assert "https://b.com" in safe

    def test_get_url_info(self):
        """测试 get_url_info 函数"""
        info = get_url_info("https://example.com")

        assert info["is_safe"] is True
        assert info["scheme"] == "https"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
