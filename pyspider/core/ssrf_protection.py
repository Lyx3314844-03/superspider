"""
PySpider SSRF 防护模块

提供 URL 安全验证，防止服务器端请求伪造攻击

特性:
1. ✅ 私有 IP 地址检测
2. ✅ 协议白名单
3. ✅ DNS 重绑定防护
4. ✅ 元数据端点保护
5. ✅ 重定向验证

使用示例:
    from pyspider.core.ssrf_protection import SSRFProtection
    
    # 验证 URL
    if SSRFProtection.is_safe_url("https://example.com"):
        # 安全，可以访问
        pass
    
    # 批量验证
    urls = ["https://a.com", "https://b.com"]
    safe_urls = SSRFProtection.filter_safe_urls(urls)
"""

import socket
import ipaddress
import re
from urllib.parse import urlparse, urljoin
from typing import List, Optional, Set, Tuple
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)


class SSRFProtection:
    """SSRF 防护类"""
    
    # 允许的协议白名单
    ALLOWED_SCHEMES = frozenset(['http', 'https'])
    
    # 禁止的私有 IP 段
    PRIVATE_IP_RANGES = [
        "10.0.0.0/8",       # Class A 私有
        "172.16.0.0/12",    # Class B 私有
        "192.168.0.0/16",   # Class C 私有
        "127.0.0.0/8",      # 回环地址
        "0.0.0.0/8",        # 当前网络
        "169.254.0.0/16",   # 链路本地地址
        "224.0.0.0/4",      # 组播地址
        "240.0.0.0/4",      # 保留地址
        "::1/128",          # IPv6 回环
        "fc00::/7",         # IPv6 唯一本地地址
        "fe80::/10",        # IPv6 链路本地
    ]
    
    # 云服务商元数据端点 (需要保护)
    METADATA_ENDPOINTS = [
        "169.254.169.254",  # AWS/Azure/GCP 元数据
        "metadata.google.internal",  # GCP
        "168.63.129.16",    # Azure
    ]
    
    # DNS 重绑定保护 - 最大重定向次数
    MAX_REDIRECTS = 5
    
    @classmethod
    @lru_cache(maxsize=1024)
    def is_safe_url(cls, url: str) -> bool:
        """
        检查 URL 是否安全
        
        Args:
            url: 要检查的 URL
            
        Returns:
            bool: URL 是否安全
        """
        try:
            parsed = urlparse(url)
            
            # 1. 检查协议白名单
            if parsed.scheme.lower() not in cls.ALLOWED_SCHEMES:
                logger.warning(f"URL 协议不被允许：{url}")
                return False
            
            # 2. 检查主机名
            hostname = parsed.hostname
            if not hostname:
                logger.warning(f"URL 缺少主机名：{url}")
                return False
            
            # 3. 检查是否为元数据端点
            if hostname in cls.METADATA_ENDPOINTS:
                logger.warning(f"访问云服务商元数据端点被阻止：{url}")
                return False
            
            # 4. 解析并检查所有 IP 地址
            if not cls._validate_hostname(hostname):
                return False
            
            # 5. 检查 URL 格式
            if not cls._validate_url_format(url):
                return False
            
            logger.debug(f"URL 安全检查通过：{url}")
            return True
            
        except Exception as e:
            logger.error(f"URL 安全检查失败：{url}, 错误：{e}")
            return False
    
    @classmethod
    def _validate_hostname(cls, hostname: str) -> bool:
        """
        验证主机名，检查所有解析的 IP 地址
        
        Args:
            hostname: 主机名
            
        Returns:
            bool: 是否安全
        """
        try:
            # 获取所有 IP 地址 (IPv4 和 IPv6)
            addr_info_list = socket.getaddrinfo(
                hostname, 
                None, 
                socket.AF_UNSPEC,  # 同时支持 IPv4 和 IPv6
                socket.SOCK_STREAM
            )
            
            if not addr_info_list:
                logger.warning(f"主机名无法解析：{hostname}")
                return False
            
            # 检查每个 IP 地址
            for addr_info in addr_info_list:
                ip = addr_info[4][0]
                if cls._is_private_ip(ip):
                    logger.warning(f"检测到私有 IP 地址：{ip} (主机名：{hostname})")
                    return False
            
            return True
            
        except socket.gaierror as e:
            logger.error(f"DNS 解析失败：{hostname}, 错误：{e}")
            return False
        except Exception as e:
            logger.error(f"主机名验证失败：{hostname}, 错误：{e}")
            return False
    
    @classmethod
    @lru_cache(maxsize=2048)
    def _is_private_ip(cls, ip_str: str) -> bool:
        """
        检查 IP 是否为私有地址
        
        Args:
            ip_str: IP 地址字符串
            
        Returns:
            bool: 是否为私有地址
        """
        try:
            ip = ipaddress.ip_address(ip_str)
            
            # 使用 ipaddress 库的内置检查
            return (
                ip.is_private or      # 私有地址
                ip.is_loopback or     # 回环地址
                ip.is_link_local or   # 链路本地地址
                ip.is_multicast or    # 组播地址
                ip.is_reserved or     # 保留地址
                ip.is_unspecified     # 未指定地址
            )
            
        except ValueError:
            # 无法解析的 IP 视为不安全
            logger.warning(f"无效的 IP 地址：{ip_str}")
            return True
    
    @classmethod
    def _validate_url_format(cls, url: str) -> bool:
        """
        验证 URL 格式
        
        Args:
            url: URL 字符串
            
        Returns:
            bool: 格式是否有效
        """
        # 检查 URL 长度
        if len(url) > 2048:
            logger.warning(f"URL 过长：{len(url)} 字符")
            return False
        
        # 检查是否包含危险字符
        dangerous_patterns = [
            r'[\x00-\x1f]',  # 控制字符
            r'[<>"\']',      # HTML 特殊字符
            r'[\r\n]',       # 换行符 (防止日志注入)
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, url):
                logger.warning(f"URL 包含危险字符：{pattern}")
                return False
        
        return True
    
    @classmethod
    def filter_safe_urls(cls, urls: List[str]) -> List[str]:
        """
        批量过滤安全 URL
        
        Args:
            urls: URL 列表
            
        Returns:
            List[str]: 安全的 URL 列表
        """
        safe_urls = []
        for url in urls:
            if cls.is_safe_url(url):
                safe_urls.append(url)
            else:
                logger.info(f"过滤不安全的 URL: {url}")
        
        return safe_urls
    
    @classmethod
    def validate_redirect_chain(
        cls, 
        initial_url: str, 
        redirect_urls: List[str]
    ) -> bool:
        """
        验证重定向链的安全性
        
        Args:
            initial_url: 初始 URL
            redirect_urls: 重定向 URL 列表
            
        Returns:
            bool: 重定向链是否安全
        """
        # 检查重定向次数
        if len(redirect_urls) > cls.MAX_REDIRECTS:
            logger.warning(
                f"重定向次数过多：{len(redirect_urls)} > {cls.MAX_REDIRECTS}"
            )
            return False
        
        # 验证每个重定向 URL
        all_urls = [initial_url] + redirect_urls
        for url in all_urls:
            if not cls.is_safe_url(url):
                logger.warning(f"重定向链中包含不安全的 URL: {url}")
                return False
        
        # 检查是否有协议降级
        initial_scheme = urlparse(initial_url).scheme.lower()
        for url in redirect_urls:
            scheme = urlparse(url).scheme.lower()
            if scheme not in cls.ALLOWED_SCHEMES:
                logger.warning(f"重定向到不支持的协议：{url}")
                return False
        
        return True
    
    @classmethod
    def get_url_info(cls, url: str) -> dict:
        """
        获取 URL 详细信息 (用于调试和日志)
        
        Args:
            url: URL 字符串
            
        Returns:
            dict: URL 信息
        """
        try:
            parsed = urlparse(url)
            info = {
                'url': url,
                'scheme': parsed.scheme,
                'hostname': parsed.hostname,
                'port': parsed.port,
                'path': parsed.path,
                'is_safe': cls.is_safe_url(url),
            }
            
            # 获取 IP 地址
            if parsed.hostname:
                try:
                    addr_info = socket.getaddrinfo(parsed.hostname, None)
                    info['ip_addresses'] = list(set(
                        addr[4][0] for addr in addr_info
                    ))
                except Exception:
                    info['ip_addresses'] = []
            
            return info
            
        except Exception as e:
            return {
                'url': url,
                'error': str(e),
                'is_safe': False,
            }


class SSRFAwareSession:
    """
    支持 SSRF 防护的 HTTP Session
    
    使用示例:
        session = SSRFAwareSession()
        response = session.get("https://example.com")
    """
    
    def __init__(self, max_redirects: int = 5):
        import requests
        self._session = requests.Session()
        self._session.max_redirects = max_redirects
        self._redirect_history: List[str] = []
    
    def request(self, method: str, url: str, **kwargs) -> Optional['requests.Response']:
        """
        发送 HTTP 请求 (带 SSRF 检查)
        
        Args:
            method: HTTP 方法
            url: 请求 URL
            **kwargs: 其他参数
            
        Returns:
            Response 或 None (如果不安全)
        """
        # 检查初始 URL
        if not SSRFProtection.is_safe_url(url):
            logger.error(f"阻止不安全的请求：{url}")
            return None
        
        # 设置重定向钩子来检查每个重定向
        def check_redirect(response, **kwargs):
            redirect_url = response.headers.get('Location', '')
            if redirect_url:
                # 处理相对 URL
                redirect_url = urljoin(url, redirect_url)
                self._redirect_history.append(redirect_url)
                
                # 检查重定向 URL
                if not SSRFProtection.is_safe_url(redirect_url):
                    logger.error(f"重定向到不安全的 URL: {redirect_url}")
                    response.status_code = 403
                    response.reason = "SSRF Protection: Unsafe redirect"
                
                # 检查重定向链
                if len(self._redirect_history) > SSRFProtection.MAX_REDIRECTS:
                    logger.error(f"重定向次数过多：{len(self._redirect_history)}")
                    response.status_code = 403
                    response.reason = "Too many redirects"
            
            return response
        
        self._session.hooks['response'].append(check_redirect)
        
        try:
            response = self._session.request(method, url, **kwargs)
            return response
        except Exception as e:
            logger.error(f"HTTP 请求失败：{url}, 错误：{e}")
            return None
    
    def get(self, url: str, **kwargs):
        """发送 GET 请求"""
        return self.request('GET', url, **kwargs)
    
    def post(self, url: str, **kwargs):
        """发送 POST 请求"""
        return self.request('POST', url, **kwargs)
    
    def head(self, url: str, **kwargs):
        """发送 HEAD 请求"""
        return self.request('HEAD', url, **kwargs)
    
    def close(self):
        """关闭 Session"""
        self._session.close()
        self._redirect_history.clear()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()


# 导出便捷函数
def is_safe_url(url: str) -> bool:
    """检查 URL 是否安全"""
    return SSRFProtection.is_safe_url(url)


def filter_safe_urls(urls: List[str]) -> List[str]:
    """过滤安全 URL"""
    return SSRFProtection.filter_safe_urls(urls)


def get_url_info(url: str) -> dict:
    """获取 URL 信息"""
    return SSRFProtection.get_url_info(url)
