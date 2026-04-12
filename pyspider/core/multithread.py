"""
多线程增强模块
支持线程池、并发控制、异步执行
"""

import threading
import queue
import time
from typing import Callable, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
from dataclasses import dataclass
import asyncio


@dataclass
class TaskResult:
    """任务结果"""

    task_id: str
    result: Any
    error: Optional[Exception]
    duration: float


class WorkerPool:
    """工作池（增强多线程）"""

    def __init__(self, max_workers: int = 10, queue_size: int = 100):
        self.max_workers = max_workers
        self.queue_size = queue_size
        self.task_queue = queue.Queue(maxsize=queue_size)
        self.workers: List[threading.Thread] = []
        self.shutdown_flag = threading.Event()
        self.active_count = 0
        self.lock = threading.Lock()
        self.completed_count = 0

    def start(self) -> None:
        """启动工作池"""
        for i in range(self.max_workers):
            worker = threading.Thread(target=self._worker, daemon=True)
            worker.start()
            self.workers.append(worker)

    def _worker(self) -> None:
        """工作线程"""
        while not self.shutdown_flag.is_set():
            try:
                task = self.task_queue.get(timeout=0.5)
                if task is None:
                    break

                with self.lock:
                    self.active_count += 1

                try:
                    task()
                    with self.lock:
                        self.completed_count += 1
                except Exception as e:
                    print(f"Task error: {e}")
                finally:
                    with self.lock:
                        self.active_count -= 1

                self.task_queue.task_done()
            except queue.Empty:
                continue

    def submit(self, task: Callable) -> bool:
        """提交任务"""
        try:
            self.task_queue.put(task, block=False)
            return True
        except queue.Full:
            return False

    def submit_wait(self, task: Callable) -> None:
        """提交任务（等待）"""
        self.task_queue.put(task)

    def shutdown(self, wait: bool = True) -> None:
        """关闭工作池"""
        self.shutdown_flag.set()

        # 发送停止信号
        for _ in range(self.max_workers):
            try:
                self.task_queue.put(None, block=False)
            except queue.Full:
                pass

        if wait:
            for worker in self.workers:
                worker.join()

    def wait_completion(self) -> None:
        """等待所有任务完成"""
        self.task_queue.join()

    def get_stats(self) -> dict:
        """获取统计"""
        with self.lock:
            return {
                "max_workers": self.max_workers,
                "active_count": self.active_count,
                "queue_size": self.task_queue.qsize(),
                "completed_count": self.completed_count,
            }


class ConcurrentExecutor:
    """并发执行器"""

    def __init__(self, max_concurrent: int = 10):
        self.max_concurrent = max_concurrent
        self.semaphore = threading.Semaphore(max_concurrent)
        self.futures: List[Future] = []
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent)

    def execute(self, task: Callable, *args, **kwargs) -> Future:
        """执行任务"""

        def wrapped_task():
            with self.semaphore:
                return task(*args, **kwargs)

        future = self.executor.submit(wrapped_task)
        self.futures.append(future)
        return future

    def execute_many(self, tasks: List[Callable]) -> List[Any]:
        """执行多个任务"""
        results = []
        futures = []

        for task in tasks:
            future = self.execute(task)
            futures.append(future)

        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print(f"Task error: {e}")

        return results

    def shutdown(self, wait: bool = True) -> None:
        """关闭"""
        self.executor.shutdown(wait=wait)


class AsyncExecutor:
    """异步执行器"""

    def __init__(self, max_concurrent: int = 10):
        self.max_concurrent = max_concurrent
        self.semaphore = None
        self.results = []

    async def execute(self, coro: Callable, *args, **kwargs) -> Any:
        """执行异步任务"""
        if self.semaphore is None:
            self.semaphore = asyncio.Semaphore(self.max_concurrent)

        async with self.semaphore:
            return await coro(*args, **kwargs)

    async def execute_many(self, coros: List[Callable]) -> List[Any]:
        """执行多个异步任务"""
        tasks = [asyncio.create_task(self.execute(coro)) for coro in coros]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results


class RateLimitedExecutor:
    """限流执行器"""

    def __init__(self, rate: int, interval: float = 1.0):
        self.rate = rate
        self.interval = interval
        self.tokens = rate
        self.last_refill = time.time()
        self.lock = threading.Lock()

    def wait(self) -> None:
        """等待令牌"""
        with self.lock:
            self._refill()

            while self.tokens <= 0:
                time.sleep(0.1)
                with self.lock:
                    self._refill()

            self.tokens -= 1

    def _refill(self) -> None:
        """补充令牌"""
        now = time.time()
        elapsed = now - self.last_refill
        tokens_to_add = int(elapsed / self.interval) * self.rate

        if tokens_to_add > 0:
            self.tokens = min(self.rate, self.tokens + tokens_to_add)
            self.last_refill = now

    def execute(self, task: Callable, *args, **kwargs) -> Any:
        """执行任务（带限流）"""
        self.wait()
        return task(*args, **kwargs)


class PriorityTaskQueue:
    """优先级任务队列"""

    def __init__(self):
        self.queue = queue.PriorityQueue()
        self.lock = threading.Lock()

    def put(self, priority: int, task: Callable) -> None:
        """添加任务"""
        self.queue.put((priority, task))

    def get(self) -> Optional[Callable]:
        """获取任务"""
        try:
            _, task = self.queue.get(block=False)
            return task
        except queue.Empty:
            return None

    def empty(self) -> bool:
        """是否为空"""
        return self.queue.empty()

    def qsize(self) -> int:
        """队列大小"""
        return self.queue.qsize()
