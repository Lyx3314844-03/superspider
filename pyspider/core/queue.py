"""
持久化队列模块
支持 SQLite 存储，重启后恢复
"""

import sqlite3
import pickle
import threading
import time
from typing import Optional, Any, List
from dataclasses import dataclass


@dataclass
class QueueItem:
    """队列项"""

    url: str
    priority: int = 0
    depth: int = 0
    request_data: Any = None
    created_at: float = 0.0
    retry_count: int = 0

    def __post_init__(self):
        if self.created_at == 0.0:
            self.created_at = time.time()


class PersistentPriorityQueue:
    """持久化优先队列"""

    def __init__(
        self,
        db_path: str = "queue.db",
        max_size: int = 100000,
        table_name: str = "requests",
    ):
        self.db_path = db_path
        self.max_size = max_size
        self.table_name = table_name
        self._lock = threading.RLock()
        self._conn = None
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.execute("PRAGMA journal_mode=WAL")  # 提高并发性能
        return self._conn

    def _init_db(self):
        """初始化数据库"""
        conn = self._get_connection()
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                priority INTEGER DEFAULT 0,
                depth INTEGER DEFAULT 0,
                retry_count INTEGER DEFAULT 0,
                request_data BLOB,
                created_at REAL,
                updated_at REAL
            )
        """)
        conn.execute(
            f"CREATE INDEX IF NOT EXISTS idx_priority ON {self.table_name}(priority DESC, created_at ASC)"
        )
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_url ON {self.table_name}(url)")
        conn.commit()

    def put(
        self,
        url: str,
        priority: int = 0,
        depth: int = 0,
        request_data: Any = None,
        retry_count: int = 0,
    ) -> bool:
        """
        添加请求到队列

        Args:
            url: 请求 URL
            priority: 优先级（越高越优先）
            depth: 爬取深度
            request_data: 请求数据（可序列化对象）
            retry_count: 重试次数

        Returns:
            bool: 是否添加成功
        """
        with self._lock:
            if self.size() >= self.max_size:
                return False

            conn = self._get_connection()
            now = time.time()

            try:
                # 序列化请求数据
                if request_data is not None:
                    blob_data = pickle.dumps(request_data)
                else:
                    blob_data = None

                conn.execute(
                    f"""
                    INSERT OR IGNORE INTO {self.table_name} 
                    (url, priority, depth, retry_count, request_data, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (url, priority, depth, retry_count, blob_data, now, now),
                )
                conn.commit()
                return conn.total_changes > 0

            except sqlite3.IntegrityError:
                return False  # 已存在

    def get(self, timeout: float = None) -> Optional[QueueItem]:
        """
        获取最高优先级的请求

        Args:
            timeout: 超时时间（秒）

        Returns:
            QueueItem 或 None
        """
        start_time = time.time()

        while True:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.execute(f"""
                    SELECT url, priority, depth, request_data, retry_count, created_at
                    FROM {self.table_name}
                    ORDER BY priority DESC, created_at ASC
                    LIMIT 1
                    """)
                row = cursor.fetchone()

                if row:
                    url, priority, depth, blob_data, retry_count, created_at = row

                    # 删除已获取的记录
                    conn.execute(f"DELETE FROM {self.table_name} WHERE url = ?", (url,))
                    conn.commit()

                    # 反序列化请求数据
                    request_data = None
                    if blob_data:
                        request_data = pickle.loads(blob_data)

                    return QueueItem(
                        url=url,
                        priority=priority,
                        depth=depth,
                        request_data=request_data,
                        retry_count=retry_count,
                        created_at=created_at,
                    )

            # 超时检查
            if timeout and (time.time() - start_time) > timeout:
                return None

            # 等待后重试
            time.sleep(0.1)

    def get_batch(self, batch_size: int = 10) -> List[QueueItem]:
        """批量获取请求"""
        items = []

        with self._lock:
            conn = self._get_connection()
            cursor = conn.execute(
                f"""
                SELECT url, priority, depth, request_data, retry_count, created_at
                FROM {self.table_name}
                ORDER BY priority DESC, created_at ASC
                LIMIT ?
                """,
                (batch_size,),
            )

            for row in cursor.fetchall():
                url, priority, depth, blob_data, retry_count, created_at = row

                # 删除已获取的记录
                conn.execute(f"DELETE FROM {self.table_name} WHERE url = ?", (url,))

                # 反序列化
                request_data = None
                if blob_data:
                    request_data = pickle.loads(blob_data)

                items.append(
                    QueueItem(
                        url=url,
                        priority=priority,
                        depth=depth,
                        request_data=request_data,
                        retry_count=retry_count,
                        created_at=created_at,
                    )
                )

            conn.commit()

        return items

    def remove(self, url: str) -> bool:
        """移除指定 URL"""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.execute(
                f"DELETE FROM {self.table_name} WHERE url = ?", (url,)
            )
            conn.commit()
            return cursor.rowcount > 0

    def exists(self, url: str) -> bool:
        """检查 URL 是否存在"""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.execute(
                f"SELECT 1 FROM {self.table_name} WHERE url = ? LIMIT 1", (url,)
            )
            return cursor.fetchone() is not None

    def size(self) -> int:
        """获取队列大小"""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.execute(f"SELECT COUNT(*) FROM {self.table_name}")
            return cursor.fetchone()[0]

    def clear(self):
        """清空队列"""
        with self._lock:
            conn = self._get_connection()
            conn.execute(f"DELETE FROM {self.table_name}")
            conn.commit()

    def update_priority(self, url: str, new_priority: int) -> bool:
        """更新优先级"""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.execute(
                f"UPDATE {self.table_name} SET priority = ?, updated_at = ? WHERE url = ?",
                (new_priority, time.time(), url),
            )
            conn.commit()
            return cursor.rowcount > 0

    def increment_retry(self, url: str) -> int:
        """增加重试次数"""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.execute(
                f"UPDATE {self.table_name} SET retry_count = retry_count + 1, updated_at = ? WHERE url = ?",
                (time.time(), url),
            )
            conn.commit()

            # 获取新的重试次数
            cursor = conn.execute(
                f"SELECT retry_count FROM {self.table_name} WHERE url = ?", (url,)
            )
            row = cursor.fetchone()
            return row[0] if row else 0

    def get_stats(self) -> dict:
        """获取统计信息"""
        with self._lock:
            conn = self._get_connection()

            # 总数
            cursor = conn.execute(f"SELECT COUNT(*) FROM {self.table_name}")
            total = cursor.fetchone()[0]

            # 按优先级分组
            cursor = conn.execute(
                f"SELECT priority, COUNT(*) FROM {self.table_name} GROUP BY priority"
            )
            by_priority = dict(cursor.fetchall())

            # 平均深度
            cursor = conn.execute(f"SELECT AVG(depth) FROM {self.table_name}")
            avg_depth = cursor.fetchone()[0] or 0

            # 重试中的请求
            cursor = conn.execute(
                f"SELECT COUNT(*) FROM {self.table_name} WHERE retry_count > 0"
            )
            retrying = cursor.fetchone()[0]

            return {
                "total": total,
                "by_priority": by_priority,
                "avg_depth": avg_depth,
                "retrying": retrying,
                "max_size": self.max_size,
                "utilization": total / self.max_size if self.max_size > 0 else 0,
            }

    def close(self):
        """关闭数据库连接"""
        with self._lock:
            if self._conn:
                self._conn.close()
                self._conn = None

    def __del__(self):
        self.close()

    def __len__(self) -> int:
        return self.size()

    def __bool__(self) -> bool:
        return self.size() > 0


class RetryQueue:
    """重试队列"""

    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self._queue = PersistentPriorityQueue(
            db_path="retry_queue.db", table_name="retries"
        )
        self._lock = threading.RLock()

    def add_retry(self, item: QueueItem, reason: str = "") -> bool:
        """添加重试"""
        if item.retry_count >= self.max_retries:
            return False

        # 延迟重试（指数退避）
        priority = item.priority - 10  # 降低优先级

        return self._queue.put(
            url=item.url,
            priority=priority,
            depth=item.depth,
            request_data=item.request_data,
            retry_count=item.retry_count + 1,
        )

    def get(self) -> Optional[QueueItem]:
        """获取重试请求"""
        return self._queue.get(timeout=0.1)

    def size(self) -> int:
        """获取队列大小"""
        return self._queue.size()

    def clear(self):
        """清空队列"""
        self._queue.clear()


# 使用示例
if __name__ == "__main__":
    # 创建队列
    queue = PersistentPriorityQueue(db_path="test_queue.db", max_size=10000)

    # 添加请求
    queue.put("https://example.com/1", priority=10, depth=0)
    queue.put("https://example.com/2", priority=5, depth=1)
    queue.put("https://example.com/3", priority=15, depth=0)

    print(f"队列大小：{queue.size()}")
    print(f"统计信息：{queue.get_stats()}")

    # 获取请求（按优先级）
    while queue.size() > 0:
        item = queue.get()
        print(f"获取：{item.url} (优先级：{item.priority})")

    # 重试队列示例
    retry_queue = RetryQueue(max_retries=3)
    test_item = QueueItem(url="https://example.com/failed", priority=10)
    retry_queue.add_retry(test_item, reason="Timeout")

    print(f"重试队列大小：{retry_queue.size()}")
