"""
调度器模块
支持优先级队列和 URL 去重
"""

import heapq
import threading
from typing import Optional, List, Set
from dataclasses import dataclass, field
from pyspider.core.models import Request


@dataclass(order=True)
class PrioritizedRequest:
    """优先级请求"""
    priority: int
    request: Request = field(compare=False)


class Scheduler:
    """请求调度器"""
    
    def __init__(self):
        self._queue: List[PrioritizedRequest] = []
        self._visited: Set[str] = set()
        self._lock = threading.RLock()
    
    def add_request(self, request: Request) -> None:
        """添加请求"""
        with self._lock:
            if request.url in self._visited:
                return
            self._visited.add(request.url)
            heapq.heappush(self._queue, PrioritizedRequest(request.priority, request))
    
    def next_request(self) -> Optional[Request]:
        """获取下一个请求"""
        with self._lock:
            if not self._queue:
                return None
            return heapq.heappop(self._queue).request
    
    def is_visited(self, url: str) -> bool:
        """检查是否已访问"""
        with self._lock:
            return url in self._visited
    
    def queue_len(self) -> int:
        """获取队列长度"""
        with self._lock:
            return len(self._queue)
    
    def visited_count(self) -> int:
        """获取已访问数量"""
        with self._lock:
            return len(self._visited)
    
    def clear(self) -> None:
        """清空队列"""
        with self._lock:
            self._queue.clear()
            self._visited.clear()


class BloomFilter:
    """布隆过滤器"""
    
    def __init__(self, size: int = 1000000, hash_count: int = 7):
        self.size = size
        self.hash_count = hash_count
        self.bit_array = [False] * size
    
    def _hashes(self, item: str) -> List[int]:
        """生成哈希值"""
        import hashlib
        hashes = []
        for i in range(self.hash_count):
            h = hashlib.md5(f"{item}{i}".encode()).hexdigest()
            hashes.append(int(h, 16) % self.size)
        return hashes
    
    def add(self, item: str) -> None:
        """添加元素"""
        for hash_val in self._hashes(item):
            self.bit_array[hash_val] = True
    
    def contains(self, item: str) -> bool:
        """检查元素是否存在"""
        return all(self.bit_array[hash_val] for hash_val in self._hashes(item))
    
    def clear(self) -> None:
        """清空"""
        self.bit_array = [False] * self.size
