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
        self.pending_key = f"pyspider:{spider_name}:pending"
        self.processing_key = f"pyspider:{spider_name}:processing"
        self.dead_letter_key = f"pyspider:{spider_name}:dead"
        self.visited_key = f"pyspider:{spider_name}:visited"
        self.visited_set_key = f"pyspider:{spider_name}:visited:set"
        self.stats_key = f"pyspider:{spider_name}:stats"

    def add_request(self, request: Request) -> bool:
        """添加请求到队列"""
        if (
            self.is_visited(request.url)
            or self.redis_client.sismember(self.pending_key, request.url)
            or self.redis_client.hexists(self.processing_key, request.url)
        ):
            return False

        # 添加到队列
        data = json.dumps(
            {
                "url": request.url,
                "method": request.method,
                "headers": request.headers,
                "body": request.body,
                "meta": request.meta,
                "priority": request.priority,
            }
        ).encode()

        self.redis_client.lpush(self.queue_key, data)
        self.redis_client.sadd(self.pending_key, request.url)

        return True

    def lease_request(
        self, worker_id: str = "scheduler", lease_ttl: int = 30
    ) -> Optional[Request]:
        """通过租约获取下一个请求"""
        data = self.redis_client.rpop(self.queue_key)
        if not data:
            return None

        req_data = json.loads(data.decode())
        request = Request(
            url=req_data["url"],
            method=req_data["method"],
            headers=req_data.get("headers", {}),
            body=req_data.get("body"),
            meta=req_data.get("meta", {}),
            priority=req_data.get("priority", 0),
        )
        self.redis_client.srem(self.pending_key, request.url)
        lease = {
            "worker_id": worker_id,
            "expires_at": time.time() + lease_ttl,
            "request": req_data,
            "retry_count": int(req_data.get("meta", {}).get("retry_count", 0)),
        }
        self.redis_client.hset(
            self.processing_key, request.url, json.dumps(lease).encode()
        )
        return request

    def next_request(self) -> Optional[Request]:
        """从队列获取下一个请求"""
        return self.lease_request()

    def heartbeat(self, url: str, lease_ttl: int = 30) -> bool:
        payload = self.redis_client.hget(self.processing_key, url)
        if not payload:
            return False
        lease = json.loads(payload.decode() if isinstance(payload, bytes) else payload)
        lease["expires_at"] = time.time() + lease_ttl
        self.redis_client.hset(self.processing_key, url, json.dumps(lease).encode())
        return True

    def ack_request(self, url: str, success: bool = True, max_retries: int = 3) -> bool:
        payload = self.redis_client.hget(self.processing_key, url)
        if not payload:
            return False
        lease = json.loads(payload.decode() if isinstance(payload, bytes) else payload)
        self.redis_client.hdel(self.processing_key, url)
        if success:
            self.mark_visited(url)
            return True

        request_data = lease["request"]
        retry_count = int(lease.get("retry_count", 0)) + 1
        request_data.setdefault("meta", {})
        request_data["meta"]["retry_count"] = retry_count
        if retry_count > max_retries:
            self.redis_client.lpush(
                self.dead_letter_key, json.dumps(request_data).encode()
            )
            self.mark_visited(url)
        else:
            self.redis_client.lpush(self.queue_key, json.dumps(request_data).encode())
            self.redis_client.sadd(self.pending_key, url)
        return True

    def reap_expired_leases(
        self, now: Optional[float] = None, max_retries: int = 3
    ) -> int:
        now = now or time.time()
        reaped = 0
        for raw_url, raw_payload in list(
            self.redis_client.hgetall(self.processing_key).items()
        ):
            url = raw_url.decode() if isinstance(raw_url, bytes) else raw_url
            payload = (
                raw_payload.decode() if isinstance(raw_payload, bytes) else raw_payload
            )
            lease = json.loads(payload)
            if float(lease.get("expires_at", 0)) > now:
                continue
            reaped += 1
            self.ack_request(url, success=False, max_retries=max_retries)
        return reaped

    def is_visited(self, url: str) -> bool:
        """检查是否已访问"""
        return self.redis_client.exists(f"{self.visited_key}:{url}") > 0

    def mark_visited(self, url: str) -> None:
        """标记为已访问"""
        self.redis_client.setex(f"{self.visited_key}:{url}", 86400, "1")
        self.redis_client.sadd(self.visited_set_key, url)

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

    def processing_count(self) -> int:
        return self.redis_client.hlen(self.processing_key)

    def dead_letter_count(self) -> int:
        return self.redis_client.llen(self.dead_letter_key)

    def visited_count(self) -> int:
        """获取已访问数量"""
        return self.redis_client.scard(self.visited_set_key)

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
                    stop_heartbeat = threading.Event()
                    heartbeat_thread = threading.Thread(
                        target=self._heartbeat_loop,
                        args=(req.url, stop_heartbeat),
                        daemon=True,
                    )
                    heartbeat_thread.start()
                    callback(req)
                    stop_heartbeat.set()
                    heartbeat_thread.join(timeout=1)
                    self.scheduler.ack_request(req.url, success=True)
                    self.scheduler.update_stats("success", 1)
                except Exception as e:
                    stop_heartbeat.set()
                    heartbeat_thread.join(timeout=1)
                    print(f"[{self.name}] Error processing {req.url}: {e}")
                    self.scheduler.ack_request(req.url, success=False)
                    self.scheduler.update_stats("failed", 1)

            except Exception as e:
                print(f"[{self.name}] Worker error: {e}")
                time.sleep(1)

    def _heartbeat_loop(
        self, url: str, stop_event: threading.Event, lease_ttl: int = 30
    ) -> None:
        while not stop_event.wait(max(1, lease_ttl // 3)):
            try:
                if not self.scheduler.heartbeat(url, lease_ttl=lease_ttl):
                    break
            except Exception:
                break

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
