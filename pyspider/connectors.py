from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any


@dataclass(slots=True)
class OutputEnvelope:
    job_id: str
    run_id: str
    extracted: dict[str, Any] = field(default_factory=dict)
    artifacts: list[str] = field(default_factory=list)


class Connector:
    def write(self, envelope: OutputEnvelope) -> None:  # pragma: no cover - interface
        raise NotImplementedError


class InMemoryConnector(Connector):
    def __init__(self) -> None:
        self._lock = Lock()
        self._envelopes: list[OutputEnvelope] = []

    def write(self, envelope: OutputEnvelope) -> None:
        clone = OutputEnvelope(
            job_id=envelope.job_id,
            run_id=envelope.run_id,
            extracted=dict(envelope.extracted),
            artifacts=list(envelope.artifacts),
        )
        with self._lock:
            self._envelopes.append(clone)

    def list(self) -> list[OutputEnvelope]:
        with self._lock:
            return [
                OutputEnvelope(
                    job_id=item.job_id,
                    run_id=item.run_id,
                    extracted=dict(item.extracted),
                    artifacts=list(item.artifacts),
                )
                for item in self._envelopes
            ]


class FileConnector(Connector):
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._lock = Lock()

    def write(self, envelope: OutputEnvelope) -> None:
        payload = {
            "job_id": envelope.job_id,
            "run_id": envelope.run_id,
            "extracted": envelope.extracted,
            "artifacts": envelope.artifacts,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(payload, ensure_ascii=False)
        with self._lock:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(line)
                handle.write("\n")
