"""
Web 控制台模块
提供 Web 界面监控爬虫状态
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import threading
import time
from datetime import datetime
from typing import Dict, Any, Optional


class Stats:
    """统计信息"""

    def __init__(self, name: str = "pyspider"):
        self.name = name
        self.start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.pages_scraped = 0
        self.pages_failed = 0
        self.items_scraped = 0
        self.bytes_downloaded = 0
        self.start_timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        duration = time.time() - self.start_timestamp
        return {
            "name": self.name,
            "start_time": self.start_time,
            "pages_scraped": self.pages_scraped,
            "pages_failed": self.pages_failed,
            "items_scraped": self.items_scraped,
            "bytes_downloaded": self.bytes_downloaded,
            "duration": f"{duration:.2f}s",
            "pages_per_second": self.pages_scraped / duration if duration > 0 else 0,
        }


class WebConsole:
    """Web 控制台"""

    def __init__(self, port: int = 8080, stats: Stats = None):
        self.port = port
        self.stats = stats or Stats()
        self.server: Optional[HTTPServer] = None
        self.thread: Optional[threading.Thread] = None
        self.spiders: Dict[str, Dict[str, Any]] = {}

    def start(self) -> None:
        """启动 Web 控制台"""
        handler = self._create_handler()
        self.server = HTTPServer(("0.0.0.0", self.port), handler)

        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

        print(f"Web Console started at http://0.0.0.0:{self.port}")

    def stop(self) -> None:
        """停止 Web 控制台"""
        if self.server:
            self.server.shutdown()
            self.server = None

    def _create_handler(self) -> type:
        """创建请求处理器"""
        console = self

        class ConsoleHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/api/stats":
                    self._send_json(console.stats.to_dict())
                elif self.path == "/api/spiders":
                    self._send_json(list(console.spiders.values()))
                elif self.path == "/":
                    self._send_html()
                else:
                    self.send_error(404)

            def _send_json(self, data: Dict[str, Any]):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(data).encode())

            def _send_html(self):
                html = self._generate_html()
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(html.encode())

            def _generate_html(self):
                stats = console.stats.to_dict()
                return f"""
<!DOCTYPE html>
<html>
<head>
    <title>PySpider Web Console</title>
    <meta http-equiv="refresh" content="5">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #1a1a2e; color: #eee; }}
        .card {{ background: #16213e; padding: 20px; border-radius: 10px; margin: 10px 0; }}
        .stat {{ font-size: 24px; color: #00d9ff; }}
        h1 {{ color: #00d9ff; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #2a2a4a; }}
    </style>
</head>
<body>
    <h1>🕷️ PySpider Web Console</h1>
    <div class="card">
        <h2>爬虫统计</h2>
        <table>
            <tr><td>爬虫名称</td><td>{stats['name']}</td></tr>
            <tr><td>启动时间</td><td>{stats['start_time']}</td></tr>
            <tr><td>运行时长</td><td>{stats['duration']}</td></tr>
            <tr><td>爬取页面</td><td class="stat">{stats['pages_scraped']}</td></tr>
            <tr><td>失败页面</td><td class="stat">{stats['pages_failed']}</td></tr>
            <tr><td>提取物品</td><td class="stat">{stats['items_scraped']}</td></tr>
            <tr><td>下载字节</td><td class="stat">{stats['bytes_downloaded'] / 1024:.2f} KB</td></tr>
            <tr><td>页面/秒</td><td class="stat">{stats['pages_per_second']:.2f}</td></tr>
        </table>
    </div>
    <div class="card">
        <h2>爬虫列表</h2>
        <table>
            <tr><th>名称</th><th>状态</th><th>页面</th><th>物品</th></tr>
            <tr><td>{stats['name']}</td><td>running</td><td>{stats['pages_scraped']}</td><td>{stats['items_scraped']}</td></tr>
        </table>
    </div>
    <script>
        // 自动刷新
        setTimeout(() => location.reload(), 5000);
    </script>
</body>
</html>
"""

            def log_message(self, format, *args):
                pass  # 禁用日志

        return ConsoleHandler

    def update_stats(
        self,
        pages_scraped: int = None,
        pages_failed: int = None,
        items_scraped: int = None,
        bytes_downloaded: int = None,
    ) -> None:
        """更新统计"""
        if pages_scraped is not None:
            self.stats.pages_scraped = pages_scraped
        if pages_failed is not None:
            self.stats.pages_failed = pages_failed
        if items_scraped is not None:
            self.stats.items_scraped = items_scraped
        if bytes_downloaded is not None:
            self.stats.bytes_downloaded = bytes_downloaded

    def record_page(self, bytes_downloaded: int = 0) -> None:
        """记录页面"""
        self.stats.pages_scraped += 1
        self.stats.bytes_downloaded += bytes_downloaded

    def record_item(self) -> None:
        """记录物品"""
        self.stats.items_scraped += 1

    def record_error(self) -> None:
        """记录错误"""
        self.stats.pages_failed += 1

    def register_spider(self, name: str, spider_info: Dict[str, Any]) -> None:
        """注册爬虫"""
        self.spiders[name] = {
            "name": name,
            "status": "running",
            "info": spider_info,
        }

    def unregister_spider(self, name: str) -> None:
        """注销爬虫"""
        if name in self.spiders:
            self.spiders[name]["status"] = "stopped"


class ConsoleMiddleware:
    """控制台中间件（Scrapy 风格）"""

    def __init__(self, console: WebConsole):
        self.console = console

    def process_request(self, request, spider):
        """处理请求"""
        pass

    def process_response(self, request, response, spider):
        """处理响应"""
        self.console.record_page(len(response.content))
        return response

    def process_exception(self, request, exception, spider):
        """处理异常"""
        self.console.record_error()
        return None
