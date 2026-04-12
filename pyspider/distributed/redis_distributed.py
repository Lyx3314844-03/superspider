"""
Redis 分布式爬虫支持
支持分布式队列、去重、任务分发
"""

import redis
import json
import time
import hashlib
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import threading

logger = logging.getLogger(__name__)


@dataclass
class CrawlTask:
    """爬取任务"""

    url: str
    priority: int = 0
    depth: int = 0
    task_type: str = "crawl"  # crawl, download, parse
    spider_name: str = "default"
    created_at: float = 0.0
    retry_count: int = 0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.created_at == 0.0:
            self.created_at = time.time()
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "CrawlTask":
        return cls(**data)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "CrawlTask":
        return cls.from_dict(json.loads(json_str))


class RedisDistributedQueue:
    """Redis 分布式队列"""

    def __init__(
        self,
        name: str,
        redis_url: str = "redis://localhost:6379",
        max_size: int = 1000000,
    ):
        self.name = name
        self.max_size = max_size
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self._lock = threading.RLock()

        # 统一队列 key
        self.queue_key = "spider:shared:queue"
        self.priority_queue_key = "spider:shared:queue"
        self.visited_key = "spider:shared:visited"
        self.processing_key = f"queue:{name}:processing"
        self.failed_queue_key = f"queue:{name}:failed"

    def push(self, task: CrawlTask) -> bool:
        """添加任务到队列"""
        with self._lock:
            # 检查队列大小
            if self.size() >= self.max_size:
                logger.warning(f"队列已满：{self.name}")
                return False

            # 检查是否已存在
            if self.exists(task.url):
                return False

            # 添加到优先级队列
            task_json = task.to_json()
            self.redis.zadd(self.priority_queue_key, {task_json: task.priority})

            # 添加到已访问集合 (去重)
            self.redis.sadd(self.visited_key, task.url)

            logger.debug(f"任务入队：{task.url}")
            return True

    def pop(self, timeout: float = 0) -> Optional[CrawlTask]:
        """从队列获取任务"""
        # 从优先级队列获取最高优先级的任务
        with self._lock:
            results = self.redis.zpopmin(self.priority_queue_key, count=1)

            if not results:
                return None

            task_json, score = results[0]
            task = CrawlTask.from_json(task_json)

            # 添加到处理中集合
            self.redis.hset(
                self.processing_key,
                self._url_key(task.url),
                json.dumps(
                    {"url": task.url, "started_at": time.time(), "task": task.to_dict()}
                ),
            )

            logger.debug(f"任务出队：{task.url}")
            return task

    def ack(self, task: CrawlTask, success: bool = True):
        """确认任务完成"""
        with self._lock:
            url_key = self._url_key(task.url)

            # 从处理中集合移除
            self.redis.hdel(self.processing_key, url_key)

            if not success:
                # 添加到失败队列
                if task.retry_count < 3:
                    task.retry_count += 1
                    self.push(task)
                else:
                    self.redis.lpush(self.failed_queue_key, task.to_json())

    def exists(self, url: str) -> bool:
        """检查 URL 是否已访问"""
        return self.redis.sismember(self.visited_key, url)

    def size(self) -> int:
        """获取队列大小"""
        return self.redis.zcard(self.priority_queue_key)

    def processing_count(self) -> int:
        """获取处理中的任务数"""
        return self.redis.hlen(self.processing_key)

    def failed_count(self) -> int:
        """获取失败队列大小"""
        return self.redis.llen(self.failed_queue_key)

    def clear(self):
        """清空队列"""
        with self._lock:
            self.redis.delete(
                self.queue_key,
                f"{self.queue_key}:urls",
                self.priority_queue_key,
                self.processing_key,
                self.failed_queue_key,
            )

    def _url_key(self, url: str) -> str:
        """生成 URL 键"""
        return hashlib.md5(url.encode()).hexdigest()

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "queue_size": self.size(),
            "processing": self.processing_count(),
            "failed": self.failed_count(),
            "max_size": self.max_size,
        }


class RedisBloomFilter:
    """Redis 布隆过滤器（分布式去重）"""

    def __init__(
        self,
        name: str,
        redis_url: str = "redis://localhost:6379",
        expected_items: int = 1000000,
        error_rate: float = 0.01,
    ):
        self.name = name
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.key = f"bloom:{name}"

        # 计算布隆过滤器参数
        import math

        self.size = int(-expected_items * math.log(error_rate) / (math.log(2) ** 2))
        self.hash_count = int((self.size / expected_items) * math.log(2))

        # 调整大小
        self.size = ((self.size + 7) // 8) * 8  # 对齐到字节

    def add(self, item: str) -> bool:
        """添加元素，返回是否可能已存在"""
        item_bytes = item.encode("utf-8")
        is_new = True

        for seed in range(self.hash_count):
            pos = self._hash(item_bytes, seed) % self.size
            if not self.redis.setbit(self.key, pos, 1):
                is_new = False

        return is_new

    def contains(self, item: str) -> bool:
        """检查元素是否存在"""
        item_bytes = item.encode("utf-8")

        for seed in range(self.hash_count):
            pos = self._hash(item_bytes, seed) % self.size
            if not self.redis.getbit(self.key, pos):
                return False

        return True

    def _hash(self, item: bytes, seed: int) -> int:
        """哈希函数"""
        return int(hashlib.md5(item + str(seed).encode()).hexdigest(), 16)

    def clear(self):
        """清空过滤器"""
        self.redis.delete(self.key)

    def count(self) -> int:
        """估算元素数量"""
        import math

        bits_set = self.redis.bitcount(self.key)
        if bits_set == 0:
            return 0
        return int(-self.size / self.hash_count * math.log(1 - bits_set / self.size))


class RedisDistributedScheduler:
    """Redis 分布式调度器"""

    def __init__(
        self,
        spider_name: str,
        redis_url: str = "redis://localhost:6379",
        queue_cls=RedisDistributedQueue,
    ):
        self.spider_name = spider_name
        self.redis = redis.from_url(redis_url, decode_responses=True)

        # 任务队列
        self.queue = queue_cls(spider_name, redis_url)

        # 布隆过滤器（去重）
        self.filter = RedisBloomFilter(spider_name, redis_url)

        # 统计信息
        self.stats_key = "spider:shared:stats"

    def schedule(self, url: str, priority: int = 0, depth: int = 0, **metadata) -> bool:
        """调度 URL"""
        # 检查是否已爬取
        if self.filter.contains(url):
            logger.debug(f"URL 已存在：{url}")
            return False

        # 添加到过滤器
        self.filter.add(url)

        # 创建任务
        task = CrawlTask(
            url=url,
            priority=priority,
            depth=depth,
            spider_name=self.spider_name,
            metadata=metadata,
        )

        # 入队
        return self.queue.push(task)

    def next_task(self) -> Optional[CrawlTask]:
        """获取下一个任务"""
        return self.queue.pop()

    def ack(self, task: CrawlTask, success: bool = True):
        """确认任务完成"""
        self.queue.ack(task, success)
        self._update_stats(success)

    def _update_stats(self, success: bool):
        """更新统计"""
        if success:
            self.redis.hincrby(self.stats_key, "success", 1)
            self.redis.hincrby(self.stats_key, "python:success", 1)
        else:
            self.redis.hincrby(self.stats_key, "failed", 1)
            self.redis.hincrby(self.stats_key, "python:failed", 1)

        self.redis.hincrby(self.stats_key, "processed", 1)
        self.redis.hincrby(self.stats_key, "python:processed", 1)

    def get_stats(self) -> dict:
        """获取统计信息"""
        queue_stats = self.queue.get_stats()

        # 获取历史统计
        today = datetime.now().strftime("%Y-%m-%d")
        success = int(self.redis.hget(f"{self.stats_key}:success", today) or 0)
        failed = int(self.redis.hget(f"{self.stats_key}:failed", today) or 0)

        return {
            **queue_stats,
            "spider_name": self.spider_name,
            "success_today": success,
            "failed_today": failed,
            "total_processed": success + failed,
        }

    def clear(self):
        """清空调度器"""
        self.queue.clear()
        self.filter.clear()


class RedisWorker:
    """Redis 分布式工作节点"""

    def __init__(
        self,
        spider_name: str,
        redis_url: str = "redis://localhost:6379",
        callback: callable = None,
    ):
        self.spider_name = spider_name
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.callback = callback

        self.scheduler = RedisDistributedScheduler(spider_name, redis_url)
        self.running = False
        self.stats = {
            "processed": 0,
            "failed": 0,
            "start_time": None,
            "last_task_time": None,
        }

    def start(self, max_tasks: int = 0, timeout: int = 300):
        """启动工作节点"""
        self.running = True
        self.stats["start_time"] = time.time()

        logger.info(f"工作节点启动：{self.spider_name}")

        tasks_processed = 0

        while self.running:
            # 检查是否达到最大任务数
            if max_tasks > 0 and tasks_processed >= max_tasks:
                logger.info(f"达到最大任务数：{max_tasks}")
                break

            # 获取任务
            task = self.scheduler.next_task()

            if task:
                self.stats["last_task_time"] = time.time()
                logger.info(f"处理任务：{task.url}")

                try:
                    # 执行回调
                    if self.callback:
                        self.callback(task)

                    # 确认成功
                    self.scheduler.ack(task, success=True)
                    self.stats["processed"] += 1
                    tasks_processed += 1

                except Exception as e:
                    logger.error(f"任务失败：{task.url} - {e}")
                    self.scheduler.ack(task, success=False)
                    self.stats["failed"] += 1
            else:
                # 队列为空，等待
                time.sleep(1)

                # 检查超时
                if (
                    timeout > 0
                    and (time.time() - self.stats["last_task_time"]) > timeout
                ):
                    logger.info("队列超时，退出")
                    break

        self.stop()

    def stop(self):
        """停止工作节点"""
        self.running = False
        logger.info(f"工作节点停止：{self.spider_name}")

    def get_stats(self) -> dict:
        """获取统计信息"""
        scheduler_stats = self.scheduler.get_stats()

        runtime = (
            time.time() - self.stats["start_time"] if self.stats["start_time"] else 0
        )
        rate = self.stats["processed"] / runtime if runtime > 0 else 0

        return {
            **scheduler_stats,
            "processed": self.stats["processed"],
            "failed": self.stats["failed"],
            "runtime": runtime,
            "rate": rate,
        }


# 使用示例
if __name__ == "__main__":
    # 创建调度器
    scheduler = RedisDistributedScheduler(
        spider_name="test_spider", redis_url="redis://localhost:6379"
    )

    # 添加任务
    scheduler.schedule("https://example.com/1", priority=10)
    scheduler.schedule("https://example.com/2", priority=5)
    scheduler.schedule("https://example.com/3", priority=15)

    print(f"队列大小：{scheduler.queue.size()}")
    print(f"统计：{scheduler.get_stats()}")

    # 创建工作节点
    def process_task(task: CrawlTask):
        print(f"处理：{task.url}")
        time.sleep(1)  # 模拟处理

    worker = RedisWorker(
        spider_name="test_spider",
        redis_url="redis://localhost:6379",
        callback=process_task,
    )

    # 启动 worker
    worker.start(max_tasks=10)

    print(f"最终统计：{worker.get_stats()}")
