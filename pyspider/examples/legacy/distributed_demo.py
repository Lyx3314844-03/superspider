"""
分布式爬虫综合示例
演示 Redis 分布式、监控、API 的使用
"""

import sys
import time
import logging
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from pyspider.distributed.redis_distributed import (
    RedisDistributedScheduler,
    RedisWorker,
    CrawlTask,
)
from pyspider.monitor.monitor import SpiderMonitor, MonitorCenter
from pyspider.api.server import SpiderAPI

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def demo_distributed_scheduler():
    """演示分布式调度器"""
    print("\n" + "=" * 60)
    print("分布式调度器演示")
    print("=" * 60)

    try:
        # 创建调度器
        scheduler = RedisDistributedScheduler(
            spider_name="demo_spider", redis_url="redis://localhost:6379"
        )

        # 添加任务
        urls = [
            ("https://example.com/1", 10),
            ("https://example.com/2", 5),
            ("https://example.com/3", 15),
            ("https://example.com/4", 8),
            ("https://example.com/5", 20),
        ]

        for url, priority in urls:
            success = scheduler.schedule(url, priority=priority)
            print(f"{'✓' if success else '✗'} 调度：{url} (优先级：{priority})")

        # 获取统计
        stats = scheduler.get_stats()
        print(f"\n队列统计:")
        print(f"  队列大小：{stats['queue_size']}")
        print(f"  处理中：{stats['processing']}")

        # 获取任务
        print("\n获取任务（按优先级）:")
        for _ in range(3):
            task = scheduler.next_task()
            if task:
                print(f"  任务：{task.url} (优先级：{task.priority})")
                scheduler.ack(task, success=True)

        return scheduler

    except Exception as e:
        print(f"演示失败：{e}")
        return None


def demo_worker():
    """演示工作节点"""
    print("\n" + "=" * 60)
    print("工作节点演示")
    print("=" * 60)

    def process_task(task: CrawlTask):
        """任务处理回调"""
        logger.info(f"处理任务：{task.url}")
        time.sleep(0.5)  # 模拟处理

    try:
        # 创建 worker
        worker = RedisWorker(
            spider_name="demo_spider",
            redis_url="redis://localhost:6379",
            callback=process_task,
        )

        # 启动 worker（处理 5 个任务）
        worker.start(max_tasks=5, timeout=60)

        # 获取统计
        stats = worker.get_stats()
        print(f"\nWorker 统计:")
        print(f"  已处理：{stats['processed']}")
        print(f"  失败：{stats['failed']}")
        print(f"  处理速率：{stats['rate']:.2f} tasks/s")

        return worker

    except Exception as e:
        print(f"演示失败：{e}")
        return None


def demo_monitor():
    """演示监控"""
    print("\n" + "=" * 60)
    print("监控演示")
    print("=" * 60)

    try:
        # 创建监控
        monitor = SpiderMonitor("demo_spider")
        monitor.start()

        # 模拟爬取
        print("模拟爬取...")
        for i in range(50):
            monitor.record_page_crawled(f"https://example.com/{i}", 200, 1024)
            monitor.record_response_time(0.3 + i * 0.01)

            if i % 5 == 0:
                monitor.record_item_extracted(3)

        # 获取统计
        stats = monitor.get_stats()
        print(f"\n监控统计:")
        print(f"  爬取页面：{stats['stats']['pages_crawled']}")
        print(f"  成功率：{stats['stats']['success_rate'] * 100:.1f}%")
        print(f"  提取数据：{stats['stats']['items_extracted']}")
        print(f"  平均响应：{stats['performance']['response_time_avg'] * 1000:.1f}ms")
        print(f"  请求速率：{stats['performance']['requests_per_second']:.1f} req/s")

        # 仪表盘数据
        dashboard = monitor.get_dashboard_data()
        print(f"\n仪表盘:")
        print(f"  状态：{dashboard['status']}")
        print(f"  CPU: {dashboard['cpu_usage']:.1f}%")
        print(f"  内存：{dashboard['memory_usage']:.1f}MB")

        monitor.stop()

        return monitor

    except Exception as e:
        print(f"演示失败：{e}")
        return None


def demo_api_server():
    """演示 API 服务器"""
    print("\n" + "=" * 60)
    print("API 服务器演示")
    print("=" * 60)

    try:
        # 创建 API
        api = SpiderAPI(host="127.0.0.1", port=5000, debug=False)

        # 注册爬虫
        class MockSpider:
            pass

        class MockMonitor:
            def __init__(self):
                self._running = True

            def get_stats(self):
                return {
                    "stats": {
                        "pages_crawled": 100,
                        "pages_failed": 5,
                        "items_extracted": 50,
                        "bytes_downloaded": 1024 * 1024,
                    },
                    "performance": {
                        "response_time_avg": 0.5,
                        "requests_per_second": 10,
                    },
                    "resources": {
                        "cpu_percent": 25,
                        "memory_used_mb": 512,
                    },
                }

            def get_dashboard_data(self):
                return {
                    "spider_name": "demo_spider",
                    "status": "running",
                    "pages_crawled": 100,
                    "success_rate": 95.0,
                    "cpu_usage": 25,
                    "memory_usage": 512,
                }

        api.register_spider("demo_spider", MockSpider(), MockMonitor())

        # 启动 API
        thread = api.run()
        print("✓ API 服务器已启动：http://127.0.0.1:5000")

        # 测试 API
        import requests

        endpoints = [
            ("健康检查", "http://127.0.0.1:5000/health"),
            ("系统状态", "http://127.0.0.1:5000/api/v1/status"),
            ("爬虫列表", "http://127.0.0.1:5000/api/v1/spiders"),
            ("爬虫详情", "http://127.0.0.1:5000/api/v1/spiders/demo_spider"),
            ("爬虫统计", "http://127.0.0.1:5000/api/v1/spiders/demo_spider/stats"),
            ("仪表盘", "http://127.0.0.1:5000/api/v1/monitors/demo_spider/dashboard"),
        ]

        print("\nAPI 测试:")
        for name, url in endpoints:
            try:
                resp = requests.get(url, timeout=5)
                print(f"  ✓ {name}: {resp.status_code}")
            except Exception as e:
                print(f"  ✗ {name}: {e}")

        # 创建任务
        print("\n创建任务:")
        resp = requests.post(
            "http://127.0.0.1:5000/api/v1/tasks",
            json={"url": "https://example.com", "spider": "demo_spider"},
            timeout=5,
        )
        print(f"  状态码：{resp.status_code}")
        print(f"  响应：{resp.json()}")

        return api

    except Exception as e:
        print(f"演示失败：{e}")
        return None


def main():
    """主函数"""
    print("\n" + "╔" * 60 + "╗")
    print("║" * 20 + " 分布式爬虫综合演示 " + "║" * 20)
    print("╚" * 60 + "╝")

    # 检查 Redis
    print("\n检查 Redis 连接...")
    try:
        import redis

        r = redis.Redis(host="localhost", port=6379, decode_responses=True)
        r.ping()
        print("✓ Redis 已连接")
    except Exception as e:
        print(f"✗ Redis 连接失败：{e}")
        print("请确保 Redis 服务已启动：redis-server")
        return

    try:
        # 1. 分布式调度器
        scheduler = demo_distributed_scheduler()

        # 2. 工作节点
        if scheduler:
            worker = demo_worker()

        # 3. 监控
        monitor = demo_monitor()

        # 4. API 服务器
        api = demo_api_server()

        print("\n" + "═" * 60)
        print("演示完成！")
        print("═" * 60)

        if api:
            print("\nAPI 服务器仍在运行，按 Ctrl+C 退出...")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                api.stop()
                print("\n已退出")

    except Exception as e:
        logger.error(f"演示失败：{e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
