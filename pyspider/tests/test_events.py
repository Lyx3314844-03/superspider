from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pyspider.events import (
    FileEventBus,
    InMemoryEventBus,
    TOPIC_TASK_RESULT,
    TOPIC_TASK_RUNNING,
    TaskLifecyclePayload,
    TaskResultPayload,
)
from pyspider.runtime.sinks import FileAuditSink


def test_event_bus_publishes_and_replays_history(tmp_path: Path) -> None:
    _ = FileAuditSink(tmp_path / "events.jsonl")
    bus = InMemoryEventBus()
    received = []
    bus.subscribe(TOPIC_TASK_RUNNING, received.append)

    event = bus.publish(
        TOPIC_TASK_RUNNING,
        TaskLifecyclePayload(task_id="job-1", state="running", runtime="python"),
    )

    assert event.topic == TOPIC_TASK_RUNNING
    assert len(received) == 1
    assert received[0].payload["task_id"] == "job-1"
    assert bus.recent(TOPIC_TASK_RUNNING)[0].payload["state"] == "running"


def test_event_bus_persists_jsonl_records(tmp_path: Path) -> None:
    sink_path = tmp_path / "events.jsonl"
    bus = FileEventBus(sink_path)

    bus.publish(
        TOPIC_TASK_RESULT,
        TaskResultPayload(task_id="job-1", state="succeeded", runtime="python"),
    )

    lines = sink_path.read_text(encoding="utf-8").strip().splitlines()
    payload = json.loads(lines[0])
    assert payload["topic"] == TOPIC_TASK_RESULT
    assert payload["payload"]["task_id"] == "job-1"
