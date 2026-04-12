"""
Dataset - 结构化数据存储

吸收 Crawlee Dataset 设计
支持 JSON/CSV/XML 等格式导出

@author: Lan
@version: 2.0.0
@date: 2026-03-20
"""

import json
import csv
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional
from pathlib import Path


class Dataset:
    """
    数据集 - 结构化数据存储

    类似 Crawlee 的 Dataset，用于存储结构化爬取结果
    """

    def __init__(self, name: str = "default", id: Optional[str] = None):
        """
        初始化数据集

        Args:
            name: 数据集名称
            id: 数据集 ID
        """
        self.name = name
        self.id = id or f"dataset_{name}"
        self.items: List[Dict[str, Any]] = []

    def push(self, item: Dict[str, Any]) -> int:
        """
        添加数据项

        Args:
            item: 数据项

        Returns:
            添加后的总项数
        """
        self.items.append(item)
        return len(self.items)

    def push_many(self, items: List[Dict[str, Any]]) -> int:
        """
        批量添加数据项

        Args:
            items: 数据项列表

        Returns:
            添加后的总项数
        """
        self.items.extend(items)
        return len(self.items)

    def get(self, index: int, default: Any = None) -> Optional[Dict[str, Any]]:
        """
        获取指定索引的数据

        Args:
            index: 索引
            default: 默认值

        Returns:
            数据项
        """
        try:
            return self.items[index]
        except IndexError:
            return default

    def get_all(self) -> List[Dict[str, Any]]:
        """
        获取所有数据

        Returns:
            数据列表
        """
        return self.items.copy()

    def filter(self, condition) -> List[Dict[str, Any]]:
        """
        过滤数据

        Args:
            condition: 过滤函数

        Returns:
            过滤后的数据
        """
        return [item for item in self.items if condition(item)]

    def map(self, func):
        """
        映射数据

        Args:
            func: 映射函数

        Returns:
            映射后的数据
        """
        return [func(item) for item in self.items]

    def reduce(self, func, initial=None):
        """
        归约数据

        Args:
            func: 归约函数
            initial: 初始值

        Returns:
            归约结果
        """
        result = initial
        for item in self.items:
            if result is None:
                result = item
            else:
                result = func(result, item)
        return result

    def save(self, path: str, format: str = "json", **kwargs) -> None:
        """
        保存到文件

        Args:
            path: 文件路径
            format: 文件格式 (json/csv/xml)
            **kwargs: 其他参数
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        if format == "json":
            self._save_json(path, **kwargs)
        elif format == "csv":
            self._save_csv(path, **kwargs)
        elif format == "xml":
            self._save_xml(path, **kwargs)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _save_json(
        self, path: Path, indent: int = 2, ensure_ascii: bool = False
    ) -> None:
        """保存为 JSON"""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.items, f, indent=indent, ensure_ascii=ensure_ascii)

    def _save_csv(
        self, path: Path, delimiter: str = ",", encoding: str = "utf-8"
    ) -> None:
        """保存为 CSV"""
        if not self.items:
            return

        with open(path, "w", encoding=encoding, newline="") as f:
            writer = csv.DictWriter(
                f, fieldnames=self.items[0].keys(), delimiter=delimiter
            )
            writer.writeheader()
            writer.writerows(self.items)

    def _save_xml(
        self, path: Path, root_tag: str = "dataset", item_tag: str = "item"
    ) -> None:
        """保存为 XML"""
        root = ET.Element(root_tag)

        for item in self.items:
            item_elem = ET.SubElement(root, item_tag)
            for key, value in item.items():
                child = ET.SubElement(item_elem, str(key))
                child.text = str(value)

        tree = ET.ElementTree(root)
        tree.write(path, encoding="utf-8", xml_declaration=True)

    def load(self, path: str, format: str = "json") -> None:
        """
        从文件加载

        Args:
            path: 文件路径
            format: 文件格式
        """
        path = Path(path)

        if format == "json":
            self._load_json(path)
        elif format == "csv":
            self._load_csv(path)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _load_json(self, path: Path) -> None:
        """从 JSON 加载"""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                self.items = data
            else:
                self.items = [data]

    def _load_csv(self, path: Path) -> None:
        """从 CSV 加载"""
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            self.items = list(reader)

    def clear(self) -> None:
        """清空数据"""
        self.items.clear()

    @property
    def count(self) -> int:
        """数据项数量"""
        return len(self.items)

    @property
    def is_empty(self) -> bool:
        """是否为空"""
        return len(self.items) == 0

    def __len__(self) -> int:
        return self.count

    def __iter__(self):
        return iter(self.items)

    def __getitem__(self, index):
        return self.items[index]

    def __repr__(self):
        return f"Dataset(name='{self.name}', count={self.count})"

    @classmethod
    def from_list(cls, items: List[Dict[str, Any]], name: str = "default") -> "Dataset":
        """
        从列表创建数据集

        Args:
            items: 数据列表
            name: 数据集名称

        Returns:
            数据集实例
        """
        dataset = cls(name)
        dataset.items = items.copy()
        return dataset


# 便捷函数
def create_dataset(name: str = "default") -> Dataset:
    """创建数据集"""
    return Dataset(name)


def save_to_json(items: List[Dict], path: str, **kwargs) -> None:
    """保存为 JSON 的便捷函数"""
    dataset = Dataset.from_list(items)
    dataset.save(path, format="json", **kwargs)


def save_to_csv(items: List[Dict], path: str, **kwargs) -> None:
    """保存为 CSV 的便捷函数"""
    dataset = Dataset.from_list(items)
    dataset.save(path, format="csv", **kwargs)
