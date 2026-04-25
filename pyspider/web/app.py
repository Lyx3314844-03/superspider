"""
PySpider Web UI - Flask 应用
提供爬虫任务管理、监控和结果查看功能
"""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import sqlite3
import json
import threading
import os
import re
from datetime import datetime
from pathlib import Path

import requests
from pyspider.runtime.sinks import FileAuditSink, FileResultSink

try:
    from pyspider.graph_crawler.graph_builder import GraphBuilder
except Exception:  # pragma: no cover - optional graph dependency fallback
    GraphBuilder = None

app = Flask(__name__)
CORS(app)

DATABASE = os.path.join(os.path.dirname(__file__), "spider.db")
TASK_STOPS = {}
TASK_STOPS_LOCK = threading.Lock()


def control_plane_dir():
    return Path(__file__).resolve().parents[1] / "artifacts" / "control-plane"


def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库"""
    conn = get_db()
    cursor = conn.cursor()

    # 创建任务表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            url TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            config TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP,
            finished_at TIMESTAMP,
            total_requests INTEGER DEFAULT 0,
            success_requests INTEGER DEFAULT 0,
            failed_requests INTEGER DEFAULT 0
        )
    """)

    # 创建结果表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER,
            url TEXT,
            data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES tasks(id)
        )
    """)

    # 创建日志表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER,
            level TEXT,
            message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES tasks(id)
        )
    """)

    conn.commit()
    conn.close()


def get_task_row(task_id):
    """读取单个任务"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    conn.close()
    return normalize_task_row(dict(row)) if row else None


def normalize_task_row(row):
    if not row:
        return row
    config = row.get("config")
    if isinstance(config, str) and config.strip():
        try:
            row["config"] = json.loads(config)
        except json.JSONDecodeError:
            row["config"] = {}
    elif config is None:
        row["config"] = {}
    row["running"] = row.get("status") == "running"
    row["stats"] = {
        "total_requests": row.get("total_requests", 0),
        "success_requests": row.get("success_requests", 0),
        "failed_requests": row.get("failed_requests", 0),
    }
    return row


def normalize_result_row(row):
    payload = {}
    raw = row.get("data")
    if isinstance(raw, str) and raw.strip():
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {}
    return {
        "id": row.get("id"),
        "task_id": row.get("task_id"),
        "url": row.get("url"),
        "final_url": payload.get("final_url", row.get("url")),
        "status": payload.get("status", ""),
        "http_status": payload.get("http_status", 0),
        "content_type": payload.get("content_type", ""),
        "title": payload.get("title", ""),
        "bytes": payload.get("bytes", 0),
        "duration_ms": payload.get("duration_ms", 0),
        "created_at": row.get("created_at"),
        "artifacts": payload.get("artifacts", {}),
        "artifact_refs": payload.get("artifact_refs", payload.get("artifacts", {})),
    }


def _sqlite_timestamp(value):
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def append_log(task_id, level, message):
    """写入任务日志"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO logs (task_id, level, message) VALUES (?, ?, ?)",
        (task_id, level, message),
    )
    conn.commit()
    conn.close()
    payload = {
        "task_id": task_id,
        "level": level,
        "message": message,
        "runtime": "python",
        "timestamp": datetime.now().isoformat(),
    }
    FileAuditSink(control_plane_dir() / "py-web-audit.jsonl").emit("task.log", payload)
    FileAuditSink(control_plane_dir() / "events.jsonl").emit("task.log", payload)


def append_result(task_id, url, data):
    """写入任务结果"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO results (task_id, url, data) VALUES (?, ?, ?)",
        (task_id, url, json.dumps(data, ensure_ascii=False)),
    )
    conn.commit()
    conn.close()
    FileResultSink(control_plane_dir() / "results.jsonl").write(
        {
            "id": f"py-web-{task_id}-{int(datetime.now().timestamp() * 1000)}",
            "runtime": "python",
            "state": data.get("status", ""),
            "url": data.get("final_url") or url,
            "status_code": data.get("http_status", 0),
            "extract": {
                "task_id": task_id,
                "title": data.get("title", ""),
                "content_type": data.get("content_type", ""),
                "bytes": data.get("bytes", 0),
                "duration_ms": data.get("duration_ms", 0),
                "artifacts": data.get("artifacts", {}),
            },
            "artifact_refs": data.get("artifact_refs", data.get("artifacts", {})),
            "updated_at": datetime.now().isoformat(),
        }
    )


def update_task_state(
    task_id,
    status,
    started_at=None,
    finished_at=None,
    total_requests=None,
    success_requests=None,
    failed_requests=None,
    set_started_at=False,
    set_finished_at=False,
):
    """更新任务状态"""
    conn = get_db()
    cursor = conn.cursor()
    started_at = _sqlite_timestamp(started_at)
    finished_at = _sqlite_timestamp(finished_at)
    started_value = started_at if set_started_at else "__KEEP__"
    finished_value = finished_at if set_finished_at else "__KEEP__"
    cursor.execute(
        """
        UPDATE tasks
        SET status = ?,
            started_at = CASE WHEN ? = '__KEEP__' THEN started_at ELSE ? END,
            finished_at = CASE WHEN ? = '__KEEP__' THEN finished_at ELSE ? END,
            total_requests = COALESCE(?, total_requests),
            success_requests = COALESCE(?, success_requests),
            failed_requests = COALESCE(?, failed_requests)
        WHERE id = ?
        """,
        (
            status,
            started_value,
            started_at,
            finished_value,
            finished_at,
            total_requests,
            success_requests,
            failed_requests,
            task_id,
        ),
    )
    conn.commit()
    conn.close()


def extract_title(content):
    """从 HTML 提取标题"""
    match = re.search(
        r"<title[^>]*>(.*?)</title>", content, flags=re.IGNORECASE | re.DOTALL
    )
    if not match:
        return ""
    return re.sub(r"\s+", " ", match.group(1)).strip()


def build_graph_artifact(task_id, html):
    if not html or not html.strip():
        return {}

    payload = build_graph_payload(html)

    path = (
        control_plane_dir()
        / "graphs"
        / f"python-{task_id}-{int(datetime.now().timestamp() * 1000)}.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "graph": {
            "kind": "graph",
            "path": str(path),
            "root_id": payload["root_id"],
            "stats": payload["stats"],
        }
    }


def build_graph_payload(html):
    if GraphBuilder is None:
        links = re.findall(
            r'<a[^>]+href=["\']([^"\']+)["\']', html, flags=re.IGNORECASE
        )
        images = re.findall(
            r'<img[^>]+src=["\']([^"\']+)["\']', html, flags=re.IGNORECASE
        )
        headings = re.findall(
            r"<h[1-3][^>]*>(.*?)</h[1-3]>", html, flags=re.IGNORECASE | re.DOTALL
        )
        title = extract_title(html)
        return {
            "root_id": "document",
            "nodes": {
                "document": {"id": "document", "type": "document", "tag": "document"},
                **(
                    {
                        "title": {
                            "id": "title",
                            "type": "title",
                            "tag": "title",
                            "text": title,
                        }
                    }
                    if title
                    else {}
                ),
            },
            "edges": {},
            "stats": {
                "total_nodes": 1
                + (1 if title else 0)
                + len(links)
                + len(images)
                + len(headings),
                "total_edges": len(links) + len(images),
                "node_types": {
                    "document": 1,
                    "title": 1 if title else 0,
                    "link": len(links),
                    "image": len(images),
                    "heading": len(headings),
                },
            },
        }
    graph = GraphBuilder().build(html).to_dict()
    return {
        "root_id": "document",
        "graph_root_id": graph.get("root") or "document",
        "nodes": graph.get("nodes", {}),
        "edges": graph.get("edges", {}),
        "stats": graph.get("stats", {}),
    }


def run_task(task_id, target_url, stop_event):
    """后台执行一次真实请求"""
    append_log(task_id, "info", f"fetching {target_url}")
    started_at = datetime.now()

    if stop_event.is_set():
        append_log(task_id, "warning", "task cancelled before request")
        return

    try:
        response = requests.get(
            target_url,
            timeout=15,
            headers={"User-Agent": "PySpider-WebUI/1.0"},
        )
        duration_ms = int((datetime.now() - started_at).total_seconds() * 1000)
        if stop_event.is_set():
            append_log(task_id, "warning", "task cancelled before completion")
            return

        body = response.text[: 1024 * 1024]
        graph_artifacts = build_graph_artifact(task_id, body)
        graph_artifacts = build_graph_artifact(task_id, body)
        payload = {
            "status": "completed" if response.ok else "failed",
            "http_status": response.status_code,
            "final_url": response.url,
            "title": extract_title(body),
            "content_type": response.headers.get("Content-Type", ""),
            "bytes": len(response.content),
            "duration_ms": duration_ms,
            "artifacts": graph_artifacts,
            "artifact_refs": graph_artifacts,
        }
        append_result(task_id, target_url, payload)
        update_task_state(
            task_id,
            "completed" if response.ok else "failed",
            finished_at=datetime.now(),
            total_requests=1,
            success_requests=1 if response.ok else 0,
            failed_requests=0 if response.ok else 1,
            set_finished_at=True,
        )
        append_log(
            task_id,
            "info",
            f"task finished with status {response.status_code} in {duration_ms}ms",
        )
    except requests.RequestException as exc:
        if stop_event.is_set():
            append_log(task_id, "warning", "task cancelled during request")
            return

        duration_ms = int((datetime.now() - started_at).total_seconds() * 1000)
        append_result(
            task_id,
            target_url,
            {
                "status": "failed",
                "http_status": 0,
                "final_url": target_url,
                "title": "",
                "content_type": "",
                "bytes": 0,
                "duration_ms": duration_ms,
                "error": str(exc),
                "artifacts": {},
            },
        )
        update_task_state(
            task_id,
            "failed",
            finished_at=datetime.now(),
            total_requests=1,
            success_requests=0,
            failed_requests=1,
            set_finished_at=True,
        )
        append_log(task_id, "error", f"request failed: {exc}")
    finally:
        with TASK_STOPS_LOCK:
            TASK_STOPS.pop(task_id, None)


# ==================== API 路由 ====================


@app.route("/api/tasks", methods=["GET"])
def list_tasks():
    """获取所有任务列表"""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    offset = (page - 1) * per_page
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM tasks ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (per_page, offset),
    )
    tasks = [normalize_task_row(dict(row)) for row in cursor.fetchall()]
    cursor.execute("SELECT COUNT(*) FROM tasks")
    total = cursor.fetchone()[0]
    conn.close()
    return jsonify(
        {
            "success": True,
            "data": tasks,
            "pagination": {"page": page, "per_page": per_page, "total": total},
        }
    )


@app.route("/api/tasks", methods=["POST"])
def create_task():
    """创建新任务"""
    data = request.json
    name = data.get("name", "Unnamed Task")
    url = data.get("url")
    config = json.dumps(data.get("config", {}))

    if not url:
        return jsonify({"success": False, "error": "URL is required"}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO tasks (name, url, config) VALUES (?, ?, ?)", (name, url, config)
    )
    task_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return jsonify({"success": True, "data": {"id": task_id}})


@app.route("/api/tasks/<int:task_id>", methods=["GET"])
def get_task(task_id):
    """获取任务详情"""
    task = get_task_row(task_id)
    if task:
        return jsonify({"success": True, "data": task})
    return jsonify({"success": False, "error": "Task not found"}), 404


@app.route("/api/tasks/<int:task_id>/start", methods=["POST"])
def start_task(task_id):
    """启动任务"""
    task = get_task_row(task_id)
    if not task:
        return jsonify({"success": False, "error": "Task not found"}), 404
    if task["status"] == "running":
        return jsonify({"success": False, "error": "Task is already running"}), 409

    started_at = datetime.now()
    update_task_state(
        task_id,
        "running",
        started_at=started_at,
        finished_at=None,
        total_requests=0,
        success_requests=0,
        failed_requests=0,
        set_started_at=True,
        set_finished_at=True,
    )
    append_log(task_id, "info", "task started")

    stop_event = threading.Event()
    with TASK_STOPS_LOCK:
        TASK_STOPS[task_id] = stop_event

    thread = threading.Thread(
        target=run_task, args=(task_id, task["url"], stop_event), daemon=True
    )
    thread.start()

    return jsonify(
        {
            "success": True,
            "message": "Task started",
            "data": {"message": "Task started"},
        }
    )


@app.route("/api/tasks/<int:task_id>/stop", methods=["POST"])
def stop_task(task_id):
    """停止任务"""
    task = get_task_row(task_id)
    if not task:
        return jsonify({"success": False, "error": "Task not found"}), 404

    with TASK_STOPS_LOCK:
        stop_event = TASK_STOPS.get(task_id)
        if stop_event is not None:
            stop_event.set()

    update_task_state(
        task_id, "stopped", finished_at=datetime.now(), set_finished_at=True
    )
    append_log(task_id, "warning", "task stop requested")
    return jsonify(
        {
            "success": True,
            "message": "Task stopped",
            "data": {"message": "Task stopped"},
        }
    )


def _delete_task(task_id):
    """删除任务"""
    with TASK_STOPS_LOCK:
        stop_event = TASK_STOPS.pop(task_id, None)
        if stop_event is not None:
            stop_event.set()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    cursor.execute("DELETE FROM results WHERE task_id = ?", (task_id,))
    cursor.execute("DELETE FROM logs WHERE task_id = ?", (task_id,))
    conn.commit()
    conn.close()

    return jsonify(
        {
            "success": True,
            "message": "Task deleted",
            "data": {"message": "Task deleted"},
        }
    )


@app.route("/api/tasks/<int:task_id>/delete", methods=["POST"])
def delete_task_alias(task_id):
    return _delete_task(task_id)


@app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    return _delete_task(task_id)


@app.route("/api/tasks/<int:task_id>/results", methods=["GET"])
def get_task_results(task_id):
    """获取任务结果"""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    offset = (page - 1) * per_page

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM results WHERE task_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (task_id, per_page, offset),
    )
    results = [normalize_result_row(dict(row)) for row in cursor.fetchall()]

    cursor.execute("SELECT COUNT(*) FROM results WHERE task_id = ?", (task_id,))
    total = cursor.fetchone()[0]
    conn.close()

    return jsonify(
        {
            "success": True,
            "data": results,
            "pagination": {"page": page, "per_page": per_page, "total": total},
        }
    )


@app.route("/api/tasks/<int:task_id>/artifacts", methods=["GET"])
def get_task_artifacts(task_id):
    """获取任务工件"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM results WHERE task_id = ? ORDER BY created_at DESC", (task_id,)
    )
    results = [normalize_result_row(dict(row)) for row in cursor.fetchall()]
    conn.close()

    artifacts = {}
    for result in results:
        for name, artifact in result.get("artifacts", {}).items():
            artifacts.setdefault(name, artifact)

    return jsonify(
        {
            "success": True,
            "data": artifacts,
        }
    )


@app.route("/api/tasks/<int:task_id>/logs", methods=["GET"])
def get_task_logs(task_id):
    """获取任务日志"""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)
    offset = (page - 1) * per_page

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM logs WHERE task_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (task_id, per_page, offset),
    )
    logs = [dict(row) for row in cursor.fetchall()]
    cursor.execute("SELECT COUNT(*) FROM logs WHERE task_id = ?", (task_id,))
    total = cursor.fetchone()[0]
    conn.close()

    return jsonify(
        {
            "success": True,
            "data": logs,
            "pagination": {"page": page, "per_page": per_page, "total": total},
        }
    )


@app.route("/api/stats", methods=["GET"])
def get_stats():
    """获取统计信息"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM tasks")
    total_tasks = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'running'")
    running_tasks = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM results")
    total_results = cursor.fetchone()[0]

    conn.close()

    return jsonify(
        {
            "success": True,
            "data": {
                "total_tasks": total_tasks,
                "running_tasks": running_tasks,
                "total_results": total_results,
            },
        }
    )


@app.route("/api/graph/extract", methods=["POST"])
@app.route("/api/v1/graph/extract", methods=["POST"])
def extract_graph():
    payload = request.get_json(silent=True) or {}
    html = str(payload.get("html") or "").strip()
    url = str(payload.get("url") or "").strip()

    if not html and not url:
        return jsonify({"success": False, "error": "html or url is required"}), 400

    if not html:
        try:
            response = requests.get(
                url, timeout=15, headers={"User-Agent": "PySpider-WebUI/1.0"}
            )
            html = response.text
        except requests.RequestException as exc:
            return (
                jsonify(
                    {"success": False, "error": f"failed to fetch graph url: {exc}"}
                ),
                400,
            )

    return jsonify({"success": True, "data": build_graph_payload(html)})


# ==================== 页面路由 ====================


@app.route("/")
def index():
    """主页"""
    return render_template("index.html")


@app.route("/tasks")
def tasks_page():
    """任务管理页面"""
    return render_template("tasks.html")


@app.route("/tasks/<int:task_id>")
def task_detail_page(task_id):
    """任务详情页面"""
    return render_template("task_detail.html", task_id=task_id)


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
