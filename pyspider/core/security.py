"""
URL 验证和安全模块 - 修复版
修复 SSRF 漏洞，添加 URL 白名单验证
"""

import re
import socket
import ipaddress
from typing import Optional, List, Set
from urllib.parse import urlparse
from dataclasses import dataclass


@dataclass
class SecurityConfig:
    """安全配置"""
    allowed_domains: Optional[List[str]] = None
    blocked_domains: Optional[List[str]] = None
    allowed_schemes: Set[str] = None
    max_url_length: int = 2048
    block_private_ips: bool = True
    
    def __post_init__(self):
        if self.allowed_schemes is None:
            self.allowed_schemes = {'http', 'https'}


class URLValidator:
    """URL 验证器 - 防止 SSRF 攻击"""
    
    def __init__(self, config: Optional[SecurityConfig] = None):
        self.config = config or SecurityConfig()
        self._blocked_ips: Set[str] = set()
    
    def validate(self, url: str) -> bool:
        """验证 URL"""
        if not url or not isinstance(url, str):
            return False
        
        # 检查长度
        if len(url) > self.config.max_url_length:
            return False
        
        # 解析 URL
        try:
            parsed = urlparse(url)
        except Exception:
            return False
        
        # 检查协议
        if parsed.scheme not in self.config.allowed_schemes:
            return False
        
        # 检查域名
        domain = parsed.netloc.split(':')[0]  # 移除端口
        if not domain:
            return False
        
        # 检查域名白名单
        if self.config.allowed_domains:
            if not self._domain_matches(domain, self.config.allowed_domains):
                return False
        
        # 检查域名黑名单
        if self.config.blocked_domains:
            if self._domain_matches(domain, self.config.blocked_domains):
                return False
        
        # 检查 IP 地址（防止 SSRF）
        if self.config.block_private_ips:
            if not self._check_ip_security(domain):
                return False
        
        return True
    
    def _domain_matches(self, domain: str, domain_list: List[str]) -> bool:
        """检查域名是否匹配列表"""
        domain = domain.lower()
        for pattern in domain_list:
            pattern = pattern.lower()
            if domain == pattern or domain.endswith('.' + pattern):
                return True
        return False
    
    def _check_ip_security(self, domain: str) -> bool:
        """检查 IP 地址安全性"""
        try:
            # 解析域名获取 IP
            ip_addresses = socket.getaddrinfo(domain, None)
            
            for family, _, _, _, sockaddr in ip_addresses:
                ip_str = sockaddr[0]
                
                # 检查是否是私有 IP
                if self._is_private_ip(ip_str):
                    return False
                
                # 检查是否在黑名单中
                if ip_str in self._blocked_ips:
                    return False
            
            return True
            
        except socket.gaierror:
            # DNS 解析失败，允许（可能是内部域名）
            return True
        except Exception:
            return True
    
    def _is_private_ip(self, ip_str: str) -> bool:
        """检查是否是私有 IP 地址"""
        try:
            ip = ipaddress.ip_address(ip_str)
            
            # 检查是否是私有地址
            if ip.is_private:
                return True
            
            # 检查是否是回环地址
            if ip.is_loopback:
                return True
            
            # 检查是否是链路本地地址
            if ip.is_link_local:
                return True
            
            # 检查是否是保留地址
            if ip.is_reserved:
                return True
            
            # 检查是否是组播地址
            if ip.is_multicast:
                return True
            
            return False
            
        except ValueError:
            return False
    
    def add_blocked_ip(self, ip: str) -> None:
        """添加被阻止的 IP"""
        self._blocked_ips.add(ip)
    
    def clear_blocked_ips(self) -> None:
        """清除被阻止的 IP 列表"""
        self._blocked_ips.clear()


class InputSanitizer:
    """输入清理器 - 防止 XSS 注入"""
    
    # HTML 标签正则
    HTML_TAG_PATTERN = re.compile(r'<[^>]+>')
    # 脚本标签正则
    SCRIPT_PATTERN = re.compile(r'<script[^>]*>.*?</script>', re.DOTALL | re.IGNORECASE)
    # 事件处理器正则
    EVENT_HANDLER_PATTERN = re.compile(r'on\w+\s*=\s*["\'][^"\']*["\']', re.IGNORECASE)
    
    @classmethod
    def sanitize_html(cls, html: str, remove_scripts: bool = True) -> str:
        """清理 HTML"""
        if not html:
            return ''
        
        # 移除脚本标签
        if remove_scripts:
            html = cls.SCRIPT_PATTERN.sub('', html)
        
        # 移除事件处理器
        html = cls.EVENT_HANDLER_PATTERN.sub('', html)
        
        return html
    
    @classmethod
    def strip_tags(cls, html: str) -> str:
        """移除所有 HTML 标签"""
        if not html:
            return ''
        return cls.HTML_TAG_PATTERN.sub('', html)
    
    @classmethod
    def sanitize_url(cls, url: str) -> str:
        """清理 URL"""
        if not url:
            return ''
        
        # 移除空白字符
        url = url.strip()
        
        # 移除 javascript: 协议
        if url.lower().startswith('javascript:'):
            return ''
        
        # 移除 data: 协议
        if url.lower().startswith('data:'):
            return ''
        
        return url
    
    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """清理文件名"""
        if not filename:
            return ''
        
        # 移除危险字符
        dangerous_chars = '<>:"/\\|？*'
        for char in dangerous_chars:
            filename = filename.replace(char, '_')
        
        # 移除控制字符
        filename = ''.join(c for c in filename if ord(c) >= 32)
        
        return filename.strip()
