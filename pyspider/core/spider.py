"""
爬虫引擎
"""

import logging
import threading
import queue
import itertools
from typing import List, Callable, Optional
from concurrent.futures import ThreadPoolExecutor

from .models import Request, Response, Page
from pyspider.downloader.downloader import HTTPDownloader


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Spider:
    """爬虫引擎"""
    
    def __init__(self, name: str = "Spider"):
        self.name = name
        self.start_urls: List[str] = []
        self.thread_count: int = 5
        self.downloader = HTTPDownloader()
        self.pipelines: List[Callable[[Page], None]] = []
        self.request_queue = queue.PriorityQueue()
        self.visited_urls = set()
        self._lock = threading.Lock()
        self._sequence = itertools.count()
    
    def set_start_urls(self, *urls: str) -> 'Spider':
        """设置起始 URL"""
        self.start_urls.extend(urls)
        return self
    
    def set_thread_count(self, count: int) -> 'Spider':
        """设置线程数"""
        self.thread_count = count
        return self
    
    def add_pipeline(self, func: Callable[[Page], None]) -> 'Spider':
        """添加数据管道"""
        self.pipelines.append(func)
        return self
    
    def _parse(self, page: Page) -> None:
        """默认解析函数"""
        logger.info(f"Parsed: {page.response.url} (Status: {page.response.status_code})")
    
    def _process_request(self, req: Request) -> None:
        """处理请求"""
        try:
            # 下载页面
            resp = self.downloader.download(req)
            if resp.error:
                logger.error(f"Download error: {resp.error}")
                return
            
            # 创建页面对象
            page = Page(response=resp)
            
            # 执行回调
            if req.callback:
                req.callback(page)
            
            # 执行管道
            for pipeline in self.pipelines:
                pipeline(page)
                
        except Exception as e:
            logger.error(f"Error processing {req.url}: {e}")
    
    def _worker(self) -> None:
        """工作线程"""
        while True:
            try:
                priority, _, req = self.request_queue.get(timeout=1)
                if req is None:  # 停止信号
                    break
                self._process_request(req)
                self.request_queue.task_done()
            except queue.Empty:
                break
    
    def start(self) -> None:
        """启动爬虫"""
        logger.info(f"Spider [{self.name}] started with {self.thread_count} threads")
        
        # 添加起始请求
        for url in self.start_urls:
            req = Request(url=url, callback=self._parse)
            self.request_queue.put((req.priority, next(self._sequence), req))
        
        # 启动工作线程
        threads = []
        for _ in range(self.thread_count):
            t = threading.Thread(target=self._worker)
            t.start()
            threads.append(t)
        
        # 等待队列完成
        self.request_queue.join()
        
        # 发送停止信号
        for _ in range(self.thread_count):
            self.request_queue.put((0, next(self._sequence), None))
        
        # 等待线程结束
        for t in threads:
            t.join()
        
        logger.info(f"Spider [{self.name}] finished")
    
    def add_request(self, req: Request) -> None:
        """添加请求"""
        with self._lock:
            if req.url not in self.visited_urls:
                self.visited_urls.add(req.url)
                self.request_queue.put((req.priority, next(self._sequence), req))
