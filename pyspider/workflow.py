from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

from pyspider.connectors import Connector, OutputEnvelope
from pyspider.events import EventBus


@dataclass(slots=True)
class ExecutionPolicy:
    step_timeout_millis: int = 0
    max_retries: int = 0


@dataclass(slots=True)
class FlowStep:
    id: str
    type: str
    selector: str = ""
    value: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class FlowJob:
    id: str
    name: str
    steps: list[FlowStep]
    output_contract: dict[str, Any] = field(default_factory=dict)
    policy: ExecutionPolicy = field(default_factory=ExecutionPolicy)

    @classmethod
    def from_mapping(cls, payload: dict[str, Any]) -> "FlowJob":
        steps = [
            FlowStep(
                id=str(item.get("id") or item.get("type") or f"step-{index}"),
                type=str(item.get("type") or "").strip().lower(),
                selector=str(item.get("selector") or ""),
                value=str(item.get("value") or ""),
                metadata=dict(item.get("metadata") or {}),
            )
            for index, item in enumerate(payload.get("steps") or [])
        ]
        policy_payload = payload.get("policy") or {}
        policy = ExecutionPolicy(
            step_timeout_millis=int(policy_payload.get("step_timeout_millis") or 0),
            max_retries=int(policy_payload.get("max_retries") or 0),
        )
        name = str(payload.get("name") or payload.get("id") or "workflow").strip()
        job_id = str(payload.get("id") or name).strip()
        return cls(
            id=job_id,
            name=name,
            steps=steps,
            output_contract=dict(payload.get("output_contract") or {}),
            policy=policy,
        )


@dataclass(slots=True)
class FlowResult:
    job_id: str
    run_id: str
    extracted: dict[str, Any]
    artifacts: list[str]


class WorkflowExecutionContext(Protocol):
    def goto_url(self, url: str) -> None: ...
    def wait_for(self, timeout_ms: int) -> None: ...
    def click(self, selector: str) -> None: ...
    def type(self, selector: str, value: str) -> None: ...
    def select(self, selector: str, value: str, options: dict[str, Any]) -> None: ...
    def hover(self, selector: str) -> None: ...
    def scroll(self, selector: str, options: dict[str, Any]) -> None: ...
    def evaluate(self, script: str) -> Any: ...
    def listen_network(self, options: dict[str, Any]) -> list[dict[str, Any]]: ...
    def capture_html(self) -> str: ...
    def capture_screenshot(self, artifact_path: str) -> None: ...
    def current_url(self) -> str: ...
    def title(self) -> str: ...
    def close(self) -> None: ...


class MemoryWorkflowContext:
    def __init__(self) -> None:
        self._current_url = ""
        self._title = "workflow"
        self._html = "<html><title>workflow</title></html>"
        self._evaluations: dict[str, Any] = {}
        self._network_events = [
            {"url": "https://example.com/api", "method": "GET", "status": 200}
        ]

    def goto_url(self, url: str) -> None:
        self._current_url = url

    def wait_for(self, timeout_ms: int) -> None:
        if timeout_ms > 0:
            time.sleep(timeout_ms / 1000.0)

    def click(self, selector: str) -> None:
        return None

    def type(self, selector: str, value: str) -> None:
        return None

    def select(self, selector: str, value: str, options: dict[str, Any]) -> None:
        return None

    def hover(self, selector: str) -> None:
        return None

    def scroll(self, selector: str, options: dict[str, Any]) -> None:
        return None

    def evaluate(self, script: str) -> Any:
        return self._evaluations.get(script, script)

    def listen_network(self, options: dict[str, Any]) -> list[dict[str, Any]]:
        return list(self._network_events)

    def capture_html(self) -> str:
        return self._html

    def capture_screenshot(self, artifact_path: str) -> None:
        path = Path(artifact_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("workflow-screenshot", encoding="utf-8")

    def current_url(self) -> str:
        return self._current_url

    def title(self) -> str:
        return self._title

    def close(self) -> None:
        return None

    def set_title(self, title: str) -> None:
        self._title = title

    def set_html(self, html: str) -> None:
        self._html = html

    def set_evaluation(self, script: str, value: Any) -> None:
        self._evaluations[script] = value


class WorkflowRunner:
    def __init__(
        self,
        *,
        event_bus: EventBus | None = None,
        connectors: list[Connector] | None = None,
        context_factory: type[MemoryWorkflowContext] | None = None,
    ) -> None:
        self.event_bus = event_bus
        self.connectors = list(connectors or [])
        self.context_factory = context_factory or MemoryWorkflowContext

    def add_connector(self, connector: Connector) -> "WorkflowRunner":
        self.connectors.append(connector)
        return self

    def execute(self, job: FlowJob) -> FlowResult:
        run_id = f"{job.id}-{uuid4()}"
        extracted: dict[str, Any] = {}
        artifacts: list[str] = []
        if self.event_bus:
            self.event_bus.publish(
                "workflow.job.started",
                {"job_id": job.id, "run_id": run_id, "step_count": len(job.steps)},
            )

        context = self.context_factory()
        try:
            for step in job.steps:
                if self.event_bus:
                    self.event_bus.publish(
                        "workflow.step.started",
                        {
                            "job_id": job.id,
                            "run_id": run_id,
                            "step_id": step.id,
                            "type": step.type,
                        },
                    )
                self._execute_step(context, step, extracted, artifacts)
                if self.event_bus:
                    self.event_bus.publish(
                        "workflow.step.succeeded",
                        {
                            "job_id": job.id,
                            "run_id": run_id,
                            "step_id": step.id,
                            "type": step.type,
                        },
                    )
        finally:
            context.close()

        result = FlowResult(job_id=job.id, run_id=run_id, extracted=extracted, artifacts=artifacts)
        envelope = OutputEnvelope(
            job_id=result.job_id,
            run_id=result.run_id,
            extracted=result.extracted,
            artifacts=result.artifacts,
        )
        for connector in self.connectors:
            connector.write(envelope)
        if self.event_bus:
            self.event_bus.publish(
                "workflow.job.completed",
                {
                    "job_id": job.id,
                    "run_id": run_id,
                    "fields": list(extracted.keys()),
                    "artifacts": len(artifacts),
                },
            )
        return result

    def _execute_step(
        self,
        context: WorkflowExecutionContext,
        step: FlowStep,
        extracted: dict[str, Any],
        artifacts: list[str],
    ) -> None:
        metadata = dict(step.metadata or {})
        step_type = step.type.lower()
        if step_type == "goto":
            context.goto_url(str(metadata.get("url") or step.selector))
            return
        if step_type == "wait":
            context.wait_for(int(metadata.get("timeout_ms") or 0))
            return
        if step_type == "click":
            context.click(step.selector)
            return
        if step_type == "type":
            context.type(step.selector, step.value)
            return
        if step_type == "select":
            context.select(step.selector, step.value, metadata)
            return
        if step_type == "hover":
            context.hover(step.selector)
            return
        if step_type == "scroll":
            context.scroll(step.selector, metadata)
            return
        if step_type == "eval":
            field = str(metadata.get("field") or metadata.get("save_as") or "eval")
            extracted[field] = context.evaluate(step.value)
            return
        if step_type == "listen_network":
            field = str(
                metadata.get("field") or metadata.get("save_as") or "network_requests"
            )
            extracted[field] = context.listen_network(metadata)
            return
        if step_type == "extract":
            field = str(metadata.get("field") or step.selector or "value")
            if "value" in metadata:
                extracted[field] = metadata["value"]
                return
            if field == "title":
                extracted[field] = context.title()
                return
            if field == "url":
                extracted[field] = context.current_url()
                return
            if field in {"html", "dom"}:
                extracted[field] = context.capture_html()
                return
            extracted[field] = step.value
            return
        if step_type == "screenshot":
            artifact = str(metadata.get("artifact") or step.value or f"{step.id}.png")
            context.capture_screenshot(artifact)
            artifacts.append(artifact)
            return
        if step_type == "download":
            artifact = Path(str(metadata.get("artifact") or step.value or f"{step.id}.bin"))
            artifact.parent.mkdir(parents=True, exist_ok=True)
            artifact.write_text("workflow-artifact", encoding="utf-8")
            artifacts.append(str(artifact))
            return
        raise ValueError(f"unsupported workflow step: {step.type}")
