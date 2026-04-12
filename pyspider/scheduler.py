#!/usr/bin/env python3
"""
PySpider 任务调度模块 - 定时任务、循环爬取、优先级调度
"""

import time
import threading
import uuid
from typing import Dict, List, Optional, Callable
from datetime import datetime
from enum import Enum
from dataclasses import dataclass


class TaskType(Enum):
    """任务类型"""

    ONCE = "once"  # 单次任务
    INTERVAL = "interval"  # 间隔任务
    CRON = "cron"  # Cron 任务


class TaskStatus(Enum):
    """任务状态"""

    PENDING = "pending"  # 等待中
    RUNNING = "running"  # 运行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    STOPPED = "stopped"  # 已停止


@dataclass
class SpiderTask:
    """爬虫任务"""

    id: str
    name: str
    url: str
    engine: str
    task_type: TaskType
    interval: int = 0  # 间隔秒数
    cron_expr: str = ""  # Cron 表达式
    max_runs: int = 0  # 0 = 无限
    priority: int = 5  # 优先级 1-10
    enabled: bool = True
    run_count: int = 0
    last_run: Optional[datetime] = None
    status: TaskStatus = TaskStatus.PENDING


class Scheduler:
    """任务调度器"""

    def __init__(self):
        self.tasks: Dict[str, SpiderTask] = {}
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.callback: Optional[Callable] = None

    def add_task(self, task: SpiderTask) -> str:
        """添加任务"""
        if not task.id:
            task.id = str(uuid.uuid4())
        self.tasks[task.id] = task
        print(f"✅ 任务已添加: {task.name} (ID: {task.id})")
        return task.id

    def remove_task(self, task_id: str) -> bool:
        """删除任务"""
        if task_id in self.tasks:
            del self.tasks[task_id]
            print(f"✅ 任务已删除: {task_id}")
            return True
        return False

    def list_tasks(self) -> List[SpiderTask]:
        """列出所有任务"""
        return list(self.tasks.values())

    def enable_task(self, task_id: str) -> bool:
        """启用任务"""
        if task_id in self.tasks:
            self.tasks[task_id].enabled = True
            print(f"✅ 任务已启用: {task_id}")
            return True
        return False

    def disable_task(self, task_id: str) -> bool:
        """禁用任务"""
        if task_id in self.tasks:
            self.tasks[task_id].enabled = False
            print(f"✅ 任务已禁用: {task_id}")
            return True
        return False

    def start(self, callback: Callable[[SpiderTask], None] = None):
        """启动调度器"""
        self.callback = callback
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        print("✅ 调度器已启动")

    def stop(self):
        """停止调度器"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print("✅ 调度器已停止")

    def _run_loop(self):
        """调度循环"""
        while self.running:
            now = datetime.now()

            for task in self.tasks.values():
                if not task.enabled:
                    continue

                # 检查是否应该执行
                should_run = False

                if task.task_type == TaskType.ONCE:
                    if task.status == TaskStatus.PENDING:
                        should_run = True

                elif task.task_type == TaskType.INTERVAL:
                    if task.last_run is None:
                        should_run = True
                    elif (now - task.last_run).total_seconds() >= task.interval:
                        should_run = True

                if should_run and self.callback:
                    task.run_count += 1
                    task.last_run = now
                    task.status = TaskStatus.RUNNING

                    # 在新线程中执行
                    threading.Thread(
                        target=self._execute_task, args=(task,), daemon=True
                    ).start()

            time.sleep(1)  # 每秒检查一次

    def _execute_task(self, task: SpiderTask):
        """执行任务"""
        try:
            if self.callback:
                self.callback(task)
            task.status = TaskStatus.COMPLETED

            # 检查是否达到最大运行次数
            if task.max_runs > 0 and task.run_count >= task.max_runs:
                task.enabled = False
                print(f"⚠️ 任务 {task.name} 已达到最大运行次数")

        except Exception as e:
            task.status = TaskStatus.FAILED
            print(f"❌ 任务执行失败: {e}")


def show_scheduler_menu():
    """显示调度菜单"""
    print("\n📝 任务调度功能:")
    print("  scheduler add <name> <url> <interval> - 添加定时任务")
    print("  scheduler list                         - 列出所有任务")
    print("  scheduler enable <id>                  - 启用任务")
    print("  scheduler disable <id>                 - 禁用任务")
    print("  scheduler remove <id>                  - 删除任务")
    print("  scheduler start                        - 启动调度器")
    print("  scheduler stop                         - 停止调度器")
