"""
URL 验证和输入安全模块。
"""

from __future__ import annotations

import html
import ipaddress
import re
import socket
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional, Set
from urllib.parse import urlparse


@dataclass
class SecurityConfig:
    enable_ssrf_protection: bool = True
    enable_input_sanitization: bool = True
    enable_url_validation: bool = True
    max_redirects: int = 5
    timeout_seconds: int = 30
    allowed_domains: Optional[List[str]] = None
    blocked_domains: Optional[List[str]] = None
    allowed_protocols: List[str] = field(default_factory=lambda: ["http", "https"])
    allowed_schemes: Optional[Set[str]] = None
    allowed_hosts: Optional[List[str]] = None
    allowed_ports: Optional[List[int]] = None
    max_url_length: int = 2048
    block_private_ips: bool = True
    decode_html_entities: bool = False
    max_input_length: int = 10000

    def __post_init__(self):
        if self.allowed_schemes is not None:
            self.allowed_protocols = list(self.allowed_schemes)
        else:
            self.allowed_schemes = set(self.allowed_protocols)
        self.allowed_schemes = set(self.allowed_protocols)

    def validate(self) -> bool:
        return (
            self.max_redirects >= 0
            and self.timeout_seconds >= 0
            and self.max_url_length > 0
        )

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "SecurityConfig":
        return cls(**data)


class URLValidator:
    METADATA_HOSTS = {"169.254.169.254", "168.63.129.16", "metadata.google.internal"}

    def __init__(
        self,
        config: Optional[SecurityConfig] = None,
        allowed_protocols: Optional[List[str]] = None,
        allowed_hosts: Optional[List[str]] = None,
        allowed_ports: Optional[List[int]] = None,
        max_length: Optional[int] = None,
        allowed_domains: Optional[List[str]] = None,
        blocked_domains: Optional[List[str]] = None,
    ):
        self.config = config or SecurityConfig()
        if allowed_protocols is not None:
            self.config.allowed_protocols = list(allowed_protocols)
        if allowed_hosts is not None:
            self.config.allowed_hosts = list(allowed_hosts)
        if allowed_ports is not None:
            self.config.allowed_ports = list(allowed_ports)
        if max_length is not None:
            self.config.max_url_length = max_length
        if allowed_domains is not None:
            self.config.allowed_domains = list(allowed_domains)
        if blocked_domains is not None:
            self.config.blocked_domains = list(blocked_domains)
        self._blocked_ips: Set[str] = set()

    def validate(self, url: str) -> bool:
        if not self.config.enable_url_validation or not isinstance(url, str) or not url:
            return False
        if len(url) > self.config.max_url_length:
            return False
        if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f\r\n]", url):
            return False
        if any(ch in url for ch in ["<", ">", '"']):
            return False

        try:
            parsed = urlparse(url)
        except Exception:
            return False

        if parsed.scheme.lower() not in {
            scheme.lower() for scheme in self.config.allowed_protocols
        }:
            return False

        hostname = parsed.hostname
        if not hostname:
            return False

        if hostname in self.METADATA_HOSTS:
            return False

        if self.config.allowed_hosts and not self._domain_matches(
            hostname, self.config.allowed_hosts
        ):
            return False
        if self.config.allowed_domains and not self._domain_matches(
            hostname, self.config.allowed_domains
        ):
            return False
        if self.config.blocked_domains and self._domain_matches(
            hostname, self.config.blocked_domains
        ):
            return False

        if (
            parsed.port
            and self.config.allowed_ports
            and parsed.port not in self.config.allowed_ports
        ):
            return False

        if self.config.block_private_ips and not self._check_ip_security(hostname):
            return False

        return True

    def _domain_matches(self, domain: str, domain_list: List[str]) -> bool:
        normalized = domain.lower()
        for pattern in domain_list:
            pattern = pattern.lower()
            if normalized == pattern or normalized.endswith("." + pattern):
                return True
        return False

    def _check_ip_security(self, hostname: str) -> bool:
        try:
            ip = ipaddress.ip_address(hostname)
            return not self._is_private_ip(ip.exploded)
        except ValueError:
            pass

        try:
            addresses = socket.getaddrinfo(hostname, None)
        except socket.gaierror:
            return not hostname.endswith(".invalid")
        except Exception:
            return False

        for _, _, _, _, sockaddr in addresses:
            ip_str = sockaddr[0]
            if self._is_private_ip(ip_str) or ip_str in self._blocked_ips:
                return False
        return True

    def _is_private_ip(self, ip_str: str) -> bool:
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            return False
        if ip.version == 6 and ip in ipaddress.ip_network("2001:db8::/32"):
            return False
        return (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_unspecified
        )

    def add_blocked_ip(self, ip: str) -> None:
        self._blocked_ips.add(ip)

    def clear_blocked_ips(self) -> None:
        self._blocked_ips.clear()


class InputSanitizer:
    SCRIPT_PATTERN = re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL)
    TAG_PATTERN = re.compile(r"<[^>]+>")
    EVENT_PATTERN = re.compile(r"on\w+\s*=\s*(['\"]).*?\1", re.IGNORECASE)
    CONTROL_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")

    def __init__(self, decode_html_entities: bool = False, max_length: int = 10000):
        self.decode_html_entities = decode_html_entities
        self.max_length = max_length

    def sanitize_string(self, value: str) -> str:
        if value is None:
            return ""
        if not isinstance(value, str):
            value = str(value)

        value = value.replace("\x00", "")
        value = self.CONTROL_PATTERN.sub("", value)

        lowered = value.lower()
        if any(
            token in lowered
            for token in [
                "javascript:",
                "data:text/html",
                "<script",
                "onerror=",
                "onload=",
            ]
        ):
            value = self.SCRIPT_PATTERN.sub("", value)
            value = self.EVENT_PATTERN.sub("", value)
            value = self.TAG_PATTERN.sub("", value)
            if any(token in value.lower() for token in ["script", "alert"]):
                value = ""

        value = self.SCRIPT_PATTERN.sub("", value)
        value = self.EVENT_PATTERN.sub("", value)
        value = self.TAG_PATTERN.sub("", value)
        value = value.replace(";", "")

        if len(value) > self.max_length:
            value = value[: self.max_length]

        if self.decode_html_entities:
            value = html.unescape(value)

        return value

    def sanitize_dict(self, data: Dict[str, object]) -> Dict[str, object]:
        sanitized: Dict[str, object] = {}
        for key, value in data.items():
            if isinstance(value, dict):
                sanitized[key] = self.sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[key] = self.sanitize_list(value)
            else:
                sanitized[key] = self.sanitize_string(
                    value if value is not None else ""
                )
        return sanitized

    def sanitize_list(self, data: List[object]) -> List[object]:
        cleaned: List[object] = []
        for value in data:
            if isinstance(value, dict):
                nested = self.sanitize_dict(value)
                if nested:
                    cleaned.append(nested)
            else:
                sanitized = self.sanitize_string(value if value is not None else "")
                if sanitized:
                    cleaned.append(sanitized)
        return cleaned

    @classmethod
    def sanitize_html(cls, html_text: str, remove_scripts: bool = True) -> str:
        if not html_text:
            return ""
        cleaned = html_text
        if remove_scripts:
            cleaned = cls.SCRIPT_PATTERN.sub("", cleaned)
        cleaned = cls.EVENT_PATTERN.sub("", cleaned)
        return cleaned

    @classmethod
    def strip_tags(cls, html_text: str) -> str:
        if not html_text:
            return ""
        return cls.TAG_PATTERN.sub("", html_text)

    @classmethod
    def sanitize_url(cls, url: str) -> str:
        if not url:
            return ""
        normalized = url.strip()
        lowered = normalized.lower()
        if lowered.startswith("javascript:") or lowered.startswith("data:"):
            return ""
        return normalized

    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        if not filename:
            return ""
        dangerous_chars = '<>:"/\\|？*'
        sanitized = filename
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, "_")
        sanitized = "".join(c for c in sanitized if ord(c) >= 32)
        return sanitized.strip()
