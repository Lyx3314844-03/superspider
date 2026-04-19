import argparse
import asyncio
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict
from urllib.parse import urlparse

from pyspider import __version__
from pyspider.browser.compat import browser_compatibility_matrix
from pyspider.feature_gates import catalog as feature_gate_catalog
from pyspider.research.job import ResearchJob
from pyspider.runtime.orchestrator import ResearchRuntime
from pyspider.runtime.sinks import FileAuditSink, FileResultSink

FRAMEWORK_CLI_COMMANDS = {
    "config",
    "crawl",
    "browser",
    "ai",
    "doctor",
    "preflight",
    "export",
    "curl",
    "web",
    "version",
    "media",
    "download",
    "convert",
    "info",
    "screenshot",
    "merge",
    "parse",
    "drm",
    "artifact",
    "youtube",
    "audit",
    "workflow",
    "sitemap-discover",
    "plugins",
    "selector-studio",
    "scrapy",
    "profile-site",
    "ultimate",
    "anti-bot",
    "node-reverse",
    "help",
    "-h",
    "--help",
}

SUPPORTED_JOB_RUNTIMES = {"http", "browser", "media", "ai"}


def _delegate_framework_cli(argv: list[str]) -> int:
    from pyspider.cli import main as framework_cli

    delegated_argv = [] if argv and argv[0] in {"help", "-h", "--help"} else argv
    return framework_cli.main(delegated_argv)


def _schema_from_extract_list(extract_list: list[dict]) -> dict:
    properties = {}
    for item in extract_list:
        field = item.get("field")
        if not field:
            continue
        schema = item.get("schema")
        if isinstance(schema, dict) and schema:
            properties[field] = schema
        else:
            properties[field] = {"type": "string"}
    return {"properties": properties} if properties else {}


def _inline_job_content(job_spec: Dict[str, Any], content: str | None) -> str | None:
    metadata = job_spec.get("metadata") if isinstance(job_spec.get("metadata"), dict) else {}
    target = job_spec.get("target") if isinstance(job_spec.get("target"), dict) else {}
    for value in (
        content,
        metadata.get("content"),
        metadata.get("mock_html"),
        target.get("body"),
    ):
        if isinstance(value, str) and value:
            return value
    return None


def _artifact_texts_from_metadata(job_spec: Dict[str, Any]) -> list[str]:
    metadata = job_spec.get("metadata") if isinstance(job_spec.get("metadata"), dict) else {}
    collected: list[str] = []
    for key in ("artifact_texts", "mock_artifact_texts"):
        value = metadata.get(key)
        if isinstance(value, list):
            collected.extend(str(item) for item in value if str(item).strip())
    for key in ("network", "network_text", "har", "har_text"):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            collected.append(value)
    return collected


def _infer_media_platform(url: str) -> str:
    lower = url.lower()
    if "youtube.com" in lower or "youtu.be" in lower:
        return "youtube"
    if "youku.com" in lower or "youku.tv" in lower:
        return "youku"
    if "bilibili.com" in lower or "b23.tv" in lower:
        return "bilibili"
    if "iqiyi.com" in lower:
        return "iqiyi"
    if "qq.com" in lower or "v.qq.com" in lower:
        return "tencent"
    if "douyin.com" in lower:
        return "douyin"
    return "generic"


def _infer_media_id(url: str) -> str:
    patterns = (
        r"[?&]v=([A-Za-z0-9_-]+)",
        r"youtu\.be/([A-Za-z0-9_-]+)",
        r"id_([A-Za-z0-9=]+)",
        r"/video/((?:BV|av)[A-Za-z0-9]+)",
        r"/bangumi/play/(ep\d+)",
        r"/v_(\w+)\.html",
        r"/play/(\w+)",
        r"[?&]curid=([^&]+)",
        r"/x/cover/[^/]+/([A-Za-z0-9]+)\.html",
        r"/x/page/([A-Za-z0-9]+)\.html",
        r"/x/([A-Za-z0-9]+)\.html",
        r"[?&]vid=([A-Za-z0-9]+)",
        r"/video/(\d+)",
        r"modal_id=(\d+)",
    )
    for pattern in patterns:
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            return match.group(1)
    return ""


def _build_research_job(job_spec: Dict[str, Any]) -> ResearchJob:
    metadata = job_spec.get("metadata") or {}
    extract_schema = metadata.get("extract_schema")
    if not isinstance(extract_schema, dict) or not extract_schema:
        extract_schema = _schema_from_extract_list(job_spec.get("extract") or [])

    output = job_spec.get("output") or {}
    if not isinstance(output, dict):
        output = {}

    return ResearchJob(
        seed_urls=[job_spec["target"]["url"]],
        site_profile=metadata.get("site_profile") or {},
        extract_schema=extract_schema,
        extract_specs=list(job_spec.get("extract") or []),
        policy=job_spec.get("policy") or {},
        output=output,
    )


def _persist_dataset_if_requested(
    runtime: ResearchRuntime, job: ResearchJob, extract: Dict[str, Any]
) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    output_target = job.output or {}
    if output_target.get("path"):
        result["dataset"] = runtime.writer.write([extract], output_target)
    return result


def _run_http_runtime(
    job_spec: Dict[str, Any], job: ResearchJob, content: str | None
) -> Dict[str, Any]:
    return ResearchRuntime().run(job, content=content)


def _run_browser_runtime(
    job_spec: Dict[str, Any], job: ResearchJob, content: str | None
) -> Dict[str, Any]:
    runtime = ResearchRuntime()
    seed = job.seed_urls[0]
    resolved_content = content or f"<title>{seed}</title>"
    profile = runtime.profiler.profile(seed, resolved_content)
    extracted = runtime.studio.run(
        resolved_content, job.extract_schema, job.extract_specs
    )
    result: Dict[str, Any] = {
        "seed": seed,
        "profile": profile,
        "extract": extracted,
        "dispatch": {
            "runtime": "browser",
            "actions": list(
                ((job_spec.get("browser") or {}).get("actions") or [])
                if isinstance(job_spec.get("browser"), dict)
                else []
            ),
            "capture": list(
                ((job_spec.get("browser") or {}).get("capture") or [])
                if isinstance(job_spec.get("browser"), dict)
                else []
            ),
        },
    }
    result.update(_persist_dataset_if_requested(runtime, job, extracted))
    return result


def _media_extract_payload(video: Any) -> Dict[str, Any]:
    if video is None:
        return {}
    payload = {
        "title": getattr(video, "title", "") or "",
        "video_id": getattr(video, "video_id", "") or "",
        "platform": getattr(video, "platform", "") or "",
        "m3u8_url": getattr(video, "m3u8_url", None),
        "dash_url": getattr(video, "dash_url", None),
        "mp4_url": getattr(video, "mp4_url", None),
        "download_url": getattr(video, "download_url", None),
        "cover_url": getattr(video, "cover_url", None),
        "duration": getattr(video, "duration", 0) or 0,
        "description": getattr(video, "description", "") or "",
        "quality_options": list(getattr(video, "quality_options", []) or []),
    }
    return {
        key: value
        for key, value in payload.items()
        if value not in (None, "", [])
        or key in {"duration"}
    }


def _run_media_runtime(
    job_spec: Dict[str, Any], job: ResearchJob, content: str | None
) -> Dict[str, Any]:
    from pyspider.media.video_parser import UniversalParser

    runtime = ResearchRuntime()
    seed = job.seed_urls[0]
    resolved_content = content or ""
    artifact_texts = _artifact_texts_from_metadata(job_spec)
    parser = UniversalParser()
    video = None
    if resolved_content or artifact_texts:
        video = parser.parse_artifacts(
            seed, html=resolved_content, artifact_texts=artifact_texts
        )
    if video is None:
        video = parser.parse(seed)
    if video is None:
        return runtime.run(job, content=resolved_content or None)

    media_extract = _media_extract_payload(video)
    inferred_platform = _infer_media_platform(seed)
    inferred_video_id = _infer_media_id(seed)
    if media_extract.get("platform") in {"", "generic", "generic-artifact"}:
        media_extract["platform"] = inferred_platform
    if inferred_video_id and (
        not media_extract.get("video_id")
        or re.fullmatch(r"[0-9a-f]{16}", str(media_extract["video_id"]))
    ):
        media_extract["video_id"] = inferred_video_id
    extracted = dict(media_extract)
    if job.extract_specs:
        extracted = runtime.studio.run(
            resolved_content or json.dumps(media_extract, ensure_ascii=False),
            job.extract_schema,
            job.extract_specs,
        )
        for field, value in media_extract.items():
            if field not in extracted and value not in ("", None, []):
                extracted[field] = value

    profile = runtime.profiler.profile(
        seed,
        resolved_content or f"<title>{media_extract.get('title', seed)}</title>",
    )
    result: Dict[str, Any] = {
        "seed": seed,
        "profile": profile,
        "extract": extracted,
        "dispatch": {"runtime": "media"},
    }
    result.update(_persist_dataset_if_requested(runtime, job, extracted))
    return result


def _run_ai_runtime(
    job_spec: Dict[str, Any], job: ResearchJob, content: str | None
) -> Dict[str, Any]:
    result = ResearchRuntime().run(job, content=content)
    result["dispatch"] = {"runtime": "ai"}
    return result


def _execute_sync_runtime(
    job_spec: Dict[str, Any], job: ResearchJob, content: str | None
) -> Dict[str, Any]:
    runtime = str(job_spec.get("runtime", "http")).strip()
    executors = {
        "http": _run_http_runtime,
        "browser": _run_browser_runtime,
        "media": _run_media_runtime,
        "ai": _run_ai_runtime,
    }
    try:
        executor = executors[runtime]
    except KeyError as exc:
        raise ValueError(f"unsupported runtime in pyspider job runtime: {runtime}") from exc
    return executor(job_spec, job, content)


def _extract_host(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").strip()
    except ValueError:
        return ""


def _effective_allowed_domains(job_spec: Dict[str, Any]) -> list[str]:
    target = job_spec.get("target") if isinstance(job_spec.get("target"), dict) else {}
    allowed = target.get("allowed_domains")
    if isinstance(allowed, list) and allowed:
        return [str(item).strip() for item in allowed if str(item).strip()]
    policy = job_spec.get("policy") if isinstance(job_spec.get("policy"), dict) else {}
    if policy.get("same_domain_only"):
        host = _extract_host(str(target.get("url", "")))
        if host:
            return [host]
    return []


def _validate_job_policies(job_spec: Dict[str, Any]) -> None:
    runtime = str(job_spec.get("runtime", "")).strip()
    if runtime not in SUPPORTED_JOB_RUNTIMES:
        raise ValueError(f"unsupported runtime in pyspider job runtime: {runtime}")

    target = job_spec.get("target") if isinstance(job_spec.get("target"), dict) else {}
    host = _extract_host(str(target.get("url", "")))
    allowed_domains = _effective_allowed_domains(job_spec)
    if allowed_domains and not host:
        raise ValueError("target.url is missing host")
    host_lower = host.lower()
    for allowed in allowed_domains:
        allowed_lower = allowed.lower()
        if host_lower == allowed_lower or host_lower.endswith(f".{allowed_lower}"):
            return
    if allowed_domains:
        raise ValueError(f"target host {host} is outside allowed_domains")


def _apply_rate_limit(job_spec: Dict[str, Any]) -> None:
    resources = (
        job_spec.get("resources") if isinstance(job_spec.get("resources"), dict) else {}
    )
    rate = resources.get("rate_limit_per_sec")
    if isinstance(rate, (int, float)) and rate > 0:
        time.sleep(max(0.001, 1.0 / float(rate)))


def _estimate_bytes_in(job_spec: Dict[str, Any], inline_content: str | None) -> int:
    if inline_content:
        return len(inline_content.encode("utf-8"))
    metadata = (
        job_spec.get("metadata") if isinstance(job_spec.get("metadata"), dict) else {}
    )
    for key in ("mock_html", "content"):
        value = metadata.get(key)
        if isinstance(value, str) and value:
            return len(value.encode("utf-8"))
    target = job_spec.get("target") if isinstance(job_spec.get("target"), dict) else {}
    body = target.get("body")
    if isinstance(body, str) and body:
        return len(body.encode("utf-8"))
    return 0


def _enforce_job_budget(
    job_spec: Dict[str, Any], inline_content: str | None, latency_ms: int
) -> None:
    policy = job_spec.get("policy") if isinstance(job_spec.get("policy"), dict) else {}
    budget = policy.get("budget") if isinstance(policy.get("budget"), dict) else {}
    wall_time_ms = budget.get("wall_time_ms")
    if (
        isinstance(wall_time_ms, (int, float))
        and wall_time_ms > 0
        and latency_ms > int(wall_time_ms)
    ):
        raise ValueError(
            f"job exceeded budget.wall_time_ms: used={latency_ms} limit={int(wall_time_ms)}"
        )
    bytes_in = budget.get("bytes_in")
    if isinstance(bytes_in, (int, float)) and bytes_in > 0:
        used = _estimate_bytes_in(job_spec, inline_content)
        if used > int(bytes_in):
            raise ValueError(
                f"job exceeded budget.bytes_in: used={used} limit={int(bytes_in)}"
            )


def _failure_payload(
    job_spec: Dict[str, Any],
    output: Dict[str, Any] | None,
    metadata: Dict[str, Any],
    error: str,
) -> Dict[str, Any]:
    payload = {
        "job_name": job_spec.get("name"),
        "runtime": job_spec.get("runtime"),
        "state": "failed",
        "url": (job_spec.get("target") or {}).get("url"),
        "extract": {},
        "artifacts": {},
        "artifact_refs": {},
        "output": {
            "path": (output or {}).get("path", ""),
            "format": (output or {}).get("format", ""),
        },
        "error": error,
        "metrics": {"latency_ms": 0},
    }
    anti_bot = _mock_antibot_payload(metadata)
    if anti_bot:
        payload["anti_bot"] = anti_bot
    recovery = _mock_recovery_payload(metadata)
    if recovery:
        payload["recovery"] = recovery
    warnings = _mock_warnings(metadata)
    if warnings:
        payload["warnings"] = warnings
    reverse = _job_reverse_payload(job_spec)
    if reverse:
        payload["reverse"] = reverse
    return payload


def _sink_dir(job_spec: Dict[str, Any], output: Dict[str, Any] | None) -> Path:
    if output and output.get("path"):
        return Path(str(output["path"])).parent / "control-plane"
    return Path("artifacts") / "control-plane"


def _build_graph_artifact(
    job_spec: Dict[str, Any],
    output: Dict[str, Any] | None,
    inline_content: str | None,
    extract: Dict[str, Any],
) -> Dict[str, Any]:
    source = inline_content or ""
    metadata = (
        job_spec.get("metadata") if isinstance(job_spec.get("metadata"), dict) else {}
    )
    if not source:
        for key in ("mock_html", "content"):
            value = metadata.get(key)
            if isinstance(value, str) and value:
                source = value
                break
    if not source:
        title = extract.get("title")
        if isinstance(title, str) and title:
            source = f"<html><head><title>{title}</title></head><body></body></html>"
    if not source:
        return {}

    title = ""
    title_match = re.search(
        r"<title[^>]*>(.*?)</title>", source, flags=re.IGNORECASE | re.DOTALL
    )
    if title_match:
        title = re.sub(r"\s+", " ", title_match.group(1)).strip()
    links = re.findall(r'<a[^>]+href=["\']([^"\']+)["\']', source, flags=re.IGNORECASE)
    images = re.findall(
        r'<img[^>]+src=["\']([^"\']+)["\']', source, flags=re.IGNORECASE
    )

    graph_payload = {
        "root_id": "document",
        "stats": {
            "total_nodes": 1 + (1 if title else 0) + len(links) + len(images),
            "total_edges": len(links) + len(images),
            "node_types": {
                "document": 1,
                "title": 1 if title else 0,
                "link": len(links),
                "image": len(images),
            },
        },
        "title": title,
        "links": links,
        "images": images,
    }
    sink_dir = _sink_dir(job_spec, output)
    graph_dir = sink_dir / "graphs"
    graph_dir.mkdir(parents=True, exist_ok=True)
    job_name = str(job_spec.get("name") or "pyspider-job")
    graph_path = graph_dir / f"{job_name}-graph.json"
    graph_path.write_text(
        json.dumps(graph_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    artifact = {
        "kind": "graph",
        "path": str(graph_path),
        "root_id": graph_payload["root_id"],
        "stats": graph_payload["stats"],
    }
    return {"graph": artifact}


def _persist_runtime_payload(
    job_spec: Dict[str, Any],
    output: Dict[str, Any] | None,
    payload: Dict[str, Any],
    state: str,
) -> None:
    sink_dir = _sink_dir(job_spec, output)
    job_name = str(job_spec.get("name") or "job")
    audit_sink = FileAuditSink(sink_dir / f"{job_name}-audit.jsonl")
    connector_sink = FileResultSink(sink_dir / f"{job_name}-connector.jsonl")
    result_sink = FileResultSink(sink_dir / "results.jsonl")
    audit_sink.emit(
        "job_state",
        {
            "job_name": job_name,
            "runtime": job_spec.get("runtime"),
            "state": state,
            "url": (job_spec.get("target") or {}).get("url"),
        },
    )
    connector_sink.write(
        {
            "job_name": job_name,
            "runtime": job_spec.get("runtime"),
            "state": state,
            "url": (job_spec.get("target") or {}).get("url"),
            "output": output or {},
            "artifact_refs": payload.get("artifact_refs", {}),
            "extract": payload.get("extract", {}),
        }
    )
    result_sink.write(payload)


def _build_result_payload(
    result: Dict[str, Any],
    *,
    job_name: str | None = None,
    runtime: str | None = None,
    output: Dict[str, Any] | None = None,
    metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    printable = {
        "seed": result["seed"],
        "profile": {
            "url": result["profile"].url,
            "page_type": result["profile"].page_type,
            "signals": result["profile"].signals,
            "candidate_fields": result["profile"].candidate_fields,
            "risk_level": result["profile"].risk_level,
        },
        "extract": result["extract"],
    }
    if job_name:
        printable["job_name"] = job_name
    if runtime:
        printable["runtime"] = runtime
        printable["url"] = result["profile"].url
        printable["state"] = "succeeded"
    if output:
        printable["output"] = {
            "path": output.get("path", ""),
            "format": output.get("format", ""),
        }
    if "dataset" in result:
        dataset = result["dataset"]
        printable["dataset"] = {
            "path": dataset.path,
            "format": dataset.output_format,
        }
    anti_bot = _mock_antibot_payload(metadata or {})
    if anti_bot:
        printable["anti_bot"] = anti_bot
    recovery = _mock_recovery_payload(metadata or {})
    if recovery:
        printable["recovery"] = recovery
    warnings = _mock_warnings(metadata or {})
    if warnings:
        printable["warnings"] = warnings
    reverse = _job_reverse_payload(
        {
            "target": {"url": result["profile"].url if runtime else result["seed"]},
            "metadata": metadata or {},
        }
    )
    if reverse:
        printable["reverse"] = reverse
    return printable


def _print_result(
    result: Dict[str, Any],
    *,
    job_name: str | None = None,
    runtime: str | None = None,
    output: Dict[str, Any] | None = None,
    metadata: Dict[str, Any] | None = None,
    latency_ms: int | None = None,
    error: str = "",
) -> None:
    printable = _build_result_payload(
        result, job_name=job_name, runtime=runtime, output=output, metadata=metadata
    )
    if runtime:
        printable["error"] = error
        printable["metrics"] = {"latency_ms": max(latency_ms or 0, 0)}
    print(json.dumps(printable, ensure_ascii=False, indent=2))


def _mock_antibot_payload(metadata: Dict[str, Any]) -> Dict[str, Any]:
    anti_bot = metadata.get("mock_antibot")
    return anti_bot if isinstance(anti_bot, dict) else {}


def _mock_warnings(metadata: Dict[str, Any]) -> list[str]:
    warnings = metadata.get("mock_warnings")
    if isinstance(warnings, list):
        return [str(item) for item in warnings if str(item).strip()]
    return []


def _mock_recovery_payload(metadata: Dict[str, Any]) -> Dict[str, Any]:
    recovery = metadata.get("mock_recovery")
    return recovery if isinstance(recovery, dict) else {}


def _mock_reverse_payload(metadata: Dict[str, Any]) -> Dict[str, Any]:
    reverse = metadata.get("mock_reverse")
    return reverse if isinstance(reverse, dict) else {}


def _job_reverse_payload(
    job_spec: Dict[str, Any], inline_content: str | None = None
) -> Dict[str, Any]:
    metadata = (
        job_spec.get("metadata") if isinstance(job_spec.get("metadata"), dict) else {}
    )
    mocked = _mock_reverse_payload(metadata)
    if mocked:
        return mocked

    reverse_url = str(os.getenv("SPIDER_REVERSE_SERVICE_URL", "")).strip()
    if not reverse_url:
        return {}

    source = inline_content or ""
    if not source:
        for key in ("mock_html", "content"):
            value = metadata.get(key)
            if isinstance(value, str) and value:
                source = value
                break
    if not source:
        target = (
            job_spec.get("target") if isinstance(job_spec.get("target"), dict) else {}
        )
        body = target.get("body")
        if isinstance(body, str) and body:
            source = body
    if not source:
        return {}

    try:
        from pyspider.node_reverse.client import NodeReverseClient

        target = (
            job_spec.get("target") if isinstance(job_spec.get("target"), dict) else {}
        )
        target_url = str(target.get("url", "") or "")
        client = NodeReverseClient(reverse_url)
        return {
            "detect": client.detect_anti_bot(html=source, url=target_url),
            "profile": client.profile_anti_bot(html=source, url=target_url),
            "fingerprint_spoof": client.spoof_fingerprint("chrome", "windows"),
            "tls_fingerprint": client.generate_tls_fingerprint("chrome", "120"),
        }
    except Exception:
        return {}


def _run_legacy_url_mode(
    url: str,
    schema: str,
    content: str | None,
    output_path: str | None,
    output_format: str,
    runtime: str = "http",
) -> int:
    output = {}
    if output_path:
        output = {"path": output_path, "format": output_format}

    job_spec: Dict[str, Any] = {
        "name": "inline-run",
        "runtime": runtime,
        "target": {"url": url},
        "output": output,
        "metadata": {"content": content} if content else {},
    }
    _validate_job_policies(job_spec)
    job = ResearchJob(
        seed_urls=[url],
        extract_schema=json.loads(schema),
        output=output,
    )
    result = _execute_sync_runtime(job_spec, job, content)
    _print_result(result)
    return 0


def _run_job_file(path: str, content: str | None = None) -> int:
    job_spec = json.loads(Path(path).read_text(encoding="utf-8"))
    metadata = job_spec.get("metadata") or {}
    injected_failure = metadata.get("fail_job")
    output = (
        job_spec.get("output") if isinstance(job_spec.get("output"), dict) else None
    )
    if injected_failure:
        failure_payload = _failure_payload(
            job_spec, output, metadata, f"injected failure: {injected_failure}"
        )
        _persist_runtime_payload(job_spec, output, failure_payload, "failed")
        print(json.dumps(failure_payload, ensure_ascii=False, indent=2))
        print(f"injected failure: {injected_failure}", file=sys.stderr)
        return 1
    inline_content = _inline_job_content(job_spec, content)
    try:
        _validate_job_policies(job_spec)
        job = _build_research_job(job_spec)
        _apply_rate_limit(job_spec)
        started = time.perf_counter()
        result = _execute_sync_runtime(job_spec, job, inline_content)
        latency_ms = int((time.perf_counter() - started) * 1000)
        _enforce_job_budget(job_spec, inline_content, latency_ms)
        payload = _build_result_payload(
            result,
            job_name=job_spec.get("name"),
            runtime=job_spec.get("runtime"),
            output=output,
            metadata=metadata,
        ) | {
            "error": "",
            "metrics": {"latency_ms": max(latency_ms, 0)},
            "state": "succeeded",
            "url": result["profile"].url,
        }
        graph_artifacts = _build_graph_artifact(
            job_spec, output, inline_content, result.get("extract") or {}
        )
        if graph_artifacts:
            payload["artifacts"] = graph_artifacts
            payload["artifact_refs"] = graph_artifacts
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        _persist_runtime_payload(job_spec, output, payload, "succeeded")
        return 0
    except Exception as exc:
        payload = _failure_payload(job_spec, output, metadata, str(exc))
        _persist_runtime_payload(job_spec, output, payload, "failed")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        print(str(exc), file=sys.stderr)
        return 1


async def _run_async_job_file(path: str, content: str | None = None) -> int:
    job_spec = json.loads(Path(path).read_text(encoding="utf-8"))
    metadata = job_spec.get("metadata") or {}
    inline_content = _inline_job_content(job_spec, content)
    output = (
        job_spec.get("output") if isinstance(job_spec.get("output"), dict) else None
    )
    try:
        _validate_job_policies(job_spec)
        job = _build_research_job(job_spec)
        _apply_rate_limit(job_spec)
        started = time.perf_counter()
        result = await asyncio.to_thread(
            _execute_sync_runtime, job_spec, job, inline_content
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        _enforce_job_budget(job_spec, inline_content, latency_ms)
        printable = {
            "seed": result["seed"],
            "duration_ms": round(latency_ms, 2),
            "extract": result["extract"],
            "error": "",
        }
        if result.get("profile"):
            profile = result["profile"]
            printable["profile"] = {
                "url": profile.url,
                "page_type": profile.page_type,
                "risk_level": profile.risk_level,
            }
        reverse = _job_reverse_payload(job_spec, inline_content)
        if reverse:
            printable["reverse"] = reverse
        payload = printable | {
            "state": "succeeded",
            "runtime": job_spec.get("runtime"),
            "job_name": job_spec.get("name"),
        }
        graph_artifacts = _build_graph_artifact(
            job_spec, output, inline_content, result.get("extract") or {}
        )
        if graph_artifacts:
            payload["artifacts"] = graph_artifacts
            payload["artifact_refs"] = graph_artifacts
        _persist_runtime_payload(job_spec, output, payload, "succeeded")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        payload = _failure_payload(job_spec, output, metadata, str(exc))
        _persist_runtime_payload(job_spec, output, payload, "failed")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        print(str(exc), file=sys.stderr)
        return 1


def _print_capabilities() -> int:
    payload = {
        "command": "capabilities",
        "framework": "pyspider",
        "runtime": "python",
        "version": __version__,
        "entrypoints": [
            "config",
            "crawl",
            "browser",
            "ai",
            "doctor",
            "preflight",
            "export",
            "curl",
            "web",
            "version",
            "run",
            "job",
            "async-job",
            "workflow",
            "jobdir",
            "http-cache",
            "console",
            "audit",
            "sitemap-discover",
            "plugins",
            "selector-studio",
            "scrapy",
            "profile-site",
            "ultimate",
            "anti-bot",
            "node-reverse",
            "capabilities",
        ],
        "modules": [
            "research.job",
            "runtime.orchestrator",
            "runtime.async_runtime",
            "core.contracts",
            "core.incremental",
            "core.curlconverter",
            "workflow.WorkflowRunner",
            "events.FileEventBus",
            "runtime.audit",
            "connectors.FileConnector",
            "ai_extractor.sentiment_analyzer",
            "ai_extractor.summarizer",
            "ai_extractor.entity_extractor",
            "feature_gates",
            "bridge.crawlee_bridge",
            "profiler.site_profiler",
            "extract.studio",
            "dataset.writer",
            "profiler.site_profiler",
            "advanced.ultimate",
            "antibot.antibot",
            "media.drm_detector",
            "node_reverse.client",
            "node_reverse.fetcher",
            "web.app",
            "api.server",
        ],
        "runtimes": ["http", "browser", "media", "ai"],
        "shared_contracts": [
            "shared-cli",
            "shared-config",
            "runtime-core",
            "autoscaled-frontier",
            "incremental-cache",
            "observability-envelope",
            "scrapy-project",
            "scrapy-plugins-manifest",
            "web-control-plane",
        ],
        "feature_gates": feature_gate_catalog(),
        "ai_capabilities": {
            "providers": ["openai", "anthropic", "claude"],
            "few_shot": True,
            "sentiment_analysis": True,
            "summarization": True,
            "entity_extraction_specialized": True,
        },
        "operator_products": {
            "jobdir": {
                "pause_resume": True,
                "state_file": "job-state.json",
            },
            "http_cache": {
                "status_seed_clear": True,
                "backends": ["file-json", "memory"],
                "strategies": ["revalidate", "delta-fetch"],
            },
            "browser_tooling": {
                "trace": True,
                "har": True,
                "route_mocking": True,
                "codegen": True,
            },
            "autoscaling_pools": {
                "frontier": True,
                "request_queue": "priority-queue",
                "session_pool": True,
                "browser_pool": True,
            },
            "debug_console": {
                "snapshot": True,
                "tail": True,
                "control_plane_jsonl": True,
            },
            "queue_backends": {
                "native": ["redis", "rabbitmq", "kafka"],
            },
            "event_system": {
                "topics": [
                    "task:created",
                    "task:queued",
                    "task:running",
                    "task:succeeded",
                    "task:failed",
                    "task:cancelled",
                    "task:deleted",
                    "task:result",
                    "workflow.job.started",
                    "workflow.step.started",
                    "workflow.step.succeeded",
                    "workflow.job.completed",
                ],
                "pubsub": "in-memory",
                "jsonl_sink": True,
            },
            "connectors": {
                "native": ["memory", "jsonl"],
            },
            "workflow": {
                "step_types": [
                    "goto",
                    "wait",
                    "click",
                    "type",
                    "select",
                    "hover",
                    "scroll",
                    "eval",
                    "listen_network",
                    "extract",
                    "download",
                    "screenshot",
                ],
                "connectors": True,
                "events": True,
            },
            "crawlee_bridge": {
                "client": True,
                "endpoint": "/api/crawl",
            },
        },
        "browser_compatibility": browser_compatibility_matrix(),
        "control_plane": {
            "task_api": True,
            "result_envelope": True,
            "artifact_refs": True,
            "graph_artifact": True,
            "graph_extract": True,
        },
        "kernel_contracts": {
            "request": ["core.models.Request"],
            "fingerprint": ["core.contracts.RequestFingerprint"],
            "frontier": ["core.contracts.AutoscaledFrontier"],
            "scheduler": ["scheduler.Scheduler"],
            "middleware": ["core.contracts.MiddlewareChain"],
            "artifact_store": ["core.contracts.FileArtifactStore"],
            "session_pool": ["core.contracts.SessionPool"],
            "proxy_policy": ["core.contracts.ProxyPolicy"],
            "observability": ["core.contracts.ObservabilityCollector"],
            "cache": ["core.incremental.IncrementalCrawler"],
        },
        "observability": [
            "doctor",
            "profile-site",
            "selector-studio",
            "scrapy doctor",
            "scrapy profile",
            "scrapy bench",
            "prometheus",
            "opentelemetry-json",
        ],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    if not argv:
        print(
            "Usage: python -m pyspider <url> [--schema JSON] or python -m pyspider <command> ...",
            file=sys.stderr,
        )
        return 2

    if argv[0] in FRAMEWORK_CLI_COMMANDS:
        return _delegate_framework_cli(argv)

    if argv[0] not in {"run", "job", "async-job", "capabilities"}:
        parser = argparse.ArgumentParser(description="PySpider X1 research runtime")
        parser.add_argument("url", help="Seed URL")
        parser.add_argument(
            "--schema", default="{}", help="JSON schema/properties payload"
        )
        parser.add_argument(
            "--content", default=None, help="Inline content for offline execution"
        )
        parser.add_argument(
            "--output", default=None, help="Optional dataset output path"
        )
        parser.add_argument("--format", default="jsonl", help="Dataset output format")
        args = parser.parse_args(argv)
        return _run_legacy_url_mode(
            args.url, args.schema, args.content, args.output, args.format
        )

    parser = argparse.ArgumentParser(description="PySpider unified runtime CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_cmd = subparsers.add_parser("run", help="Run inline research job from URL")
    run_cmd.add_argument("url")
    run_cmd.add_argument("--schema", default="{}")
    run_cmd.add_argument("--content", default=None)
    run_cmd.add_argument("--output", default=None)
    run_cmd.add_argument("--format", default="jsonl")
    run_cmd.add_argument("--runtime", default="http", choices=sorted(SUPPORTED_JOB_RUNTIMES))

    job_cmd = subparsers.add_parser("job", help="Run a normalized JobSpec JSON file")
    job_cmd.add_argument("--file", required=True)
    job_cmd.add_argument("--content", default=None)

    async_cmd = subparsers.add_parser(
        "async-job", help="Run a normalized JobSpec JSON file through async runtime"
    )
    async_cmd.add_argument("--file", required=True)
    async_cmd.add_argument("--content", default=None)

    subparsers.add_parser("capabilities", help="Print integrated capabilities")

    args = parser.parse_args(argv)
    if args.command == "run":
        return _run_legacy_url_mode(
            args.url, args.schema, args.content, args.output, args.format, args.runtime
        )
    if args.command == "job":
        return _run_job_file(args.file, args.content)
    if args.command == "async-job":
        return asyncio.run(_run_async_job_file(args.file, args.content))
    return _print_capabilities()


if __name__ == "__main__":
    raise SystemExit(main())
