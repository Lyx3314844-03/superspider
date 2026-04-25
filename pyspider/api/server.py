"""
REST API 服务器
提供爬虫控制、状态查询、任务管理等 API
"""

import logging
import os
import threading
import requests
from typing import Dict, List, Optional, Any
from html.parser import HTMLParser
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import time

from pyspider.llm_output import html_to_markdown, sse_markdown_events

logger = logging.getLogger(__name__)


class SpiderAPI:
    """爬虫 REST API"""

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 5000,
        debug: bool = False,
        auth_token: Optional[str] = None,
    ):
        self.host = host
        self.port = port
        self.debug = debug
        self.auth_token = (auth_token or os.getenv("PYSPIDER_API_TOKEN") or "").strip()

        # 创建 Flask 应用
        self.app = Flask(__name__)
        CORS(self.app)  # 启用 CORS
        self.app.before_request(self._before_request)

        # 注册路由
        self._register_routes()

        # 爬虫实例存储
        self.spiders: Dict[str, Any] = {}
        self.spider_threads: Dict[str, threading.Thread] = {}
        self.monitors: Dict[str, Any] = {}
        self.tasks: Dict[str, Dict] = {}
        self.queues: Dict[str, List[Dict[str, Any]]] = {}

        # API 统计
        self.api_stats = {
            "requests_total": 0,
            "requests_by_endpoint": {},
            "start_time": time.time(),
        }

    def _register_routes(self):
        """注册路由"""
        # 健康检查
        self.app.route("/health", methods=["GET"])(self.health_check)
        self.app.route("/api/v1/status", methods=["GET"])(self.get_status)

        # 爬虫管理
        self.app.route("/api/v1/spiders", methods=["GET"])(self.list_spiders)
        self.app.route("/api/v1/spiders/<name>", methods=["GET"])(self.get_spider)
        self.app.route("/api/v1/spiders/<name>/start", methods=["POST"])(
            self.start_spider
        )
        self.app.route("/api/v1/spiders/<name>/stop", methods=["POST"])(
            self.stop_spider
        )
        self.app.route("/api/v1/spiders/<name>/stats", methods=["GET"])(
            self.get_spider_stats
        )

        # 任务管理
        self.app.route("/api/v1/tasks", methods=["GET"])(self.list_tasks)
        self.app.route("/api/v1/tasks", methods=["POST"])(self.create_task)
        self.app.route("/api/v1/tasks/<task_id>", methods=["GET"])(self.get_task)
        self.app.route("/api/v1/tasks/<task_id>", methods=["DELETE"])(self.delete_task)

        # 监控
        self.app.route("/api/v1/monitors", methods=["GET"])(self.list_monitors)
        self.app.route("/api/v1/monitors/<name>/dashboard", methods=["GET"])(
            self.get_dashboard
        )
        self.app.route("/api/v1/metrics", methods=["GET"])(self.get_metrics)

        # 队列管理
        self.app.route("/api/v1/queues", methods=["GET"])(self.list_queues)
        self.app.route("/api/v1/queues/<name>", methods=["GET"])(self.get_queue)
        self.app.route("/api/v1/queues/<name>", methods=["POST"])(self.add_to_queue)
        self.app.route("/api/v1/queues/<name>", methods=["DELETE"])(self.clear_queue)

        # 统计
        self.app.route("/api/v1/stats", methods=["GET"])(self.get_stats)
        self.app.route("/api/v1/graph/extract", methods=["POST"])(self.extract_graph)
        self.app.route("/api/graph/extract", methods=["POST"])(self.extract_graph)
        self.app.route("/api/v1/llm/markdown", methods=["POST"])(self.llm_markdown)
        self.app.route("/api/v1/llm/markdown/stream", methods=["POST"])(
            self.llm_markdown_stream
        )

        # 错误处理
        self.app.errorhandler(404)(self.not_found)
        self.app.errorhandler(500)(self.internal_error)

    # ============ 健康检查 ============

    def health_check(self) -> Response:
        """健康检查"""
        return jsonify(
            {
                "status": "healthy",
                "timestamp": time.time(),
                "version": "1.0.0",
            }
        )

    def get_status(self) -> Response:
        """获取系统状态"""
        uptime = time.time() - self.api_stats["start_time"]

        return jsonify(
            {
                "status": "running",
                "uptime_seconds": uptime,
                "spiders_count": len(self.spiders),
                "tasks_count": len(self.tasks),
                "api_requests": self.api_stats["requests_total"],
            }
        )

    # ============ 爬虫管理 ============

    def list_spiders(self) -> Response:
        """获取爬虫列表"""
        spiders_info = {}

        for name, spider in self.spiders.items():
            monitor = self.monitors.get(name)
            stats = monitor.get_stats() if monitor else {}

            spiders_info[name] = {
                "name": name,
                "status": "running" if monitor and monitor._running else "stopped",
                "stats": stats.get("stats", {}),
            }

        return jsonify(
            {
                "spiders": spiders_info,
                "total": len(spiders_info),
            }
        )

    def get_spider(self, name: str) -> Response:
        """获取爬虫详情"""
        if name not in self.spiders:
            return jsonify({"error": f"Spider {name} not found"}), 404

        monitor = self.monitors.get(name)
        stats = monitor.get_stats() if monitor else {}

        return jsonify(
            {
                "name": name,
                "status": "running" if monitor and monitor._running else "stopped",
                "stats": stats,
            }
        )

    def start_spider(self, name: str) -> Response:
        """启动爬虫"""
        if name not in self.spiders:
            return jsonify({"error": f"Spider {name} not found"}), 404

        spider = self.spiders[name]
        start = getattr(spider, "start", None)
        if callable(start):
            thread = threading.Thread(target=start, daemon=True)
            thread.start()
            self.spider_threads[name] = thread

        if name in self.monitors:
            self.monitors[name].start()

        return jsonify(
            {
                "status": "started",
                "spider": name,
            }
        )

    def stop_spider(self, name: str) -> Response:
        """停止爬虫"""
        if name not in self.spiders:
            return jsonify({"error": f"Spider {name} not found"}), 404

        spider = self.spiders[name]
        stop = getattr(spider, "stop", None)
        if callable(stop):
            stop()

        if name in self.monitors:
            self.monitors[name].stop()

        return jsonify(
            {
                "status": "stopped",
                "spider": name,
            }
        )

    def get_spider_stats(self, name: str) -> Response:
        """获取爬虫统计"""
        if name not in self.spiders:
            return jsonify({"error": f"Spider {name} not found"}), 404

        monitor = self.monitors.get(name)
        if not monitor:
            return jsonify({"error": f"No monitor for spider {name}"}), 404

        stats = monitor.get_stats()
        return jsonify(stats)

    # ============ 任务管理 ============

    def list_tasks(self) -> Response:
        """获取任务列表"""
        return jsonify(
            {
                "tasks": list(self.tasks.values()),
                "total": len(self.tasks),
            }
        )

    def create_task(self) -> Response:
        """创建任务"""
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        if not data.get("url"):
            return jsonify({"error": "Task url is required"}), 400

        task_id = f"task_{int(time.time() * 1000)}"

        task = {
            "id": task_id,
            "url": data.get("url"),
            "spider": data.get("spider", "default"),
            "priority": data.get("priority", 0),
            "status": "pending",
            "created_at": time.time(),
            "updated_at": time.time(),
            "metadata": data.get("metadata", {}),
        }

        self.tasks[task_id] = task

        return (
            jsonify(
                {
                    "status": "created",
                    "task": task,
                }
            ),
            201,
        )

    def get_task(self, task_id: str) -> Response:
        """获取任务详情"""
        if task_id not in self.tasks:
            return jsonify({"error": f"Task {task_id} not found"}), 404

        return jsonify(self.tasks[task_id])

    def delete_task(self, task_id: str) -> Response:
        """删除任务"""
        if task_id not in self.tasks:
            return jsonify({"error": f"Task {task_id} not found"}), 404

        del self.tasks[task_id]

        return jsonify(
            {
                "status": "deleted",
                "task_id": task_id,
            }
        )

    # ============ 监控 ============

    def list_monitors(self) -> Response:
        """获取监控器列表"""
        monitors_info = {}

        for name, monitor in self.monitors.items():
            monitors_info[name] = {
                "name": name,
                "status": "running" if monitor._running else "stopped",
            }

        return jsonify(
            {
                "monitors": monitors_info,
                "total": len(monitors_info),
            }
        )

    def get_dashboard(self, name: str) -> Response:
        """获取仪表盘数据"""
        if name not in self.monitors:
            return jsonify({"error": f"Monitor {name} not found"}), 404

        monitor = self.monitors[name]
        dashboard = monitor.get_dashboard_data()

        return jsonify(dashboard)

    def get_metrics(self) -> Response:
        """获取性能指标"""
        metrics = {}

        for name, monitor in self.monitors.items():
            stats = monitor.get_stats()
            metrics[name] = {
                "performance": stats.get("performance", {}),
                "resources": stats.get("resources", {}),
            }

        return jsonify(
            {
                "metrics": metrics,
            }
        )

    # ============ 队列管理 ============

    def list_queues(self) -> Response:
        """获取队列列表"""
        queues = [
            {
                "name": name,
                "size": len(items),
            }
            for name, items in self.queues.items()
        ]

        return jsonify(
            {
                "queues": queues,
                "total": len(queues),
            }
        )

    def get_queue(self, name: str) -> Response:
        """获取队列详情"""
        items = list(self.queues.get(name, []))
        return jsonify(
            {
                "name": name,
                "size": len(items),
                "items": items,
            }
        )

    def add_to_queue(self, name: str) -> Response:
        """添加到队列"""
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        item = dict(data)
        item.setdefault("added_at", time.time())
        self.queues.setdefault(name, []).append(item)

        return jsonify(
            {
                "status": "added",
                "queue": name,
                "size": len(self.queues[name]),
            }
        )

    def clear_queue(self, name: str) -> Response:
        """清空队列"""
        cleared = len(self.queues.get(name, []))
        self.queues[name] = []

        return jsonify(
            {
                "status": "cleared",
                "queue": name,
                "cleared": cleared,
            }
        )

    # ============ 统计 ============

    def get_stats(self) -> Response:
        """获取 API 统计"""
        uptime = time.time() - self.api_stats["start_time"]

        return jsonify(
            {
                "api": {
                    "uptime_seconds": uptime,
                    "total_requests": self.api_stats["requests_total"],
                    "requests_by_endpoint": self.api_stats["requests_by_endpoint"],
                },
                "spiders": len(self.spiders),
                "tasks": len(self.tasks),
                "monitors": len(self.monitors),
            }
        )

    def extract_graph(self) -> Response:
        """提取 HTML 图结构"""
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400

        html = (data.get("html") or "").strip()
        url = (data.get("url") or "").strip()
        if not html and not url:
            return (
                jsonify({"success": False, "error": "Graph html or url is required"}),
                400,
            )

        if not html:
            try:
                response = requests.get(url, timeout=15)
                response.raise_for_status()
                html = response.text
            except requests.RequestException as exc:
                return (
                    jsonify(
                        {"success": False, "error": f"Failed to fetch graph url: {exc}"}
                    ),
                    400,
                )

        return jsonify(
            {
                "success": True,
                "data": self._build_graph_payload(html),
            }
        )

    def llm_markdown(self) -> Response:
        """Convert provided HTML into compact Markdown for AI CLI contexts."""
        data = request.get_json() or {}
        html = str(data.get("html") or "")
        if not html:
            return jsonify({"success": False, "error": "html is required"}), 400
        max_chars = int(data.get("max_chars") or 12000)
        markdown = html_to_markdown(
            html,
            base_url=str(data.get("url") or ""),
            max_chars=max_chars,
        )
        return jsonify(
            {
                "success": True,
                "markdown": markdown,
                "truncated": markdown.endswith("[truncated]"),
            }
        )

    def llm_markdown_stream(self) -> Response:
        """Stream Markdown chunks as server-sent events."""
        data = request.get_json() or {}
        html = str(data.get("html") or "")
        if not html:
            return jsonify({"success": False, "error": "html is required"}), 400
        markdown = html_to_markdown(
            html,
            base_url=str(data.get("url") or ""),
            max_chars=int(data.get("max_chars") or 12000),
        )
        chunk_size = int(data.get("chunk_size") or 2048)
        return Response(
            sse_markdown_events(markdown, chunk_size=chunk_size),
            mimetype="text/event-stream",
        )

    # ============ 错误处理 ============

    def not_found(self, error) -> Response:
        """404 处理"""
        return (
            jsonify(
                {
                    "error": "Not found",
                    "path": request.path,
                }
            ),
            404,
        )

    def internal_error(self, error) -> Response:
        """500 处理"""
        logger.error(f"Internal error: {error}")
        return (
            jsonify(
                {
                    "error": "Internal server error",
                    "message": str(error),
                }
            ),
            500,
        )

    # ============ 中间件 ============

    def _before_request(self):
        """请求前处理"""
        self.api_stats["requests_total"] += 1
        endpoint = request.endpoint or "unknown"
        self.api_stats["requests_by_endpoint"][endpoint] = (
            self.api_stats["requests_by_endpoint"].get(endpoint, 0) + 1
        )
        if request.method == "OPTIONS":
            return None
        if not self.auth_token:
            return None
        if request.path == "/health":
            return None

        token = (request.headers.get("Authorization") or "").strip()
        if token.lower().startswith("bearer "):
            token = token[7:].strip()
        if not token:
            token = (request.headers.get("X-API-Token") or "").strip()
        if token != self.auth_token:
            return jsonify({"error": "unauthorized"}), 401
        return None

    def _build_graph_payload(self, html: str) -> Dict[str, Any]:
        try:
            from pyspider.graph_crawler.graph_builder import GraphBuilder

            graph = GraphBuilder().build(html)
            payload = graph.to_dict()
            return {
                "root_id": payload["root"],
                "nodes": payload["nodes"],
                "edges": payload["edges"],
                "stats": payload["stats"],
            }
        except ModuleNotFoundError:
            parser = _FallbackGraphParser()
            parser.feed(html)
            return parser.payload()

    # ============ 运行 ============

    def register_spider(self, name: str, spider: Any, monitor: Any = None):
        """注册爬虫"""
        self.spiders[name] = spider
        if monitor:
            self.monitors[name] = monitor

    def run(self, host: str = None, port: int = None, debug: bool = None, **kwargs):
        """运行 API 服务器"""
        host = host or self.host
        port = port or self.port
        debug = debug if debug is not None else self.debug

        logger.info(f"Starting API server on {host}:{port}")

        # 在新线程中运行
        thread = threading.Thread(
            target=self.app.run,
            kwargs={
                "host": host,
                "port": port,
                "debug": debug,
                "use_reloader": False,
                "use_debugger": debug,
                "threaded": True,
                **kwargs,
            },
        )
        thread.daemon = True
        thread.start()

        return thread

    def stop(self):
        """停止 API 服务器"""
        # Flask 没有优雅的停止方法
        logger.info("API server stopping...")


class _FallbackGraphParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.nodes: Dict[str, Dict[str, Any]] = {
            "document": {
                "id": "document",
                "type": "document",
                "tag": "html",
                "attributes": {},
                "text": "",
                "children": [],
                "parent": None,
            }
        }
        self.edges: Dict[str, Dict[str, Any]] = {}
        self.root_id = "document"
        self._title_index = 0
        self._heading_index = 0
        self._link_index = 0
        self._image_index = 0
        self._capture_tag: Optional[str] = None
        self._capture_node_id: Optional[str] = None

    def handle_starttag(self, tag: str, attrs):
        attributes = dict(attrs)
        if tag == "title":
            node_id = f"title-{self._title_index}"
            self._title_index += 1
            self._register_node(node_id, "title", tag, {})
            self._capture_tag = tag
            self._capture_node_id = node_id
        elif tag in {"h1", "h2", "h3"}:
            node_id = f"heading-{self._heading_index}"
            self._heading_index += 1
            self._register_node(node_id, "heading", tag, {})
            self._capture_tag = tag
            self._capture_node_id = node_id
        elif tag == "a" and attributes.get("href"):
            node_id = f"link-{self._link_index}"
            self._link_index += 1
            self._register_node(node_id, "link", tag, {"href": attributes["href"]})
            self._register_edge(f"link-{node_id}", node_id, attributes["href"], "link")
            self._capture_tag = tag
            self._capture_node_id = node_id
        elif tag == "img" and attributes.get("src"):
            node_id = f"image-{self._image_index}"
            self._image_index += 1
            self._register_node(node_id, "image", tag, {"src": attributes["src"]})
            self._register_edge(f"image-{node_id}", node_id, attributes["src"], "image")

    def handle_endtag(self, tag: str):
        if self._capture_tag == tag:
            self._capture_tag = None
            self._capture_node_id = None

    def handle_data(self, data: str):
        if not self._capture_node_id:
            return
        text = data.strip()
        if not text:
            return
        node = self.nodes[self._capture_node_id]
        node["text"] = f"{node['text']} {text}".strip()

    def payload(self) -> Dict[str, Any]:
        node_types: Dict[str, int] = {}
        for node in self.nodes.values():
            node_type = node["type"]
            node_types[node_type] = node_types.get(node_type, 0) + 1
        return {
            "root_id": self.root_id,
            "nodes": self.nodes,
            "edges": self.edges,
            "stats": {
                "total_nodes": len(self.nodes),
                "total_edges": len(self.edges),
                "node_types": node_types,
            },
        }

    def _register_node(
        self, node_id: str, node_type: str, tag: str, attributes: Dict[str, str]
    ):
        self.nodes[node_id] = {
            "id": node_id,
            "type": node_type,
            "tag": tag,
            "attributes": attributes,
            "text": "",
            "children": [],
            "parent": self.root_id,
        }
        self.nodes[self.root_id]["children"].append(node_id)
        self._register_edge(f"contains-{node_id}", self.root_id, node_id, "contains")

    def _register_edge(self, edge_id: str, source: str, target: str, relation: str):
        self.edges[edge_id] = {
            "id": edge_id,
            "source": source,
            "target": target,
            "relation": relation,
            "weight": 1.0,
        }


# 使用示例
if __name__ == "__main__":
    # 创建 API
    api = SpiderAPI(host="0.0.0.0", port=5000, debug=True)

    # 注册爬虫（示例）
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
                "spider_name": "test",
                "status": "running",
                "pages_crawled": 100,
                "success_rate": 95.0,
            }

    api.register_spider("test_spider", MockSpider(), MockMonitor())

    # 启动服务器
    thread = api.run()
    print("API server started on http://localhost:5000")

    # 保持运行
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        api.stop()
        print("API server stopped")
