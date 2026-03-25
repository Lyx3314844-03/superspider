"""
分布式爬虫模块
支持 Redis 分布式调度
"""

import redis
import json
import time
import threading
from typing import Optional, Callable, Dict, Any, List
from pyspider.core.models import Request
from pyspider.core.spider import Spider


class RedisScheduler:
    """Redis 分布式调度器"""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        password: str = None,
        db: int = 0,
        spider_name: str = "spider",
    ):
        self.redis_client = redis.Redis(
            host=host,
            port=port,
            password=password,
            db=db,
            decode_responses=False,
        )
        self.spider_name = spider_name
        self.queue_key = f"pyspider:{spider_name}:queue"
        self.visited_key = f"pyspider:{spider_name}:visited"
        self.stats_key = f"pyspider:{spider_name}:stats"
    
    def add_request(self, request: Request) -> bool:
        """添加请求到队列"""
        # 检查是否已访问
        if self.is_visited(request.url):
            return False
        
        # 添加到队列
        data = json.dumps({
            "url": request.url,
            "method": request.method,
            "headers": request.headers,
            "body": request.body,
            "meta": request.meta,
            "priority": request.priority,
        }).encode()
        
        self.redis_client.lpush(self.queue_key, data)
        self.mark_visited(request.url)
        
        return True
    
    def next_request(self) -> Optional[Request]:
        """从队列获取下一个请求"""
        data = self.redis_client.rpop(self.queue_key)
        if not data:
            return None
        
        req_data = json.loads(data.decode())
        return Request(
            url=req_data["url"],
            method=req_data["method"],
            headers=req_data.get("headers", {}),
            body=req_data.get("body"),
            meta=req_data.get("meta", {}),
            priority=req_data.get("priority", 0),
        )
    
    def is_visited(self, url: str) -> bool:
        """检查是否已访问"""
        return self.redis_client.exists(f"{self.visited_key}:{url}") > 0
    
    def mark_visited(self, url: str) -> None:
        """标记为已访问"""
        self.redis_client.setex(f"{self.visited_key}:{url}", 86400, "1")
    
    def update_stats(self, field: str, value: int) -> None:
        """更新统计"""
        self.redis_client.hincrby(self.stats_key, field, value)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        data = self.redis_client.hgetall(self.stats_key)
        return {k.decode(): int(v) for k, v in data.items()}
    
    def queue_len(self) -> int:
        """获取队列长度"""
        return self.redis_client.llen(self.queue_key)
    
    def visited_count(self) -> int:
        """获取已访问数量"""
        keys = self.redis_client.keys(f"{self.visited_key}:*")
        return len(keys)
    
    def close(self) -> None:
        """关闭连接"""
        self.redis_client.close()


class DistributedSpider:
    """分布式爬虫"""
    
    def __init__(
        self,
        name: str,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_password: str = None,
        redis_db: int = 0,
        thread_count: int = 5,
    ):
        self.name = name
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_password = redis_password
        self.redis_db = redis_db
        self.thread_count = thread_count
        self.scheduler = None
        self.running = False
    
    def start(
        self,
        callback: Callable[[Request], None],
        master: bool = False,
        start_urls: List[str] = None,
    ) -> None:
        """启动分布式爬虫
        
        Args:
            callback: 处理函数
            master: 是否为主节点（负责添加起始 URL）
            start_urls: 起始 URL 列表（仅主节点使用）
        """
        self.scheduler = RedisScheduler(
            host=self.redis_host,
            port=self.redis_port,
            password=self.redis_password,
            db=self.redis_db,
            spider_name=self.name,
        )
        
        self.running = True
        
        # 主节点添加起始 URL
        if master and start_urls:
            for url in start_urls:
                req = Request(url=url)
                self.scheduler.add_request(req)
            print(f"[{self.name}] Added {len(start_urls)} start URLs")
        
        # 启动工作线程
        threads = []
        for i in range(self.thread_count):
            t = threading.Thread(target=self._worker, args=(callback,), daemon=True)
            t.start()
            threads.append(t)
        
        print(f"[{self.name}] Started with {self.thread_count} threads")
        
        # 保持运行
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
        
        # 等待线程结束
        for t in threads:
            t.join(timeout=1)
    
    def _worker(self, callback: Callable[[Request], None]) -> None:
        """工作线程"""
        while self.running:
            try:
                req = self.scheduler.next_request()
                if req is None:
                    time.sleep(0.5)
                    continue
                
                try:
                    callback(req)
                    self.scheduler.update_stats("success", 1)
                except Exception as e:
                    print(f"[{self.name}] Error processing {req.url}: {e}")
                    self.scheduler.update_stats("failed", 1)
                    
            except Exception as e:
                print(f"[{self.name}] Worker error: {e}")
                time.sleep(1)
    
    def stop(self) -> None:
        """停止爬虫"""
        self.running = False
        if self.scheduler:
            self.scheduler.close()
    
    def add_start_url(self, url: str) -> None:
        """添加起始 URL"""
        if self.scheduler:
            req = Request(url=url)
            self.scheduler.add_request(req)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        if self.scheduler:
            stats = self.scheduler.get_stats()
            stats["queue_len"] = self.scheduler.queue_len()
            stats["visited"] = self.scheduler.visited_count()
            return stats
        return {}


class DistributedScheduler:
    """分布式调度器（Scrapy 风格）"""
    
    def __init__(self, spider: Spider, redis_url: str = "redis://localhost:6379/0"):
        self.spider = spider
        self.redis_url = redis_url
        self.scheduler = None
    
    def open(self) -> None:
        """打开调度器"""
        from urllib.parse import urlparse
        
        parsed = urlparse(self.redis_url)
        self.scheduler = RedisScheduler(
            host=parsed.hostname or "localhost",
            port=parsed.port or 6379,
            password=parsed.password,
            db=int(parsed.path.strip("/") or 0),
            spider_name=self.spider.name,
        )
    
    def enqueue_request(self, request: Request) -> bool:
        """添加请求到队列"""
        if not self.scheduler:
            self.open()
        return self.scheduler.add_request(request)
    
    def next_request(self) -> Optional[Request]:
        """获取下一个请求"""
        if not self.scheduler:
            self.open()
        return self.scheduler.next_request()
    
    def close(self) -> None:
        """关闭调度器"""
        if self.scheduler:
            self.scheduler.close()
            self.scheduler = None
