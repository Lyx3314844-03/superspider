"""
PySpider 安全模块完整测试套件

测试覆盖率目标：>95%
"""

import pytest
from unittest.mock import patch, MagicMock
import socket
import ipaddress

from pyspider.core.security import (
    URLValidator,
    InputSanitizer,
    SecurityConfig,
)
from pyspider.core.ssrf_protection import (
    SSRFProtection,
)


class TestURLValidator:
    """URL 验证器测试"""

    def test_valid_http_url(self):
        """测试有效 HTTP URL"""
        validator = URLValidator()
        assert validator.validate("http://example.com") is True
        assert validator.validate("http://www.google.com/search?q=test") is True

    def test_valid_https_url(self):
        """测试有效 HTTPS URL"""
        validator = URLValidator()
        assert validator.validate("https://example.com") is True
        assert validator.validate("https://api.github.com/users") is True

    def test_invalid_protocol(self):
        """测试无效协议"""
        validator = URLValidator(allowed_protocols=["http", "https"])
        assert validator.validate("ftp://example.com") is False
        assert validator.validate("file:///etc/passwd") is False
        assert validator.validate("javascript:alert(1)") is False

    def test_private_ip_v4(self):
        """测试 IPv4 私有地址"""
        validator = URLValidator()

        # Class A
        assert validator.validate("http://10.0.0.1") is False
        assert validator.validate("http://10.255.255.255") is False

        # Class B
        assert validator.validate("http://172.16.0.1") is False
        assert validator.validate("http://172.31.255.255") is False

        # Class C
        assert validator.validate("http://192.168.0.1") is False
        assert validator.validate("http://192.168.255.255") is False

    def test_localhost(self):
        """测试本地回环地址"""
        validator = URLValidator()
        assert validator.validate("http://127.0.0.1") is False
        assert validator.validate("http://127.1.2.3") is False
        assert validator.validate("http://localhost") is False

    def test_link_local(self):
        """测试链路本地地址"""
        validator = URLValidator()
        assert validator.validate("http://169.254.0.1") is False
        assert validator.validate("http://169.254.255.255") is False

    def test_multicast(self):
        """测试组播地址"""
        validator = URLValidator()
        assert validator.validate("http://224.0.0.1") is False
        assert validator.validate("http://239.255.255.255") is False

    def test_cloud_metadata(self):
        """测试云服务商元数据端点"""
        validator = URLValidator()

        # AWS
        assert validator.validate("http://169.254.169.254") is False
        # Azure
        assert validator.validate("http://168.63.129.16") is False
        # GCP
        assert validator.validate("http://metadata.google.internal") is False

    def test_url_length(self):
        """测试 URL 长度限制"""
        validator = URLValidator(max_length=2048)

        # 正常长度
        assert validator.validate("http://example.com/" + "a" * 100) is True

        # 过长
        assert validator.validate("http://example.com/" + "a" * 3000) is False

    def test_dangerous_characters(self):
        """测试危险字符"""
        validator = URLValidator()

        # 控制字符
        assert validator.validate("http://example.com/\x00") is False

        # HTML 特殊字符
        assert validator.validate("http://example.com/<script>") is False

        # 换行符 (日志注入)
        assert validator.validate("http://example.com/\r\n") is False

    def test_custom_allowed_protocols(self):
        """测试自定义允许的协议"""
        validator = URLValidator(allowed_protocols=["http", "https", "ftp"])

        assert validator.validate("http://example.com") is True
        assert validator.validate("https://example.com") is True
        assert validator.validate("ftp://example.com") is True
        assert validator.validate("file:///etc/passwd") is False

    def test_custom_allowed_hosts(self):
        """测试自定义允许的主机"""
        validator = URLValidator(allowed_hosts=["example.com", "google.com"])

        assert validator.validate("http://example.com") is True
        assert validator.validate("http://google.com") is True
        assert validator.validate("http://evil.com") is False

    def test_port_validation(self):
        """测试端口验证"""
        validator = URLValidator(allowed_ports=[80, 443, 8080])

        assert validator.validate("http://example.com:80") is True
        assert validator.validate("https://example.com:443") is True
        assert validator.validate("http://example.com:8080") is True
        assert validator.validate("http://example.com:65535") is False

    def test_ipv6_validation(self):
        """测试 IPv6 验证"""
        validator = URLValidator()

        # 公网 IPv6
        assert validator.validate("http://[2001:db8::1]") is True

        # 本地回环 IPv6
        assert validator.validate("http://[::1]") is False

        # 唯一本地 IPv6
        assert validator.validate("http://[fc00::1]") is False

    def test_dns_rebinding_protection(self):
        """测试 DNS 重绑定防护"""
        validator = URLValidator()

        # Mock DNS 解析返回私有 IP
        with patch("socket.getaddrinfo") as mock_getaddrinfo:
            mock_getaddrinfo.return_value = [
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.1", 0)),
            ]

            assert validator.validate("http://example.com") is False

    def test_dns_resolution_failure(self):
        """测试 DNS 解析失败"""
        validator = URLValidator()

        with patch("socket.getaddrinfo") as mock_getaddrinfo:
            mock_getaddrinfo.side_effect = socket.gaierror("DNS resolution failed")

            assert validator.validate("http://nonexistent.invalid") is False

    def test_url_with_credentials(self):
        """测试带凭证的 URL"""
        validator = URLValidator()

        # 允许带凭证的 URL
        assert validator.validate("http://user:pass@example.com") is True

    def test_url_with_fragment(self):
        """测试带片段的 URL"""
        validator = URLValidator()

        assert validator.validate("http://example.com/page#section") is True

    def test_international_domain(self):
        """测试国际域名"""
        validator = URLValidator()

        assert validator.validate("http://中文.com") is True
        assert validator.validate("http://münchen.de") is True

    def test_concurrent_validation(self):
        """测试并发验证"""
        import threading

        validator = URLValidator()
        results = []

        def validate_url(url):
            results.append(validator.validate(url))

        threads = []
        urls = [
            "http://example.com",
            "http://10.0.0.1",
            "https://google.com",
            "http://192.168.1.1",
        ]

        for url in urls:
            t = threading.Thread(target=validate_url, args=(url,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(results) == 4
        assert results.count(True) == 2
        assert results.count(False) == 2


class TestInputSanitizer:
    """输入清理器测试"""

    def test_sanitize_string(self):
        """测试字符串清理"""
        sanitizer = InputSanitizer()

        # 正常字符串
        assert sanitizer.sanitize_string("hello world") == "hello world"

        # 带 HTML 标签
        assert sanitizer.sanitize_string("<script>alert(1)</script>") == ""

        # 带特殊字符
        assert sanitizer.sanitize_string("hello\x00world") == "helloworld"

    def test_sanitize_dict(self):
        """测试字典清理"""
        sanitizer = InputSanitizer()

        data = {
            "name": "John",
            "html": "<script>alert(1)</script>",
            "nested": {"safe": "value", "unsafe": "<img src=x onerror=alert(1)>"},
        }

        cleaned = sanitizer.sanitize_dict(data)

        assert cleaned["name"] == "John"
        assert cleaned["html"] == ""
        assert cleaned["nested"]["safe"] == "value"
        assert cleaned["nested"]["unsafe"] == ""

    def test_sanitize_list(self):
        """测试列表清理"""
        sanitizer = InputSanitizer()

        data = ["safe", "<script>bad</script>", "also safe"]

        cleaned = sanitizer.sanitize_list(data)

        assert len(cleaned) == 2
        assert "safe" in cleaned
        assert "also safe" in cleaned
        assert "<script>bad</script>" not in cleaned

    def test_remove_null_bytes(self):
        """测试移除空字节"""
        sanitizer = InputSanitizer()

        assert sanitizer.sanitize_string("hello\x00world") == "helloworld"
        assert sanitizer.sanitize_string("test\x00\x00\x00") == "test"

    def test_remove_control_characters(self):
        """测试移除控制字符"""
        sanitizer = InputSanitizer()

        # 控制字符 (0x00-0x1F 除了 0x09, 0x0A, 0x0D)
        assert sanitizer.sanitize_string("hello\x01\x02\x03world") == "helloworld"

        # 保留的空白字符
        assert sanitizer.sanitize_string("hello\t\n\rworld") == "hello\t\n\rworld"

    def test_html_entity_decode(self):
        """测试 HTML 实体解码"""
        sanitizer = InputSanitizer(decode_html_entities=True)

        assert sanitizer.sanitize_string("&lt;script&gt;") == "<script>"
        assert sanitizer.sanitize_string("&amp;") == "&"

    def test_max_string_length(self):
        """测试最大字符串长度"""
        sanitizer = InputSanitizer(max_length=100)

        # 短字符串
        assert len(sanitizer.sanitize_string("short")) == 5

        # 长字符串
        long_string = "a" * 200
        cleaned = sanitizer.sanitize_string(long_string)
        assert len(cleaned) <= 100

    def test_strip_tags(self):
        """测试移除标签"""
        sanitizer = InputSanitizer()

        html = "<p>Hello <b>World</b></p>"
        cleaned = sanitizer.sanitize_string(html)

        assert "<" not in cleaned
        assert ">" not in cleaned

    def test_xss_protection(self):
        """测试 XSS 防护"""
        sanitizer = InputSanitizer()

        xss_payloads = [
            "<script>alert(1)</script>",
            "<img src=x onerror=alert(1)>",
            "<svg onload=alert(1)>",
            "javascript:alert(1)",
            "data:text/html,<script>alert(1)</script>",
        ]

        for payload in xss_payloads:
            cleaned = sanitizer.sanitize_string(payload)
            assert "script" not in cleaned.lower()
            assert "alert" not in cleaned.lower()

    def test_sql_injection_protection(self):
        """测试 SQL 注入防护"""
        sanitizer = InputSanitizer()

        sql_payloads = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "1; DELETE FROM users",
        ]

        for payload in sql_payloads:
            cleaned = sanitizer.sanitize_string(payload)
            # 至少应该移除分号
            assert ";" not in cleaned

    def test_concurrent_sanitization(self):
        """测试并发清理"""
        import threading

        sanitizer = InputSanitizer()
        results = []

        def sanitize(data):
            results.append(sanitizer.sanitize_string(data))

        threads = []
        data_list = [
            "safe input",
            "<script>bad</script>",
            "normal text",
            "<img src=x>",
        ]

        for data in data_list:
            t = threading.Thread(target=sanitize, args=(data,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(results) == 4


class TestSecurityConfig:
    """安全配置测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = SecurityConfig()

        assert config.enable_ssrf_protection is True
        assert config.enable_input_sanitization is True
        assert config.enable_url_validation is True
        assert config.max_redirects == 5
        assert config.timeout_seconds == 30

    def test_custom_config(self):
        """测试自定义配置"""
        config = SecurityConfig(
            enable_ssrf_protection=False,
            max_redirects=10,
            timeout_seconds=60,
        )

        assert config.enable_ssrf_protection is False
        assert config.max_redirects == 10
        assert config.timeout_seconds == 60

    def test_config_validation(self):
        """测试配置验证"""
        config = SecurityConfig()

        # 验证应该通过
        assert config.validate() is True

        # 无效配置
        config.max_redirects = -1
        assert config.validate() is False

        config.max_redirects = 5
        config.timeout_seconds = -1
        assert config.validate() is False

    def test_config_to_dict(self):
        """测试配置转字典"""
        config = SecurityConfig()

        config_dict = config.to_dict()

        assert "enable_ssrf_protection" in config_dict
        assert "enable_input_sanitization" in config_dict
        assert "max_redirects" in config_dict

    def test_config_from_dict(self):
        """测试从字典创建配置"""
        config_dict = {
            "enable_ssrf_protection": False,
            "max_redirects": 10,
            "timeout_seconds": 60,
        }

        config = SecurityConfig.from_dict(config_dict)

        assert config.enable_ssrf_protection is False
        assert config.max_redirects == 10
        assert config.timeout_seconds == 60


class TestIntegration:
    """集成测试"""

    def test_full_request_validation(self):
        """测试完整的请求验证流程"""
        validator = URLValidator()
        sanitizer = InputSanitizer()

        # 有效请求
        url = "https://example.com/api?key=value"
        assert validator.validate(url) is True

        # 清理参数
        params = {"key": "value", "html": "<script>bad</script>"}
        cleaned_params = sanitizer.sanitize_dict(params)

        assert cleaned_params["key"] == "value"
        assert cleaned_params["html"] == ""

    def test_malicious_request_blocking(self):
        """测试恶意请求阻断"""
        validator = URLValidator()
        sanitizer = InputSanitizer()

        # SSRF 攻击
        assert validator.validate("http://169.254.169.254/latest/meta-data/") is False

        # XSS 攻击
        xss_payload = sanitizer.sanitize_string("<script>alert(1)</script>")
        assert "script" not in xss_payload.lower()

        # SQL 注入
        sql_payload = sanitizer.sanitize_string("'; DROP TABLE users; --")
        assert ";" not in sql_payload

    def test_redirect_chain_validation(self):
        """测试重定向链验证"""
        validator = URLValidator()

        # 安全重定向
        redirect_chain = [
            "http://example.com",
            "http://example.com/page1",
            "http://example.com/page2",
        ]

        for url in redirect_chain:
            assert validator.validate(url) is True

        # 不安全重定向
        malicious_chain = [
            "http://example.com",
            "http://10.0.0.1/internal",
        ]

        for url in malicious_chain:
            if "10.0.0.1" in url:
                assert validator.validate(url) is False
            else:
                assert validator.validate(url) is True


if __name__ == "__main__":
    pytest.main(
        [
            __file__,
            "-v",
            "--tb=short",
            "--cov=pyspider.core.security",
            "--cov-report=term-missing",
        ]
    )
