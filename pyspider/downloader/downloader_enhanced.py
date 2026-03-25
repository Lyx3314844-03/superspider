"""
HTTP 下载器 - 修复版
修复问题:
1. 连接池管理
2. 资源泄漏修复
3. 添加重试机制
4. 添加 SSL 验证
5. 添加 User-Agent 轮换
6. 添加请求速率限制
"""

import time
import random
from typing import Optional, Dict, List
from contextlib import contextmanager
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from pyspider.core.models import Request, Response
from pyspider.core.exceptions import DownloadError, TimeoutError


class HTTPDownloader:
    """HTTP 下载器 - 修复版"""

    # 默认 User-Agent 列表
    DEFAULT_USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]

    def __init__(
        self,
        timeout: int = 30,
        pool_connections: int = 10,
        pool_maxsize: int = 50,
        max_retries: int = 3,
        verify_ssl: bool = True,
        random_ua: bool = True,
        rate_limit: Optional[float] = None,
        proxy: Optional[str] = None,
    ):
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.random_ua = random_ua
        self.rate_limit = rate_limit
        self.proxy = proxy
        
        # 创建会话（连接池）
        self.session = self._create_session(
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize,
            max_retries=max_retries
        )
        
        # 代理设置
        if proxy:
            self.set_proxy(proxy)
        
        self._last_request_time: float = 0

    @staticmethod
    def _create_session(
        pool_connections: int = 10,
        pool_maxsize: int = 50,
        max_retries: int = 3
    ) -> requests.Session:
        """创建带重试策略的会话"""
        session = requests.Session()
        
        # 配置重试策略
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
        )
        
        adapter = HTTPAdapter(
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize,
            max_retries=retry_strategy,
            pool_block=False
        )
        
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session

    @contextmanager
    def _rate_limit_context(self):
        """速率限制上下文管理器"""
        if self.rate_limit:
            elapsed = time.time() - self._last_request_time
            min_interval = 1.0 / self.rate_limit
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
        
        yield
        
        self._last_request_time = time.time()

    def _get_user_agent(self) -> str:
        """获取 User-Agent"""
        if self.random_ua:
            return random.choice(self.DEFAULT_USER_AGENTS)
        return self.DEFAULT_USER_AGENTS[0]

    def download(self, req: Request) -> Response:
        """下载页面 - 带资源管理"""
        start_time = time.time()
        
        # 确保有 User-Agent
        headers = req.headers.copy() if req.headers else {}
        if 'User-Agent' not in headers:
            headers['User-Agent'] = self._get_user_agent()

        try:
            with self._rate_limit_context():
                # 使用上下文管理器确保连接关闭
                resp = self.session.request(
                    method=req.method.upper(),
                    url=req.url,
                    headers=headers,
                    data=req.body,
                    cookies=req.cookies,
                    timeout=self.timeout,
                    verify=self.verify_ssl,
                    stream=False,
                    allow_redirects=True
                )

                duration = time.time() - start_time

                # 检查响应状态
                if resp.status_code >= 400:
                    return Response(
                        url=req.url,
                        status_code=resp.status_code,
                        headers=dict(resp.headers),
                        content=b'',
                        text='',
                        request=req,
                        duration=duration,
                        error=DownloadError(f"HTTP {resp.status_code}")
                    )

                return Response(
                    url=req.url,
                    status_code=resp.status_code,
                    headers=dict(resp.headers),
                    content=resp.content,
                    text=resp.text,
                    request=req,
                    duration=duration,
                    error=None
                )

        except requests.exceptions.Timeout as e:
            return Response(
                url=req.url,
                status_code=0,
                headers={},
                content=b'',
                text='',
                request=req,
                duration=time.time() - start_time,
                error=TimeoutError(f"Request timeout: {e}")
            )
            
        except requests.exceptions.SSLError as e:
            return Response(
                url=req.url,
                status_code=0,
                headers={},
                content=b'',
                text='',
                request=req,
                duration=time.time() - start_time,
                error=DownloadError(f"SSL error: {e}")
            )
            
        except requests.exceptions.RequestException as e:
            return Response(
                url=req.url,
                status_code=0,
                headers={},
                content=b'',
                text='',
                request=req,
                duration=time.time() - start_time,
                error=DownloadError(f"Request failed: {e}")
            )
            
        except Exception as e:
            return Response(
                url=req.url,
                status_code=0,
                headers={},
                content=b'',
                text='',
                request=req,
                duration=time.time() - start_time,
                error=DownloadError(f"Unexpected error: {e}")
            )

    def set_timeout(self, timeout: int) -> None:
        """设置超时"""
        if timeout < 1:
            raise ValueError("Timeout must be at least 1 second")
        self.timeout = timeout

    def set_headers(self, headers: Dict[str, str]) -> None:
        """设置默认请求头"""
        if not isinstance(headers, dict):
            raise TypeError("Headers must be a dictionary")
        self.session.headers.update(headers)

    def set_cookies(self, cookies: Dict[str, str]) -> None:
        """设置 Cookie"""
        if not isinstance(cookies, dict):
            raise TypeError("Cookies must be a dictionary")
        self.session.cookies.update(cookies)

    def set_proxy(self, proxy: str) -> None:
        """设置代理"""
        if not proxy:
            raise ValueError("Proxy URL cannot be empty")
        
        proxies = {
            "http": proxy,
            "https": proxy
        }
        self.session.proxies.update(proxies)
        self.proxy = proxy

    def clear_proxy(self) -> None:
        """清除代理设置"""
        self.session.proxies.clear()
        self.proxy = None

    def close(self) -> None:
        """关闭下载器，释放资源"""
        if self.session:
            self.session.close()
            self.session = None

    def __enter__(self) -> 'HTTPDownloader':
        """上下文管理器进入"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """上下文管理器退出"""
        self.close()

    def __del__(self) -> None:
        """析构函数，确保资源释放"""
        self.close()
