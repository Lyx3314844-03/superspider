from __future__ import annotations

from .compiler import compile_job
from .models import CompiledJob, DispatchPlan, WorkerCapability


def _supports(worker: WorkerCapability, capability: str) -> bool:
    if capability in {"http", "browser", "media", "ai"}:
        return worker.runtime == capability or getattr(worker, capability, False)
    if capability == "graph":
        return worker.graph
    return False


def dispatch_job(raw_job: dict, workers: list[WorkerCapability]) -> DispatchPlan:
    compiled = compile_job(raw_job) if not isinstance(raw_job, CompiledJob) else raw_job

    candidates: list[tuple[int, WorkerCapability, list[str]]] = []
    for worker in workers:
        missing = [cap for cap in compiled.required_capabilities if not _supports(worker, cap)]
        if missing:
            continue
        score = 0
        reasons = []
        if worker.language in compiled.preferred_languages:
            score += 10
            reasons.append(f"preferred language {worker.language}")
        if worker.runtime == compiled.runtime:
            score += 5
            reasons.append(f"native runtime {worker.runtime}")
        score += worker.max_concurrency
        reasons.append(f"capacity {worker.max_concurrency}")
        candidates.append((score, worker, reasons))

    if not candidates:
        raise ValueError(f"no worker can satisfy capabilities: {compiled.required_capabilities}")

    candidates.sort(key=lambda item: item[0], reverse=True)
    _, selected, reasons = candidates[0]
    return DispatchPlan(
        job_name=compiled.job_name,
        selected_runtime=compiled.runtime,
        selected_language=selected.language,
        worker_id=selected.worker_id,
        required_capabilities=list(compiled.required_capabilities),
        reasons=reasons,
    )
