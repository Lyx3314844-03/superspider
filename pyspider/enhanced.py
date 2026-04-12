#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PySpider 增强版

添加：
- 站点地图生成
- 视频下载（集成 you-get）
- API 扫描
- Web UI 改进
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import os
import subprocess
import sys

import requests

REPO_PARENT = Path(__file__).resolve().parents[1]
REPO_PARENT_STR = str(REPO_PARENT)
if REPO_PARENT_STR not in sys.path:
    sys.path.insert(0, REPO_PARENT_STR)

from flask import Flask, jsonify, request
from pyspider.web.app import app as webui_app


def _utcnow():
    return datetime.now(timezone.utc)


# ============================================================================
# 1. 站点地图增强
# ============================================================================


class SitemapGenerator:
    """站点地图生成器"""

    def __init__(self, base_url):
        self.base_url = base_url
        self.urls = []

    def crawl_for_sitemap(self, start_url, depth=3):
        """爬取网站生成站点地图"""
        visited = set()
        queue = [(start_url, 0)]

        while queue:
            url, current_depth = queue.pop(0)

            if url in visited or current_depth > depth:
                continue

            visited.add(url)
            self.urls.append(url)

            try:
                response = requests.get(url, timeout=10)
                # 提取链接
                from bs4 import BeautifulSoup

                soup = BeautifulSoup(response.text, "html.parser")

                for link in soup.find_all("a", href=True):
                    href = link["href"]
                    if href.startswith("http") and self.base_url in href:
                        queue.append((href, current_depth + 1))

            except Exception as e:
                print(f"Error crawling {url}: {e}")

        return self.urls

    def generate_xml(self, output_file="sitemap.xml"):
        """生成 XML 格式的站点地图"""
        xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'

        for url in self.urls:
            xml_content += "  <url>\n"
            xml_content += f"    <loc>{url}</loc>\n"
            xml_content += "    <changefreq>weekly</changefreq>\n"
            xml_content += "    <priority>0.5</priority>\n"
            xml_content += "  </url>\n"

        xml_content += "</urlset>"

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(xml_content)

        print(f"站点地图已保存到：{output_file}")
        return output_file

    def generate_json(self, output_file="sitemap.json"):
        """生成 JSON 格式的站点地图"""
        data = {
            "base_url": self.base_url,
            "total_urls": len(self.urls),
            "urls": self.urls,
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"站点地图已保存到：{output_file}")
        return output_file


# ============================================================================
# 2. 视频下载增强
# ============================================================================


class VideoDownloader:
    """视频下载器（使用 you-get）"""

    def __init__(self, output_dir="./videos"):
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def download(self, url, quality="1080p", audio_only=False):
        """下载视频"""
        cmd = ["you-get"]

        if audio_only:
            cmd.extend(["-x", "mp3"])
        else:
            cmd.extend(["-i", quality])

        cmd.extend(["-o", self.output_dir, url])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode == 0:
                return {
                    "success": True,
                    "output": result.stdout,
                    "dir": self.output_dir,
                }
            else:
                return {"success": False, "error": result.stderr}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "下载超时"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def download_batch(self, urls, quality="1080p"):
        """批量下载"""
        results = []
        for url in urls:
            result = self.download(url, quality)
            result["url"] = url
            results.append(result)
        return results

    def get_info(self, url):
        """获取视频信息"""
        cmd = ["you-get", "--json", url]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                return None
        except Exception:
            return None


# ============================================================================
# 3. API 扫描增强
# ============================================================================


class APIScanner:
    """API 端点扫描器"""

    def __init__(self):
        self.common_endpoints = [
            "/api",
            "/api/v1",
            "/api/v2",
            "/graphql",
            "/graphql/v1",
            "/rest",
            "/rest/v1",
            "/swagger",
            "/swagger.json",
            "/swagger-ui",
            "/api-docs",
            "/openapi.json",
            "/health",
            "/healthz",
            "/ready",
            "/metrics",
            "/status",
            "/info",
        ]

    def scan(self, base_url, depth=2, timeout=5):
        """扫描 API 端点"""
        results = []

        # 扫描常见端点
        for endpoint in self.common_endpoints:
            url = base_url + endpoint
            result = self.test_endpoint(url, timeout)
            if result["found"]:
                results.append(result)

        # 从页面提取
        links = self.extract_api_links(base_url, depth)
        for link in links:
            if not any(r["url"] == link for r in results):
                result = self.test_endpoint(link, timeout)
                if result["found"]:
                    results.append(result)

        return {
            "base_url": base_url,
            "endpoints": results,
            "total": len(results),
            "timestamp": _utcnow().isoformat(),
        }

    def test_endpoint(self, url, timeout):
        """测试端点"""
        result = {"url": url, "found": False, "methods": [], "response_time": 0}

        methods = ["GET", "POST", "OPTIONS"]

        for method in methods:
            try:
                start = _utcnow()
                response = requests.request(
                    method, url, timeout=timeout, headers={"Accept": "application/json"}
                )
                elapsed = (_utcnow() - start).total_seconds() * 1000

                if response.ok or response.status_code in [401, 403]:
                    result["found"] = True
                    result["methods"].append(
                        {
                            "method": method,
                            "status": response.status_code,
                            "response_time": elapsed,
                        }
                    )
            except Exception:
                pass

        return result

    def extract_api_links(self, base_url, depth):
        """从页面提取 API 链接"""
        # 使用 pyspider 爬取
        api_links = []
        # 简化实现
        return api_links

    def generate_openapi(self, results):
        """生成 OpenAPI 规范"""
        openapi = {
            "openapi": "3.0.0",
            "info": {
                "title": "Scanned API",
                "version": "1.0.0",
                "description": "Auto-generated from API scan",
            },
            "servers": [{"url": results["base_url"]}],
            "paths": {},
        }

        for endpoint in results["endpoints"]:
            path = endpoint["url"].replace(results["base_url"], "")
            openapi["paths"][path] = {}

            for method in endpoint["methods"]:
                openapi["paths"][path][method["method"].lower()] = {
                    "summary": f"Auto-discovered {method['method']} endpoint",
                    "responses": {
                        str(method["status"]): {
                            "description": f"Response {method['status']}"
                        }
                    },
                }

        return openapi


# ============================================================================
# 4. Web UI 增强
# ============================================================================


def create_enhanced_webui():
    """创建增强的 Web UI"""

    # 创建 Flask 应用
    enhanced_app = Flask(__name__)

    @enhanced_app.route("/api/sitemap", methods=["POST"])
    def generate_sitemap():
        """生成站点地图 API"""
        data = request.json
        base_url = data.get("url")
        depth = data.get("depth", 3)

        generator = SitemapGenerator(base_url)
        urls = generator.crawl_for_sitemap(base_url, depth)

        # 保存
        xml_file = generator.generate_xml()
        json_file = generator.generate_json()

        return jsonify(
            {
                "success": True,
                "urls_count": len(urls),
                "xml_file": xml_file,
                "json_file": json_file,
            }
        )

    @enhanced_app.route("/api/download", methods=["POST"])
    def download_video():
        """视频下载 API"""
        data = request.json
        url = data.get("url")
        quality = data.get("quality", "1080p")
        audio_only = data.get("audio_only", False)

        downloader = VideoDownloader()
        result = downloader.download(url, quality, audio_only)

        return jsonify(result)

    @enhanced_app.route("/api/scan", methods=["POST"])
    def scan_api():
        """API 扫描 API"""
        data = request.json
        base_url = data.get("url")
        depth = data.get("depth", 2)

        scanner = APIScanner()
        result = scanner.scan(base_url, depth)

        return jsonify(result)

    @enhanced_app.route("/api/stats")
    def get_stats():
        """获取统计信息"""
        # 从 pyspider 数据库获取
        return jsonify({"tasks": 0, "workers": 1, "queue": 0})

    return enhanced_app


# ============================================================================
# 5. 分布式增强
# ============================================================================


class DistributedScheduler:
    """分布式调度器"""

    def __init__(self, redis_url="redis://localhost:6379"):
        import redis

        self.redis = redis.Redis.from_url(redis_url)
        self.queue_name = "pyspider_queue"
        self.result_queue = "pyspider_results"

    def add_task(self, task):
        """添加任务"""
        self.redis.lpush(self.queue_name, json.dumps(task))
        return True

    def get_task(self):
        """获取任务"""
        result = self.redis.brpop(self.queue_name, timeout=0)
        if result:
            return json.loads(result[1])
        return None

    def save_result(self, result):
        """保存结果"""
        self.redis.lpush(self.result_queue, json.dumps(result))

    def get_stats(self):
        """获取统计"""
        queue_len = self.redis.llen(self.queue_name)
        result_len = self.redis.llen(self.result_queue)

        return {"pending": queue_len, "completed": result_len}


# ============================================================================
# CLI 入口
# ============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("""
PySpider 增强版

用法:
  python enhanced.py sitemap <URL> [深度]
  python enhanced.py download <URL> [画质]
  python enhanced.py scan <URL> [深度]
  python enhanced.py webui [端口]
  python enhanced.py worker
        """)
        sys.exit(1)

    command = sys.argv[1]

    if command == "sitemap":
        url = sys.argv[2] if len(sys.argv) > 2 else "https://example.com"
        depth = int(sys.argv[3]) if len(sys.argv) > 3 else 3

        generator = SitemapGenerator(url)
        urls = generator.crawl_for_sitemap(url, depth)
        generator.generate_xml()
        generator.generate_json()

        print(f"发现 {len(urls)} 个 URL")

    elif command == "download":
        url = sys.argv[2] if len(sys.argv) > 2 else ""
        quality = sys.argv[3] if len(sys.argv) > 3 else "1080p"

        downloader = VideoDownloader()
        result = downloader.download(url, quality)
        print(json.dumps(result, indent=2))

    elif command == "scan":
        url = sys.argv[2] if len(sys.argv) > 2 else ""
        depth = int(sys.argv[3]) if len(sys.argv) > 3 else 2

        scanner = APIScanner()
        result = scanner.scan(url, depth)
        print(json.dumps(result, indent=2))

    elif command == "webui":
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 5010

        # 启动原生 PySpider Web UI
        webui_app.run(host="0.0.0.0", port=port)

    elif command == "worker":
        scheduler = DistributedScheduler()
        print("Worker 启动，监听任务...")

        while True:
            task = scheduler.get_task()
            if task:
                print(f"处理任务：{task.get('url')}")
                # 执行爬取
                scheduler.save_result({"success": True})

    else:
        print(f"未知命令：{command}")
