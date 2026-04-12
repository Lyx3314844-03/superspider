from __future__ import annotations

from collections.abc import Iterable

from .models import WorkerCapability


FRAMEWORK_LANGUAGE = {
    "javaspider": "java",
    "gospider": "go",
    "pyspider": "python",
    "rustspider": "rust",
}


def _unique_strings(values: Iterable[object]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if not isinstance(value, str):
            continue
        text = value.strip()
        if not text or text in seen:
            continue
        ordered.append(text)
        seen.add(text)
    return ordered


def _framework_language(payload_name: str, payload: dict) -> str:
    runtime = payload.get("runtime")
    if isinstance(runtime, str) and runtime.strip():
        return runtime.strip()
    return FRAMEWORK_LANGUAGE.get(payload_name, payload_name)


def _control_plane_support(payload: dict) -> bool:
    control_plane = payload.get("control_plane")
    if isinstance(control_plane, dict):
        return bool(
            control_plane.get("result_envelope")
            and control_plane.get("artifact_refs")
            and control_plane.get("graph_artifact")
        )

    operator_products = payload.get("operator_products") or {}
    debug_console = operator_products.get("debug_console") or {}
    shared_contracts = set(payload.get("shared_contracts") or [])
    return bool(debug_console.get("control_plane_jsonl")) and "web-control-plane" in shared_contracts


def _max_concurrency(payload: dict) -> int:
    resources = payload.get("resources") or {}
    if isinstance(resources, dict):
        for key in ("default_concurrency", "request_concurrency", "max_concurrency"):
            value = resources.get(key)
            if isinstance(value, int) and value > 0:
                return value

    autoscaling = (payload.get("operator_products") or {}).get("autoscaling_pools") or {}
    for key in ("request_concurrency", "max_concurrency"):
        value = autoscaling.get(key)
        if isinstance(value, int) and value > 0:
            return value
    return 1


def build_worker_catalog(payloads: dict[str, dict] | Iterable[tuple[str, dict]]) -> list[WorkerCapability]:
    if isinstance(payloads, dict):
        items = payloads.items()
    else:
        items = payloads

    workers: list[WorkerCapability] = []
    for framework_name, payload in items:
        runtimes = _unique_strings(payload.get("runtimes") or ["http"])
        if not runtimes:
            runtimes = ["http"]

        language = _framework_language(framework_name, payload)
        graph = _control_plane_support(payload)
        supports_http = "http" in runtimes
        supports_browser = "browser" in runtimes
        supports_media = "media" in runtimes
        supports_ai = "ai" in runtimes
        max_concurrency = _max_concurrency(payload)

        for runtime in runtimes:
            workers.append(
                WorkerCapability(
                    worker_id=f"{framework_name}-{runtime}",
                    runtime=runtime,
                    language=language,
                    http=supports_http,
                    browser=supports_browser,
                    media=supports_media,
                    ai=supports_ai,
                    graph=graph,
                    max_concurrency=max_concurrency,
                    tags=[framework_name, language, runtime],
                )
            )
    return workers
