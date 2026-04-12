"""
PySpider 持久化队列 - 基于 SQLite
支持爬虫重启后恢复队列
"""

import sqlite3
import json
import threading
from typing import Optional, Dict
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class Request:
    """爬取请求"""

    url: str
    method: str = "GET"
    headers: Optional[Dict] = None
    body: Optional[str] = None
    meta: Optional[Dict] = None
    priority: int = 0
    callback: Optional[str] = None
    created_at: str = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.headers is None:
            self.headers = {}
        if self.meta is None:
            self.meta = {}

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "Request":
        return cls(**data)


class PersistentPriorityQueue:
    """
    持久化优先级队列

    特性:
    - 基于 SQLite 持久化存储
    - 支持优先级排序
    - 线程安全
    - 支持去重

    使用示例:
        queue = PersistentPriorityQueue("my_spider")
        queue.push(Request(url="https://example.com", priority=10))
        request = queue.pop()
    """

    def __init__(self, name: str, db_path: Optional[str] = None):
        self.name = name
        self.db_path = db_path or f"{name}_queue.db"
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        """初始化数据库"""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 创建请求表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    method TEXT DEFAULT 'GET',
                    headers TEXT,
                    body TEXT,
                    meta TEXT,
                    priority INTEGER DEFAULT 0,
                    callback TEXT,
                    created_at TEXT,
                    UNIQUE(url)
                )
            """)

            # 创建索引
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_priority ON requests(priority DESC)"
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_url ON requests(url)")

            # 创建去重表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS visited (
                    url TEXT PRIMARY KEY,
                    visited_at TEXT
                )
            """)

            # 创建统计信息表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stats (
                    key TEXT PRIMARY KEY,
                    value INTEGER DEFAULT 0
                )
            """)

            # 初始化统计信息
            cursor.execute(
                "INSERT OR IGNORE INTO stats (key, value) VALUES ('total_pushed', 0)"
            )
            cursor.execute(
                "INSERT OR IGNORE INTO stats (key, value) VALUES ('total_popped', 0)"
            )

            conn.commit()
            conn.close()

    def push(self, request: Request) -> bool:
        """
        添加请求到队列

        Returns:
            bool: 是否添加成功（如果 URL 已存在则返回 False）
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            try:
                cursor.execute(
                    """
                    INSERT INTO requests 
                    (url, method, headers, body, meta, priority, callback, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        request.url,
                        request.method,
                        json.dumps(request.headers or {}),
                        request.body,
                        json.dumps(request.meta or {}),
                        request.priority,
                        request.callback,
                        request.created_at,
                    ),
                )

                # 更新统计
                cursor.execute(
                    "UPDATE stats SET value = value + 1 WHERE key = 'total_pushed'"
                )

                conn.commit()
                return True
            except sqlite3.IntegrityError:
                # URL 已存在
                return False
            finally:
                conn.close()

    def pop(self) -> Optional[Request]:
        """
        弹出优先级最高的请求

        Returns:
            Optional[Request]: 请求对象，如果队列为空则返回 None
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 获取优先级最高的请求
            cursor.execute("""
                SELECT url, method, headers, body, meta, priority, callback, created_at
                FROM requests
                ORDER BY priority DESC, id ASC
                LIMIT 1
            """)

            row = cursor.fetchone()
            if row is None:
                conn.close()
                return None

            request = Request(
                url=row[0],
                method=row[1],
                headers=json.loads(row[2]),
                body=row[3],
                meta=json.loads(row[4]),
                priority=row[5],
                callback=row[6],
                created_at=row[7],
            )

            # 删除已弹出的请求
            cursor.execute(
                "DELETE FROM requests WHERE id = (SELECT id FROM requests ORDER BY priority DESC, id ASC LIMIT 1)"
            )

            # 更新统计
            cursor.execute(
                "UPDATE stats SET value = value + 1 WHERE key = 'total_popped'"
            )

            conn.commit()
            conn.close()

            return request

    def mark_visited(self, url: str):
        """标记 URL 为已访问"""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT OR REPLACE INTO visited (url, visited_at)
                VALUES (?, ?)
            """,
                (url, datetime.now().isoformat()),
            )

            conn.commit()
            conn.close()

    def is_visited(self, url: str) -> bool:
        """检查 URL 是否已访问"""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT 1 FROM visited WHERE url = ? LIMIT 1", (url,))
            exists = cursor.fetchone() is not None

            conn.close()
            return exists

    def size(self) -> int:
        """获取队列大小"""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM requests")
            count = cursor.fetchone()[0]

            conn.close()
            return count

    def clear(self):
        """清空队列"""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("DELETE FROM requests")
            cursor.execute("DELETE FROM visited")

            conn.commit()
            conn.close()

    def get_stats(self) -> Dict:
        """获取统计信息"""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            stats = {}
            cursor.execute("SELECT key, value FROM stats")
            for row in cursor.fetchall():
                stats[row[0]] = row[1]

            cursor.execute("SELECT COUNT(*) FROM requests")
            stats["queue_size"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM visited")
            stats["visited_count"] = cursor.fetchone()[0]

            conn.close()
            return stats

    def __len__(self) -> int:
        return self.size()

    def __repr__(self) -> str:
        stats = self.get_stats()
        return f"PersistentPriorityQueue(size={stats.get('queue_size', 0)}, visited={stats.get('visited_count', 0)})"
