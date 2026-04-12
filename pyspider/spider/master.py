# Omega-Spider Cluster - Python Master 调度器 (专业版)
import sqlite3
import json
import os
from flask import Flask, request, jsonify, g
from datetime import datetime

app = Flask(__name__)
DATABASE = os.path.join(os.path.dirname(__file__), "tasks.db")


def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
        # 1. 开启 WAL 模式提高并发性能
        db.execute("PRAGMA journal_mode=WAL;")
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


def init_db():
    with app.app_context():
        db = get_db()
        # 任务表
        db.execute("""CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            priority INTEGER DEFAULT 0,
            depth INTEGER DEFAULT 0,
            data TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")
        # 2. Worker 心跳表
        db.execute("""CREATE TABLE IF NOT EXISTS workers (
            id TEXT PRIMARY KEY,
            lang TEXT,
            last_heartbeat DATETIME,
            stats TEXT
        )""")
        db.execute("CREATE INDEX IF NOT EXISTS idx_status ON tasks(status)")
        db.commit()


@app.route("/worker/heartbeat", methods=["POST"])
def heartbeat():
    """接收 Worker 心跳"""
    data = request.json
    worker_id = data.get("id")
    lang = data.get("lang")
    stats = data.get("stats", {})

    db = get_db()
    db.execute(
        """INSERT OR REPLACE INTO workers (id, lang, last_heartbeat, stats)
                  VALUES (?, ?, ?, ?)""",
        (worker_id, lang, datetime.now(), json.dumps(stats)),
    )
    db.commit()
    return jsonify({"status": "alive"})


@app.route("/task/add", methods=["POST"])
def add_task():
    data = request.json
    tasks = data if isinstance(data, list) else [data]
    db = get_db()
    added = 0
    for t in tasks:
        try:
            db.execute(
                "INSERT INTO tasks (url, priority, depth, status) VALUES (?, ?, ?, ?)",
                (t["url"], t.get("priority", 0), t.get("depth", 0), "pending"),
            )
            added += 1
        except Exception:
            pass
    db.commit()
    return jsonify({"added": added}), 201


@app.route("/task/get", methods=["GET"])
def get_task():
    db = get_db()
    task = db.execute(
        'SELECT id, url, priority, depth FROM tasks WHERE status = "pending" ORDER BY priority DESC LIMIT 1'
    ).fetchone()
    if not task:
        return jsonify({"message": "no tasks"}), 404
    db.execute(
        'UPDATE tasks SET status = "running", updated_at = ? WHERE id = ?',
        (datetime.now(), task["id"]),
    )
    db.commit()
    return jsonify(dict(task))


@app.route("/task/submit", methods=["POST"])
def submit_task():
    data = request.json
    db = get_db()
    db.execute(
        "UPDATE tasks SET status = ?, data = ?, updated_at = ? WHERE url = ?",
        (
            data.get("status", "completed"),
            json.dumps(data.get("data")),
            datetime.now(),
            data["url"],
        ),
    )
    db.commit()
    return jsonify({"status": "ok"})


@app.route("/stats", methods=["GET"])
def get_stats():
    db = get_db()
    counts = db.execute(
        "SELECT status, COUNT(*) as c FROM tasks GROUP BY status"
    ).fetchall()
    langs = db.execute(
        "SELECT lang, COUNT(*) as c FROM workers WHERE last_heartbeat > datetime('now', '-1 minute') GROUP BY lang"
    ).fetchall()
    return jsonify(
        {
            "status": {r["status"]: r["c"] for r in counts},
            "online_workers": {r["lang"]: r["c"] for r in langs},
            "total": sum(r["c"] for r in counts),
            "server_time": datetime.now().isoformat(),
        }
    )


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)
