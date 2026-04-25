"""
Canonical spider engine for pyspider.

This is now the single runtime implementation. Older
`spider_enhanced.py` callers should move here.
"""

from __future__ import annotations

import json
import hashlib
import itertools
import logging
import re
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set
from urllib.parse import urlparse

from .contracts import (
    AutoscaledFrontier,
    FileArtifactStore,
    FrontierConfig,
    ObservabilityCollector,
)
from .incremental import IncrementalCrawler
from .models import Page, Request
from .proxy_pool import Proxy, ProxyPool
from .robots import RobotsChecker
from pyspider.downloader.downloader import HTTPDownloader

logger = logging.getLogger(__name__)


class _FrontierQueueView:
    """Backward-compatible queue metrics surface backed by the frontier."""

    def __init__(self, snapshot_fn: Callable[[], Dict[str, Any]]):
        self._snapshot_fn = snapshot_fn

    def _pending(self) -> List[Any]:
        snapshot = self._snapshot_fn() or {}
        pending = snapshot.get("pending", [])
        return pending if isinstance(pending, list) else []

    def qsize(self) -> int:
        return len(self._pending())

    def empty(self) -> bool:
        return self.qsize() == 0


@dataclass
class SpiderStats:
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_items: int = 0
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None

    @property
    def duration(self) -> float:
        end = self.end_time or time.time()
        return end - self.start_time

    @property
    def requests_per_second(self) -> float:
        if self.duration > 0:
            return self.total_requests / self.duration
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "total_items": self.total_items,
            "duration_seconds": round(self.duration, 2),
            "requests_per_second": round(self.requests_per_second, 2),
        }


class Spider:
    """Spider runtime with proxy, robots, incremental, and compatibility APIs."""

    def __init__(
        self,
        name: str = "Spider",
        thread_count: int = 5,
        max_retries: int = 3,
        request_timeout: int = 30,
        rate_limit: Optional[float] = None,
        enable_stats: bool = True,
        max_depth: int = 10,
    ):
        if thread_count < 1:
            raise ValueError("thread_count must be at least 1")

        self.name = name
        self.start_urls: List[str] = []
        self.thread_count = thread_count
        self.max_retries = max_retries
        self.request_timeout = request_timeout
        self.rate_limit = rate_limit
        self.max_depth = max_depth

        self.downloader = HTTPDownloader(
            timeout=request_timeout,
            max_retries=max_retries,
            rate_limit=rate_limit,
        )
        self.pipelines: List[Callable[[Page], None]] = []
        self.middlewares: List[Callable[[Request], Optional[Request]]] = []
        self.visited_urls: Set[str] = set()
        self._url_hashes: Set[str] = set()
        self._content_hashes: Set[str] = set()
        self._lock = threading.RLock()
        self._sequence = itertools.count()

        self._proxy_pool: Optional[ProxyPool] = None
        self._robots_checker = RobotsChecker()
        self._incremental = IncrementalCrawler()
        self._frontier_config = FrontierConfig(
            checkpoint_id=f"{self.name}-frontier-{time.time_ns()}",
        )
        self._frontier = AutoscaledFrontier(self._frontier_config)
        self.request_queue = _FrontierQueueView(lambda: self._frontier.snapshot())
        self._observability = ObservabilityCollector()
        self._artifact_store = FileArtifactStore("artifacts/observability")
        self._incremental_store_path: Optional[str] = None
        self._max_pages: int = 0
        self._pages_crawled: int = 0
        self._start_time: float = 0.0
        self._last_request_time: float = 0.0
        self._enable_content_dedup = True

        self._running = False
        self.running = False
        self.stopped = False
        self._stop_event = threading.Event()
        self.stats = SpiderStats() if enable_stats else None

        # Keep robots enforcement wired by default so downloader can honor
        # both robots disallow and crawl-delay pacing when enabled.
        self.downloader.set_robots_checker(self._robots_checker)

    def set_start_urls(self, *urls: str) -> "Spider":
        normalized: List[str] = []
        for value in urls:
            if isinstance(value, (list, tuple, set)):
                normalized.extend(str(url) for url in value)
            else:
                normalized.append(str(value))

        for url in normalized:
            if self._validate_url(url):
                self.start_urls.append(url)
            else:
                logger.warning("invalid URL skipped: %s", url[:100])
        return self

    def set_thread_count(self, count: int) -> "Spider":
        if count < 1:
            raise ValueError("thread_count must be at least 1")
        self.thread_count = count
        return self

    def add_pipeline(self, func: Callable[[Page], None]) -> "Spider":
        self.pipelines.append(func)
        return self

    def add_middleware(self, func: Callable[[Request], Optional[Request]]) -> "Spider":
        self.middlewares.append(func)
        return self

    def set_proxy_pool(self, proxy_pool: ProxyPool) -> "Spider":
        self._proxy_pool = proxy_pool
        self.downloader.set_proxy_pool(proxy_pool)
        return self

    def add_proxy(self, proxy: Proxy) -> "Spider":
        if not self._proxy_pool:
            self._proxy_pool = ProxyPool()
            self.downloader.set_proxy_pool(self._proxy_pool)
        self._proxy_pool.add_proxy(proxy)
        return self

    def add_proxy_from_string(self, proxy_str: str) -> "Spider":
        if not self._proxy_pool:
            self._proxy_pool = ProxyPool()
            self.downloader.set_proxy_pool(self._proxy_pool)
        self._proxy_pool.add_proxy_from_string(proxy_str)
        return self

    def set_respect_robots(
        self, respect: bool = True, user_agent: str = "*"
    ) -> "Spider":
        self._robots_checker = RobotsChecker(user_agent=user_agent)
        self._robots_checker.set_respect_robots(respect)
        self.downloader.set_robots_checker(self._robots_checker)
        return self

    def set_user_agents(self, user_agents: List[str]) -> "Spider":
        self.downloader.set_user_agents(user_agents)
        return self

    def set_incremental(
        self,
        enabled: bool = True,
        min_change_interval: int = 3600,
        store_path: str | None = None,
    ) -> "Spider":
        self._incremental = IncrementalCrawler(
            enabled=enabled,
            min_change_interval=min_change_interval,
            store_path=store_path,
        )
        self._incremental_store_path = store_path
        self.downloader.set_incremental(self._incremental)
        return self

    def configure_frontier(
        self,
        *,
        checkpoint_dir: str | None = None,
        checkpoint_id: str | None = None,
        autoscale: bool | None = None,
        min_concurrency: int | None = None,
        max_concurrency: int | None = None,
        lease_ttl_seconds: int | None = None,
        max_inflight_per_domain: int | None = None,
    ) -> "Spider":
        cfg = FrontierConfig(
            checkpoint_dir=checkpoint_dir or self._frontier_config.checkpoint_dir,
            checkpoint_id=checkpoint_id or self._frontier_config.checkpoint_id,
            autoscale=(
                self._frontier_config.autoscale if autoscale is None else autoscale
            ),
            min_concurrency=(
                self._frontier_config.min_concurrency
                if min_concurrency is None
                else min_concurrency
            ),
            max_concurrency=(
                self._frontier_config.max_concurrency
                if max_concurrency is None
                else max_concurrency
            ),
            target_latency_ms=self._frontier_config.target_latency_ms,
            lease_ttl_seconds=(
                self._frontier_config.lease_ttl_seconds
                if lease_ttl_seconds is None
                else lease_ttl_seconds
            ),
            max_inflight_per_domain=(
                self._frontier_config.max_inflight_per_domain
                if max_inflight_per_domain is None
                else max_inflight_per_domain
            ),
        )
        self._frontier_config = cfg
        self._frontier = AutoscaledFrontier(cfg)
        return self

    def set_max_pages(self, max_pages: int) -> "Spider":
        self._max_pages = max_pages
        return self

    def set_min_request_interval(self, seconds: float) -> "Spider":
        self.downloader.set_min_request_interval(seconds)
        return self

    def enable_content_dedup(self, enabled: bool = True) -> "Spider":
        self._enable_content_dedup = enabled
        if not enabled:
            self._content_hashes.clear()
        return self

    @staticmethod
    def _validate_url(url: str) -> bool:
        if not url or not isinstance(url, str):
            return False
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False
        return len(url) <= 2048

    @staticmethod
    def _url_hash(url: str) -> str:
        return hashlib.md5(url.encode("utf-8")).hexdigest()

    def _parse(self, page: Page) -> None:
        logger.info(
            "Parsed: %s (Status: %s)", page.response.url, page.response.status_code
        )

    def _is_duplicate(self, request_or_url) -> bool:
        url = (
            request_or_url.url
            if isinstance(request_or_url, Request)
            else str(request_or_url)
        )
        if not url:
            return True

        url_hash = self._url_hash(url)
        with self._lock:
            if url_hash in self._url_hashes:
                return True
            self._url_hashes.add(url_hash)
            return False

    def _is_content_duplicate(self, content: bytes) -> bool:
        if not content or not self._enable_content_dedup:
            return False

        content_hash = hashlib.sha256(content).hexdigest()
        with self._lock:
            if content_hash in self._content_hashes:
                return True
            self._content_hashes.add(content_hash)
            return False

    def _should_stop(self) -> bool:
        if self._stop_event.is_set() or not self._running:
            return True
        if self._max_pages > 0 and self._pages_crawled >= self._max_pages:
            logger.info("maximum page limit reached: %s", self._max_pages)
            return True
        return False

    @contextmanager
    def _rate_limit_context(self):
        if self.rate_limit:
            min_interval = 1.0 / self.rate_limit
            elapsed = time.time() - self._last_request_time
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
        try:
            yield
        finally:
            self._last_request_time = time.time()

    def _process_request(self, req: Request) -> bool:
        trace_id = self._observability.start_trace("spider.request")
        started_at = time.time()
        try:
            if req.depth > self.max_depth:
                return self._finalize_request(
                    req,
                    trace_id,
                    started_at,
                    success=False,
                    error=ValueError("max depth exceeded"),
                )

            for middleware in self.middlewares:
                result = middleware(req)
                if result is None:
                    return self._finalize_request(
                        req, trace_id, started_at, success=True, status_code=204
                    )
                req = result

            if self.stats:
                self.stats.total_requests += 1

            last_error: Optional[Exception] = None
            status_code: Optional[int] = None
            for attempt in range(self.max_retries + 1):
                with self._rate_limit_context():
                    resp = self.downloader.download(req)
                status_code = resp.status_code
                access_friction = self._access_friction_report(resp)

                if access_friction.get("blocked"):
                    if self.stats:
                        self.stats.failed_requests += 1
                    return self._finalize_request(
                        req,
                        trace_id,
                        started_at,
                        success=False,
                        status_code=status_code,
                        error=RuntimeError(self._access_friction_error(access_friction)),
                        response=resp,
                    )

                if resp.error:
                    last_error = resp.error
                    if attempt < self.max_retries:
                        time.sleep(0.5 * (attempt + 1))
                        continue
                    if self.stats:
                        self.stats.failed_requests += 1
                    return self._finalize_request(
                        req,
                        trace_id,
                        started_at,
                        success=False,
                        status_code=status_code,
                        error=resp.error,
                        response=resp,
                    )

                if resp.status_code == 304:
                    return self._finalize_request(
                        req,
                        trace_id,
                        started_at,
                        success=True,
                        status_code=304,
                        response=resp,
                    )

                if self._is_content_duplicate(resp.content):
                    return self._finalize_request(
                        req,
                        trace_id,
                        started_at,
                        success=True,
                        status_code=208,
                        response=resp,
                    )

                self._pages_crawled += 1
                if self.stats:
                    self.stats.successful_requests += 1

                page = Page(response=resp)
                if req.callback:
                    req.callback(page)

                for pipeline in self.pipelines:
                    pipeline(page)
                    if self.stats:
                        self.stats.total_items += 1

                return self._finalize_request(
                    req,
                    trace_id,
                    started_at,
                    success=True,
                    status_code=resp.status_code,
                    response=resp,
                )

            if self.stats:
                self.stats.failed_requests += 1
            return self._finalize_request(
                req,
                trace_id,
                started_at,
                success=False,
                status_code=status_code,
                error=last_error,
            )
        except Exception as exc:
            logger.error(
                "Error processing %s: %s", getattr(req, "url", "<unknown>"), exc
            )
            if self.stats:
                self.stats.failed_requests += 1
            return self._finalize_request(
                req, trace_id, started_at, success=False, error=exc
            )

    def _worker(self) -> None:
        while not self._should_stop():
            req = self._frontier.lease()
            if req is None:
                if self._should_stop():
                    break
                if self._frontier_pending_count() == 0:
                    break
                time.sleep(0.1)
                continue
            self._process_request(req)

    def _signal_stop(self) -> None:
        self._frontier.persist()

    def start(self) -> None:
        self._frontier.load()
        if self._enable_content_dedup:
            self._content_hashes.clear()

        if self.stats:
            self.stats = SpiderStats()

        self._running = True
        self.running = True
        self.stopped = False
        self._stop_event.clear()
        self._start_time = time.time()
        self._pages_crawled = 0

        logger.info("Spider [%s] started with %s threads", self.name, self.thread_count)

        if self._proxy_pool:
            self._proxy_pool.start_health_check()

        for url in self.start_urls:
            self.add_request(Request(url=url, callback=self._parse))

        threads = []
        if self.thread_count == 1:
            try:
                self._worker()
            except KeyboardInterrupt:
                logger.info("received interrupt signal, stopping")
                self.stop()
        else:
            for _ in range(self.thread_count):
                worker = threading.Thread(target=self._worker, daemon=True)
                worker.start()
                threads.append(worker)

            try:
                while not self._should_stop():
                    if self._frontier_pending_count() == 0:
                        break
                    time.sleep(0.1)
            except KeyboardInterrupt:
                logger.info("received interrupt signal, stopping")
                self.stop()

        self._signal_stop()
        for worker in threads:
            worker.join(timeout=10)

        if self._proxy_pool:
            self._proxy_pool.stop_health_check()

        if self.stats:
            self.stats.end_time = time.time()

        self._running = False
        self.running = False
        self.stopped = True
        self._stop_event.set()
        self._frontier.persist()
        if self._incremental_store_path:
            self._incremental.save(self._incremental_store_path)
        self._persist_runtime_artifacts()

        logger.info("Spider [%s] finished", self.name)
        logger.info("Stats: %s", self.get_runtime_stats())

    def stop(self) -> None:
        self._running = False
        self.running = False
        self.stopped = True
        self._stop_event.set()

    def add_request(self, req: Request) -> bool:
        with self._lock:
            if req is None or not req.url or not self._validate_url(req.url):
                return False
            if req.depth > self.max_depth:
                return False
            if self._is_duplicate(req.url):
                return False

            self.visited_urls.add(req.url)
            return self._frontier.push(req)

    def _purge_stop_signals(self) -> None:
        return None

    def _frontier_pending_count(self) -> int:
        return len(self._frontier.snapshot().get("pending", []))

    def _finalize_request(
        self,
        req: Request,
        trace_id: str,
        started_at: float,
        *,
        success: bool,
        status_code: Optional[int] = None,
        error: Optional[Exception] = None,
        response: Optional[Any] = None,
    ) -> bool:
        latency_ms = int((time.time() - started_at) * 1000)
        self._frontier.ack(
            req,
            success=success,
            latency_ms=latency_ms,
            error=error,
            status_code=status_code,
            max_retries=self.max_retries,
        )
        self._observability.record_result(
            request=req,
            latency_ms=latency_ms,
            status_code=status_code,
            error=error,
            trace_id=trace_id,
        )
        if success and response is not None:
            self._persist_graph_artifact(req, response)
        self._observability.end_trace(trace_id, status="ok" if success else "failed")
        return success

    def _access_friction_report(self, response: Any) -> Dict[str, Any]:
        meta = getattr(response, "meta", {}) or {}
        report = meta.get("access_friction")
        return report if isinstance(report, dict) else {}

    def _access_friction_error(self, report: Dict[str, Any]) -> str:
        level = str(report.get("level", "unknown"))
        signals = report.get("signals") or []
        if isinstance(signals, list):
            signal_text = ",".join(str(signal) for signal in signals)
        else:
            signal_text = str(signals)
        return f"access friction {level}: {signal_text}".strip()

    def _persist_graph_artifact(self, req: Request, response: Any) -> None:
        content_type = str(getattr(response, "headers", {}).get("Content-Type", ""))
        text = str(getattr(response, "text", "") or "")
        if not text.strip():
            return
        lower = text.lower()
        if (
            "html" not in content_type.lower()
            and "<html" not in lower
            and "<title" not in lower
        ):
            return

        title_match = re.search(
            r"<title[^>]*>(.*?)</title>", text, flags=re.IGNORECASE | re.DOTALL
        )
        title = re.sub(r"\s+", " ", title_match.group(1)).strip() if title_match else ""
        links = re.findall(
            r'<a[^>]+href=["\']([^"\']+)["\']', text, flags=re.IGNORECASE
        )
        images = re.findall(
            r'<img[^>]+src=["\']([^"\']+)["\']', text, flags=re.IGNORECASE
        )
        headings = re.findall(
            r"<h[1-3][^>]*>(.*?)</h[1-3]>", text, flags=re.IGNORECASE | re.DOTALL
        )

        payload = {
            "root_id": "document",
            "stats": {
                "total_nodes": 1
                + (1 if title else 0)
                + len(links)
                + len(images)
                + len(headings),
                "total_edges": len(links) + len(images),
                "node_types": {
                    "document": 1,
                    "title": 1 if title else 0,
                    "link": len(links),
                    "image": len(images),
                    "heading": len(headings),
                },
            },
            "title": title,
            "links": links,
            "images": images,
        }
        name = (
            f"{self.name}-{hashlib.md5(req.url.encode('utf-8')).hexdigest()[:12]}-graph"
        )
        self._artifact_store.put_bytes(
            name,
            "json",
            json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
            metadata={"url": req.url, "root_id": "document", "stats": payload["stats"]},
        )

    def _persist_runtime_artifacts(self) -> None:
        frontier_bytes = json.dumps(
            self._frontier.snapshot(), ensure_ascii=False, indent=2
        ).encode("utf-8")
        observability_bytes = json.dumps(
            self._observability.summary(), ensure_ascii=False, indent=2
        ).encode("utf-8")
        self._artifact_store.put_bytes(f"{self.name}-frontier", "json", frontier_bytes)
        self._artifact_store.put_bytes(
            f"{self.name}-observability", "json", observability_bytes
        )

    def get_stats(self) -> Dict[str, Any]:
        return self.stats.to_dict() if self.stats else {}

    def get_runtime_stats(self) -> Dict[str, Any]:
        elapsed = time.time() - self._start_time if self._start_time else 0
        return {
            "name": self.name,
            "running": self.running,
            "pages_crawled": self._pages_crawled,
            "queue_size": self._frontier_pending_count(),
            "visited_urls": len(self.visited_urls),
            "content_hashes": len(self._content_hashes),
            "elapsed": f"{elapsed:.2f}s",
            "stats": self.get_stats(),
            "proxy_pool": self._proxy_pool.stats() if self._proxy_pool else None,
            "incremental": (
                self._incremental.get_cache_stats() if self._incremental else None
            ),
            "frontier": {
                "recommended_concurrency": self._frontier.recommended_concurrency,
                "dead_letters": self._frontier.dead_letter_count,
                "pending": self._frontier_pending_count(),
            },
            "observability": self._observability.summary(),
        }

    def __enter__(self) -> "Spider":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()
