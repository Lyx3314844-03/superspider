"""
安全模块测试
测试 URL 验证、SSRF 防护、XSS 防护
"""

import pytest
import socket
from unittest.mock import patch, MagicMock

from pyspider.core.security import URLValidator, InputSanitizer, SecurityConfig


class TestSecurityConfig:
    """测试安全配置"""

    def test_config_default(self):
        """测试默认配置"""
        config = SecurityConfig()
        assert config.allowed_schemes == {"http", "https"}
        assert config.max_url_length == 2048
        assert config.block_private_ips is True

    def test_config_custom(self):
        """测试自定义配置"""
        config = SecurityConfig(
            allowed_domains=["example.com"],
            blocked_domains=["evil.com"],
            allowed_schemes={"https"},
            max_url_length=1000,
            block_private_ips=False,
        )
        assert config.allowed_domains == ["example.com"]
        assert config.blocked_domains == ["evil.com"]
        assert config.allowed_schemes == {"https"}
        assert config.max_url_length == 1000
        assert config.block_private_ips is False


class TestURLValidator:
    """测试 URL 验证器"""

    def test_validator_init(self):
        """测试验证器初始化"""
        validator = URLValidator()
        assert validator.config is not None
        assert validator.config.block_private_ips is True

    def test_validate_valid_url(self):
        """测试有效 URL"""
        validator = URLValidator()
        assert validator.validate("https://www.example.com") is True
        assert validator.validate("http://example.com/page") is True

    def test_validate_empty_url(self):
        """测试空 URL"""
        validator = URLValidator()
        assert validator.validate("") is False
        assert validator.validate(None) is False

    def test_validate_url_length(self):
        """测试 URL 长度"""
        validator = URLValidator()
        long_url = "http://example.com/" + "a" * 3000
        assert validator.validate(long_url) is False

    def test_validate_scheme(self):
        """测试协议验证"""
        validator = URLValidator()
        # 默认只允许 http 和 https
        assert validator.validate("ftp://example.com/file") is False
        assert validator.validate("javascript:alert(1)") is False

    def test_validate_domain_whitelist(self):
        """测试域名白名单"""
        config = SecurityConfig(allowed_domains=["example.com", "trusted.org"])
        validator = URLValidator(config)

        assert validator.validate("https://www.example.com") is True
        assert validator.validate("https://sub.trusted.org") is True
        assert validator.validate("https://evil.com") is False

    def test_validate_domain_blacklist(self):
        """测试域名黑名单"""
        config = SecurityConfig(blocked_domains=["evil.com", "malware.org"])
        validator = URLValidator(config)

        assert validator.validate("https://www.example.com") is True
        assert validator.validate("https://evil.com") is False
        assert validator.validate("https://sub.malware.org") is False

    @patch("pyspider.core.security.socket.getaddrinfo")
    def test_validate_private_ip(self, mock_getaddrinfo):
        """测试私有 IP 防护"""
        # Mock DNS 解析返回私有 IP
        mock_getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.168.1.1", 80))
        ]

        validator = URLValidator()
        assert validator._check_ip_security("example.com") is False

    @patch("pyspider.core.security.socket.getaddrinfo")
    def test_validate_public_ip(self, mock_getaddrinfo):
        """测试公有 IP"""
        # Mock DNS 解析返回公有 IP
        mock_getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 80))
        ]

        validator = URLValidator()
        assert validator._check_ip_security("example.com") is True

    def test_validate_loopback_ip(self):
        """测试回环地址"""
        validator = URLValidator()
        assert validator._is_private_ip("127.0.0.1") is True
        assert validator._is_private_ip("::1") is True

    def test_validate_private_ips(self):
        """测试私有 IP 列表"""
        validator = URLValidator()

        # 私有 IP 范围
        assert validator._is_private_ip("10.0.0.1") is True
        assert validator._is_private_ip("172.16.0.1") is True
        assert validator._is_private_ip("192.168.0.1") is True

        # 公有 IP
        assert validator._is_private_ip("8.8.8.8") is False
        assert validator._is_private_ip("1.1.1.1") is False

    def test_add_blocked_ip(self):
        """测试添加被阻止的 IP"""
        validator = URLValidator()
        validator.add_blocked_ip("192.168.1.1")
        assert "192.168.1.1" in validator._blocked_ips

    def test_clear_blocked_ips(self):
        """测试清除被阻止的 IP"""
        validator = URLValidator()
        validator.add_blocked_ip("192.168.1.1")
        validator.clear_blocked_ips()
        assert len(validator._blocked_ips) == 0


class TestInputSanitizer:
    """测试输入清理器"""

    def test_sanitize_html(self):
        """测试 HTML 清理"""
        html = '<script>alert("XSS")</script><p>Safe</p>'
        result = InputSanitizer.sanitize_html(html)
        assert "<script>" not in result
        assert "alert" not in result

    def test_sanitize_html_remove_scripts(self):
        """测试移除脚本"""
        html = "<div><script>evil()</script><p>Good</p></div>"
        result = InputSanitizer.sanitize_html(html, remove_scripts=True)
        assert "<script>" not in result

    def test_sanitize_html_keep_scripts(self):
        """测试保留脚本"""
        html = "<div><script>code()</script><p>Content</p></div>"
        result = InputSanitizer.sanitize_html(html, remove_scripts=False)
        # 事件处理器仍然应该被移除
        assert "on" not in result.lower() or "script" in result.lower()

    def test_strip_tags(self):
        """测试移除标签"""
        html = "<div><p>Hello <b>World</b></p></div>"
        result = InputSanitizer.strip_tags(html)
        assert result == "Hello World"

    def test_sanitize_url(self):
        """测试 URL 清理"""
        assert (
            InputSanitizer.sanitize_url("  https://example.com  ")
            == "https://example.com"
        )
        assert InputSanitizer.sanitize_url("javascript:alert(1)") == ""
        assert (
            InputSanitizer.sanitize_url("data:text/html,<script>alert(1)</script>")
            == ""
        )

    def test_sanitize_filename(self):
        """测试文件名清理"""
        assert InputSanitizer.sanitize_filename("file<name>.txt") == "file_name_.txt"
        assert (
            InputSanitizer.sanitize_filename("path/to/file.txt") == "path_to_file.txt"
        )
        assert InputSanitizer.sanitize_filename("file\x00name.txt") == "filename.txt"

    def test_sanitize_empty_input(self):
        """测试空输入"""
        assert InputSanitizer.sanitize_html("") == ""
        assert InputSanitizer.strip_tags("") == ""
        assert InputSanitizer.sanitize_url("") == ""
        assert InputSanitizer.sanitize_filename("") == ""

    def test_sanitize_event_handlers(self):
        """测试事件处理器清理"""
        html = '<img src="x" onerror="alert(1)" onclick="evil()">'
        result = InputSanitizer.sanitize_html(html)
        assert "onerror" not in result
        assert "onclick" not in result


class TestSSRFProtection:
    """测试 SSRF 防护"""

    @patch("pyspider.core.security.socket.getaddrinfo")
    def test_ssrf_private_ip(self, mock_getaddrinfo):
        """测试 SSRF 私有 IP 防护"""
        mock_getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.1", 80))
        ]

        validator = URLValidator()
        result = validator.validate("http://internal.example.com")
        assert result is False

    @patch("pyspider.core.security.socket.getaddrinfo")
    def test_ssrf_localhost(self, mock_getaddrinfo):
        """测试 SSRF 本地主机防护"""
        mock_getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 80))
        ]

        validator = URLValidator()
        result = validator.validate("http://localhost")
        assert result is False

    @patch("pyspider.core.security.socket.getaddrinfo")
    def test_ssrf_link_local(self, mock_getaddrinfo):
        """测试 SSRF 链路本地地址防护"""
        mock_getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("169.254.1.1", 80))
        ]

        validator = URLValidator()
        result = validator.validate("http://example.com")
        assert result is False


class TestXSSProtection:
    """测试 XSS 防护"""

    def test_xss_script_tag(self):
        """测试脚本标签 XSS"""
        html = '<script>alert("XSS")</script>'
        result = InputSanitizer.sanitize_html(html)
        assert "alert" not in result

    def test_xss_img_onerror(self):
        """测试图片 onerror XSS"""
        html = '<img src="x" onerror="alert(1)">'
        result = InputSanitizer.sanitize_html(html)
        assert "onerror" not in result

    def test_xss_svg_onload(self):
        """测试 SVG onload XSS"""
        html = '<svg onload="alert(1)">'
        result = InputSanitizer.sanitize_html(html)
        assert "onload" not in result

    def test_xss_javascript_url(self):
        """测试 JavaScript URL XSS"""
        url = 'javascript:alert("XSS")'
        result = InputSanitizer.sanitize_url(url)
        assert result == ""

    def test_xss_data_url(self):
        """测试 Data URL XSS"""
        url = "data:text/html,<script>alert(1)</script>"
        result = InputSanitizer.sanitize_url(url)
        assert result == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=pyspider.core.security", "--cov-report=html"])
