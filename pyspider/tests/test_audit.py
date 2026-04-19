from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pyspider.runtime.audit import AuditEvent, CompositeAuditTrail, FileAuditTrail, MemoryAuditTrail


def test_audit_trails_persist_and_replay(tmp_path: Path) -> None:
    file_trail = FileAuditTrail(tmp_path / "audit.jsonl")
    memory_trail = MemoryAuditTrail()
    composite = CompositeAuditTrail([file_trail, memory_trail])

    event = AuditEvent(
        timestamp=datetime.now(timezone.utc).isoformat(),
        job_id="job-1",
        step_id="goto",
        event_type="step.started",
        payload={"url": "https://example.com"},
    )
    composite.append(event)

    assert len(memory_trail.events()) == 1
    assert len(file_trail.events()) == 1
    assert file_trail.events()[0].payload == {"url": "https://example.com"}
