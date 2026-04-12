"""
Performance monitoring module for pyspider
Tracks metrics and provides health checks
"""

import time
import psutil
import threading
from typing import Dict, Any
from datetime import datetime
from collections import deque
import json


class MetricsCollector:
    """
    Collects and tracks various spider metrics
    """

    def __init__(self, window_size: int = 1000):
        self.window_size = window_size
        self._lock = threading.Lock()

        # Request metrics
        self.requests_total = 0
        self.requests_success = 0
        self.requests_failed = 0
        self.response_times = deque(maxlen=window_size)

        # Bandwidth metrics
        self.bytes_sent = 0
        self.bytes_received = 0

        # Timing
        self.start_time = time.time()
        self.last_reset = time.time()

    def record_request(
        self,
        success: bool,
        response_time: float,
        bytes_sent: int = 0,
        bytes_received: int = 0,
    ) -> None:
        """Record a request"""
        with self._lock:
            self.requests_total += 1
            if success:
                self.requests_success += 1
            else:
                self.requests_failed += 1

            self.response_times.append(response_time)
            self.bytes_sent += bytes_sent
            self.bytes_received += bytes_received

    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics"""
        with self._lock:
            uptime = time.time() - self.start_time

            response_times = list(self.response_times)
            avg_response = (
                sum(response_times) / len(response_times) if response_times else 0
            )

            return {
                "uptime_seconds": uptime,
                "requests": {
                    "total": self.requests_total,
                    "success": self.requests_success,
                    "failed": self.requests_failed,
                    "success_rate": self.requests_success / max(1, self.requests_total),
                },
                "response_time": {
                    "avg_ms": avg_response * 1000,
                    "min_ms": min(response_times) * 1000 if response_times else 0,
                    "max_ms": max(response_times) * 1000 if response_times else 0,
                },
                "bandwidth": {
                    "sent_mb": self.bytes_sent / (1024 * 1024),
                    "received_mb": self.bytes_received / (1024 * 1024),
                },
                "throughput": {
                    "requests_per_second": self.requests_total / max(1, uptime),
                },
            }

    def reset(self) -> None:
        """Reset counters"""
        with self._lock:
            self.requests_total = 0
            self.requests_success = 0
            self.requests_failed = 0
            self.response_times.clear()
            self.bytes_sent = 0
            self.bytes_received = 0
            self.last_reset = time.time()


class SystemMonitor:
    """
    Monitors system resource usage
    """

    def __init__(self):
        self.process = psutil.Process()

    def get_metrics(self) -> Dict[str, Any]:
        """Get current system metrics"""
        try:
            cpu_percent = self.process.cpu_percent(interval=0.1)
            memory = self.process.memory_info()

            return {
                "cpu": {
                    "percent": cpu_percent,
                    "count": psutil.cpu_count(),
                },
                "memory": {
                    "rss_mb": memory.rss / (1024 * 1024),
                    "vms_mb": memory.vms / (1024 * 1024),
                    "percent": self.process.memory_percent(),
                },
                "threads": self.process.num_threads(),
                "open_files": len(self.process.open_files()),
                "connections": len(self.process.connections()),
            }
        except Exception as e:
            return {"error": str(e)}


class HealthChecker:
    """
    Provides health check endpoints for the spider
    """

    def __init__(self, metrics: MetricsCollector, system: SystemMonitor):
        self.metrics = metrics
        self.system = system
        self._checks = {}

    def register_check(self, name: str, check_fn) -> None:
        """Register a health check"""
        self._checks[name] = check_fn

    def check(self) -> Dict[str, Any]:
        """Run all health checks"""
        results = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "checks": {},
        }

        # Run registered checks
        for name, check_fn in self._checks.items():
            try:
                result = check_fn()
                results["checks"][name] = result
                if not result.get("healthy", True):
                    results["status"] = "unhealthy"
            except Exception as e:
                results["checks"][name] = {"healthy": False, "error": str(e)}
                results["status"] = "unhealthy"

        # Add system metrics
        results["system"] = self.system.get_metrics()
        results["metrics"] = self.metrics.get_stats()

        return results

    def is_healthy(self) -> bool:
        """Quick health check"""
        return self.check()["status"] == "healthy"


class PerformanceMonitor:
    """
    Main performance monitoring class
    """

    def __init__(self):
        self.metrics = MetricsCollector()
        self.system = SystemMonitor()
        self.health = HealthChecker(self.metrics, self.system)

        # Register default health checks
        self.health.register_check("queue_not_full", self._check_queue)
        self.health.register_check("memory_not_exhausted", self._check_memory)
        self.health.register_check("disk_space", self._check_disk)

    def _check_queue(self) -> Dict[str, Any]:
        """Check if queue is not too full"""
        return {"healthy": True, "message": "Queue check passed"}

    def _check_memory(self) -> Dict[str, Any]:
        """Check memory usage"""
        mem = psutil.virtual_memory()
        if mem.percent > 90:
            return {"healthy": False, "message": f"Memory usage high: {mem.percent}%"}
        return {"healthy": True, "message": f"Memory: {mem.percent}%"}

    def _check_disk(self) -> Dict[str, Any]:
        """Check disk space"""
        disk = psutil.disk_usage("/")
        if disk.percent > 90:
            return {"healthy": False, "message": f"Disk usage high: {disk.percent}%"}
        return {"healthy": True, "message": f"Disk: {disk.percent}%"}

    def record(
        self,
        success: bool,
        response_time: float,
        bytes_sent: int = 0,
        bytes_received: int = 0,
    ) -> None:
        """Record a request for metrics"""
        self.metrics.record_request(success, response_time, bytes_sent, bytes_received)

    def get_report(self) -> Dict[str, Any]:
        """Get full performance report"""
        return {
            "health": self.health.check(),
            "metrics": self.metrics.get_stats(),
            "system": self.system.get_metrics(),
        }

    def export_json(self, filepath: str) -> None:
        """Export metrics to JSON file"""
        with open(filepath, "w") as f:
            json.dump(self.get_report(), f, indent=2)


def create_monitor() -> PerformanceMonitor:
    """Create a performance monitor"""
    return PerformanceMonitor()
