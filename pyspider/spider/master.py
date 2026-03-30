# Omega-Spider Cluster - Python Master 调度器
# 实现基于 Flask 和 SQLite 的任务分发与结果收集中心

import sqlite3
import json
import os
from flask import Flask, request, jsonify, g
from datetime import datetime

app = Flask(__name__)
# 数据库路径：保存在 spider/tasks.db
DATABASE = os.path.join(os.path.dirname(__file__), 'tasks.db')
SCHEMA = os.path.join(os.path.dirname(__file__), 'schema.sql')

def get_db():
    """获取数据库连接"""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    """关闭数据库连接"""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    """初始化数据库"""
    if not os.path.exists(DATABASE):
        with app.app_context():
            db = get_db()
            with open(SCHEMA, mode='r', encoding='utf-8') as f:
                db.cursor().executescript(f.read())
            db.commit()
            print("数据库已成功初始化。")

@app.route('/task/add', methods=['POST'])
def add_task():
    """添加新任务（用于初始数据填充或外部动态添加）"""
    data = request.json
    url = data.get('url')
    priority = data.get('priority', 0)
    depth = data.get('depth', 0)
    
    if not url:
        return jsonify({"error": "URL 是必需的"}), 400
    
    db = get_db()
    try:
        db.execute(
            'INSERT INTO tasks (url, priority, depth, status) VALUES (?, ?, ?, ?)',
            (url, priority, depth, 'pending')
        )
        db.commit()
        return jsonify({"message": f"任务 {url} 已添加"}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "URL 已存在"}), 409

@app.route('/task/get', methods=['GET'])
def get_task():
    """分发一个待处理任务并标记为运行中"""
    db = get_db()
    # 按照优先级从高到低选取一个状态为 pending 的任务
    task = db.execute(
        'SELECT id, url, priority, depth FROM tasks WHERE status = "pending" ORDER BY priority DESC LIMIT 1'
    ).fetchone()
    
    if not task:
        return jsonify({"message": "目前没有待处理的任务"}), 404
    
    # 将任务状态更新为 running
    db.execute(
        'UPDATE tasks SET status = "running", updated_at = ? WHERE id = ?',
        (datetime.now(), task['id'])
    )
    db.commit()
    
    return jsonify({
        "id": task['id'],
        "url": task['url'],
        "priority": task['priority'],
        "depth": task['depth']
    })

@app.route('/task/submit', methods=['POST'])
def submit_task():
    """接收爬取结果并更新任务状态"""
    data = request.json
    url = data.get('url')
    status = data.get('status', 'completed')
    result_data = data.get('data')
    
    if not url:
        return jsonify({"error": "URL 是必需的"}), 400
    
    db = get_db()
    # 根据 URL 更新任务状态和结果
    db.execute(
        'UPDATE tasks SET status = ?, data = ?, updated_at = ? WHERE url = ?',
        (status, json.dumps(result_data) if result_data else None, datetime.now(), url)
    )
    db.commit()
    
    return jsonify({"message": "任务结果已成功提交"})

@app.route('/stats', methods=['GET'])
def get_stats():
    """返回爬虫集群的总体进度统计"""
    db = get_db()
    stats = db.execute(
        'SELECT status, COUNT(*) as count FROM tasks GROUP BY status'
    ).fetchall()
    
    result = {row['status']: row['count'] for row in stats}
    # 确保返回所有可能的状态（如果某状态计数为0）
    all_statuses = ['pending', 'running', 'completed', 'failed']
    for s in all_statuses:
        if s not in result:
            result[s] = 0
            
    return jsonify({
        "total_tasks": sum(result.values()),
        "status_counts": result,
        "timestamp": datetime.now().isoformat()
    })

if __name__ == '__main__':
    init_db()
    # 监听 0.0.0.0 以允许外部 Worker 访问
    app.run(host='0.0.0.0', port=5000, debug=True)
