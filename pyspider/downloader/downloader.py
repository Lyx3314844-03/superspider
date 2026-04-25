"""
Canonical HTTP downloader for pyspider.

This is now the single implementation used by the framework. Older
`downloader_enhanced.py` callers are expected to move here.
"""

from __future__ import annotations

import logging
import random
import threading
import time
from contextlib import contextmanager
from typing import Dict, List, Optional

import requests

from pyspider.antibot.friction import analyze_access_friction
from pyspider.core.exceptions import DownloadError, TimeoutError as SpiderTimeoutError
from pyspider.core.models import Request, Response

logger = logging.getLogger(__name__)


class HTTPDownloader:
    """HTTP downloader with retry, proxy, robots, incremental, and rate-limit support."""

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
        retry_delay: float = 1.0,
        backoff_factor: float = 2.0,
        retry_on_status: Optional[List[int]] = None,
    ):
        if timeout < 1:
            raise ValueError("Timeout must be at least 1 second")

        self.session = requests.Session()
        self.timeout = timeout
        self.pool_connections = pool_connections
        self.pool_maxsize = pool_maxsize
        self.max_retries = max_retries
        self.verify_ssl = verify_ssl
        self.random_ua = random_ua
        self.rate_limit = rate_limit
        self.proxy = None
        self.retry_delay = retry_delay
        self.backoff_factor = backoff_factor
        self.retry_on_status = retry_on_status or [429, 500, 502, 503, 504]

        self._proxy_pool = None
        self._incremental = None
        self._robots_checker = None
        self._min_request_interval = 0.0
        self._last_request_time = 0.0
        self._rate_limit_lock = threading.Lock()
        self._user_agents: List[str] = []
        self._current_ua_index = 0

        if proxy:
            self.set_proxy(proxy)

    def set_proxy_pool(self, proxy_pool) -> None:
        self._proxy_pool = proxy_pool

    def set_incremental(self, incremental) -> None:
        self._incremental = incremental

    def set_robots_checker(self, robots_checker) -> None:
        self._robots_checker = robots_checker

    def set_user_agents(self, user_agents: List[str]) -> None:
        self._user_agents = list(user_agents)

    def set_min_request_interval(self, seconds: float) -> None:
        self._min_request_interval = max(0.0, float(seconds))

    def _get_user_agent(self) -> str:
        if self._user_agents:
            if self.random_ua:
                return random.choice(self._user_agents)
            user_agent = self._user_agents[
                self._current_ua_index % len(self._user_agents)
            ]
            self._current_ua_index += 1
            return user_agent
        if self.random_ua:
            return random.choice(self.DEFAULT_USER_AGENTS)
        return self.DEFAULT_USER_AGENTS[0]

    def _current_min_interval(self) -> float:
        intervals = [self._min_request_interval]
        if self.rate_limit:
            intervals.append(1.0 / self.rate_limit)
        return max(intervals)

    def _effective_min_interval(self, url: Optional[str] = None) -> float:
        interval = self._current_min_interval()
        if self._robots_checker and url:
            try:
                crawl_delay = self._robots_checker.get_crawl_delay(url)
                if crawl_delay and crawl_delay > interval:
                    interval = float(crawl_delay)
            except Exception:
                pass
        return interval

    @contextmanager
    def _rate_limit_context(self, min_interval: Optional[float] = None):
        with self._rate_limit_lock:
            if min_interval is None:
                min_interval = self._current_min_interval()
            if min_interval > 0:
                elapsed = time.time() - self._last_request_time
                if elapsed < min_interval:
                    time.sleep(min_interval - elapsed)
            try:
                yield
            finally:
                self._last_request_time = time.time()

    def download(self, req: Request) -> Response:
        start_time = time.time()

        if self._robots_checker and not self._robots_checker.is_allowed(req.url):
            logger.warning("robots.txt forbids: %s", req.url)
            return Response(
                url=req.url,
                status_code=403,
                headers={},
                content=b"",
                text="",
                request=req,
                duration=time.time() - start_time,
                error=PermissionError(f"robots.txt forbids: {req.url}"),
                meta=self._access_friction_meta(403, {}, "", req.url),
            )

        headers = dict(req.headers)
        if self._incremental:
            conditional_headers = self._incremental.get_conditional_headers(req.url)
            if conditional_headers:
                headers.update(conditional_headers)
        if not headers.get("User-Agent"):
            headers["User-Agent"] = self._get_user_agent()

        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                proxy = None
                proxies = dict(self.session.proxies) if self.session.proxies else None
                if self._proxy_pool:
                    proxy = self._proxy_pool.get_proxy()
                    if proxy:
                        proxies = proxy.proxies_dict
                    else:
                        logger.warning("no healthy proxy available")

                with self._rate_limit_context(self._effective_min_interval(req.url)):
                    resp = self.session.request(
                        method=req.method,
                        url=req.url,
                        headers=headers,
                        data=req.body,
                        cookies=getattr(req, "cookies", {}),
                        timeout=self.timeout,
                        verify=self.verify_ssl,
                        proxies=proxies,
                        stream=False,
                        allow_redirects=True,
                    )

                duration = time.time() - start_time

                if self._proxy_pool and proxy and proxies:
                    if resp.status_code < 400:
                        self._proxy_pool.record_success(proxy)
                    else:
                        self._proxy_pool.record_failure(proxy)

                access_friction = analyze_access_friction(
                    html=resp.text,
                    status_code=resp.status_code,
                    headers=dict(resp.headers),
                    url=req.url,
                )
                access_friction_meta = {"access_friction": access_friction.to_dict()}

                if (
                    resp.status_code in self.retry_on_status
                    and self._should_retry_with_friction(
                        access_friction.to_dict(), attempt
                    )
                ):
                    retry_after = self.retry_delay * (self.backoff_factor**attempt)
                    if access_friction.retry_after_seconds is not None:
                        retry_after = max(
                            retry_after, float(access_friction.retry_after_seconds)
                        )
                    time.sleep(retry_after)
                    continue

                if resp.status_code == 304:
                    if self._incremental:
                        self._incremental.update_cache(
                            req.url, content=b"", status_code=304
                        )
                    return Response(
                        url=req.url,
                        status_code=304,
                        headers=dict(resp.headers),
                        content=b"",
                        text="",
                        request=req,
                        duration=duration,
                        error=None,
                        meta=self._access_friction_meta(304, dict(resp.headers), "", req.url),
                    )

                if self._incremental and resp.status_code == 200:
                    self._incremental.update_cache(
                        req.url,
                        etag=resp.headers.get("ETag"),
                        last_modified=resp.headers.get("Last-Modified"),
                        content=resp.content,
                        status_code=resp.status_code,
                    )

                if resp.status_code >= 400:
                    return Response(
                        url=req.url,
                        status_code=resp.status_code,
                        headers=dict(resp.headers),
                        content=resp.content,
                        text=resp.text,
                        request=req,
                        duration=duration,
                        error=DownloadError(
                            f"HTTP {resp.status_code}",
                            url=req.url,
                            status_code=resp.status_code,
                        ),
                        meta=access_friction_meta,
                    )

                return Response(
                    url=req.url,
                    status_code=resp.status_code,
                    headers=dict(resp.headers),
                    content=resp.content,
                    text=resp.text,
                    request=req,
                    duration=duration,
                    error=None,
                    meta=access_friction_meta,
                )
            except requests.exceptions.Timeout as exc:
                last_error = SpiderTimeoutError(f"Request timeout: {exc}", url=req.url)
            except requests.exceptions.SSLError as exc:
                last_error = DownloadError(f"SSL error: {exc}", url=req.url)
            except requests.exceptions.ConnectionError as exc:
                last_error = DownloadError(f"Request failed: {exc}", url=req.url)
            except requests.exceptions.RequestException as exc:
                last_error = DownloadError(f"Request failed: {exc}", url=req.url)
            except (
                Exception
            ) as exc:  # preserves built-in TimeoutError behavior for existing tests
                last_error = exc

            if attempt < self.max_retries:
                delay = self.retry_delay * (
                    self.backoff_factor**attempt
                ) + random.uniform(0, 1)
                time.sleep(delay)

        return Response(
            url=req.url,
            status_code=0,
            headers={},
            content=b"",
            text="",
            request=req,
            duration=time.time() - start_time,
            error=last_error,
            meta=self._access_friction_meta(0, {}, "", req.url),
        )

    def _access_friction_meta(
        self, status_code: int, headers: Dict[str, str], text: str, url: str
    ) -> Dict[str, object]:
        report = analyze_access_friction(
            html=text,
            status_code=status_code,
            headers=headers,
            url=url,
        )
        return {"access_friction": report.to_dict()}

    def _should_retry_with_friction(
        self, access_friction: Dict[str, object], attempt: int
    ) -> bool:
        if attempt >= self.max_retries:
            return False
        if access_friction.get("requires_human_access"):
            return False
        capability_plan = access_friction.get("capability_plan")
        retry_budget = self.max_retries
        if isinstance(capability_plan, dict):
            raw_budget = capability_plan.get("retry_budget")
            if isinstance(raw_budget, int):
                retry_budget = raw_budget
        return attempt < min(self.max_retries, retry_budget)

    def set_timeout(self, timeout: int) -> None:
        if timeout < 1:
            raise ValueError("Timeout must be at least 1 second")
        self.timeout = timeout

    def set_headers(self, headers: Dict[str, str]) -> None:
        if not isinstance(headers, dict):
            raise TypeError("Headers must be a dictionary")
        self.session.headers.update(headers)

    def set_cookies(self, cookies: Dict[str, str]) -> None:
        if not isinstance(cookies, dict):
            raise TypeError("Cookies must be a dictionary")
        self.session.cookies.update(cookies)

    def set_proxy(self, proxy: str) -> None:
        if not proxy:
            raise ValueError("Proxy URL cannot be empty")
        self.session.proxies.update({"http": proxy, "https": proxy})
        self.proxy = proxy

    def clear_proxy(self) -> None:
        self.session.proxies.clear()
        self.proxy = None

    def close(self) -> None:
        if self.session is not None:
            self.session.close()
            self.session = None

    def __enter__(self) -> "HTTPDownloader":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def __del__(self) -> None:  # pragma: no cover
        self.close()
