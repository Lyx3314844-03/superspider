from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class WorkerCapability:
    worker_id: str
    runtime: str
    language: str
    http: bool = False
    browser: bool = False
    media: bool = False
    ai: bool = False
    graph: bool = False
    max_concurrency: int = 1
    tags: list[str] = field(default_factory=list)


@dataclass
class CompiledJob:
    job_name: str
    runtime: str
    target: dict[str, Any]
    extract: list[dict[str, Any]] = field(default_factory=list)
    output: dict[str, Any] = field(default_factory=dict)
    browser: dict[str, Any] = field(default_factory=dict)
    anti_bot: dict[str, Any] = field(default_factory=dict)
    policy: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    required_capabilities: list[str] = field(default_factory=list)
    preferred_languages: list[str] = field(default_factory=list)


@dataclass
class DispatchPlan:
    job_name: str
    selected_runtime: str
    selected_language: str
    worker_id: str
    required_capabilities: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
