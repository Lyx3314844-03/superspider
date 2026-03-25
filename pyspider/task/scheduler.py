"""
定时任务模块
支持 Cron 表达式和延时任务
"""

import threading
import time
from typing import Callable, Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass
import re


@dataclass
class Task:
    """任务"""
    name: str
    cron: str
    handler: Callable
    running: bool = False
    stop_event: Optional[threading.Event] = None


class Scheduler:
    """任务调度器"""
    
    def __init__(self):
        self.tasks: List[Task] = []
        self.running = False
        self._lock = threading.Lock()
        self._threads: List[threading.Thread] = []
    
    def add_task(self, name: str, cron: str, handler: Callable) -> Task:
        """添加定时任务
        
        Args:
            name: 任务名称
            cron: Cron 表达式 (*/n * * * *)
            handler: 处理函数
        """
        task = Task(name=name, cron=cron, handler=handler)
        
        with self._lock:
            self.tasks.append(task)
        
        return task
    
    def start_task(self, task: Task) -> None:
        """启动任务"""
        task.running = True
        task.stop_event = threading.Event()
        
        def run():
            interval = self._parse_cron(task.cron)
            
            while task.running and not task.stop_event.is_set():
                try:
                    task.handler()
                except Exception as e:
                    print(f"[{task.name}] Error: {e}")
                
                task.stop_event.wait(interval)
        
        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        self._threads.append(thread)
    
    def stop_task(self, task: Task) -> None:
        """停止任务"""
        task.running = False
        if task.stop_event:
            task.stop_event.set()
    
    def start(self) -> None:
        """启动所有任务"""
        self.running = True
        
        with self._lock:
            for task in self.tasks:
                self.start_task(task)
    
    def stop(self) -> None:
        """停止所有任务"""
        self.running = False
        
        with self._lock:
            for task in self.tasks:
                self.stop_task(task)
        
        # 等待线程结束
        for thread in self._threads:
            thread.join(timeout=1)
    
    def _parse_cron(self, cron: str) -> float:
        """解析 Cron 表达式（简化版）
        
        支持格式：*/n * * * * (每 n 分钟)
        """
        # 匹配 */n 格式
        match = re.match(r'\*/(\d+)\s+\*\s+\*\s+\*\s+\*', cron)
        if match:
            minutes = int(match.group(1))
            return minutes * 60
        
        # 默认每分钟
        return 60
    
    def get_stats(self) -> Dict:
        """获取统计"""
        return {
            "total_tasks": len(self.tasks),
            "running_tasks": sum(1 for t in self.tasks if t.running),
        }


class TimedTask:
    """延时任务"""
    
    def __init__(self, delay: float, handler: Callable):
        self.delay = delay
        self.handler = handler
        self._thread: Optional[threading.Thread] = None
        self._cancelled = False
    
    def start(self) -> None:
        """启动任务"""
        def run():
            time.sleep(self.delay)
            if not self._cancelled:
                self.handler()
        
        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()
    
    def cancel(self) -> None:
        """取消任务"""
        self._cancelled = True


def schedule_task(delay: float, handler: Callable) -> TimedTask:
    """调度延时任务"""
    task = TimedTask(delay, handler)
    task.start()
    return task


class CronTask:
    """Cron 任务"""
    
    def __init__(self, interval: float, handler: Callable):
        self.interval = interval
        self.handler = handler
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
    
    def start(self) -> None:
        """启动任务"""
        self._running = True
        
        def run():
            while self._running and not self._stop_event.is_set():
                try:
                    self.handler()
                except Exception as e:
                    print(f"CronTask Error: {e}")
                
                self._stop_event.wait(self.interval)
        
        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()
    
    def stop(self) -> None:
        """停止任务"""
        self._running = False
        self._stop_event.set()
