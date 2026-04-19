from __future__ import annotations

import json
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from threading import RLock
from typing import Any, Iterable, List, Protocol


@dataclass(slots=True)
class AuditEvent:
    timestamp: str
    job_id: str = ""
    step_id: str = ""
    event_type: str = ""
    payload: dict[str, Any] | None = None


class AuditTrail(Protocol):
    def append(self, event: AuditEvent) -> None: ...
    def events(self) -> List[AuditEvent]: ...


class MemoryAuditTrail:
    def __init__(self) -> None:
        self._lock = RLock()
        self._events: List[AuditEvent] = []

    def append(self, event: AuditEvent) -> None:
        with self._lock:
            self._events.append(event)

    def events(self) -> List[AuditEvent]:
        with self._lock:
            return list(self._events)


class FileAuditTrail:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._lock = RLock()

    def append(self, event: AuditEvent) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock, self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(_normalize(event), ensure_ascii=False) + "\n")

    def events(self) -> List[AuditEvent]:
        if not self.path.exists():
            return []
        items = []
        with self._lock:
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                items.append(
                    AuditEvent(
                        timestamp=payload.get("timestamp", ""),
                        job_id=payload.get("job_id", ""),
                        step_id=payload.get("step_id", ""),
                        event_type=payload.get("event_type", ""),
                        payload=payload.get("payload"),
                    )
                )
        return items


class CompositeAuditTrail:
    def __init__(self, trails: Iterable[AuditTrail]) -> None:
        self.trails = list(trails)

    def append(self, event: AuditEvent) -> None:
        for trail in self.trails:
            trail.append(event)

    def events(self) -> List[AuditEvent]:
        events: List[AuditEvent] = []
        for trail in self.trails:
            events.extend(trail.events())
        return events


def _normalize(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return {str(key): _normalize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    return value
