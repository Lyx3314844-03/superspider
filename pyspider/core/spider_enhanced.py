"""
爬虫引擎 - 修复版
修复问题:
1. 添加类型注解
2. 完善错误处理
3. 资源管理优化
4. 添加线程安全
5. 添加超时控制
6. 添加监控指标
"""

import logging
import threading
import queue
import itertools
import time
from typing import List, Callable, Optional, Dict, Any, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from contextlib import contextmanager
import hashlib

from .models import Request, Response, Page
from .exceptions import SpiderError, MaxRetriesExceeded, CrawlError
from pyspider.downloader.downloader import HTTPDownloader


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SpiderStats:
    """爬虫统计信息"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_items: int = 0
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    
    @property
    def duration(self) -> float:
        """获取运行时长"""
        end = self.end_time or time.time()
        return end - self.start_time
    
    @property
    def requests_per_second(self) -> float:
        """获取每秒请求数"""
        if self.duration > 0:
            return self.total_requests / self.duration
        return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'total_items': self.total_items,
            'duration_seconds': round(self.duration, 2),
            'requests_per_second': round(self.requests_per_second, 2)
        }


class Spider:
    """爬虫引擎 - 修复版"""

    def __init__(
        self, 
        name: str = "Spider",
        thread_count: int = 5,
        max_retries: int = 3,
        request_timeout: int = 30,
        rate_limit: Optional[float] = None,
        enable_stats: bool = True
    ):
        self.name = name
        self.thread_count = thread_count
        self.max_retries = max_retries
        self.request_timeout = request_timeout
        self.rate_limit = rate_limit
        
        # 线程安全组件
        self._lock = threading.RLock()
        self._visited_urls: Set[str] = set()
        self._url_hashes: Set[str] = set()
        self._sequence = itertools.count()
        self._stop_event = threading.Event()
        
        # 下载器
        self.downloader = HTTPDownloader(timeout=request_timeout)
        
        # 管道和中间件
        self.pipelines: List[Callable[[Page], None]] = []
        self.middlewares: List[Callable[[Request], Optional[Request]]] = []
        
        # 统计信息
        self.stats = SpiderStats() if enable_stats else None
        
        # 队列
        self._queue: queue.PriorityQueue = queue.PriorityQueue()
        self._executor: Optional[ThreadPoolExecutor] = None
        
        logger.info(f"Spider [{name}] initialized with {thread_count} threads")

    def set_start_urls(self, *urls: str) -> 'Spider':
        """设置起始 URL"""
        for url in urls:
            if self._validate_url(url):
                self.start_urls.append(url)
            else:
                logger.warning(f"Invalid URL skipped: {url[:100]}")
        return self

    def set_thread_count(self, count: int) -> 'Spider':
        """设置线程数"""
        if count < 1:
            raise ValueError("Thread count must be at least 1")
        self.thread_count = count
        return self

    def add_pipeline(self, func: Callable[[Page], None]) -> 'Spider':
        """添加数据管道"""
        self.pipelines.append(func)
        logger.debug(f"Pipeline added: {func.__name__}")
        return self

    def add_middleware(self, func: Callable[[Request], Optional[Request]]) -> 'Spider':
        """添加中间件"""
        self.middlewares.append(func)
        logger.debug(f"Middleware added: {func.__name__}")
        return self

    @staticmethod
    def _validate_url(url: str) -> bool:
        """验证 URL"""
        if not url:
            return False
        if not isinstance(url, str):
            return False
        # 检查协议
        if not (url.startswith('http://') or url.startswith('https://')):
            return False
        # 检查长度
        if len(url) > 2048:
            return False
        return True

    @staticmethod
    def _url_hash(url: str) -> str:
        """生成 URL 哈希"""
        return hashlib.md5(url.encode()).hexdigest()

    def _is_duplicate(self, url: str) -> bool:
        """检查是否重复"""
        url_hash = self._url_hash(url)
        with self._lock:
            if url_hash in self._url_hashes:
                return True
            self._url_hashes.add(url_hash)
            return False

    def _process_request(self, req: Request, retry_count: int = 0) -> bool:
        """处理请求 - 带重试"""
        try:
            # 执行中间件
            for middleware in self.middlewares:
                try:
                    result = middleware(req)
                    if result is None:
                        logger.debug(f"Request filtered by middleware: {req.url}")
                        return True
                    req = result
                except Exception as e:
                    logger.error(f"Middleware error: {e}")
                    continue

            # 下载页面
            resp = self.downloader.download(req)
            
            if resp.error:
                if retry_count < self.max_retries:
                    logger.warning(f"Retrying {req.url} ({retry_count + 1}/{self.max_retries}): {resp.error}")
                    time.sleep(0.5 * (retry_count + 1))
                    return self._process_request(req, retry_count + 1)
                else:
                    logger.error(f"Max retries exceeded for {req.url}: {resp.error}")
                    if self.stats:
                        self.stats.failed_requests += 1
                    return False

            # 创建页面对象
            page = Page(response=resp)

            # 执行回调
            if req.callback:
                try:
                    req.callback(page)
                except Exception as e:
                    logger.error(f"Callback error for {req.url}: {e}")

            # 执行管道
            for pipeline in self.pipelines:
                try:
                    pipeline(page)
                    if self.stats:
                        self.stats.total_items += 1
                except Exception as e:
                    logger.error(f"Pipeline error: {e}")

            if self.stats:
                self.stats.successful_requests += 1
            
            return True

        except Exception as e:
            logger.error(f"Error processing {req.url}: {e}")
            if retry_count < self.max_retries:
                return self._process_request(req, retry_count + 1)
            if self.stats:
                self.stats.failed_requests += 1
            return False

    def _worker(self, future: Any) -> None:
        """工作线程回调"""
        try:
            req = future.result()
            if req:
                self._process_request(req)
        except Exception as e:
            logger.error(f"Worker error: {e}")
        finally:
            if self.stats:
                self.stats.total_requests += 1

    @contextmanager
    def _rate_limit_context(self):
        """速率限制上下文"""
        if self.rate_limit:
            start = time.time()
            yield
            elapsed = time.time() - start
            min_interval = 1.0 / self.rate_limit
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
        else:
            yield

    def start(self) -> None:
        """启动爬虫 - 使用线程池"""
        logger.info(f"Spider [{self.name}] starting with {self.thread_count} threads")
        
        if self.stats:
            self.stats = SpiderStats()
        
        self._stop_event.clear()
        self._executor = ThreadPoolExecutor(max_workers=self.thread_count)
        
        try:
            futures = []
            
            # 添加起始请求
            for url in self.start_urls:
                if not self._is_duplicate(url):
                    req = Request(url=url, callback=self._parse)
                    with self._rate_limit_context():
                        future = self._executor.submit(self._process_request, req)
                        futures.append(future)
            
            # 等待所有任务完成
            for future in as_completed(futures):
                if self._stop_event.is_set():
                    break
                    
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, stopping...")
            self._stop_event.set()
        except Exception as e:
            logger.error(f"Spider error: {e}")
            raise
        finally:
            self._executor.shutdown(wait=True)
            
            if self.stats:
                self.stats.end_time = time.time()
                logger.info(f"Spider [{self.name}] finished - Stats: {self.stats.to_dict()}")
            else:
                logger.info(f"Spider [{self.name}] finished")

    def _parse(self, page: Page) -> None:
        """默认解析函数"""
        logger.debug(f"Parsed: {page.response.url} (Status: {page.response.status_code})")

    def add_request(self, req: Request) -> bool:
        """添加请求 - 线程安全"""
        with self._lock:
            if self._is_duplicate(req.url):
                logger.debug(f"Duplicate URL skipped: {req.url}")
                return False
            
            if self._executor:
                future = self._executor.submit(self._process_request, req)
                return True
            return False

    def stop(self) -> None:
        """停止爬虫"""
        logger.info(f"Stopping spider [{self.name}]")
        self._stop_event.set()
        if self._executor:
            self._executor.shutdown(wait=False)

    def get_stats(self) -> Optional[Dict[str, Any]]:
        """获取统计信息"""
        if self.stats:
            return self.stats.to_dict()
        return None

    def __enter__(self) -> 'Spider':
        """上下文管理器进入"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """上下文管理器退出"""
        self.stop()
        if exc_type:
            logger.error(f"Spider exited with exception: {exc_val}")
