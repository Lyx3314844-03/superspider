from __future__ import annotations

from copy import deepcopy

from .models import CompiledJob


LANGUAGE_PREFERENCE = {
    "http": ["rust", "go"],
    "browser": ["java", "rust", "go"],
    "media": ["rust", "go"],
    "ai": ["python"],
}


def _required_capabilities(job: dict) -> list[str]:
    required: list[str] = []
    runtime = job.get("runtime", "")
    if runtime:
        required.append(runtime)

    browser = job.get("browser") or {}
    if browser.get("actions") or browser.get("capture"):
        required.append("browser")

    if any((item or {}).get("type") == "media" for item in job.get("extract") or []):
        required.append("media")
    if any((item or {}).get("type") == "ai" for item in job.get("extract") or []):
        required.append("ai")

    output = job.get("output") or {}
    metadata = job.get("metadata") or {}
    if output.get("attach_graph_artifact", True) or metadata.get("emit_graph_artifact", False):
        required.append("graph")

    anti_bot = job.get("anti_bot") or {}
    if anti_bot.get("fallback_runtime") == "browser" and "browser" not in required:
        required.append("browser")

    seen = set()
    ordered = []
    for item in required:
        if item not in seen:
            ordered.append(item)
            seen.add(item)
    return ordered


def compile_job(raw_job: dict) -> CompiledJob:
    job = deepcopy(raw_job)
    runtime = str(job.get("runtime") or "").strip() or "http"
    target = dict(job.get("target") or {})
    extract = list(job.get("extract") or [])
    output = dict(job.get("output") or {})
    browser = dict(job.get("browser") or {})
    anti_bot = dict(job.get("anti_bot") or {})
    policy = dict(job.get("policy") or {})
    metadata = dict(job.get("metadata") or {})

    if output.get("format") == "artifact":
        metadata.setdefault("emit_graph_artifact", True)
    if browser.get("capture") and "graph" in browser.get("capture", []):
        metadata.setdefault("emit_graph_artifact", True)

    required = _required_capabilities(
        {
            "runtime": runtime,
            "extract": extract,
            "output": output,
            "browser": browser,
            "anti_bot": anti_bot,
            "metadata": metadata,
        }
    )

    return CompiledJob(
        job_name=str(job.get("name") or "unnamed-job"),
        runtime=runtime,
        target=target,
        extract=extract,
        output=output,
        browser=browser,
        anti_bot=anti_bot,
        policy=policy,
        metadata=metadata,
        required_capabilities=required,
        preferred_languages=list(LANGUAGE_PREFERENCE.get(runtime, [])),
    )
