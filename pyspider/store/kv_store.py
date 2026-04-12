"""
KeyValueStore - 键值存储

吸收 Crawlee KeyValueStore 设计
支持多种数据类型和格式

@author: Lan
@version: 2.0.0
@date: 2026-03-20
"""

import json
import pickle
from typing import Any, Dict, List, Optional
from pathlib import Path


class KeyValueStore:
    """
    键值存储

    类似 Crawlee 的 KeyValueStore，用于存储键值对数据
    支持字符串、数字、列表、字典、对象等类型
    """

    def __init__(self, name: str = "default", id: Optional[str] = None):
        """
        初始化键值存储

        Args:
            name: 存储名称
            id: 存储 ID
        """
        self.name = name
        self.id = id or f"kvs_{name}"
        self.data: Dict[str, Any] = {}

    def get(self, key: str, default: Any = None) -> Optional[Any]:
        """
        获取值

        Args:
            key: 键
            default: 默认值

        Returns:
            值
        """
        return self.data.get(key, default)

    def get_or_default(self, key: str, default: Any) -> Any:
        """
        获取值或默认值

        Args:
            key: 键
            default: 默认值

        Returns:
            值
        """
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """
        设置值

        Args:
            key: 键
            value: 值
        """
        self.data[key] = value

    def set_many(self, items: Dict[str, Any]) -> None:
        """
        批量设置值

        Args:
            items: 键值对字典
        """
        self.data.update(items)

    def delete(self, key: str) -> bool:
        """
        删除值

        Args:
            key: 键

        Returns:
            是否删除成功
        """
        if key in self.data:
            del self.data[key]
            return True
        return False

    def delete_many(self, keys: List[str]) -> int:
        """
        批量删除

        Args:
            keys: 键列表

        Returns:
            删除的数量
        """
        count = 0
        for key in keys:
            if self.delete(key):
                count += 1
        return count

    def has(self, key: str) -> bool:
        """
        检查键是否存在

        Args:
            key: 键

        Returns:
            是否存在
        """
        return key in self.data

    def keys(self) -> List[str]:
        """
        获取所有键

        Returns:
            键列表
        """
        return list(self.data.keys())

    def values(self) -> List[Any]:
        """
        获取所有值

        Returns:
            值列表
        """
        return list(self.data.values())

    def items(self) -> List[tuple]:
        """
        获取所有键值对

        Returns:
            键值对列表
        """
        return list(self.data.items())

    def get_json(self, key: str) -> Optional[Dict]:
        """
        获取 JSON 数据

        Args:
            key: 键

        Returns:
            JSON 数据
        """
        value = self.get(key)
        if isinstance(value, str):
            try:
                return json.loads(value)
            except Exception:
                return None
        return value

    def set_json(self, key: str, value: Dict) -> None:
        """
        设置 JSON 数据

        Args:
            key: 键
            value: JSON 数据
        """
        self.data[key] = json.dumps(value, ensure_ascii=False)

    def get_pickle(self, key: str) -> Optional[Any]:
        """
        获取 Pickle 数据

        Args:
            key: 键

        Returns:
            数据
        """
        value = self.get(key)
        if isinstance(value, bytes):
            try:
                return pickle.loads(value)
            except Exception:
                return None
        return None

    def set_pickle(self, key: str, value: Any) -> None:
        """
        设置 Pickle 数据

        Args:
            key: 键
            value: 数据
        """
        self.data[key] = pickle.dumps(value)

    def save(self, path: str, format: str = "json") -> None:
        """
        保存到文件

        Args:
            path: 文件路径
            format: 文件格式
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        if format == "json":
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        elif format == "pickle":
            with open(path, "wb") as f:
                pickle.dump(self.data, f)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def load(self, path: str, format: str = "json") -> None:
        """
        从文件加载

        Args:
            path: 文件路径
            format: 文件格式
        """
        path = Path(path)

        if format == "json":
            with open(path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        elif format == "pickle":
            with open(path, "rb") as f:
                self.data = pickle.load(f)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def clear(self) -> None:
        """清空所有数据"""
        self.data.clear()

    @property
    def count(self) -> int:
        """数据项数量"""
        return len(self.data)

    @property
    def is_empty(self) -> bool:
        """是否为空"""
        return len(self.data) == 0

    def __len__(self) -> int:
        return self.count

    def __getitem__(self, key: str) -> Any:
        return self.data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.data[key] = value

    def __delitem__(self, key: str) -> None:
        del self.data[key]

    def __contains__(self, key: str) -> bool:
        return key in self.data

    def __repr__(self):
        return f"KeyValueStore(name='{self.name}', count={self.count})"

    @classmethod
    def from_dict(cls, data: Dict[str, Any], name: str = "default") -> "KeyValueStore":
        """
        从字典创建

        Args:
            data: 字典数据
            name: 存储名称

        Returns:
            实例
        """
        kvs = cls(name)
        kvs.data = data.copy()
        return kvs


# 便捷函数
def create_kv_store(name: str = "default") -> KeyValueStore:
    """创建键值存储"""
    return KeyValueStore(name)


def save_to_json(data: Dict, path: str) -> None:
    """保存为 JSON 的便捷函数"""
    kvs = KeyValueStore.from_dict(data)
    kvs.save(path, format="json")
