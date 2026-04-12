from __future__ import annotations

import json
import queue
import threading
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict


class FileResultSink:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def write(self, payload: Dict[str, Any]) -> None:
        _writer_registry().append(
            self.path, json.dumps(payload, ensure_ascii=False) + "\n"
        )


class FileAuditSink:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def emit(self, event_type: str, payload: Dict[str, Any]) -> None:
        record = {"type": event_type, "payload": _normalize(payload)}
        _writer_registry().append(
            self.path, json.dumps(record, ensure_ascii=False) + "\n"
        )


def _normalize(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return {str(k): _normalize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalize(v) for v in value]
    return value


class _WriteTask:
    def __init__(self, payload: str) -> None:
        self.payload = payload
        self.done = threading.Event()
        self.error: Exception | None = None


class _WriterWorker:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.queue: queue.Queue[_WriteTask] = queue.Queue()
        self.thread = threading.Thread(
            target=self._run, daemon=True, name=f"jsonl-writer-{path.name}"
        )
        self.thread.start()

    def append(self, payload: str) -> None:
        task = _WriteTask(payload)
        self.queue.put(task)
        task.done.wait()
        if task.error is not None:
            raise task.error

    def _run(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        while True:
            task = self.queue.get()
            try:
                with self.path.open("a", encoding="utf-8") as handle:
                    handle.write(task.payload)
                    handle.flush()
            except Exception as exc:  # pragma: no cover
                task.error = exc
            finally:
                task.done.set()


class _WriterRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._workers: dict[Path, _WriterWorker] = {}

    def append(self, path: Path, payload: str) -> None:
        with self._lock:
            worker = self._workers.get(path)
            if worker is None:
                worker = _WriterWorker(path)
                self._workers[path] = worker
        worker.append(payload)


_REGISTRY: _WriterRegistry | None = None


def _writer_registry() -> _WriterRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = _WriterRegistry()
    return _REGISTRY
