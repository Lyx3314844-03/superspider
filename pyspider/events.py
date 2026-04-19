from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Callable

TOPIC_TASK_CREATED = "task:created"
TOPIC_TASK_QUEUED = "task:queued"
TOPIC_TASK_RUNNING = "task:running"
TOPIC_TASK_SUCCEEDED = "task:succeeded"
TOPIC_TASK_FAILED = "task:failed"
TOPIC_TASK_CANCELLED = "task:cancelled"
TOPIC_TASK_DELETED = "task:deleted"
TOPIC_TASK_RESULT = "task:result"


@dataclass(slots=True)
class EventEnvelope:
    topic: str
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )


Event = EventEnvelope


@dataclass(slots=True)
class TaskLifecyclePayload:
    task_id: str
    state: str
    runtime: str = ""
    url: str = ""
    worker_id: str = ""
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )
    has_result: bool = False


@dataclass(slots=True)
class ArtifactRef:
    kind: str = ""
    uri: str = ""
    path: str = ""
    size: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TaskResultPayload:
    task_id: str
    state: str
    runtime: str = ""
    url: str = ""
    status_code: int = 0
    artifacts: list[str] = field(default_factory=list)
    artifact_refs: dict[str, ArtifactRef] = field(default_factory=dict)
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )


@dataclass(slots=True)
class TaskDeletedPayload:
    task_id: str
    deleted_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )


class EventBus:
    def publish(self, topic: str, payload: dict[str, Any]) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    def list(self, limit: int = 100, topic: str = "") -> list[EventEnvelope]:  # pragma: no cover - interface
        raise NotImplementedError

    def recent(self, topic: str = "", limit: int = 100) -> list[EventEnvelope]:
        return self.list(limit=limit, topic=topic)

    def subscribe(self, topic: str, callback: Callable[[EventEnvelope], None]) -> None:  # pragma: no cover - interface
        raise NotImplementedError


class InMemoryEventBus(EventBus):
    def __init__(self, max_size: int = 256) -> None:
        self.max_size = max(1, max_size)
        self._events: list[EventEnvelope] = []
        self._lock = Lock()
        self._subscribers: dict[str, list[Callable[[EventEnvelope], None]]] = defaultdict(list)

    def publish(self, topic: str, payload: dict[str, Any] | Any) -> EventEnvelope:
        item = EventEnvelope(topic=topic, payload=_normalize(payload))
        with self._lock:
            self._events.append(item)
            if len(self._events) > self.max_size:
                self._events = self._events[-self.max_size :]
            callbacks = list(self._subscribers.get(topic, ())) + list(
                self._subscribers.get("*", ())
            )
        for callback in callbacks:
            callback(item)
        return item

    def list(self, limit: int = 100, topic: str = "") -> list[EventEnvelope]:
        with self._lock:
            items = [
                item
                for item in reversed(self._events)
                if not topic or item.topic == topic
            ]
        return items[:limit]

    def subscribe(self, topic: str, callback: Callable[[EventEnvelope], None]) -> None:
        with self._lock:
            self._subscribers[topic].append(callback)


class FileEventBus(EventBus):
    def __init__(self, path: str | Path, max_size: int = 1024) -> None:
        self.path = Path(path)
        self.memory = InMemoryEventBus(max_size=max_size)
        self._lock = Lock()

    def publish(self, topic: str, payload: dict[str, Any] | Any) -> EventEnvelope:
        item = self.memory.publish(topic, payload)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(
            {
                "topic": item.topic,
                "payload": item.payload,
                "timestamp": item.timestamp,
            },
            ensure_ascii=False,
        )
        with self._lock:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(line)
                handle.write("\n")
        return item

    def list(self, limit: int = 100, topic: str = "") -> list[EventEnvelope]:
        return self.memory.list(limit=limit, topic=topic)

    def subscribe(self, topic: str, callback: Callable[[EventEnvelope], None]) -> None:
        self.memory.subscribe(topic, callback)


def _normalize(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return {str(key): _normalize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    return value
