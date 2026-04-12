"""
异步 HTTP 下载器 - 高性能 aiohttp 版本
使用 asyncio 实现真正的异步并发，大幅提升爬取速度
"""

import asyncio
import time
import logging
from typing import Optional, Dict, List
import aiohttp

from pyspider.core.models import Request, Response

logger = logging.getLogger(__name__)


class AsyncHTTPDownloader:
    """异步 HTTP 下载器 - 高性能版本"""

    def __init__(
        self,
        timeout: int = 30,
        max_retries: int = 3,
        max_concurrent: int = 100,
        retry_delay: float = 1.0,
        backoff_factor: float = 2.0,
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self.max_concurrent = max_concurrent
        self.retry_delay = retry_delay
        self.backoff_factor = backoff_factor
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._session: Optional[aiohttp.ClientSession] = None
        self._proxy_pool = None
        self._incremental = None
        self._robots_checker = None
        self._user_agents: List[str] = []
        self._ua_index = 0
        self._rate_limit_lock = asyncio.Lock()
        self._last_request_time = 0.0
        self._min_request_interval = 0.0

    async def __aenter__(self):
        await self._ensure_session()
        return self

    async def __aexit__(self, *args):
        await self.close()

    async def _ensure_session(self):
        """确保 session 已创建"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            connector = aiohttp.TCPConnector(
                limit=self.max_concurrent,
                limit_per_host=10,
                enable_cleanup_closed=True,
            )
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                headers={
                    "User-Agent": (
                        self._user_agents[0] if self._user_agents else "pyspider/2.0"
                    )
                },
            )

    async def close(self):
        """关闭 session"""
        if self._session and not self._session.closed:
            await self._session.close()

    def set_proxy_pool(self, proxy_pool) -> None:
        self._proxy_pool = proxy_pool

    def set_incremental(self, incremental) -> None:
        self._incremental = incremental

    def set_robots_checker(self, robots_checker) -> None:
        self._robots_checker = robots_checker

    def set_user_agents(self, user_agents: List[str]) -> None:
        self._user_agents = user_agents

    def set_min_request_interval(self, seconds: float) -> None:
        self._min_request_interval = seconds

    def _get_next_user_agent(self) -> Optional[str]:
        if not self._user_agents:
            return None
        ua = self._user_agents[self._ua_index % len(self._user_agents)]
        self._ua_index += 1
        return ua

    def _effective_min_interval(self, url: Optional[str] = None) -> float:
        interval = self._min_request_interval
        if self._robots_checker and url:
            try:
                crawl_delay = self._robots_checker.get_crawl_delay(url)
                if crawl_delay and crawl_delay > interval:
                    interval = float(crawl_delay)
            except Exception:
                pass
        return interval

    async def _apply_rate_limit(self, url: Optional[str] = None) -> None:
        """速率限制 (异步)"""
        min_interval = self._effective_min_interval(url)
        if min_interval > 0:
            async with self._rate_limit_lock:
                elapsed = time.time() - self._last_request_time
                if elapsed < min_interval:
                    await asyncio.sleep(min_interval - elapsed)
                self._last_request_time = time.time()

    async def download(self, req: Request) -> Response:
        """异步下载页面"""
        start_time = time.time()

        # robots.txt 检查
        if self._robots_checker and not self._robots_checker.is_allowed(req.url):
            logger.warning(f"robots.txt 禁止: {req.url}")
            return Response(
                url=req.url,
                status_code=403,
                headers={},
                content=b"",
                text="",
                request=req,
                duration=time.time() - start_time,
                error=PermissionError(f"robots.txt forbids: {req.url}"),
            )

        # 速率限制
        await self._apply_rate_limit(req.url)

        # 构建请求头
        headers = dict(req.headers)
        if not headers.get("User-Agent") and self._user_agents:
            headers["User-Agent"] = self._get_next_user_agent()

        # 并发控制
        async with self._semaphore:
            return await self._do_download(req, headers, start_time)

    async def _do_download(
        self, req: Request, headers: Dict[str, str], start_time: float, attempt: int = 0
    ) -> Response:
        """执行下载 (带重试)"""
        try:
            await self._ensure_session()

            # 代理设置
            proxy = None
            if self._proxy_pool:
                p = self._proxy_pool.get_proxy()
                if p:
                    proxy = p.url

            # 执行请求
            async with self._session.request(
                method=req.method,
                url=req.url,
                headers=headers,
                data=req.body,
                proxy=proxy,
                allow_redirects=True,
            ) as resp:
                content = await resp.read()
                text = await resp.text(errors="replace")
                duration = time.time() - start_time

                # 记录代理结果
                if self._proxy_pool and proxy and p:
                    if resp.status < 400:
                        self._proxy_pool.record_success(p)
                    else:
                        self._proxy_pool.record_failure(p)

                # 更新增量缓存
                if self._incremental and resp.status == 200:
                    etag = resp.headers.get("ETag")
                    last_modified = resp.headers.get("Last-Modified")
                    self._incremental.update_cache(
                        req.url,
                        etag=etag,
                        last_modified=last_modified,
                        content=content,
                        status_code=resp.status,
                    )

                if (
                    resp.status in {429, 500, 502, 503, 504}
                    and attempt < self.max_retries
                ):
                    delay = self.retry_delay * (self.backoff_factor**attempt)
                    retry_after = resp.headers.get("Retry-After")
                    if retry_after:
                        try:
                            delay = max(delay, float(retry_after))
                        except ValueError:
                            pass
                    await asyncio.sleep(delay)
                    return await self._do_download(
                        req, headers, start_time, attempt + 1
                    )

                error = None
                if resp.status >= 400:
                    error = Exception(f"HTTP {resp.status}")

                return Response(
                    url=req.url,
                    status_code=resp.status,
                    headers=dict(resp.headers),
                    content=content,
                    text=text,
                    request=req,
                    duration=duration,
                    error=error,
                )

        except asyncio.TimeoutError as e:
            last_error = e
        except aiohttp.ClientError as e:
            last_error = e
        except Exception as e:
            last_error = e

        # 重试逻辑
        if attempt < self.max_retries:
            delay = self.retry_delay * (self.backoff_factor**attempt)
            logger.warning(
                f"请求失败({attempt+1}/{self.max_retries}): {req.url}, {delay:.1f}s 后重试"
            )
            await asyncio.sleep(delay)
            return await self._do_download(req, headers, start_time, attempt + 1)

        return Response(
            url=req.url,
            status_code=0,
            headers={},
            content=b"",
            text="",
            request=req,
            duration=time.time() - start_time,
            error=last_error,
        )

    async def download_batch(self, requests: List[Request]) -> List[Response]:
        """批量异步下载"""
        tasks = [self.download(req) for req in requests]
        return await asyncio.gather(*tasks, return_exceptions=True)
