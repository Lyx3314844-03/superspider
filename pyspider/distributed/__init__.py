"""
Distributed task queue using Redis for pyspider
Enables horizontal scaling across multiple spider instances
"""

import json
import time
import uuid
from typing import Optional, Dict, Any
from datetime import datetime

try:
    import redis

    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False


class RedisTaskQueue:
    """
    Redis-based distributed task queue
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.host = self.config.get("host", "localhost")
        self.port = self.config.get("port", 6379)
        self.db = self.config.get("db", 0)
        self.password = self.config.get("password", None)
        self.prefix = self.config.get("prefix", "pyspider:")

        self._client = None
        self._connect()

    def _connect(self):
        """Connect to Redis"""
        if not HAS_REDIS:
            raise ImportError("redis package not installed")

        self._client = redis.Redis(
            host=self.host,
            port=self.port,
            db=self.db,
            password=self.password,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        self._client.ping()

    @property
    def client(self):
        return self._client

    # Queue operations
    def enqueue(self, task: Dict[str, Any], priority: int = 0) -> str:
        """
        Add a task to the queue

        Args:
            task: Task data
            priority: Priority (higher = more urgent)

        Returns:
            Task ID
        """
        task_id = task.get("id") or str(uuid.uuid4())
        task["id"] = task_id
        task["enqueued_at"] = datetime.now().isoformat()
        task["status"] = "pending"

        # Use sorted set for priority queue
        score = priority * 1000000 + int(time.time() * 1000)
        self._client.zadd(f"{self.prefix}queue", {json.dumps(task): score})

        # Also add to pending set for tracking
        self._client.sadd(f"{self.prefix}pending", task_id)

        return task_id

    def dequeue(self, timeout: int = 0) -> Optional[Dict[str, Any]]:
        """
        Get next task from queue

        Args:
            timeout: Blocking timeout in seconds (0 = non-blocking)

        Returns:
            Task data or None
        """
        if timeout > 0:
            # Blocking pop
            result = self._client.bzpopmin(f"{self.prefix}queue", timeout=timeout)
            if result:
                task_data = json.loads(result[1])
                task_id = task_data.get("id")
                self._client.srem(f"{self.prefix}pending", task_id)
                self._client.sadd(f"{self.prefix}processing", task_id)
                return task_data
        else:
            # Non-blocking
            result = self._client.zpopmin(f"{self.prefix}queue")
            if result:
                task_data = json.loads(result[0][0])
                task_id = task_data.get("id")
                self._client.srem(f"{self.prefix}pending", task_id)
                self._client.sadd(f"{self.prefix}processing", task_id)
                return task_data

        return None

    def complete(self, task_id: str) -> None:
        """Mark task as completed"""
        self._client.srem(f"{self.prefix}processing", task_id)
        self._client.sadd(f"{self.prefix}completed", task_id)
        self._client.hset(
            f"{self.prefix}results",
            task_id,
            json.dumps(
                {"completed_at": datetime.now().isoformat(), "status": "success"}
            ),
        )

    def fail(self, task_id: str, error: str) -> None:
        """Mark task as failed"""
        self._client.srem(f"{self.prefix}processing", task_id)
        self._client.hset(
            f"{self.prefix}results",
            task_id,
            json.dumps(
                {
                    "failed_at": datetime.now().isoformat(),
                    "status": "failed",
                    "error": error,
                }
            ),
        )

    def retry(self, task_id: str, max_retries: int = 3) -> bool:
        """Retry a failed task"""
        result = self._client.hget(f"{self.prefix}results", task_id)
        if result:
            data = json.loads(result)
            retries = data.get("retries", 0)
            if retries < max_retries:
                data["retries"] = retries + 1
                data["retried_at"] = datetime.now().isoformat()
                task = data.get("task", {})
                self.enqueue(task, priority=data.get("priority", 0))
                return True
        return False

    def get_status(self) -> Dict[str, Any]:
        """Get queue status"""
        return {
            "pending": self._client.scard(f"{self.prefix}pending"),
            "processing": self._client.scard(f"{self.prefix}processing"),
            "completed": self._client.scard(f"{self.prefix}completed"),
            "queue_size": self._client.zcard(f"{self.prefix}queue"),
        }

    def clear_completed(self, older_than_hours: int = 24) -> int:
        """Clear old completed tasks"""
        # Implementation would need timestamp tracking
        return 0


class DistributedLock:
    """
    Distributed lock using Redis for coordinating multiple spider instances
    """

    def __init__(self, redis_client, key: str, ttl: int = 60):
        self.client = redis_client
        self.key = f"lock:{key}"
        self.ttl = ttl
        self.lock_id = str(uuid.uuid4())

    def acquire(self, blocking: bool = True, timeout: int = 10) -> bool:
        """Acquire the lock"""
        start_time = time.time()

        while True:
            acquired = self.client.set(self.key, self.lock_id, nx=True, ex=self.ttl)
            if acquired:
                return True

            if not blocking or time.time() - start_time > timeout:
                return False

            time.sleep(0.1)

    def release(self) -> bool:
        """Release the lock"""
        # Only release if we own the lock
        script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        return self.client.eval(script, 1, self.key, self.lock_id) == 1

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()


class RateLimiter:
    """
    Distributed rate limiter using Redis
    """

    def __init__(self, redis_client, key: str, max_requests: int, window_seconds: int):
        self.client = redis_client
        self.key = f"ratelimit:{key}"
        self.max_requests = max_requests
        self.window = window_seconds

    def allow(self) -> bool:
        """Check if request is allowed"""
        now = time.time()
        window_start = now - self.window

        # Remove old entries
        self.client.zremrangebyscore(self.key, 0, window_start)

        # Count current requests
        count = self.client.zcard(self.key)

        if count >= self.max_requests:
            return False

        # Add new request
        self.client.zadd(self.key, {str(now): now})
        self.client.expire(self.key, self.window)

        return True

    def get_remaining(self) -> int:
        """Get remaining requests"""
        now = time.time()
        window_start = now - self.window
        self.client.zremrangebyscore(self.key, 0, window_start)
        return max(0, self.max_requests - self.client.zcard(self.key))


def create_queue(config: Dict[str, Any] = None) -> RedisTaskQueue:
    """Create a Redis task queue"""
    return RedisTaskQueue(config)
