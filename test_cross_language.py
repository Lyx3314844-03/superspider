import redis
import json
import time
import hashlib

# 统一配置
REDIS_URL = "redis://localhost:6379"
QUEUE_KEY = "spider:shared:queue"
VISITED_KEY = "spider:shared:visited"
STATS_KEY = "spider:shared:stats"

r = redis.from_url(REDIS_URL, decode_responses=True)

def clear_redis():
    print("正在清空 Redis 相关键...")
    r.delete(QUEUE_KEY, VISITED_KEY, STATS_KEY)

def inject_tasks(count=10):
    print(f"正在注入 {count} 个测试任务...")
    for i in range(count):
        url = f"https://example.com/test_{i}"
        task = {
            "url": url,
            "priority": i % 5,
            "depth": 0,
            "task_type": "crawl",
            "spider_name": "test_injector",
            "created_at": time.time(),
            "retry_count": 0,
            "metadata": {"id": i}
        }
        r.zadd(QUEUE_KEY, {json.dumps(task): task["priority"]})
    print("任务注入完成。")

def check_stats():
    print("当前统计信息:")
    stats = r.hgetall(STATS_KEY)
    print(json.dumps(stats, indent=2))
    
    queue_len = r.zcard(QUEUE_KEY)
    visited_len = r.scard(VISITED_KEY)
    print(f"队列长度: {queue_len}")
    print(f"已访问数: {visited_len}")

if __name__ == "__main__":
    clear_redis()
    inject_tasks(20)
    check_stats()
    print("\n现在你可以分别运行 Java, Go, Rust, Python 的分布式爬虫，它们将共同消费这些任务。")
    print("Java: 运行 com.javaspider.examples.DistributedExample (需创建)")
    print("Go: 运行 examples/main.go (需配置为 DistributedSpider)")
    print("Python: 运行 examples/main.py (需配置为 RedisWorker)")
    print("Rust: 运行 examples/main.rs (需配置为 RedisWorker)")
