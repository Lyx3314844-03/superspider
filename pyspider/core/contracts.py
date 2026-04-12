from __future__ import annotations

import hashlib
import heapq
import json
import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Deque, Dict, Iterable, List, Optional, Protocol
from urllib.parse import urlparse

from .checkpoint import CheckpointManager
from .models import Request


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    return str(value)


def _normalize_domain(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except ValueError:
        return ""


@dataclass(frozen=True)
class RequestFingerprint:
    value: str
    algorithm: str = "sha256"

    @classmethod
    def from_request(
        cls,
        request: Request,
        *,
        vary_headers: Iterable[str] = ("accept", "content-type"),
    ) -> "RequestFingerprint":
        tracked_headers = {
            key.lower(): value
            for key, value in (request.headers or {}).items()
            if key.lower() in {item.lower() for item in vary_headers}
        }
        payload = {
            "url": request.url,
            "method": request.method.upper(),
            "headers": tracked_headers,
            "cookies": dict(sorted((request.cookies or {}).items())),
            "body": request.body or "",
            "meta": dict(sorted((request.meta or {}).items())),
        }
        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            default=_json_default,
        ).encode("utf-8")
        return cls(hashlib.sha256(encoded).hexdigest())


@dataclass
class ArtifactRecord:
    name: str
    kind: str
    path: str
    size: int
    metadata: Dict[str, Any] = field(default_factory=dict)


class ArtifactStore(Protocol):
    def put_bytes(
        self,
        name: str,
        kind: str,
        data: bytes,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ArtifactRecord: ...

    def list(self) -> List[ArtifactRecord]: ...


class FileArtifactStore:
    def __init__(self, root: str | Path = "artifacts/runtime") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._records: List[ArtifactRecord] = []

    def put_bytes(
        self,
        name: str,
        kind: str,
        data: bytes,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ArtifactRecord:
        suffix = {
            "html": ".html",
            "json": ".json",
            "trace": ".json",
            "text": ".txt",
            "screenshot": ".png",
        }.get(kind, "")
        safe_name = name.replace("/", "_").replace("\\", "_")
        path = self.root / f"{safe_name}{suffix}"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        record = ArtifactRecord(
            name=safe_name,
            kind=kind,
            path=str(path),
            size=len(data),
            metadata=dict(metadata or {}),
        )
        self._records.append(record)
        return record

    def list(self) -> List[ArtifactRecord]:
        return list(self._records)


@dataclass
class SessionSlot:
    session_id: str
    created_at: float
    last_used_at: float
    headers: Dict[str, str] = field(default_factory=dict)
    cookies: Dict[str, str] = field(default_factory=dict)
    fingerprint_profile: str = "default"
    proxy_id: Optional[str] = None
    lease_count: int = 0
    failure_count: int = 0
    in_use: bool = False


class SessionPool:
    def __init__(self, max_sessions: int = 32) -> None:
        self.max_sessions = max_sessions
        self._lock = threading.RLock()
        self._sessions: Dict[str, SessionSlot] = {}

    def acquire(
        self,
        *,
        proxy_id: Optional[str] = None,
        fingerprint_profile: str = "default",
    ) -> SessionSlot:
        with self._lock:
            reusable = [
                slot
                for slot in self._sessions.values()
                if not slot.in_use
                and slot.proxy_id == proxy_id
                and slot.fingerprint_profile == fingerprint_profile
            ]
            if reusable:
                slot = min(reusable, key=lambda item: item.last_used_at)
            elif len(self._sessions) < self.max_sessions:
                now = time.time()
                slot = SessionSlot(
                    session_id=f"session-{uuid.uuid4().hex[:12]}",
                    created_at=now,
                    last_used_at=now,
                    fingerprint_profile=fingerprint_profile,
                    proxy_id=proxy_id,
                )
                self._sessions[slot.session_id] = slot
            else:
                slot = min(self._sessions.values(), key=lambda item: item.last_used_at)
            slot.in_use = True
            slot.last_used_at = time.time()
            slot.lease_count += 1
            return slot

    def release(self, session_id: str, *, success: bool = True) -> None:
        with self._lock:
            slot = self._sessions.get(session_id)
            if slot is None:
                return
            slot.in_use = False
            slot.last_used_at = time.time()
            if not success:
                slot.failure_count += 1

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "max_sessions": self.max_sessions,
                "sessions": [asdict(slot) for slot in self._sessions.values()],
            }


@dataclass
class ProxyEndpoint:
    proxy_id: str
    url: str
    success_count: int = 0
    failure_count: int = 0
    available: bool = True
    last_error: str = ""

    @property
    def score(self) -> float:
        total = self.success_count + self.failure_count
        if total == 0:
            return 1.0
        return self.success_count / max(total, 1)


class ProxyPolicy:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._proxies: Dict[str, ProxyEndpoint] = {}

    def add_proxy(self, url: str, proxy_id: Optional[str] = None) -> ProxyEndpoint:
        with self._lock:
            endpoint = ProxyEndpoint(
                proxy_id=proxy_id or f"proxy-{len(self._proxies) + 1}", url=url
            )
            self._proxies[endpoint.proxy_id] = endpoint
            return endpoint

    def choose(self) -> Optional[ProxyEndpoint]:
        with self._lock:
            available = [proxy for proxy in self._proxies.values() if proxy.available]
            if not available:
                return None
            return max(available, key=lambda item: item.score)

    def record(self, proxy_id: str, *, success: bool, error: str = "") -> None:
        with self._lock:
            endpoint = self._proxies.get(proxy_id)
            if endpoint is None:
                return
            if success:
                endpoint.success_count += 1
                endpoint.last_error = ""
                endpoint.available = True
            else:
                endpoint.failure_count += 1
                endpoint.last_error = error
                if (
                    endpoint.failure_count >= 3
                    and endpoint.failure_count > endpoint.success_count
                ):
                    endpoint.available = False

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {"proxies": [asdict(proxy) for proxy in self._proxies.values()]}


class Middleware(Protocol):
    def process_request(self, request: Request) -> Optional[Request]: ...

    def process_response(self, response: Any, request: Request) -> Any: ...


class MiddlewareChain:
    def __init__(self) -> None:
        self._middlewares: List[Middleware] = []

    def add(self, middleware: Middleware) -> "MiddlewareChain":
        self._middlewares.append(middleware)
        return self

    def process_request(self, request: Request) -> Optional[Request]:
        current: Optional[Request] = request
        for middleware in self._middlewares:
            if current is None:
                return None
            current = middleware.process_request(current)
        return current

    def process_response(self, response: Any, request: Request) -> Any:
        current = response
        for middleware in reversed(self._middlewares):
            current = middleware.process_response(current, request)
        return current


@dataclass
class StructuredEvent:
    timestamp: float
    level: str
    event: str
    trace_id: Optional[str]
    fields: Dict[str, Any] = field(default_factory=dict)


class FailureClassifier:
    @staticmethod
    def classify(
        *, error: Any = None, status_code: Optional[int] = None, body: str = ""
    ) -> str:
        message = f"{error or ''} {body}".lower()
        if status_code == 304:
            return "not_modified"
        if status_code in {401, 403}:
            return "blocked"
        if status_code == 404:
            return "not_found"
        if status_code == 408 or "timeout" in message:
            return "timeout"
        if (
            status_code == 429
            or "rate limit" in message
            or "too many requests" in message
        ):
            return "throttled"
        if "captcha" in message or "challenge" in message:
            return "anti_bot"
        if "proxy" in message:
            return "proxy"
        if status_code is not None and status_code >= 500:
            return "server"
        if error:
            return "runtime"
        return "ok"


class ObservabilityCollector:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.events: List[StructuredEvent] = []
        self.metrics: Dict[str, float] = defaultdict(float)
        self.traces: Dict[str, List[StructuredEvent]] = defaultdict(list)

    def start_trace(self, name: str) -> str:
        trace_id = f"trace-{uuid.uuid4().hex[:12]}"
        self.log("info", name, trace_id=trace_id, phase="start")
        return trace_id

    def end_trace(self, trace_id: str, *, status: str = "ok", **fields: Any) -> None:
        self.log("info", "trace.complete", trace_id=trace_id, status=status, **fields)

    def log(
        self, level: str, event: str, *, trace_id: Optional[str] = None, **fields: Any
    ) -> None:
        structured = StructuredEvent(
            timestamp=time.time(),
            level=level,
            event=event,
            trace_id=trace_id,
            fields=dict(fields),
        )
        with self._lock:
            self.events.append(structured)
            self.metrics[f"events.{event}"] += 1
            if trace_id:
                self.traces[trace_id].append(structured)

    def record_request(
        self, request: Request, *, trace_id: Optional[str] = None
    ) -> None:
        self.metrics["requests.total"] += 1
        self.log(
            "info",
            "request.enqueued",
            trace_id=trace_id,
            url=request.url,
            priority=request.priority,
        )

    def record_result(
        self,
        *,
        request: Optional[Request] = None,
        latency_ms: float = 0,
        status_code: Optional[int] = None,
        error: Any = None,
        trace_id: Optional[str] = None,
    ) -> str:
        classification = FailureClassifier.classify(
            error=error, status_code=status_code
        )
        self.metrics["requests.latency_ms.total"] += max(latency_ms, 0)
        self.metrics[f"results.{classification}"] += 1
        level = "error" if classification not in {"ok", "not_modified"} else "info"
        self.log(
            level,
            "request.completed",
            trace_id=trace_id,
            url=request.url if request else "",
            latency_ms=latency_ms,
            status_code=status_code,
            classification=classification,
            error=str(error) if error else "",
        )
        return classification

    def summary(self) -> Dict[str, Any]:
        with self._lock:
            total_requests = int(self.metrics.get("requests.total", 0))
            total_latency = self.metrics.get("requests.latency_ms.total", 0.0)
            return {
                "events": len(self.events),
                "traces": len(self.traces),
                "metrics": dict(self.metrics),
                "average_latency_ms": (
                    round(total_latency / total_requests, 2) if total_requests else 0.0
                ),
            }

    def to_prometheus_text(self, prefix: str = "spider_runtime") -> str:
        summary = self.summary()
        metrics = summary["metrics"]
        lines = [
            f"# HELP {prefix}_events_total Total structured events emitted by the runtime",
            f"# TYPE {prefix}_events_total counter",
            f"{prefix}_events_total {summary['events']}",
            f"# HELP {prefix}_traces_total Total traces recorded by the runtime",
            f"# TYPE {prefix}_traces_total gauge",
            f"{prefix}_traces_total {summary['traces']}",
        ]
        for key, value in sorted(metrics.items()):
            metric_name = f"{prefix}_{key.replace('.', '_')}"
            lines.append(f"{metric_name} {value}")
        lines.append(f"{prefix}_average_latency_ms {summary['average_latency_ms']}")
        return "\n".join(lines) + "\n"

    def to_otel_payload(self, service_name: str = "spider-runtime") -> Dict[str, Any]:
        summary = self.summary()
        datapoints = []
        for key, value in sorted(summary["metrics"].items()):
            datapoints.append(
                {
                    "name": key,
                    "value": value,
                    "unit": "1",
                }
            )
        datapoints.append(
            {
                "name": "average_latency_ms",
                "value": summary["average_latency_ms"],
                "unit": "ms",
            }
        )
        return {
            "resource": {"service.name": service_name},
            "scope": "pyspider.core.contracts",
            "metrics": datapoints,
            "events": summary["events"],
            "traces": summary["traces"],
        }


@dataclass
class FrontierConfig:
    checkpoint_dir: str = "artifacts/checkpoints/frontier"
    checkpoint_id: str = "runtime-frontier"
    autoscale: bool = True
    min_concurrency: int = 1
    max_concurrency: int = 16
    target_latency_ms: int = 1200
    lease_ttl_seconds: int = 30
    max_inflight_per_domain: int = 2


@dataclass
class FrontierLease:
    request: Request
    fingerprint: str
    leased_at: float
    expires_at: float


class AutoscaledFrontier:
    def __init__(
        self,
        config: Optional[FrontierConfig] = None,
        *,
        checkpoint_manager: Optional[CheckpointManager] = None,
        observability: Optional[ObservabilityCollector] = None,
    ) -> None:
        self.config = config or FrontierConfig()
        self._lock = threading.RLock()
        self._queue: List[tuple[int, int, Dict[str, Any]]] = []
        self._sequence = 0
        self._known: set[str] = set()
        self._leases: Dict[str, FrontierLease] = {}
        self._dead_letters: List[Dict[str, Any]] = []
        self._domain_inflight: Dict[str, int] = defaultdict(int)
        self._latencies: Deque[float] = deque(maxlen=64)
        self._outcomes: Deque[bool] = deque(maxlen=64)
        self._recommended_concurrency = max(self.config.min_concurrency, 1)
        self._checkpoint_manager = checkpoint_manager or CheckpointManager(
            self.config.checkpoint_dir,
            auto_save_interval=0,
        )
        self.observability = observability or ObservabilityCollector()

    @property
    def recommended_concurrency(self) -> int:
        return self._recommended_concurrency

    @property
    def dead_letter_count(self) -> int:
        return len(self._dead_letters)

    def push(self, request: Request) -> bool:
        fingerprint = RequestFingerprint.from_request(request).value
        with self._lock:
            if fingerprint in self._known or fingerprint in self._leases:
                return False
            self._known.add(fingerprint)
            self._sequence += 1
            heapq.heappush(
                self._queue,
                (
                    -int(request.priority),
                    self._sequence,
                    self._serialize_request(request, fingerprint),
                ),
            )
        self.observability.record_request(request)
        return True

    def lease(self, now: Optional[float] = None) -> Optional[Request]:
        now = now or time.time()
        blocked: List[tuple[int, int, Dict[str, Any]]] = []
        with self._lock:
            self.reap_expired_leases(now=now)
            while self._queue:
                priority, sequence, serialized = heapq.heappop(self._queue)
                domain = _normalize_domain(serialized["url"])
                if (
                    domain
                    and self._domain_inflight[domain]
                    >= self.config.max_inflight_per_domain
                ):
                    blocked.append((priority, sequence, serialized))
                    continue
                request = self._deserialize_request(serialized)
                fingerprint = serialized["fingerprint"]
                expires_at = now + max(self.config.lease_ttl_seconds, 1)
                self._leases[fingerprint] = FrontierLease(
                    request=request,
                    fingerprint=fingerprint,
                    leased_at=now,
                    expires_at=expires_at,
                )
                if domain:
                    self._domain_inflight[domain] += 1
                for item in blocked:
                    heapq.heappush(self._queue, item)
                return request
            for item in blocked:
                heapq.heappush(self._queue, item)
        return None

    def heartbeat(self, request: Request, *, ttl_seconds: Optional[int] = None) -> bool:
        fingerprint = RequestFingerprint.from_request(request).value
        with self._lock:
            lease = self._leases.get(fingerprint)
            if lease is None:
                return False
            lease.expires_at = time.time() + max(
                ttl_seconds or self.config.lease_ttl_seconds, 1
            )
            return True

    def ack(
        self,
        request: Request,
        *,
        success: bool,
        latency_ms: float = 0,
        error: Any = None,
        status_code: Optional[int] = None,
        max_retries: int = 3,
    ) -> None:
        fingerprint = RequestFingerprint.from_request(request).value
        with self._lock:
            self._leases.pop(fingerprint, None)
            domain = _normalize_domain(request.url)
            if domain and self._domain_inflight.get(domain, 0) > 0:
                self._domain_inflight[domain] -= 1
            retries = int(request.meta.get("retry_count", 0))
            if not success:
                if retries >= max_retries:
                    self._dead_letters.append(
                        self._serialize_request(request, fingerprint)
                    )
                else:
                    request.meta["retry_count"] = retries + 1
                    self._sequence += 1
                    heapq.heappush(
                        self._queue,
                        (
                            -int(request.priority),
                            self._sequence,
                            self._serialize_request(request, fingerprint),
                        ),
                    )
                    self._leases.pop(fingerprint, None)
            self._latencies.append(max(latency_ms, 0))
            self._outcomes.append(bool(success))
            self._adjust_concurrency()
        self.observability.record_result(
            request=request,
            latency_ms=latency_ms,
            status_code=status_code,
            error=error,
        )

    def reap_expired_leases(
        self, *, now: Optional[float] = None, max_retries: int = 3
    ) -> int:
        now = now or time.time()
        expired: List[FrontierLease] = []
        with self._lock:
            for fingerprint, lease in list(self._leases.items()):
                if lease.expires_at <= now:
                    expired.append(self._leases.pop(fingerprint))
            for lease in expired:
                domain = _normalize_domain(lease.request.url)
                if domain and self._domain_inflight.get(domain, 0) > 0:
                    self._domain_inflight[domain] -= 1
                retries = int(lease.request.meta.get("retry_count", 0))
                if retries >= max_retries:
                    self._dead_letters.append(
                        self._serialize_request(lease.request, lease.fingerprint)
                    )
                    continue
                lease.request.meta["retry_count"] = retries + 1
                self._sequence += 1
                heapq.heappush(
                    self._queue,
                    (
                        -int(lease.request.priority),
                        self._sequence,
                        self._serialize_request(lease.request, lease.fingerprint),
                    ),
                )
        return len(expired)

    def persist(self, checkpoint_id: Optional[str] = None) -> None:
        snapshot = self.snapshot()
        self._checkpoint_manager.save(
            checkpoint_id or self.config.checkpoint_id,
            {
                "visited_urls": list(self._known),
                "pending_urls": [item["url"] for _, _, item in self._queue],
                "stats": {"frontier": snapshot},
                "config": asdict(self.config),
            },
            immediate=True,
        )

    def restore(self, state: Dict[str, Any]) -> None:
        snapshot = dict(state.get("stats", {})).get("frontier", state)
        with self._lock:
            self._queue.clear()
            self._leases.clear()
            self._dead_letters = list(snapshot.get("dead_letters", []))
            self._domain_inflight = defaultdict(
                int, snapshot.get("domain_inflight", {})
            )
            self._known = set(snapshot.get("known", []))
            self._latencies = deque(snapshot.get("latencies", []), maxlen=64)
            self._outcomes = deque(snapshot.get("outcomes", []), maxlen=64)
            self._recommended_concurrency = int(
                snapshot.get("recommended_concurrency", self.config.min_concurrency)
            )
            self._sequence = 0
            for item in snapshot.get("pending", []):
                self._sequence += 1
                heapq.heappush(
                    self._queue, (-int(item.get("priority", 0)), self._sequence, item)
                )

    def load(self, checkpoint_id: Optional[str] = None) -> bool:
        state = self._checkpoint_manager.load(
            checkpoint_id or self.config.checkpoint_id
        )
        if not state:
            return False
        self.restore(state)
        return True

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "pending": [item for _, _, item in sorted(self._queue)],
                "known": sorted(self._known),
                "leases": {
                    fingerprint: {
                        "request": self._serialize_request(lease.request, fingerprint),
                        "leased_at": lease.leased_at,
                        "expires_at": lease.expires_at,
                    }
                    for fingerprint, lease in self._leases.items()
                },
                "domain_inflight": dict(self._domain_inflight),
                "recommended_concurrency": self._recommended_concurrency,
                "latencies": list(self._latencies),
                "outcomes": list(self._outcomes),
                "dead_letters": list(self._dead_letters),
            }

    def _adjust_concurrency(self) -> None:
        if not self.config.autoscale:
            return
        average_latency = (
            (sum(self._latencies) / len(self._latencies)) if self._latencies else 0.0
        )
        failure_rate = (
            1.0 - (sum(1 for item in self._outcomes if item) / len(self._outcomes))
            if self._outcomes
            else 0.0
        )
        if failure_rate > 0.2 or average_latency > self.config.target_latency_ms * 1.4:
            self._recommended_concurrency = max(
                self.config.min_concurrency, self._recommended_concurrency - 1
            )
        elif (
            len(self._queue) > self._recommended_concurrency
            and average_latency < self.config.target_latency_ms
        ):
            self._recommended_concurrency = min(
                self.config.max_concurrency, self._recommended_concurrency + 1
            )

    @staticmethod
    def _serialize_request(request: Request, fingerprint: str) -> Dict[str, Any]:
        return {
            "url": request.url,
            "method": request.method,
            "headers": dict(request.headers),
            "cookies": dict(request.cookies),
            "body": request.body,
            "meta": dict(request.meta),
            "priority": request.priority,
            "depth": request.depth,
            "fingerprint": fingerprint,
        }

    @staticmethod
    def _deserialize_request(payload: Dict[str, Any]) -> Request:
        return Request(
            url=payload["url"],
            method=payload.get("method", "GET"),
            headers=dict(payload.get("headers", {})),
            cookies=dict(payload.get("cookies", {})),
            body=payload.get("body"),
            meta=dict(payload.get("meta", {})),
            priority=int(payload.get("priority", 0)),
            depth=int(payload.get("depth", 0)),
        )
