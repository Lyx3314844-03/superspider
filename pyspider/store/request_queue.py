"""
RequestQueue - 请求队列

吸收 Crawlee RequestQueue 设计
支持优先级、去重、持久化

@author: Lan
@version: 2.0.0
@date: 2026-03-20
"""

import hashlib
import json
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Request:
    """
    请求对象

    类似 Crawlee 的 Request
    """

    url: str
    method: str = "GET"
    headers: Dict[str, str] = field(default_factory=dict)
    body: Optional[bytes] = None
    priority: int = 0
    meta: Dict[str, Any] = field(default_factory=dict)
    fingerprint: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.fingerprint:
            self.fingerprint = self._generate_fingerprint()

    def _generate_fingerprint(self) -> str:
        """生成请求指纹"""
        content = f"{self.method}:{self.url}"
        return hashlib.md5(content.encode()).hexdigest()

    def to_dict(self) -> Dict:
        """转为字典"""
        return {
            "url": self.url,
            "method": self.method,
            "headers": self.headers,
            "body": self.body.decode() if self.body else None,
            "priority": self.priority,
            "meta": self.meta,
            "fingerprint": self.fingerprint,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Request":
        """从字典创建"""
        return cls(
            url=data["url"],
            method=data.get("method", "GET"),
            headers=data.get("headers", {}),
            body=data.get("body", b""),
            priority=data.get("priority", 0),
            meta=data.get("meta", {}),
            fingerprint=data.get("fingerprint"),
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if "created_at" in data
                else datetime.now()
            ),
        )


class RequestQueue:
    """
    请求队列

    类似 Crawlee 的 RequestQueue，支持优先级、去重、持久化
    """

    def __init__(
        self,
        name: str = "default",
        persist: bool = False,
        persist_path: Optional[str] = None,
    ):
        """
        初始化请求队列

        Args:
            name: 队列名称
            persist: 是否持久化
            persist_path: 持久化路径
        """
        self.name = name
        self.persist = persist
        self.persist_path = Path(persist_path) if persist_path else None
        self.requests: List[Request] = []
        self.seen: set = set()

        # 如果启用持久化且文件存在，加载数据
        if persist and self.persist_path and self.persist_path.exists():
            self._load()

    def add_request(self, url: str, **kwargs) -> bool:
        """
        添加请求

        Args:
            url: URL
            **kwargs: 其他参数

        Returns:
            是否添加成功（去重）
        """
        request = Request(url=url, **kwargs)

        if request.fingerprint in self.seen:
            return False  # 已存在

        self.requests.append(request)
        self.seen.add(request.fingerprint)

        # 按优先级排序
        self.requests.sort(key=lambda r: r.priority, reverse=True)

        # 持久化
        if self.persist:
            self._save()

        return True

    def add_requests(self, urls: List[str], **kwargs) -> int:
        """
        批量添加请求

        Args:
            urls: URL 列表
            **kwargs: 其他参数

        Returns:
            添加的数量
        """
        count = 0
        for url in urls:
            if self.add_request(url, **kwargs):
                count += 1
        return count

    def get_next_request(self) -> Optional[Request]:
        """
        获取下一个请求

        Returns:
            请求
        """
        if not self.requests:
            return None

        request = self.requests.pop(0)

        # 持久化
        if self.persist:
            self._save()

        return request

    def peek_next_request(self) -> Optional[Request]:
        """
        查看下一个请求（不移除）

        Returns:
            请求
        """
        if not self.requests:
            return None
        return self.requests[0]

    def mark_request_as_handled(self, request: Request) -> None:
        """
        标记请求已处理

        Args:
            request: 请求
        """
        # 可以在这里添加处理逻辑
        pass

    def add_request_back(self, request: Request) -> None:
        """
        将请求放回队列

        Args:
            request: 请求
        """
        self.requests.insert(0, request)
        self.requests.sort(key=lambda r: r.priority, reverse=True)

        if self.persist:
            self._save()

    def is_empty(self) -> bool:
        """
        是否为空

        Returns:
            是否为空
        """
        return len(self.requests) == 0

    def size(self) -> int:
        """
        队列大小

        Returns:
            大小
        """
        return len(self.requests)

    def pending_count(self) -> int:
        """
        待处理数量

        Returns:
            数量
        """
        return len(self.requests)

    def handled_count(self) -> int:
        """
        已处理数量

        Returns:
            数量
        """
        return len(self.seen) - len(self.requests)

    def clear(self) -> None:
        """清空队列"""
        self.requests.clear()
        self.seen.clear()

        if self.persist:
            self._save()

    def _save(self) -> None:
        """持久化保存"""
        if not self.persist_path:
            return

        data = {
            "name": self.name,
            "requests": [r.to_dict() for r in self.requests],
            "seen": list(self.seen),
        }

        with open(self.persist_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _load(self) -> None:
        """加载持久化数据"""
        if not self.persist_path or not self.persist_path.exists():
            return

        with open(self.persist_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.requests = [Request.from_dict(r) for r in data.get("requests", [])]
        self.seen = set(data.get("seen", []))

    def get_info(self) -> Dict:
        """
        获取队列信息

        Returns:
            信息字典
        """
        return {
            "name": self.name,
            "pending_count": self.pending_count(),
            "handled_count": self.handled_count(),
            "is_empty": self.is_empty(),
            "persist": self.persist,
        }

    def __len__(self) -> int:
        return self.size()

    def __repr__(self):
        return f"RequestQueue(name='{self.name}', pending={self.pending_count()})"


# 便捷函数
def create_request_queue(name: str = "default", persist: bool = False) -> RequestQueue:
    """创建请求队列"""
    return RequestQueue(name, persist)


def requests_from_urls(urls: List[str], **kwargs) -> List[Request]:
    """从 URL 列表创建请求"""
    return [Request(url=url, **kwargs) for url in urls]
