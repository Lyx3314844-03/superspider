from pathlib import Path
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pyspider.api.server import SpiderAPI


class _FakeSpider:
    def __init__(self):
        self.started = 0
        self.stopped = 0

    def start(self):
        self.started += 1

    def stop(self):
        self.stopped += 1


class _SlowStartSpider:
    def __init__(self):
        self.started = threading.Event()

    def start(self):
        time.sleep(0.2)
        self.started.set()


class _FakeMonitor:
    def __init__(self):
        self._running = False
        self.started = 0
        self.stopped = 0

    def start(self):
        self.started += 1
        self._running = True

    def stop(self):
        self.stopped += 1
        self._running = False

    def get_stats(self):
        return {"stats": {}}


def test_api_stats_track_requests_without_running_server():
    api = SpiderAPI()
    client = api.app.test_client()

    health_response = client.get("/health")
    stats_response = client.get("/api/v1/stats")

    assert health_response.status_code == 200
    assert stats_response.status_code == 200
    assert stats_response.get_json()["api"]["total_requests"] == 2


def test_queue_endpoints_round_trip_items():
    api = SpiderAPI()
    client = api.app.test_client()

    create_response = client.post(
        "/api/v1/queues/default",
        json={"url": "https://example.com", "priority": 3},
    )
    queue_response = client.get("/api/v1/queues/default")
    queues_response = client.get("/api/v1/queues")
    clear_response = client.delete("/api/v1/queues/default")
    queue_after_clear = client.get("/api/v1/queues/default")

    assert create_response.status_code == 200
    assert create_response.get_json()["status"] == "added"
    assert queue_response.get_json()["size"] == 1
    assert queue_response.get_json()["items"][0]["url"] == "https://example.com"
    assert queue_response.get_json()["items"][0]["priority"] == 3
    assert queues_response.get_json()["total"] == 1
    assert queues_response.get_json()["queues"][0]["name"] == "default"
    assert queues_response.get_json()["queues"][0]["size"] == 1
    assert clear_response.status_code == 200
    assert clear_response.get_json()["status"] == "cleared"
    assert queue_after_clear.get_json()["size"] == 0


def test_spider_start_and_stop_routes_control_spider_and_monitor():
    api = SpiderAPI()
    client = api.app.test_client()
    spider = _FakeSpider()
    monitor = _FakeMonitor()
    api.register_spider("demo", spider, monitor)

    start_response = client.post("/api/v1/spiders/demo/start")
    stop_response = client.post("/api/v1/spiders/demo/stop")

    assert start_response.status_code == 200
    assert stop_response.status_code == 200
    assert spider.started == 1
    assert spider.stopped == 1
    assert monitor.started == 1
    assert monitor.stopped == 1


def test_create_task_requires_url():
    api = SpiderAPI()
    client = api.app.test_client()

    response = client.post("/api/v1/tasks", json={"priority": 1})

    assert response.status_code == 400
    assert response.get_json()["error"] == "Task url is required"


def test_health_is_public_but_api_routes_require_auth_when_token_is_configured():
    api = SpiderAPI(auth_token="secret-token")
    client = api.app.test_client()

    health_response = client.get("/health")
    stats_response = client.get("/api/v1/stats")

    assert health_response.status_code == 200
    assert stats_response.status_code == 401
    assert stats_response.get_json()["error"] == "unauthorized"


def test_api_routes_accept_bearer_token_when_auth_is_enabled():
    api = SpiderAPI(auth_token="secret-token")
    client = api.app.test_client()

    response = client.get(
        "/api/v1/stats",
        headers={"Authorization": "Bearer secret-token"},
    )

    assert response.status_code == 200


def test_graph_extract_returns_nodes_edges_and_stats():
    api = SpiderAPI()
    client = api.app.test_client()

    response = client.post(
        "/api/v1/graph/extract",
        json={
            "html": "<html><head><title>Py Graph API</title></head><body><a href='https://example.com/page'>Read</a><img src='https://example.com/image.png'/></body></html>"
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    data = payload["data"]
    assert data["root_id"]
    assert len(data["nodes"]) >= 3
    assert len(data["edges"]) >= 2
    assert data["stats"]["total_nodes"] >= 3


def test_graph_extract_alias_route_matches_versioned_route():
    api = SpiderAPI()
    client = api.app.test_client()

    response = client.post(
        "/api/graph/extract",
        json={
            "html": "<html><head><title>Alias</title></head><body><a href='https://example.com'>A</a></body></html>"
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True


def test_llm_markdown_route_returns_compact_markdown():
    api = SpiderAPI()
    client = api.app.test_client()

    response = client.post(
        "/api/v1/llm/markdown",
        json={
            "url": "https://example.com/catalog",
            "html": "<html><head><title>Py LLM</title><style>.ad{}</style></head><body><h1>商品</h1><p>详情</p><script>ignored()</script></body></html>",
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert "# Py LLM" in payload["markdown"]
    assert "## 商品" in payload["markdown"]
    assert "ignored" not in payload["markdown"]


def test_llm_markdown_stream_route_returns_sse():
    api = SpiderAPI()
    client = api.app.test_client()

    response = client.post(
        "/api/v1/llm/markdown/stream",
        json={
            "html": "<html><body><p>商品详情</p></body></html>",
            "chunk_size": 2,
        },
    )

    assert response.status_code == 200
    assert response.content_type.startswith("text/event-stream")
    body = response.get_data(as_text=True)
    assert "event: markdown" in body
    assert "event: done" in body


def test_start_spider_returns_without_waiting_for_long_running_start():
    api = SpiderAPI()
    client = api.app.test_client()
    spider = _SlowStartSpider()
    api.register_spider("slow", spider)

    started_at = time.perf_counter()
    response = client.post("/api/v1/spiders/slow/start")
    elapsed = time.perf_counter() - started_at

    assert response.status_code == 200
    assert elapsed < 0.15
    assert spider.started.wait(timeout=1)
