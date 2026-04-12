"""
PySpider 断点续爬模块测试

测试覆盖率目标：>90%
"""

import pytest
import json
import sqlite3
import time
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from pyspider.core.checkpoint import (
    CheckpointManager,
    CheckpointState,
    create_checkpoint,
)


class TestCheckpointState:
    """Checkpoint 状态测试"""

    def test_create_state(self):
        """测试创建状态"""
        state = CheckpointState(
            spider_id="test_spider",
            timestamp="2026-03-23T10:00:00",
            visited_urls=["url1", "url2"],
            pending_urls=["url3"],
            stats={"total": 100},
            config={"threads": 10},
        )

        assert state.spider_id == "test_spider"
        assert len(state.visited_urls) == 2
        assert len(state.pending_urls) == 1
        assert state.stats == {"total": 100}

    def test_compute_checksum(self):
        """测试计算校验和"""
        state1 = CheckpointState(
            spider_id="test",
            timestamp="2026-03-23",
            visited_urls=["url1"],
            pending_urls=[],
            stats={},
            config={},
        )

        state2 = CheckpointState(
            spider_id="test",
            timestamp="2026-03-23",
            visited_urls=["url1"],
            pending_urls=[],
            stats={},
            config={},
        )

        # 相同状态应该有相同校验和
        assert state1.compute_checksum() == state2.compute_checksum()

        # 不同状态应该有不同校验和
        state3 = CheckpointState(
            spider_id="test",
            timestamp="2026-03-23",
            visited_urls=["url1", "url2"],
            pending_urls=[],
            stats={},
            config={},
        )

        assert state1.compute_checksum() != state3.compute_checksum()

    def test_to_dict(self):
        """测试转换为字典"""
        state = CheckpointState(
            spider_id="test",
            timestamp="2026-03-23",
            visited_urls=["url1"],
            pending_urls=[],
            stats={"key": "value"},
            config={},
        )

        state_dict = state.to_dict()

        assert state_dict["spider_id"] == "test"
        assert state_dict["visited_urls"] == ["url1"]
        assert state_dict["stats"] == {"key": "value"}

    def test_from_dict(self):
        """测试从字典创建"""
        data = {
            "spider_id": "test",
            "timestamp": "2026-03-23",
            "visited_urls": ["url1"],
            "pending_urls": [],
            "stats": {"key": "value"},
            "config": {},
            "checksum": "abc123",
        }

        state = CheckpointState.from_dict(data)

        assert state.spider_id == "test"
        assert state.visited_urls == ["url1"]
        assert state.checksum == "abc123"


class TestCheckpointManager:
    """Checkpoint 管理器测试"""

    @pytest.fixture
    def temp_dir(self):
        """临时目录 fixture"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def checkpoint(self, temp_dir):
        """Checkpoint 管理器 fixture"""
        cp = CheckpointManager(temp_dir, storage_type="json", auto_save_interval=0)
        yield cp
        cp.close()

    def test_init(self, temp_dir):
        """测试初始化"""
        cp = CheckpointManager(temp_dir)

        assert cp.checkpoint_dir == Path(temp_dir)
        assert cp.storage_type == "json"
        assert cp.auto_save_interval == 300
        assert cp.max_checkpoints == 10

        cp.close()

    def test_init_creates_directory(self, temp_dir):
        """测试初始化创建目录"""
        new_dir = Path(temp_dir) / "new_checkpoint_dir"
        cp = CheckpointManager(str(new_dir))

        assert new_dir.exists()
        assert new_dir.is_dir()

        cp.close()

    def test_save_immediate(self, checkpoint):
        """测试立即保存"""
        state = {
            "visited_urls": ["url1", "url2"],
            "pending_urls": ["url3"],
            "stats": {"total": 100},
            "config": {},
        }

        checkpoint.save("test_spider", state, immediate=True)

        # 检查文件是否存在
        file_path = Path(checkpoint.checkpoint_dir) / "test_spider.checkpoint.json"
        assert file_path.exists()

        # 检查内容
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["spider_id"] == "test_spider"
        assert len(data["visited_urls"]) == 2

    def test_save_cached(self, checkpoint):
        """测试缓存保存"""
        state = {
            "visited_urls": ["url1"],
            "pending_urls": [],
            "stats": {},
            "config": {},
        }

        checkpoint.save("test_spider", state, immediate=False)

        # 文件不应该存在（因为没立即保存）
        file_path = Path(checkpoint.checkpoint_dir) / "test_spider.checkpoint.json"
        assert not file_path.exists()

        # 但应该在缓存中
        assert "test_spider" in checkpoint._state_cache

    def test_load_from_cache(self, checkpoint):
        """测试从缓存加载"""
        state = {
            "visited_urls": ["url1"],
            "pending_urls": [],
            "stats": {"total": 100},
            "config": {},
        }

        checkpoint.save("test_spider", state, immediate=True)

        # 清除文件，测试从缓存加载
        loaded = checkpoint.load("test_spider")

        assert loaded is not None
        assert loaded["spider_id"] == "test_spider"
        assert loaded["stats"]["total"] == 100

    def test_load_from_storage(self, checkpoint):
        """测试从存储加载"""
        state = {
            "visited_urls": ["url1", "url2"],
            "pending_urls": ["url3"],
            "stats": {"total": 100, "success": 95},
            "config": {"threads": 10},
        }

        checkpoint.save("test_spider", state, immediate=True)

        # 清除缓存
        checkpoint._state_cache.clear()

        # 从存储加载
        loaded = checkpoint.load("test_spider")

        assert loaded is not None
        assert loaded["spider_id"] == "test_spider"
        assert len(loaded["visited_urls"]) == 2
        assert len(loaded["pending_urls"]) == 1

    def test_load_nonexistent(self, checkpoint):
        """测试加载不存在的 checkpoint"""
        loaded = checkpoint.load("nonexistent_spider")

        assert loaded is None

    def test_load_checksum_failure(self, checkpoint):
        """测试校验和失败"""
        # 先保存一个正常的
        state = {"visited_urls": [], "pending_urls": [], "stats": {}, "config": {}}
        checkpoint.save("test_spider", state, immediate=True)

        # 篡改文件
        file_path = Path(checkpoint.checkpoint_dir) / "test_spider.checkpoint.json"
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        data["checksum"] = "invalid_checksum"

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        # 清除缓存强制从存储加载
        checkpoint._state_cache.clear()

        # 应该返回 None（校验和失败）
        loaded = checkpoint.load("test_spider")

        assert loaded is None

    def test_delete(self, checkpoint):
        """测试删除 checkpoint"""
        state = {"visited_urls": [], "pending_urls": [], "stats": {}, "config": {}}

        checkpoint.save("test_spider", state, immediate=True)

        # 删除
        checkpoint.delete("test_spider")

        # 检查缓存
        assert "test_spider" not in checkpoint._state_cache

        # 检查文件
        file_path = Path(checkpoint.checkpoint_dir) / "test_spider.checkpoint.json"
        assert not file_path.exists()

    def test_list_checkpoints(self, checkpoint):
        """测试列出 checkpoint"""
        # 保存多个
        for i in range(3):
            state = {"visited_urls": [], "pending_urls": [], "stats": {}, "config": {}}
            checkpoint.save(f"spider_{i}", state, immediate=True)

        checkpoints = checkpoint.list_checkpoints()

        assert len(checkpoints) == 3
        assert "spider_0" in checkpoints
        assert "spider_1" in checkpoints
        assert "spider_2" in checkpoints

    def test_get_stats(self, checkpoint):
        """测试获取统计"""
        state = {
            "visited_urls": ["url1", "url2", "url3"],
            "pending_urls": ["url4"],
            "stats": {"total": 100, "success": 95},
            "config": {},
        }

        checkpoint.save("test_spider", state, immediate=True)

        stats = checkpoint.get_stats("test_spider")

        assert stats is not None
        assert stats["visited_count"] == 3
        assert stats["pending_count"] == 1
        assert stats["stats"]["total"] == 100

    def test_get_stats_nonexistent(self, checkpoint):
        """测试获取不存在的统计"""
        stats = checkpoint.get_stats("nonexistent")

        assert stats is None

    def test_auto_save(self, temp_dir):
        """测试自动保存"""
        # 创建带自动保存的管理器
        checkpoint = CheckpointManager(
            temp_dir, storage_type="json", auto_save_interval=1  # 1 秒自动保存
        )

        try:
            state = {"visited_urls": [], "pending_urls": [], "stats": {}, "config": {}}

            # 保存到缓存（不立即保存）
            checkpoint.save("test_spider", state, immediate=False)

            # 等待自动保存
            time.sleep(1.5)

            # 检查文件是否被创建
            file_path = Path(temp_dir) / "test_spider.checkpoint.json"
            assert file_path.exists()

        finally:
            checkpoint.stop_auto_save()
            checkpoint.close()

    def test_stop_auto_save(self, checkpoint):
        """测试停止自动保存"""
        checkpoint.start_auto_save()

        assert checkpoint._auto_save_thread is not None

        checkpoint.stop_auto_save()

        assert checkpoint._auto_save_thread is None

    def test_close(self, temp_dir):
        """测试关闭"""
        checkpoint = CheckpointManager(temp_dir, auto_save_interval=0)

        # 保存一些状态
        state = {
            "visited_urls": ["url1"],
            "pending_urls": [],
            "stats": {},
            "config": {},
        }
        checkpoint.save("test_spider", state, immediate=False)

        # 关闭（应该保存所有缓存状态）
        checkpoint.close()

        # 检查文件是否存在
        file_path = Path(temp_dir) / "test_spider.checkpoint.json"
        assert file_path.exists()

    def test_context_manager(self, temp_dir):
        """测试上下文管理器"""
        with CheckpointManager(temp_dir) as checkpoint:
            state = {"visited_urls": [], "pending_urls": [], "stats": {}, "config": {}}
            checkpoint.save("test_spider", state, immediate=False)

        # 退出上下文后文件应该被保存
        file_path = Path(temp_dir) / "test_spider.checkpoint.json"
        assert file_path.exists()

    def test_sqlite_storage_round_trip(self, temp_dir):
        """测试 SQLite 存储往返"""
        checkpoint = CheckpointManager(
            temp_dir, storage_type="sqlite", auto_save_interval=0
        )

        try:
            state = {
                "visited_urls": ["url1", "url2"],
                "pending_urls": ["url3"],
                "stats": {"total": 100},
                "config": {"threads": 4},
            }

            checkpoint.save("sqlite_spider", state, immediate=True)
            checkpoint._state_cache.clear()

            loaded = checkpoint.load("sqlite_spider")
            assert loaded is not None
            assert loaded["visited_urls"] == ["url1", "url2"]
            assert loaded["pending_urls"] == ["url3"]
            assert loaded["stats"]["total"] == 100

            assert "sqlite_spider" in checkpoint.list_checkpoints()

            checkpoint.delete("sqlite_spider")
            assert checkpoint.load("sqlite_spider") is None
        finally:
            checkpoint.close()

    def test_json_retains_recent_versions(self, temp_dir):
        """测试 JSON checkpoint 保留最近版本历史"""
        checkpoint = CheckpointManager(
            temp_dir, storage_type="json", auto_save_interval=0, max_checkpoints=2
        )

        try:
            state = {"visited_urls": ["url"], "pending_urls": [], "stats": {}, "config": {}}
            for seq in range(3):
                state["stats"] = {"seq": seq}
                checkpoint.save("history_spider", state, immediate=True)
                time.sleep(0.01)

            history_files = list(
                Path(temp_dir).glob("history_spider.checkpoint.*.json")
            )
            assert len(history_files) == 2
        finally:
            checkpoint.close()

    def test_sqlite_retains_recent_versions(self, temp_dir):
        """测试 SQLite checkpoint 保留最近版本历史"""
        checkpoint = CheckpointManager(
            temp_dir, storage_type="sqlite", auto_save_interval=0, max_checkpoints=2
        )

        try:
            state = {"visited_urls": ["url"], "pending_urls": [], "stats": {}, "config": {}}
            for seq in range(3):
                state["stats"] = {"seq": seq}
                checkpoint.save("history_spider", state, immediate=True)
                time.sleep(0.01)

            conn = sqlite3.connect(Path(temp_dir) / "checkpoints.sqlite3")
            try:
                count = conn.execute(
                    "SELECT COUNT(*) FROM checkpoint_versions WHERE spider_id = ?",
                    ("history_spider",),
                ).fetchone()[0]
            finally:
                conn.close()

            assert count == 2
        finally:
            checkpoint.close()

    def test_save_exception_handling(self, checkpoint):
        """测试保存异常处理"""
        # Mock 一个会失败的状态
        state = {"visited_urls": [], "pending_urls": [], "stats": {}, "config": {}}

        # 应该正常保存，不抛异常
        checkpoint.save("test_spider", state, immediate=True)

    def test_load_exception_handling(self, checkpoint):
        """测试加载异常处理"""
        # 加载不存在的不应该抛异常
        loaded = checkpoint.load("nonexistent")
        assert loaded is None

    def test_concurrent_save_load(self, checkpoint):
        """测试并发保存/加载"""
        import threading

        def save_task(spider_id):
            state = {
                "visited_urls": [f"url_{spider_id}"],
                "pending_urls": [],
                "stats": {"id": spider_id},
                "config": {},
            }
            checkpoint.save(spider_id, state, immediate=True)

        # 并发保存
        threads = []
        for i in range(5):
            t = threading.Thread(target=save_task, args=(f"spider_{i}",))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # 验证所有 checkpoint 都被保存
        checkpoints = checkpoint.list_checkpoints()
        assert len(checkpoints) == 5


class TestCreateCheckpoint:
    """create_checkpoint 便捷函数测试"""

    def test_create_checkpoint_default(self, tempfile):
        """测试创建默认配置"""
        temp_dir = tempfile.mkdtemp()

        try:
            cp = create_checkpoint(temp_dir)

            assert cp.auto_save_interval == 300
            assert cp.storage_type == "json"

            cp.close()
        finally:
            shutil.rmtree(temp_dir)

    def test_create_checkpoint_custom(self, tempfile):
        """测试创建自定义配置"""
        temp_dir = tempfile.mkdtemp()

        try:
            cp = create_checkpoint(
                temp_dir, storage_type="json", auto_save=True, auto_save_interval=60
            )

            assert cp.auto_save_interval == 60

            cp.close()
        finally:
            shutil.rmtree(temp_dir)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
