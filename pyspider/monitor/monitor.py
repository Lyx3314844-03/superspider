"""
实时状态监控模块
支持爬虫状态、性能、资源监控
"""

import time
import threading
import json
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
from collections import deque
import os
import psutil


logger = logging.getLogger(__name__)


@dataclass
class SpiderStats:
    """爬虫统计"""
    spider_name: str
    started_at: float = 0.0
    stopped_at: float = 0.0
    pages_crawled: int = 0
    pages_failed: int = 0
    items_extracted: int = 0
    requests_made: int = 0
    bytes_downloaded: int = 0
    errors: List[Dict] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        total = self.pages_crawled + self.pages_failed
        return self.pages_crawled / total if total > 0 else 0
    
    @property
    def runtime(self) -> float:
        end = self.stopped_at or time.time()
        return end - self.started_at if self.started_at else 0
    
    @property
    def pages_per_second(self) -> float:
        runtime = self.runtime
        return self.pages_crawled / runtime if runtime > 0 else 0
    
    def to_dict(self) -> dict:
        return {
            **asdict(self),
            'success_rate': self.success_rate,
            'runtime': self.runtime,
            'pages_per_second': self.pages_per_second,
        }


@dataclass
class PerformanceMetrics:
    """性能指标"""
    timestamp: float = 0.0
    response_time_avg: float = 0.0
    response_time_p95: float = 0.0
    response_time_p99: float = 0.0
    requests_per_second: float = 0.0
    errors_per_second: float = 0.0
    queue_size: int = 0
    active_threads: int = 0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0


@dataclass
class ResourceMetrics:
    """资源指标"""
    timestamp: float = 0.0
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_used_mb: float = 0.0
    memory_available_mb: float = 0.0
    disk_usage_percent: float = 0.0
    network_sent_mb: float = 0.0
    network_recv_mb: float = 0.0
    open_files: int = 0
    threads_count: int = 0


class MetricsCollector:
    """指标收集器"""
    
    def __init__(self, window_size: int = 60):
        self.window_size = window_size  # 时间窗口（秒）
        self.response_times: deque = deque(maxlen=10000)
        self.request_times: deque = deque(maxlen=10000)
        self.error_times: deque = deque(maxlen=1000)
        self._lock = threading.RLock()
    
    def record_response_time(self, response_time: float):
        """记录响应时间"""
        with self._lock:
            self.response_times.append((time.time(), response_time))
    
    def record_request(self):
        """记录请求"""
        with self._lock:
            self.request_times.append(time.time())
    
    def record_error(self):
        """记录错误"""
        with self._lock:
            self.error_times.append(time.time())
    
    def get_metrics(self) -> PerformanceMetrics:
        """获取性能指标"""
        now = time.time()
        window_start = now - self.window_size
        
        with self._lock:
            # 响应时间统计
            recent_times = [
                rt for t, rt in self.response_times
                if t > window_start
            ]
            
            if recent_times:
                avg_time = sum(recent_times) / len(recent_times)
                sorted_times = sorted(recent_times)
                p95_idx = int(len(sorted_times) * 0.95)
                p99_idx = int(len(sorted_times) * 0.99)
                p95 = sorted_times[min(p95_idx, len(sorted_times) - 1)]
                p99 = sorted_times[min(p99_idx, len(sorted_times) - 1)]
            else:
                avg_time = p95 = p99 = 0.0
            
            # 请求速率
            recent_requests = sum(1 for t in self.request_times if t > window_start)
            rps = recent_requests / self.window_size
            
            # 错误速率
            recent_errors = sum(1 for t in self.error_times if t > window_start)
            eps = recent_errors / self.window_size
        
        # 系统资源
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        
        return PerformanceMetrics(
            timestamp=now,
            response_time_avg=avg_time,
            response_time_p95=p95,
            response_time_p99=p99,
            requests_per_second=rps,
            errors_per_second=eps,
            active_threads=threading.active_count(),
            memory_usage_mb=memory.used / 1024 / 1024,
            cpu_usage_percent=cpu_percent,
        )
    
    def clear(self):
        """清空指标"""
        with self._lock:
            self.response_times.clear()
            self.request_times.clear()
            self.error_times.clear()


class ResourceMonitor:
    """资源监控器"""
    
    def __init__(self):
        self.process = psutil.Process()
    
    def get_metrics(self) -> ResourceMetrics:
        """获取资源指标"""
        # CPU
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        # 内存
        memory = psutil.virtual_memory()
        process_memory = self.process.memory_info()
        
        # 磁盘
        disk = psutil.disk_usage('/')
        
        # 网络
        net_io = psutil.net_io_counters()
        
        # 文件句柄
        try:
            open_files = len(self.process.open_files())
        except:
            open_files = 0
        
        return ResourceMetrics(
            timestamp=time.time(),
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_used_mb=process_memory.rss / 1024 / 1024,
            memory_available_mb=memory.available / 1024 / 1024,
            disk_usage_percent=disk.percent,
            network_sent_mb=net_io.bytes_sent / 1024 / 1024,
            network_recv_mb=net_io.bytes_recv / 1024 / 1024,
            open_files=open_files,
            threads_count=self.process.num_threads(),
        )


class SpiderMonitor:
    """爬虫监控器"""
    
    def __init__(self, spider_name: str):
        self.spider_name = spider_name
        self.stats = SpiderStats(spider_name=spider_name)
        self.metrics_collector = MetricsCollector()
        self.resource_monitor = ResourceMonitor()
        
        self._callbacks: List[Callable] = []
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
    
    def start(self):
        """启动监控"""
        self._running = True
        self.stats.started_at = time.time()
        
        logger.info(f"监控启动：{self.spider_name}")
    
    def stop(self):
        """停止监控"""
        self._running = False
        self.stats.stopped_at = time.time()
        
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        
        logger.info(f"监控停止：{self.spider_name}")
    
    def record_page_crawled(self, url: str, status_code: int, bytes_downloaded: int = 0):
        """记录页面爬取"""
        with self._lock:
            self.stats.pages_crawled += 1
            self.stats.bytes_downloaded += bytes_downloaded
            self.stats.requests_made += 1
            self.metrics_collector.record_request()
    
    def record_page_failed(self, url: str, error: str):
        """记录页面失败"""
        with self._lock:
            self.stats.pages_failed += 1
            self.stats.errors.append({
                'url': url,
                'error': error,
                'timestamp': time.time(),
            })
            self.metrics_collector.record_error()
    
    def record_item_extracted(self, count: int = 1):
        """记录数据提取"""
        with self._lock:
            self.stats.items_extracted += count
    
    def record_response_time(self, response_time: float):
        """记录响应时间"""
        self.metrics_collector.record_response_time(response_time)
    
    def add_callback(self, callback: Callable):
        """添加监控回调"""
        self._callbacks.append(callback)
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        with self._lock:
            stats = self.stats.to_dict()
            metrics = self.metrics_collector.get_metrics()
            resources = self.resource_monitor.get_metrics()
            
            return {
                'spider_name': self.spider_name,
                'stats': stats,
                'performance': asdict(metrics),
                'resources': asdict(resources),
                'is_running': self._running,
            }
    
    def get_dashboard_data(self) -> dict:
        """获取仪表盘数据"""
        stats = self.get_stats()
        
        return {
            'spider_name': stats['spider_name'],
            'status': 'running' if stats['is_running'] else 'stopped',
            'pages_crawled': stats['stats']['pages_crawled'],
            'pages_failed': stats['stats']['pages_failed'],
            'success_rate': stats['stats']['success_rate'] * 100,
            'items_extracted': stats['stats']['items_extracted'],
            'bytes_downloaded': stats['stats']['bytes_downloaded'],
            'runtime_seconds': stats['stats']['runtime'],
            'pages_per_second': stats['stats']['pages_per_second'],
            'avg_response_time': stats['performance']['response_time_avg'],
            'requests_per_second': stats['performance']['requests_per_second'],
            'cpu_usage': stats['resources']['cpu_percent'],
            'memory_usage': stats['resources']['memory_used_mb'],
            'timestamp': time.time(),
        }


class MonitorCenter:
    """监控中心（管理多个爬虫）"""
    
    def __init__(self):
        self.monitors: Dict[str, SpiderMonitor] = {}
        self._lock = threading.RLock()
    
    def register(self, spider_name: str) -> SpiderMonitor:
        """注册爬虫监控"""
        with self._lock:
            if spider_name not in self.monitors:
                self.monitors[spider_name] = SpiderMonitor(spider_name)
            return self.monitors[spider_name]
    
    def unregister(self, spider_name: str):
        """注销爬虫监控"""
        with self._lock:
            if spider_name in self.monitors:
                self.monitors[spider_name].stop()
                del self.monitors[spider_name]
    
    def get_spider(self, spider_name: str) -> Optional[SpiderMonitor]:
        """获取爬虫监控器"""
        return self.monitors.get(spider_name)
    
    def get_all_stats(self) -> dict:
        """获取所有爬虫统计"""
        with self._lock:
            return {
                name: monitor.get_stats()
                for name, monitor in self.monitors.items()
            }
    
    def get_summary(self) -> dict:
        """获取摘要"""
        with self._lock:
            total_crawled = sum(m.stats.pages_crawled for m in self.monitors.values())
            total_failed = sum(m.stats.pages_failed for m in self.monitors.values())
            total_items = sum(m.stats.items_extracted for m in self.monitors.values())
            running_count = sum(1 for m in self.monitors.values() if m._running)
            
            return {
                'total_spiders': len(self.monitors),
                'running_spiders': running_count,
                'total_pages_crawled': total_crawled,
                'total_pages_failed': total_failed,
                'total_items_extracted': total_items,
                'timestamp': time.time(),
            }


# 全局监控中心
_monitor_center = MonitorCenter()


def get_monitor_center() -> MonitorCenter:
    """获取监控中心"""
    return _monitor_center


# 使用示例
if __name__ == "__main__":
    # 创建监控
    monitor = SpiderMonitor("test_spider")
    monitor.start()
    
    # 模拟爬取
    for i in range(100):
        monitor.record_page_crawled(f"https://example.com/{i}", 200, 1024)
        monitor.record_response_time(0.5 + i * 0.01)
        
        if i % 10 == 0:
            monitor.record_item_extracted(5)
    
    # 获取统计
    stats = monitor.get_stats()
    print(f"爬取页面：{stats['stats']['pages_crawled']}")
    print(f"成功率：{stats['stats']['success_rate'] * 100:.1f}%")
    print(f"平均响应时间：{stats['performance']['response_time_avg'] * 1000:.1f}ms")
    
    # 仪表盘数据
    dashboard = monitor.get_dashboard_data()
    print(f"\n仪表盘数据:")
    print(json.dumps(dashboard, indent=2))
    
    monitor.stop()
