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
from datetime import datetime

app = Flask(__name__)
CORS(app)

DATABASE = os.path.join(os.path.dirname(__file__), 'spider.db')

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
    cursor.execute('''
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
    ''')
    
    # 创建结果表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER,
            url TEXT,
            data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES tasks(id)
        )
    ''')
    
    # 创建日志表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER,
            level TEXT,
            message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES tasks(id)
        )
    ''')
    
    conn.commit()
    conn.close()

# ==================== API 路由 ====================

@app.route('/api/tasks', methods=['GET'])
def list_tasks():
    """获取所有任务列表"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tasks ORDER BY created_at DESC')
    tasks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify({'success': True, 'data': tasks})

@app.route('/api/tasks', methods=['POST'])
def create_task():
    """创建新任务"""
    data = request.json
    name = data.get('name', 'Unnamed Task')
    url = data.get('url')
    config = json.dumps(data.get('config', {}))
    
    if not url:
        return jsonify({'success': False, 'error': 'URL is required'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO tasks (name, url, config) VALUES (?, ?, ?)',
        (name, url, config)
    )
    task_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'data': {'id': task_id}})

@app.route('/api/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    """获取任务详情"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
    task = dict(cursor.fetchone()) if cursor.rowcount > 0 else None
    conn.close()
    
    if task:
        return jsonify({'success': True, 'data': task})
    return jsonify({'success': False, 'error': 'Task not found'}), 404

@app.route('/api/tasks/<int:task_id>/start', methods=['POST'])
def start_task(task_id):
    """启动任务"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE tasks SET status = 'running', started_at = ? WHERE id = ?",
        (datetime.now(), task_id)
    )
    conn.commit()
    conn.close()
    
    # TODO: 实际启动爬虫逻辑
    return jsonify({'success': True, 'message': 'Task started'})

@app.route('/api/tasks/<int:task_id>/stop', methods=['POST'])
def stop_task(task_id):
    """停止任务"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE tasks SET status = 'stopped', finished_at = ? WHERE id = ?",
        (datetime.now(), task_id)
    )
    conn.commit()
    conn.close()
    
    # TODO: 实际停止爬虫逻辑
    return jsonify({'success': True, 'message': 'Task stopped'})

@app.route('/api/tasks/<int:task_id>/delete', methods=['POST'])
def delete_task(task_id):
    """删除任务"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
    cursor.execute('DELETE FROM results WHERE task_id = ?', (task_id,))
    cursor.execute('DELETE FROM logs WHERE task_id = ?', (task_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Task deleted'})

@app.route('/api/tasks/<int:task_id>/results', methods=['GET'])
def get_task_results(task_id):
    """获取任务结果"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    offset = (page - 1) * per_page
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT * FROM results WHERE task_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?',
        (task_id, per_page, offset)
    )
    results = [dict(row) for row in cursor.fetchall()]
    
    cursor.execute('SELECT COUNT(*) FROM results WHERE task_id = ?', (task_id,))
    total = cursor.fetchone()[0]
    conn.close()
    
    return jsonify({
        'success': True,
        'data': results,
        'pagination': {'page': page, 'per_page': per_page, 'total': total}
    })

@app.route('/api/tasks/<int:task_id>/logs', methods=['GET'])
def get_task_logs(task_id):
    """获取任务日志"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    offset = (page - 1) * per_page
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT * FROM logs WHERE task_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?',
        (task_id, per_page, offset)
    )
    logs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify({'success': True, 'data': logs})

@app.route('/api/stats', methods=['GET'])
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
    
    return jsonify({
        'success': True,
        'data': {
            'total_tasks': total_tasks,
            'running_tasks': running_tasks,
            'total_results': total_results
        }
    })

# ==================== 页面路由 ====================

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

@app.route('/tasks')
def tasks_page():
    """任务管理页面"""
    return render_template('tasks.html')

@app.route('/tasks/<int:task_id>')
def task_detail_page(task_id):
    """任务详情页面"""
    return render_template('task_detail.html', task_id=task_id)

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
