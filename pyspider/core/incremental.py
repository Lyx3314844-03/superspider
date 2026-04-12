"""
增量爬取支持 - ETag / Last-Modified 检查
"""

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PageCacheEntry:
    """页面缓存条目"""

    url: str
    etag: Optional[str] = None
    last_modified: Optional[str] = None
    content_hash: Optional[str] = None
    last_crawled: float = 0.0
    status_code: int = 200
    content_changed: bool = True


class IncrementalCrawler:
    """增量爬取管理器"""

    def __init__(
        self,
        enabled: bool = True,
        min_change_interval: int = 3600,
        store_path: Optional[str] = None,
    ):
        self._enabled = enabled
        self._min_change_interval = min_change_interval
        self._cache: Dict[str, PageCacheEntry] = {}
        self._store_path = Path(store_path) if store_path else None
        if self._store_path and self._store_path.exists():
            self.load(self._store_path)

    def set_enabled(self, enabled: bool) -> None:
        """启用/禁用增量爬取"""
        self._enabled = enabled

    def should_skip(
        self, url: str, etag: Optional[str] = None, last_modified: Optional[str] = None
    ) -> bool:
        """
        检查是否应该跳过此 URL(内容未变更)
        返回 True 表示可以跳过, False 表示需要重新爬取
        """
        if not self._enabled:
            return False

        if url not in self._cache:
            return False

        entry = self._cache[url]
        now = time.time()

        # 检查最小变更间隔
        if now - entry.last_crawled < self._min_change_interval:
            return True

        # ETag 比较
        if etag and entry.etag and etag == entry.etag:
            logger.debug(f"ETag 匹配,跳过: {url}")
            entry.content_changed = False
            return True

        # Last-Modified 比较
        if (
            last_modified
            and entry.last_modified
            and last_modified == entry.last_modified
        ):
            logger.debug(f"Last-Modified 匹配,跳过: {url}")
            entry.content_changed = False
            return True

        return False

    def get_conditional_headers(self, url: str) -> Dict[str, str]:
        """获取条件请求头(If-None-Match / If-Modified-Since)"""
        headers = {}
        if url in self._cache:
            entry = self._cache[url]
            if entry.etag:
                headers["If-None-Match"] = entry.etag
            if entry.last_modified:
                headers["If-Modified-Since"] = entry.last_modified
        return headers

    def update_cache(
        self,
        url: str,
        etag: Optional[str] = None,
        last_modified: Optional[str] = None,
        content: bytes = b"",
        status_code: int = 200,
    ) -> bool:
        """
        更新缓存
        返回 True 表示内容已变更, False 表示未变更
        """
        content_hash = hashlib.md5(content).hexdigest() if content else None

        if url in self._cache:
            entry = self._cache[url]
            # 检查内容是否真的变更
            if entry.content_hash == content_hash:
                entry.last_crawled = time.time()
                entry.content_changed = False
                return False

        # 创建或更新缓存
        self._cache[url] = PageCacheEntry(
            url=url,
            etag=etag or self._cache.get(url, PageCacheEntry(url=url)).etag,
            last_modified=last_modified
            or self._cache.get(url, PageCacheEntry(url=url)).last_modified,
            content_hash=content_hash,
            last_crawled=time.time(),
            status_code=status_code,
            content_changed=True,
        )
        return True

    def get_cache_stats(self) -> Dict:
        """获取缓存统计"""
        total = len(self._cache)
        changed = sum(1 for e in self._cache.values() if e.content_changed)
        unchanged = total - changed
        return {
            "total": total,
            "changed": changed,
            "unchanged": unchanged,
            "hit_rate": unchanged / total if total > 0 else 0.0,
        }

    def clear_cache(self) -> None:
        """清除所有缓存"""
        self._cache.clear()

    def remove_url(self, url: str) -> None:
        """移除指定 URL 的缓存"""
        self._cache.pop(url, None)

    def delta_token(self, url: str) -> Optional[str]:
        """返回当前缓存条目的稳定增量 token。"""
        entry = self._cache.get(url)
        if not entry:
            return None
        payload = {
            "url": entry.url,
            "etag": entry.etag,
            "last_modified": entry.last_modified,
            "content_hash": entry.content_hash,
            "status_code": entry.status_code,
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()

    def snapshot(self) -> Dict[str, Any]:
        return {
            "enabled": self._enabled,
            "min_change_interval": self._min_change_interval,
            "entries": {
                url: {
                    "url": entry.url,
                    "etag": entry.etag,
                    "last_modified": entry.last_modified,
                    "content_hash": entry.content_hash,
                    "last_crawled": entry.last_crawled,
                    "status_code": entry.status_code,
                    "content_changed": entry.content_changed,
                }
                for url, entry in self._cache.items()
            },
        }

    def restore(self, payload: Dict[str, Any]) -> None:
        self._enabled = bool(payload.get("enabled", self._enabled))
        self._min_change_interval = int(
            payload.get("min_change_interval", self._min_change_interval)
        )
        entries = payload.get("entries", {})
        restored: Dict[str, PageCacheEntry] = {}
        for url, raw in entries.items():
            restored[url] = PageCacheEntry(
                url=str(raw.get("url", url)),
                etag=raw.get("etag"),
                last_modified=raw.get("last_modified"),
                content_hash=raw.get("content_hash"),
                last_crawled=float(raw.get("last_crawled", 0.0)),
                status_code=int(raw.get("status_code", 200)),
                content_changed=bool(raw.get("content_changed", True)),
            )
        self._cache = restored

    def save(self, path: Optional[str | Path] = None) -> Optional[Path]:
        target = Path(path) if path else self._store_path
        if target is None:
            return None
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(self.snapshot(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._store_path = target
        return target

    def load(self, path: str | Path) -> None:
        target = Path(path)
        if not target.exists():
            return
        payload = json.loads(target.read_text(encoding="utf-8"))
        self.restore(payload)
        self._store_path = target
