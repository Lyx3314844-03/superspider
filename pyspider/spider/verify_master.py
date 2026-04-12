# Omega-Spider Cluster - 验证 Master API 功能
import requests
import time
import threading
import sys
import os

# 导入 master 应用进行本地测试（或假设它在 5000 端口运行）
from master import app, init_db, DATABASE

BASE_URL = "http://127.0.0.1:5000"


def run_server():
    """在后台线程中运行 Flask"""
    init_db()
    app.run(port=5000, debug=False, use_reloader=False)


def test_workflow():
    print("--- 开始 Master API 验证测试 ---")

    # 1. 检查初始状态
    print("测试 1: 获取统计信息...")
    resp = requests.get(f"{BASE_URL}/stats")
    print(f"Stats: {resp.json()}")
    assert resp.status_code == 200

    # 2. 添加测试任务
    print("\n测试 2: 添加爬取任务...")
    tasks = [
        {"url": "https://example.com/page1", "priority": 10},
        {"url": "https://example.com/page2", "priority": 5},
        {"url": "https://example.com/page3", "priority": 20},
    ]
    for task in tasks:
        resp = requests.post(f"{BASE_URL}/task/add", json=task)
        print(f"Add Task {task['url']}: {resp.status_code}")
        assert resp.status_code == 201

    # 3. 获取任务（应该返回优先级最高的 page3）
    print("\n测试 3: 获取待处理任务 (预期返回优先级最高的 page3)...")
    resp = requests.get(f"{BASE_URL}/task/get")
    data = resp.json()
    print(f"Got Task: {data}")
    assert resp.status_code == 200
    assert data["url"] == "https://example.com/page3"

    # 4. 提交任务结果
    print("\n测试 4: 提交任务结果...")
    submit_data = {
        "url": "https://example.com/page3",
        "status": "completed",
        "data": {"title": "Example Domain", "content": "This is a test content."},
    }
    resp = requests.post(f"{BASE_URL}/task/submit", json=submit_data)
    print(f"Submit Task: {resp.status_code}")
    assert resp.status_code == 200

    # 5. 再次验证状态
    print("\n测试 5: 验证更新后的统计信息...")
    resp = requests.get(f"{BASE_URL}/stats")
    stats = resp.json()
    print(f"Final Stats: {stats}")
    assert stats["status_counts"]["completed"] == 1
    assert stats["status_counts"]["running"] == 0
    assert stats["status_counts"]["pending"] == 2

    print("\n--- 所有测试均已通过！ ---")


if __name__ == "__main__":
    # 清理旧数据库以便测试
    if os.path.exists(DATABASE):
        os.remove(DATABASE)
        print(f"已删除旧数据库 {DATABASE}")

    # 启动服务器线程
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # 给服务器一点启动时间
    time.sleep(2)

    try:
        test_workflow()
    except Exception as e:
        print(f"测试失败: {e}")
        sys.exit(1)
    finally:
        print("测试完成。")
