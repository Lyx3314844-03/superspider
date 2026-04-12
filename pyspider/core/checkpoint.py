"""
PySpider 断点续爬模块

特性:
1. ✅ 自动保存爬虫状态
2. ✅ 支持手动/自动 checkpoint
3. ✅ 状态持久化 (JSON/SQLite)
4. ✅ 恢复爬虫状态
5. ✅ 增量爬取支持

使用示例:
    from pyspider.core.checkpoint import CheckpointManager

    # 创建 checkpoint 管理器
    checkpoint = CheckpointManager("artifacts/checkpoints")

    # 保存状态
    checkpoint.save("my_spider", {
        'visited_urls': [...],
        'pending_urls': [...],
        'stats': {...}
    })

    # 恢复状态
    state = checkpoint.load("my_spider")
    if state:
        spider.load_state(state)
"""

import json
import hashlib
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
import threading
import logging

logger = logging.getLogger(__name__)


@dataclass
class CheckpointState:
    """爬虫状态数据类"""

    spider_id: str
    timestamp: str
    visited_urls: List[str]
    pending_urls: List[str]
    stats: Dict[str, Any]
    config: Dict[str, Any]
    checksum: str = ""

    def compute_checksum(self) -> str:
        """计算状态校验和"""
        content = json.dumps(
            {
                "spider_id": self.spider_id,
                "visited_count": len(self.visited_urls),
                "pending_count": len(self.pending_urls),
                "stats": self.stats,
            },
            sort_keys=True,
        )
        return hashlib.md5(content.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CheckpointState":
        """从字典创建"""
        return cls(**data)


class CheckpointManager:
    """
        断点管理器

    支持方式:
        1. JSON 文件 - 简单易用
        2. SQLite - 单文件持久化
    """

    def __init__(
        self,
        checkpoint_dir: str = "artifacts/checkpoints",
        storage_type: str = "json",
        auto_save_interval: int = 300,  # 自动保存间隔 (秒)
        max_checkpoints: int = 10,  # 最大保留的 checkpoint 数量
    ):
        """
        初始化断点管理器

        Args:
            checkpoint_dir: checkpoint 存储目录
            storage_type: 存储类型 (json/sqlite)
            auto_save_interval: 自动保存间隔 (秒), 0 表示禁用
            max_checkpoints: 最大保留的 checkpoint 数量
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        self.storage_type = storage_type
        self.auto_save_interval = auto_save_interval
        self.max_checkpoints = max_checkpoints
        self._db_path = self.checkpoint_dir / "checkpoints.sqlite3"

        # 自动保存线程
        self._auto_save_thread: Optional[threading.Thread] = None
        self._stop_auto_save = threading.Event()

        # 状态缓存
        self._state_cache: Dict[str, CheckpointState] = {}

        if self.storage_type not in {"json", "sqlite"}:
            raise NotImplementedError(
                f"Unsupported checkpoint storage_type: {self.storage_type}"
            )

        # 初始化存储
        self._init_storage()

        # 启动自动保存
        if self.auto_save_interval > 0:
            self.start_auto_save()

        logger.info(f"CheckpointManager 初始化完成：{checkpoint_dir}")

    def _init_storage(self):
        """初始化存储"""
        if self.storage_type == "sqlite":
            self._init_sqlite()
        return None

    def _init_sqlite(self):
        """初始化 SQLite 存储"""
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS checkpoints (
                    spider_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    visited_urls TEXT NOT NULL,
                    pending_urls TEXT NOT NULL,
                    stats TEXT NOT NULL,
                    config TEXT NOT NULL,
                    checksum TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS checkpoint_versions (
                    version_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    spider_id TEXT NOT NULL,
                    version_timestamp TEXT NOT NULL,
                    visited_urls TEXT NOT NULL,
                    pending_urls TEXT NOT NULL,
                    stats TEXT NOT NULL,
                    config TEXT NOT NULL,
                    checksum TEXT NOT NULL
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def start_auto_save(self):
        """启动自动保存"""
        if self._auto_save_thread:
            return

        def auto_save_loop():
            while not self._stop_auto_save.is_set():
                # 等待指定间隔
                if self._stop_auto_save.wait(self.auto_save_interval):
                    break

                # 保存所有缓存的状态
                for spider_id, state in self._state_cache.items():
                    try:
                        self._save_state(spider_id, state)
                        logger.debug(f"自动保存 checkpoint: {spider_id}")
                    except Exception as e:
                        logger.error(f"自动保存失败 {spider_id}: {e}")

        self._auto_save_thread = threading.Thread(target=auto_save_loop, daemon=True)
        self._auto_save_thread.start()
        logger.info(f"自动保存已启动 (间隔：{self.auto_save_interval}秒)")

    def stop_auto_save(self):
        """停止自动保存"""
        if self._auto_save_thread:
            self._stop_auto_save.set()
            self._auto_save_thread.join(timeout=5)
            self._auto_save_thread = None
            logger.info("自动保存已停止")

    def save(self, spider_id: str, state: Dict[str, Any], immediate: bool = False):
        """
        保存爬虫状态

        Args:
            spider_id: 爬虫 ID
            state: 状态字典
            immediate: 是否立即保存 (否则保存到缓存)
        """
        try:
            # 创建 checkpoint 状态
            checkpoint_state = CheckpointState(
                spider_id=spider_id,
                timestamp=datetime.now().isoformat(),
                visited_urls=state.get("visited_urls", []),
                pending_urls=state.get("pending_urls", []),
                stats=state.get("stats", {}),
                config=state.get("config", {}),
            )
            checkpoint_state.checksum = checkpoint_state.compute_checksum()

            # 保存到缓存
            self._state_cache[spider_id] = checkpoint_state

            # 立即保存
            if immediate:
                self._save_state(spider_id, checkpoint_state)
                logger.info(f"Checkpoint 已保存：{spider_id}")

        except Exception as e:
            logger.error(f"保存 checkpoint 失败 {spider_id}: {e}")
            raise

    def _save_state(self, spider_id: str, state: CheckpointState):
        """内部保存方法"""
        if self.storage_type == "sqlite":
            self._save_sqlite(spider_id, state)
        else:
            self._save_json(spider_id, state)

    def _save_json(self, spider_id: str, state: CheckpointState):
        """JSON 文件保存"""
        file_path = self.checkpoint_dir / f"{spider_id}.checkpoint.json"

        # 保存到新文件
        temp_path = file_path.with_suffix(".json.tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(state.to_dict(), f, indent=2, ensure_ascii=False)

        # 原子替换
        temp_path.replace(file_path)

        self._write_json_version(spider_id, state)

        # 清理旧的 checkpoint
        self._cleanup_old_checkpoints(spider_id)

    def _save_sqlite(self, spider_id: str, state: CheckpointState):
        """SQLite 保存"""
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute(
                """
                INSERT INTO checkpoints (
                    spider_id, timestamp, visited_urls, pending_urls, stats, config, checksum
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(spider_id) DO UPDATE SET
                    timestamp=excluded.timestamp,
                    visited_urls=excluded.visited_urls,
                    pending_urls=excluded.pending_urls,
                    stats=excluded.stats,
                    config=excluded.config,
                    checksum=excluded.checksum
                """,
                (
                    spider_id,
                    state.timestamp,
                    json.dumps(state.visited_urls, ensure_ascii=False),
                    json.dumps(state.pending_urls, ensure_ascii=False),
                    json.dumps(state.stats, ensure_ascii=False),
                    json.dumps(state.config, ensure_ascii=False),
                    state.checksum,
                ),
            )
            conn.execute(
                """
                INSERT INTO checkpoint_versions (
                    spider_id, version_timestamp, visited_urls, pending_urls, stats, config, checksum
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    spider_id,
                    state.timestamp,
                    json.dumps(state.visited_urls, ensure_ascii=False),
                    json.dumps(state.pending_urls, ensure_ascii=False),
                    json.dumps(state.stats, ensure_ascii=False),
                    json.dumps(state.config, ensure_ascii=False),
                    state.checksum,
                ),
            )
            conn.commit()
        finally:
            conn.close()

        self._cleanup_old_checkpoints(spider_id)

    def load(self, spider_id: str) -> Optional[Dict[str, Any]]:
        """
        加载爬虫状态

        Args:
            spider_id: 爬虫 ID

        Returns:
            状态字典或 None
        """
        try:
            # 先从缓存加载
            if spider_id in self._state_cache:
                state = self._state_cache[spider_id]
                logger.info(f"从缓存加载 checkpoint: {spider_id}")
                return self._state_to_dict(state)

            # 从存储加载
            state = self._load_state(spider_id)
            if state:
                # 验证校验和
                if state.checksum != state.compute_checksum():
                    logger.warning(f"Checkpoint 校验和失败：{spider_id}")
                    return None

                logger.info(f"从存储加载 checkpoint: {spider_id}")
                return self._state_to_dict(state)

            return None

        except Exception as e:
            logger.error(f"加载 checkpoint 失败 {spider_id}: {e}")
            return None

    def _load_state(self, spider_id: str) -> Optional[CheckpointState]:
        """内部加载方法"""
        if self.storage_type == "sqlite":
            return self._load_sqlite(spider_id)
        return self._load_json(spider_id)

    def _load_json(self, spider_id: str) -> Optional[CheckpointState]:
        """JSON 文件加载"""
        file_path = self.checkpoint_dir / f"{spider_id}.checkpoint.json"

        if not file_path.exists():
            return None

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return CheckpointState.from_dict(data)

    def _load_sqlite(self, spider_id: str) -> Optional[CheckpointState]:
        """SQLite 加载"""
        conn = sqlite3.connect(self._db_path)
        try:
            row = conn.execute(
                """
                SELECT spider_id, timestamp, visited_urls, pending_urls, stats, config, checksum
                FROM checkpoints
                WHERE spider_id = ?
                """,
                (spider_id,),
            ).fetchone()
        finally:
            conn.close()

        if not row:
            return None

        return CheckpointState(
            spider_id=row[0],
            timestamp=row[1],
            visited_urls=json.loads(row[2]),
            pending_urls=json.loads(row[3]),
            stats=json.loads(row[4]),
            config=json.loads(row[5]),
            checksum=row[6],
        )

    def _state_to_dict(self, state: CheckpointState) -> Dict[str, Any]:
        """将状态转换为字典"""
        return {
            "spider_id": state.spider_id,
            "timestamp": state.timestamp,
            "visited_urls": state.visited_urls,
            "pending_urls": state.pending_urls,
            "stats": state.stats,
            "config": state.config,
            "checksum": state.checksum,
        }

    def delete(self, spider_id: str):
        """删除 checkpoint"""
        try:
            # 从缓存删除
            self._state_cache.pop(spider_id, None)

            # 从存储删除
            if self.storage_type == "sqlite":
                conn = sqlite3.connect(self._db_path)
                try:
                    conn.execute(
                        "DELETE FROM checkpoints WHERE spider_id = ?", (spider_id,)
                    )
                    conn.execute(
                        "DELETE FROM checkpoint_versions WHERE spider_id = ?",
                        (spider_id,),
                    )
                    conn.commit()
                finally:
                    conn.close()
            else:
                file_path = self.checkpoint_dir / f"{spider_id}.checkpoint.json"
                if file_path.exists():
                    file_path.unlink()
                for history_path in self.checkpoint_dir.glob(
                    f"{spider_id}.checkpoint.*.json"
                ):
                    history_path.unlink(missing_ok=True)

            logger.info(f"Checkpoint 已删除：{spider_id}")

        except Exception as e:
            logger.error(f"删除 checkpoint 失败 {spider_id}: {e}")

    def list_checkpoints(self) -> List[str]:
        """列出所有 checkpoint"""
        if self.storage_type == "sqlite":
            conn = sqlite3.connect(self._db_path)
            try:
                rows = conn.execute(
                    "SELECT spider_id FROM checkpoints ORDER BY spider_id"
                ).fetchall()
            finally:
                conn.close()
            return [row[0] for row in rows]

        return [
            f.stem.replace(".checkpoint", "")
            for f in self.checkpoint_dir.glob("*.checkpoint.json")
        ]

    def _cleanup_old_checkpoints(self, spider_id: str):
        """清理旧的 checkpoint"""
        if self.max_checkpoints <= 0:
            return

        if self.storage_type == "sqlite":
            conn = sqlite3.connect(self._db_path)
            try:
                rows = conn.execute(
                    """
                    SELECT version_id
                    FROM checkpoint_versions
                    WHERE spider_id = ?
                    ORDER BY version_timestamp DESC, version_id DESC
                    """,
                    (spider_id,),
                ).fetchall()
                stale_ids = [row[0] for row in rows[self.max_checkpoints :]]
                if stale_ids:
                    conn.executemany(
                        "DELETE FROM checkpoint_versions WHERE version_id = ?",
                        [(version_id,) for version_id in stale_ids],
                    )
                    conn.commit()
            finally:
                conn.close()
            return

        history_files = sorted(
            self.checkpoint_dir.glob(f"{spider_id}.checkpoint.*.json"), reverse=True
        )
        for path in history_files[self.max_checkpoints :]:
            path.unlink(missing_ok=True)

    def _write_json_version(self, spider_id: str, state: CheckpointState) -> None:
        if self.max_checkpoints <= 0:
            return

        version_timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S.%fZ")
        version_path = (
            self.checkpoint_dir / f"{spider_id}.checkpoint.{version_timestamp}.json"
        )
        with open(version_path, "w", encoding="utf-8") as f:
            json.dump(state.to_dict(), f, indent=2, ensure_ascii=False)

    def get_stats(self, spider_id: str) -> Optional[Dict[str, Any]]:
        """获取 checkpoint 统计信息"""
        state = self._state_cache.get(spider_id) or self._load_state(spider_id)

        if not state:
            return None

        return {
            "spider_id": state.spider_id,
            "timestamp": state.timestamp,
            "visited_count": len(state.visited_urls),
            "pending_count": len(state.pending_urls),
            "stats": state.stats,
            "checksum": state.checksum,
        }

    def close(self):
        """关闭管理器"""
        self.stop_auto_save()

        # 保存所有缓存状态
        for spider_id, state in list(self._state_cache.items()):
            try:
                self._save_state(spider_id, state)
            except Exception as e:
                logger.error(f"关闭时保存失败 {spider_id}: {e}")

        logger.info("CheckpointManager 已关闭")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# 便捷函数
def create_checkpoint(
    checkpoint_dir: str = "artifacts/checkpoints",
    storage_type: str = "json",
    auto_save: bool = True,
    auto_save_interval: int = 300,
) -> CheckpointManager:
    """
    创建 checkpoint 管理器

    Args:
        checkpoint_dir: checkpoint 目录
        storage_type: 存储类型
        auto_save: 是否自动保存
        auto_save_interval: 自动保存间隔

    Returns:
        CheckpointManager 实例
    """
    return CheckpointManager(
        checkpoint_dir=checkpoint_dir,
        storage_type=storage_type,
        auto_save_interval=auto_save_interval if auto_save else 0,
    )
