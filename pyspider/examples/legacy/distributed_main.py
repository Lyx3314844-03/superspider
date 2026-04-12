from distributed.redis_distributed import RedisWorker, CrawlTask
import time
import logging

logging.basicConfig(level=logging.INFO)


def process_task(task: CrawlTask):
    print(f"[Python] 正在处理: {task.url}")
    time.sleep(0.5)


if __name__ == "__main__":
    # 创建分布式工作节点 (指向统一队列)
    worker = RedisWorker(
        spider_name="PySpiderNode",
        redis_url="redis://localhost:6379",
        callback=process_task,
    )

    print("Python 分布式爬虫节点启动...")
    worker.start(max_tasks=100)
