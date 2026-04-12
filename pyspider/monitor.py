#!/usr/bin/env python3
"""
PySpider 性能监控模块 - 爬取速度、成功率、内存监控
"""

import time
import psutil
import threading
from typing import Dict, Optional
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class Metrics:
    """监控指标"""

    total_requests: int = 0
    success_requests: int = 0
    failed_requests: int = 0
    total_bytes: int = 0
    start_time: datetime = field(default_factory=datetime.now)
    lock: threading.Lock = field(default_factory=threading.Lock)


class Monitor:
    """性能监控器"""

    def __init__(self):
        self.metrics = Metrics()
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.process = psutil.Process()

    def record_request(self, success: bool, bytes_count: int = 0):
        """记录请求"""
        with self.metrics.lock:
            self.metrics.total_requests += 1
            if success:
                self.metrics.success_requests += 1
            else:
                self.metrics.failed_requests += 1
            self.metrics.total_bytes += bytes_count

    def get_success_rate(self) -> float:
        """获取成功率"""
        with self.metrics.lock:
            if self.metrics.total_requests == 0:
                return 0.0
            return (self.metrics.success_requests / self.metrics.total_requests) * 100

    def get_requests_per_second(self) -> float:
        """获取爬取速度 (请求/秒)"""
        with self.metrics.lock:
            elapsed = (datetime.now() - self.metrics.start_time).total_seconds()
            if elapsed == 0:
                return 0.0
            return self.metrics.total_requests / elapsed

    def get_memory_usage(self) -> Dict[str, float]:
        """获取内存使用情况 (MB)"""
        mem_info = self.process.memory_info()
        return {
            "rss": mem_info.rss / 1024 / 1024,  # 物理内存
            "vms": mem_info.vms / 1024 / 1024,  # 虚拟内存
        }

    def get_cpu_usage(self) -> float:
        """获取 CPU 使用率 (%)"""
        return self.process.cpu_percent(interval=0.1)

    def show_stats(self):
        """显示统计信息"""
        elapsed = datetime.now() - self.metrics.start_time
        success_rate = self.get_success_rate()
        reqs_per_sec = self.get_requests_per_second()
        mem = self.get_memory_usage()
        cpu = self.get_cpu_usage()

        print("\n📈 性能监控:")
        print(f"  运行时间: {elapsed}")
        print(f"  总请求数: {self.metrics.total_requests}")
        print(f"  成功请求: {self.metrics.success_requests}")
        print(f"  失败请求: {self.metrics.failed_requests}")
        print(f"  成功率: {success_rate:.2f}%")
        print(f"  爬取速度: {reqs_per_sec:.2f} 请求/秒")
        print(f"  数据量: {self.metrics.total_bytes / 1024:.2f} KB")
        print(f"  内存使用: {mem['rss']:.2f} MB")
        print(f"  CPU 使用: {cpu:.2f}%")

    def start_monitoring(self, interval: int = 5):
        """启动监控"""
        self.running = True
        self.thread = threading.Thread(
            target=self._monitor_loop, args=(interval,), daemon=True
        )
        self.thread.start()
        print("✅ 性能监控已启动")

    def stop_monitoring(self):
        """停止监控"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        print("✅ 性能监控已停止")

    def _monitor_loop(self, interval: int):
        """监控循环"""
        while self.running:
            time.sleep(interval)
            # 可以在这里添加自动告警逻辑


def show_monitor_menu():
    """显示监控菜单"""
    print("\n📈 性能监控功能:")
    print("  monitor stats    - 显示统计信息")
    print("  monitor start    - 启动监控")
    print("  monitor stop     - 停止监控")
