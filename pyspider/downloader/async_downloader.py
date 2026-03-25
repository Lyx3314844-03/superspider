"""
高性能下载器
使用 aiohttp 和连接池优化
"""

import aiohttp
import asyncio
import time
from typing import Dict, Optional, List
from dataclasses import dataclass
import threading
import logging

from pyspider.core.models import Request, Response

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class DownloaderConfig:
    """下载器配置"""
    max_connections: int = 100  # 最大连接数
    timeout: int = 30  # 超时时间
    max_retries: int = 3  # 最大重试
    retry_delay: float = 1.0  # 重试延迟
    rate_limit: float = 0  # 频率限制
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    enable_cookies: bool = True
    follow_redirects: bool = True
    verify_ssl: bool = True


class AsyncHTTPDownloader:
    """异步 HTTP 下载器"""
    
    def __init__(self, config: DownloaderConfig = None):
        self.config = config or DownloaderConfig()
        self._session: Optional[aiohttp.ClientSession] = None
        self._semaphore = asyncio.Semaphore(self.config.max_connections)
        self._rate_limiter = RateLimiter(self.config.rate_limit) if self.config.rate_limit > 0 else None
        self._stats = {
            'requests': 0,
            'success': 0,
            'failed': 0,
            'bytes_downloaded': 0,
        }
    
    async def __aenter__(self):
        connector = aiohttp.TCPConnector(
            limit=self.config.max_connections,
            ssl=self.config.verify_ssl,
            enable_cleanup_closed=True,
        )
        
        self._session = aiohttp.ClientSession(
            connector=connector,
            headers={'User-Agent': self.config.user_agent},
            timeout=aiohttp.ClientTimeout(total=self.config.timeout),
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.close()
    
    async def download(self, request: Request) -> Optional[Response]:
        """下载页面"""
        async with self._semaphore:
            if self._rate_limiter:
                await self._rate_limiter.wait()
            
            self._stats['requests'] += 1
            
            for attempt in range(self.config.max_retries):
                try:
                    async with self._session.get(
                        request.url,
                        headers=request.headers or {},
                        allow_redirects=self.config.follow_redirects,
                        cookies=request.cookies if self.config.enable_cookies else None,
                    ) as resp:
                        text = await resp.text()
                        content = await resp.read()
                        
                        self._stats['success'] += 1
                        self._stats['bytes_downloaded'] += len(content)
                        
                        return Response(
                            url=request.url,
                            status_code=resp.status,
                            headers=dict(resp.headers),
                            content=content,
                            text=text,
                            request=request,
                            duration=0,
                            error=None
                        )
                        
                except Exception as e:
                    if attempt < self.config.max_retries - 1:
                        await asyncio.sleep(self.config.retry_delay * (attempt + 1))
                    else:
                        self._stats['failed'] += 1
                        logger.error(f"下载失败 {request.url}: {e}")
                        return Response(
                            url=request.url,
                            status_code=0,
                            headers={},
                            content=b'',
                            text='',
                            request=request,
                            duration=0,
                            error=e
                        )
        
        return None
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return self._stats.copy()


class RateLimiter:
    """异步速率限制器"""
    
    def __init__(self, rate: float):
        self.rate = rate
        self.last_request = 0.0
        self._lock = asyncio.Lock()
    
    async def wait(self):
        async with self._lock:
            now = time.time()
            elapsed = now - self.last_request
            min_interval = 1.0 / self.rate
            
            if elapsed < min_interval:
                sleep_time = min_interval - elapsed
                await asyncio.sleep(sleep_time)
            
            self.last_request = time.time()


class ConnectionManager:
    """连接管理器"""
    
    def __init__(self, max_connections: int = 100):
        self.max_connections = max_connections
        self._active_connections = 0
        self._lock = threading.Lock()
        self._sessions: Dict[str, aiohttp.ClientSession] = {}
    
    def get_session(self, domain: str) -> aiohttp.ClientSession:
        """获取会话"""
        if domain not in self._sessions:
            connector = aiohttp.TCPConnector(
                limit=self.max_connections,
                enable_cleanup_closed=True,
            )
            self._sessions[domain] = aiohttp.ClientSession(connector=connector)
        
        return self._sessions[domain]
    
    async def close_all(self):
        """关闭所有会话"""
        for session in self._sessions.values():
            await session.close()
        self._sessions.clear()


class DownloadQueue:
    """下载队列（优先级）"""
    
    def __init__(self, max_size: int = 100000):
        self.max_size = max_size
        self._queue = asyncio.PriorityQueue(maxsize=max_size)
        self._seen = set()
        self._lock = asyncio.Lock()
    
    async def put(self, url: str, priority: int = 0, request: Request = None):
        """添加下载任务"""
        async with self._lock:
            if url in self._seen:
                return False
            
            if self._queue.full():
                return False
            
            self._seen.add(url)
            await self._queue.put((-priority, url, request))
            return True
    
    async def get(self) -> Optional[tuple]:
        """获取下载任务"""
        try:
            priority, url, request = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            return (-priority, url, request)
        except asyncio.TimeoutError:
            return None
    
    def size(self) -> int:
        """队列大小"""
        return self._queue.qsize()


class BatchDownloader:
    """批量下载器"""
    
    def __init__(self, config: DownloaderConfig = None):
        self.config = config or DownloaderConfig()
        self.downloader = AsyncHTTPDownloader(self.config)
        self.queue = DownloadQueue()
    
    async def download_batch(self, urls: List[str], max_concurrent: int = 50) -> List[Response]:
        """批量下载"""
        results = []
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def download_with_semaphore(url):
            async with semaphore:
                request = Request(url=url)
                return await self.downloader.download(request)
        
        tasks = [download_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return [r for r in results if isinstance(r, Response)]
    
    async def download_with_progress(self, urls: List[str]) -> List[Response]:
        """带进度显示的批量下载"""
        from tqdm import tqdm
        
        results = []
        semaphore = asyncio.Semaphore(self.config.max_connections)
        
        async def download_with_progress(url, pbar):
            async with semaphore:
                request = Request(url=url)
                result = await self.downloader.download(request)
                pbar.update(1)
                return result
        
        with tqdm(total=len(urls), desc='Downloading') as pbar:
            tasks = [download_with_progress(url, pbar) for url in urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return [r for r in results if isinstance(r, Response)]
