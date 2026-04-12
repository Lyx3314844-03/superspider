from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pyspider.core.models import Request
from pyspider.core.spider import Spider
from pyspider.distributed.redis import DistributedScheduler, RedisScheduler


class _FakeRedis:
    def __init__(self, *args, **kwargs):
        self.queue = []
        self.visited = {}
        self.stats = {}
        self.sets = {}
        self.hashes = {}
        self.closed = False

    def lpush(self, key, value):
        self.queue.insert(0, value)

    def rpop(self, key):
        if not self.queue:
            return None
        return self.queue.pop()

    def exists(self, key):
        return 1 if key in self.visited else 0

    def setex(self, key, ttl, value):
        self.visited[key] = (ttl, value)

    def sadd(self, key, value):
        self.sets.setdefault(key, set()).add(value)
        return 1

    def srem(self, key, value):
        self.sets.setdefault(key, set()).discard(value)
        return 1

    def sismember(self, key, value):
        return value in self.sets.setdefault(key, set())

    def scard(self, key):
        return len(self.sets.setdefault(key, set()))

    def hset(self, key, field, value):
        self.hashes.setdefault(key, {})[field] = value
        return 1

    def hget(self, key, field):
        return self.hashes.setdefault(key, {}).get(field)

    def hexists(self, key, field):
        return field in self.hashes.setdefault(key, {})

    def hdel(self, key, field):
        self.hashes.setdefault(key, {}).pop(field, None)
        return 1

    def hlen(self, key):
        return len(self.hashes.setdefault(key, {}))

    def hincrby(self, key, field, value):
        self.stats[field] = self.stats.get(field, 0) + value

    def hgetall(self, key):
        if key == "pyspider:demo:stats":
            return {
                field.encode(): str(value).encode()
                for field, value in self.stats.items()
            }
        return self.hashes.setdefault(key, {})

    def llen(self, key):
        return len(self.queue)

    def keys(self, pattern):
        return list(self.visited.keys())

    def close(self):
        self.closed = True


def test_redis_scheduler_uses_pyspider_namespace(monkeypatch):
    monkeypatch.setattr("pyspider.distributed.redis.redis.Redis", _FakeRedis)

    scheduler = RedisScheduler(spider_name="demo")

    assert scheduler.queue_key == "pyspider:demo:queue"
    assert scheduler.processing_key == "pyspider:demo:processing"
    assert scheduler.dead_letter_key == "pyspider:demo:dead"
    assert scheduler.visited_key == "pyspider:demo:visited"
    assert scheduler.stats_key == "pyspider:demo:stats"


def test_redis_scheduler_round_trips_requests(monkeypatch):
    monkeypatch.setattr("pyspider.distributed.redis.redis.Redis", _FakeRedis)

    scheduler = RedisScheduler(spider_name="demo")
    request = Request(
        url="https://example.com",
        method="POST",
        headers={"X-Test": "1"},
        body="payload",
        meta={"source": "test"},
        priority=7,
    )

    assert scheduler.add_request(request) is True

    next_request = scheduler.next_request()

    assert next_request.url == "https://example.com"
    assert next_request.method == "POST"
    assert next_request.headers == {"X-Test": "1"}
    assert next_request.body == "payload"
    assert next_request.meta == {"source": "test"}
    assert next_request.priority == 7
    assert scheduler.processing_count() == 1
    assert scheduler.heartbeat("https://example.com", lease_ttl=60) is True
    assert scheduler.ack_request("https://example.com", success=True) is True
    assert scheduler.is_visited("https://example.com") is True


def test_redis_scheduler_tracks_stats_and_deduplicates_requests(monkeypatch):
    monkeypatch.setattr("pyspider.distributed.redis.redis.Redis", _FakeRedis)

    scheduler = RedisScheduler(spider_name="demo")
    request = Request(url="https://example.com")

    assert scheduler.add_request(request) is True
    assert scheduler.add_request(request) is False

    scheduler.update_stats("success", 2)
    scheduler.update_stats("failed", 1)

    assert scheduler.queue_len() == 1
    assert scheduler.visited_count() == 0
    assert scheduler.get_stats() == {"success": 2, "failed": 1}


def test_redis_scheduler_reaps_expired_leases_and_dead_letters(monkeypatch):
    monkeypatch.setattr("pyspider.distributed.redis.redis.Redis", _FakeRedis)

    scheduler = RedisScheduler(spider_name="demo")
    request = Request(url="https://example.com")

    assert scheduler.add_request(request) is True
    assert scheduler.lease_request("worker-1", lease_ttl=1) is not None
    assert scheduler.reap_expired_leases(now=time.time() + 2, max_retries=0) == 1
    assert scheduler.dead_letter_count() == 1


def test_distributed_scheduler_reopens_after_close(monkeypatch):
    created = []

    class _FakeScheduler:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.closed = False
            self.requests = []
            created.append(self)

        def add_request(self, request):
            if self.closed:
                raise RuntimeError("scheduler is closed")
            self.requests.append(request)
            return True

        def next_request(self):
            if self.closed:
                raise RuntimeError("scheduler is closed")
            return self.requests.pop(0) if self.requests else None

        def close(self):
            self.closed = True

    monkeypatch.setattr("pyspider.distributed.redis.RedisScheduler", _FakeScheduler)

    scheduler = DistributedScheduler(
        Spider("demo"), redis_url="redis://:secret@redis.example.com:6380/2"
    )
    request = Request(url="https://example.com")

    assert scheduler.enqueue_request(request) is True
    scheduler.close()
    assert scheduler.enqueue_request(request) is True

    assert len(created) == 2
    assert created[0].kwargs == {
        "host": "redis.example.com",
        "port": 6380,
        "password": "secret",
        "db": 2,
        "spider_name": "demo",
    }
