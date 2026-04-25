"""
Console entrypoint for the packaged pyspider CLI.

`pyspider` 现在首先是框架 CLI；媒体下载命令作为子路由保留。
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import binascii
import contextlib
import hashlib
import hmac
import importlib
import importlib.util
import inspect
import json
import os
import re
import struct
import sys
import time
from io import StringIO
from pathlib import Path
from typing import Any, Sequence

from pyspider.core import sync
import yaml
import requests

VERSION = "1.0.0"

MEDIA_COMMANDS = {
    "download",
    "convert",
    "info",
    "screenshot",
    "merge",
    "parse",
    "drm",
    "artifact",
    "youtube",
}

DEFAULT_CONFIG_CANDIDATES = (
    "spider-framework.yaml",
    "spider-framework.yml",
    "spider-framework.json",
    "config.yaml",
)

SHARED_TOOL_CANDIDATES = (
    Path(__file__).resolve().parents[2] / "tools",
    Path(__file__).resolve().parents[3] / "tools",
)

SCRAPY_ENV_VAR_CANDIDATES = ("PYSPIDER_ENV", "SPIDER_ENV")


def default_contract_config() -> dict:
    return {
        "version": 1,
        "project": {"name": "pyspider-project"},
        "runtime": "python",
        "crawl": {
            "urls": ["https://example.com"],
            "concurrency": 5,
            "max_requests": 100,
            "max_depth": 3,
            "timeout_seconds": 30,
        },
        "sitemap": {
            "enabled": False,
            "url": "https://example.com/sitemap.xml",
            "max_urls": 50,
        },
        "browser": {
            "enabled": True,
            "headless": True,
            "timeout_seconds": 30,
            "user_agent": "",
            "screenshot_path": "artifacts/browser/page.png",
            "html_path": "artifacts/browser/page.html",
        },
        "anti_bot": {
            "enabled": True,
            "profile": "chrome-stealth",
            "proxy_pool": "local",
            "session_mode": "sticky",
            "stealth": True,
            "challenge_policy": "browser",
            "captcha_provider": "2captcha",
            "captcha_api_key": "",
        },
        "node_reverse": {
            "enabled": True,
            "base_url": "http://localhost:3000",
        },
        "middleware": {
            "user_agent_rotation": True,
            "respect_robots_txt": True,
            "min_request_interval_ms": 200,
        },
        "pipeline": {
            "console": True,
            "dataset": True,
            "jsonl_path": "artifacts/exports/results.jsonl",
        },
        "auto_throttle": {
            "enabled": True,
            "start_delay_ms": 200,
            "max_delay_ms": 5000,
            "target_response_time_ms": 2000,
        },
        "frontier": {
            "enabled": True,
            "autoscale": True,
            "min_concurrency": 1,
            "max_concurrency": 16,
            "lease_ttl_seconds": 30,
            "max_inflight_per_domain": 2,
            "checkpoint_id": "runtime-frontier",
            "checkpoint_dir": "artifacts/checkpoints/frontier",
        },
        "observability": {
            "structured_logs": True,
            "metrics": True,
            "trace": True,
            "failure_classification": True,
            "artifact_dir": "artifacts/observability",
        },
        "cache": {
            "enabled": True,
            "store_path": "artifacts/cache/incremental.json",
            "delta_fetch": True,
            "revalidate_seconds": 3600,
        },
        "plugins": {
            "enabled": True,
            "manifest": "contracts/integration-catalog.json",
        },
        "storage": {
            "checkpoint_dir": "artifacts/checkpoints",
            "dataset_dir": "artifacts/datasets",
            "export_dir": "artifacts/exports",
        },
        "export": {
            "format": "json",
            "output_path": "artifacts/exports/results.json",
        },
        "doctor": {
            "network_targets": ["https://example.com"],
        },
    }


def resolve_config_path(config_path: str | None) -> Path | None:
    if config_path:
        path = Path(config_path)
        return path if path.exists() else None
    for candidate in DEFAULT_CONFIG_CANDIDATES:
        path = Path(candidate)
        if path.exists():
            return path
    return None


def resolve_shared_tool(name: str) -> Path:
    if name == "playwright_fetch.py":
        for env_name in ("PYSPIDER_PLAYWRIGHT_HELPER", "SPIDER_PLAYWRIGHT_HELPER"):
            configured = os.getenv(env_name, "").strip()
            if configured:
                return Path(configured)
    for candidate in SHARED_TOOL_CANDIDATES:
        path = candidate / name
        if path.exists():
            return path
    return SHARED_TOOL_CANDIDATES[0] / name


def run_shared_python_tool(name: str, tool_args: list[str]) -> int:
    import subprocess

    completed = subprocess.run(
        [sys.executable, str(resolve_shared_tool(name)), *tool_args],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.stdout:
        print(completed.stdout.rstrip())
    if completed.stderr:
        print(completed.stderr.rstrip(), file=sys.stderr)
    return int(completed.returncode)


def load_contract_config(config_path: str | None) -> dict:
    resolved = resolve_config_path(config_path)
    if config_path and resolved is None:
        raise ValueError(f"config file not found: {config_path}")
    if resolved is None:
        return validate_contract_config(default_contract_config())

    if resolved.suffix.lower() == ".json":
        loaded = json.loads(resolved.read_text(encoding="utf-8"))
    else:
        loaded = yaml.safe_load(resolved.read_text(encoding="utf-8")) or {}
    if not isinstance(loaded, dict):
        raise ValueError("config root must be an object")

    return validate_contract_config(
        merge_contract_config(default_contract_config(), loaded)
    )


def write_contract_config(path: str | None) -> Path:
    target = Path(path or "spider-framework.yaml")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        yaml.safe_dump(default_contract_config(), sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return target


def merge_contract_config(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_contract_config(merged[key], value)
        else:
            merged[key] = value
    return merged


def validate_contract_config(config: dict, expected_runtime: str = "python") -> dict:
    errors: list[str] = []

    version = config.get("version")
    if not isinstance(version, int) or version < 1:
        errors.append("version must be an integer >= 1")

    project = config.get("project")
    if (
        not isinstance(project, dict)
        or not isinstance(project.get("name"), str)
        or not project["name"].strip()
    ):
        errors.append("project.name must be a non-empty string")

    runtime = config.get("runtime")
    if runtime != expected_runtime:
        errors.append(
            f"runtime mismatch: expected {expected_runtime!r}, got {runtime!r}"
        )

    crawl = config.get("crawl")
    if not isinstance(crawl, dict):
        errors.append("crawl must be an object")
    else:
        urls = crawl.get("urls")
        if (
            not isinstance(urls, list)
            or not urls
            or not all(isinstance(url, str) and url.strip() for url in urls)
        ):
            errors.append("crawl.urls must be a non-empty string array")
        _validate_int(errors, crawl, "concurrency", 1, "crawl")
        _validate_int(errors, crawl, "max_requests", 1, "crawl")
        _validate_int(errors, crawl, "max_depth", 0, "crawl")
        _validate_int(errors, crawl, "timeout_seconds", 1, "crawl")

    browser = config.get("browser")
    if not isinstance(browser, dict):
        errors.append("browser must be an object")
    else:
        _validate_bool(errors, browser, "enabled", "browser")
        _validate_bool(errors, browser, "headless", "browser")
        _validate_int(errors, browser, "timeout_seconds", 1, "browser")
        _validate_str(errors, browser, "user_agent", "browser", allow_empty=True)
        _validate_str(errors, browser, "screenshot_path", "browser", allow_empty=False)
        _validate_str(errors, browser, "html_path", "browser", allow_empty=False)

    anti_bot = config.get("anti_bot")
    if anti_bot is not None:
        if not isinstance(anti_bot, dict):
            errors.append("anti_bot must be an object")
        else:
            _validate_bool(errors, anti_bot, "enabled", "anti_bot")
            _validate_str(errors, anti_bot, "profile", "anti_bot", allow_empty=False)
            _validate_str(errors, anti_bot, "proxy_pool", "anti_bot", allow_empty=False)
            _validate_str(
                errors, anti_bot, "session_mode", "anti_bot", allow_empty=False
            )
            _validate_bool(errors, anti_bot, "stealth", "anti_bot")
            _validate_str(
                errors, anti_bot, "challenge_policy", "anti_bot", allow_empty=False
            )
            _validate_str(
                errors, anti_bot, "captcha_provider", "anti_bot", allow_empty=False
            )
            _validate_str(
                errors, anti_bot, "captcha_api_key", "anti_bot", allow_empty=True
            )

    node_reverse = config.get("node_reverse")
    if node_reverse is not None:
        if not isinstance(node_reverse, dict):
            errors.append("node_reverse must be an object")
        else:
            _validate_bool(errors, node_reverse, "enabled", "node_reverse")
            _validate_str(
                errors, node_reverse, "base_url", "node_reverse", allow_empty=False
            )

    storage = config.get("storage")
    if not isinstance(storage, dict):
        errors.append("storage must be an object")
    else:
        _validate_str(errors, storage, "checkpoint_dir", "storage", allow_empty=False)
        _validate_str(errors, storage, "dataset_dir", "storage", allow_empty=False)
        _validate_str(errors, storage, "export_dir", "storage", allow_empty=False)

    export = config.get("export")
    if not isinstance(export, dict):
        errors.append("export must be an object")
    else:
        if export.get("format") not in {"json", "csv", "md"}:
            errors.append("export.format must be one of ['csv', 'json', 'md']")
        _validate_str(errors, export, "output_path", "export", allow_empty=False)

    frontier = config.get("frontier")
    if frontier is not None:
        if not isinstance(frontier, dict):
            errors.append("frontier must be an object")
        else:
            _validate_bool(errors, frontier, "enabled", "frontier")
            _validate_bool(errors, frontier, "autoscale", "frontier")
            _validate_int(errors, frontier, "min_concurrency", 1, "frontier")
            _validate_int(errors, frontier, "max_concurrency", 1, "frontier")
            _validate_int(errors, frontier, "lease_ttl_seconds", 1, "frontier")
            _validate_int(errors, frontier, "max_inflight_per_domain", 1, "frontier")
            _validate_str(
                errors, frontier, "checkpoint_id", "frontier", allow_empty=False
            )
            _validate_str(
                errors, frontier, "checkpoint_dir", "frontier", allow_empty=False
            )

    observability = config.get("observability")
    if observability is not None:
        if not isinstance(observability, dict):
            errors.append("observability must be an object")
        else:
            _validate_bool(errors, observability, "structured_logs", "observability")
            _validate_bool(errors, observability, "metrics", "observability")
            _validate_bool(errors, observability, "trace", "observability")
            _validate_bool(
                errors, observability, "failure_classification", "observability"
            )
            _validate_str(
                errors,
                observability,
                "artifact_dir",
                "observability",
                allow_empty=False,
            )

    cache = config.get("cache")
    if cache is not None:
        if not isinstance(cache, dict):
            errors.append("cache must be an object")
        else:
            _validate_bool(errors, cache, "enabled", "cache")
            _validate_str(errors, cache, "store_path", "cache", allow_empty=False)
            _validate_bool(errors, cache, "delta_fetch", "cache")
            _validate_int(errors, cache, "revalidate_seconds", 1, "cache")

    doctor = config.get("doctor")
    if doctor is not None:
        if not isinstance(doctor, dict):
            errors.append("doctor must be an object")
        else:
            network_targets = doctor.get("network_targets")
            if network_targets is not None and (
                not isinstance(network_targets, list)
                or not all(
                    isinstance(target, str) and target.strip()
                    for target in network_targets
                )
            ):
                errors.append("doctor.network_targets must be a string array")
            redis_url = doctor.get("redis_url")
            if redis_url is not None and not isinstance(redis_url, str):
                errors.append("doctor.redis_url must be a string")

    if errors:
        raise ValueError("; ".join(errors))
    return config


def _validate_int(
    errors: list[str], section: dict, key: str, minimum: int, name: str
) -> None:
    value = section.get(key)
    if not isinstance(value, int) or value < minimum:
        errors.append(f"{name}.{key} must be an integer >= {minimum}")


def _validate_bool(errors: list[str], section: dict, key: str, name: str) -> None:
    if not isinstance(section.get(key), bool):
        errors.append(f"{name}.{key} must be a boolean")


def _validate_str(
    errors: list[str], section: dict, key: str, name: str, allow_empty: bool
) -> None:
    value = section.get(key)
    if not isinstance(value, str):
        errors.append(f"{name}.{key} must be a string")
        return
    if not allow_empty and not value.strip():
        errors.append(f"{name}.{key} must be a non-empty string")


def _resolve_project_config_file(project_root: Path) -> Path | None:
    for candidate in DEFAULT_CONFIG_CANDIDATES:
        path = project_root / candidate
        if path.exists():
            return path
    return None


def _load_project_override(path: Path) -> dict:
    if not path.exists():
        return {}
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"project config must be an object: {path}")
    return data


def load_scrapy_project_config(project_root: Path) -> dict:
    config = default_contract_config()
    config["project"]["name"] = project_root.name or config["project"]["name"]

    base_config_path = _resolve_project_config_file(project_root)
    if base_config_path:
        config = merge_contract_config(config, _load_project_override(base_config_path))

    env_name = next(
        (os.getenv(name) for name in SCRAPY_ENV_VAR_CANDIDATES if os.getenv(name)), None
    )
    if env_name:
        for suffix in ("yaml", "yml", "json"):
            env_path = project_root / f"spider-framework.{env_name}.{suffix}"
            if env_path.exists():
                config = merge_contract_config(config, _load_project_override(env_path))
                break

    return validate_contract_config(config)


def _load_module_from_path(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"unable to load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _project_module_name(project_root: Path, path: Path) -> str:
    relative = path.relative_to(project_root).with_suffix("")
    return "pyspider_project_" + "_".join(relative.parts)


def _discover_spider_files(project_root: Path, manifest: dict) -> list[Path]:
    files: list[Path] = []
    entry = project_root / str(manifest.get("entry") or "scrapy_demo.py")
    if entry.exists():
        files.append(entry)
    spiders_dir = project_root / "spiders"
    if spiders_dir.exists():
        files.extend(
            sorted(
                path for path in spiders_dir.glob("*.py") if path.name != "__init__.py"
            )
        )
    return files


def _discover_spider_classes(project_root: Path, manifest: dict) -> list[dict]:
    from pyspider.spider.spider import Spider as ScrapySpider

    discovered: list[dict] = []
    original_sys_path = list(sys.path)
    sys.path.insert(0, str(project_root))
    try:
        for path in _discover_spider_files(project_root, manifest):
            metadata = _parse_spider_metadata(path)
            module = _load_module_from_path(
                _project_module_name(project_root, path), path
            )
            found_class = False
            for _, obj in inspect.getmembers(module, inspect.isclass):
                if obj is ScrapySpider:
                    continue
                if not issubclass(obj, ScrapySpider):
                    continue
                if obj.__module__ != module.__name__:
                    continue
                found_class = True
                spider_name = str(getattr(obj, "name", "") or path.stem).strip()
                discovered.append(
                    {
                        "name": spider_name,
                        "class_name": obj.__name__,
                        "path": str(path.relative_to(project_root)),
                        "module_name": module.__name__,
                        "class": obj,
                        **metadata,
                    }
                )
            if not found_class:
                spider_name = str(metadata.get("name") or path.stem).strip()
                discovered.append(
                    {
                        "name": spider_name,
                        "class_name": None,
                        "path": str(path.relative_to(project_root)),
                        "module_name": module.__name__,
                        "class": None,
                        **metadata,
                    }
                )
    finally:
        sys.path[:] = original_sys_path

    return discovered


def _attach_resolved_spider_runner(spiders: list[dict], config: dict) -> list[dict]:
    enriched: list[dict] = []
    for spider in spiders:
        clone = dict(spider)
        clone["runner"], clone["runner_source"] = _resolve_scrapy_runner_detail(
            config, clone.get("name"), clone
        )
        clone["url"], clone["url_source"] = _resolve_scrapy_url_detail(
            config, clone.get("name"), clone, ""
        )
        enriched.append(clone)
    return enriched


def _instantiate_spider(spider_class, effective_settings: dict):
    signature = inspect.signature(spider_class)
    params = [param for name, param in signature.parameters.items() if name != "self"]
    if any(
        param.default is inspect._empty
        and param.kind
        not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
        for param in params
    ):
        raise TypeError(
            f"spider class {spider_class.__name__} requires unsupported constructor arguments"
        )

    spider = spider_class()
    spider.settings = merge_contract_config(
        effective_settings, getattr(spider, "custom_settings", {}) or {}
    )
    return spider


def _resolve_component_file(project_root: Path, module_name: str) -> Path | None:
    candidate = project_root / (module_name.replace(".", os.sep) + ".py")
    return candidate if candidate.exists() else None


def _resolve_scrapy_spider_override(config: dict, spider_name: str | None) -> dict:
    if not spider_name:
        return {}
    scrapy_cfg = (
        config.get("scrapy", {}) if isinstance(config.get("scrapy"), dict) else {}
    )
    spiders_cfg = scrapy_cfg.get("spiders")
    if not isinstance(spiders_cfg, dict):
        return {}
    spider_cfg = spiders_cfg.get(spider_name)
    return spider_cfg if isinstance(spider_cfg, dict) else {}


def _resolve_scrapy_runner(
    config: dict, spider_name: str | None, metadata: dict | None = None
) -> str:
    return _resolve_scrapy_runner_detail(config, spider_name, metadata)[0]


def _resolve_scrapy_runner_detail(
    config: dict, spider_name: str | None, metadata: dict | None = None
) -> tuple[str, str]:
    def normalize(value: Any) -> str:
        return str(value).strip().lower() if isinstance(value, str) else ""

    metadata = metadata or {}
    metadata_runner = normalize(metadata.get("runner"))
    if metadata_runner in {"browser", "http", "hybrid"}:
        return metadata_runner, "metadata"

    spider_cfg = _resolve_scrapy_spider_override(config, spider_name)
    spider_runner = normalize(spider_cfg.get("runner"))
    if spider_runner in {"browser", "http", "hybrid"}:
        return spider_runner, "scrapy.spiders"

    scrapy_cfg = (
        config.get("scrapy", {}) if isinstance(config.get("scrapy"), dict) else {}
    )
    project_runner = normalize(scrapy_cfg.get("runner"))
    if project_runner in {"browser", "http", "hybrid"}:
        return project_runner, "scrapy.runner"
    return "http", "default"


def _resolve_scrapy_url_detail(
    config: dict,
    spider_name: str | None,
    metadata: dict | None = None,
    project_url: str | None = None,
) -> tuple[str, str]:
    metadata = metadata or {}
    spider_cfg = _resolve_scrapy_spider_override(config, spider_name)
    override_url = spider_cfg.get("url")
    if isinstance(override_url, str) and override_url.strip():
        return override_url.strip(), "scrapy.spiders"
    metadata_url = metadata.get("url")
    if isinstance(metadata_url, str) and metadata_url.strip():
        return metadata_url.strip(), "metadata"
    if isinstance(project_url, str) and project_url.strip():
        return project_url.strip(), "manifest"
    return "https://example.com", "default"


def _resolve_project_artifact_path(
    project_root: Path | None, value: str | None
) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    path = Path(value)
    if not path.is_absolute() and project_root is not None:
        path = project_root / path
    return str(path)


def _extract_browser_meta(request) -> dict[str, Any]:
    meta = getattr(request, "meta", {}) or {}
    browser_meta = meta.get("browser")
    if isinstance(browser_meta, dict):
        return dict(browser_meta)
    return {}


def _resolve_browser_request_options(request) -> dict[str, Any]:
    meta = getattr(request, "meta", {}) or {}
    browser_meta = _extract_browser_meta(request)

    def value(*keys: str):
        for key in keys:
            if key in browser_meta and browser_meta[key] not in (None, ""):
                return browser_meta[key]
            if key in meta and meta[key] not in (None, ""):
                return meta[key]
        return None

    timeout_value = value("timeout_seconds", "browser_timeout_seconds")
    try:
        timeout_seconds = int(timeout_value) if timeout_value is not None else None
    except (TypeError, ValueError):
        timeout_seconds = None

    return {
        "session": value("session", "browser_session"),
        "storage_state_file": value("storage_state_file", "browser_storage_state_file"),
        "cookies_file": value("cookies_file", "browser_cookies_file"),
        "wait_until": value("wait_until", "browser_wait_until") or "networkidle",
        "wait_for_selector": value("wait_for_selector", "browser_wait_for_selector"),
        "wait_for_load_state": value(
            "wait_for_load_state", "browser_wait_for_load_state"
        ),
        "timeout_seconds": timeout_seconds,
        "screenshot_path": value("screenshot_path", "browser_screenshot_path"),
        "html_path": value("html_path", "browser_html_path"),
    }


def _fetch_browser_response(
    url: str,
    browser_cfg: dict,
    *,
    request=None,
    browser=None,
    close_browser: bool = True,
    wait_until: str = "networkidle",
    wait_for_selector: str | None = None,
    wait_for_load_state: str | None = None,
    timeout_seconds: int | None = None,
    screenshot_path: str | None = None,
    html_path: str | None = None,
    storage_state_file: str | None = None,
    cookies_file: str | None = None,
):
    from pyspider.browser.playwright_browser import PlaywrightBrowser
    from pyspider.core.models import Request, Response

    timeout_ms = int(timeout_seconds or browser_cfg.get("timeout_seconds", 30)) * 1000
    owned_browser = browser is None
    if browser is None:
        browser = PlaywrightBrowser(
            headless=bool(browser_cfg.get("headless", True)),
            timeout=timeout_ms,
            user_agent=(request.headers.get("User-Agent") if request else None)
            or browser_cfg.get("user_agent")
            or None,
            storage_state=storage_state_file,
        )
    started = time.perf_counter()
    try:
        with contextlib.redirect_stdout(StringIO()):
            if hasattr(browser, "set_timeout"):
                browser.set_timeout(timeout_ms)
            else:
                browser.timeout = timeout_ms
            browser.start()
            if cookies_file:
                cookies_path = Path(cookies_file)
                if cookies_path.exists():
                    try:
                        cookies_payload = json.loads(cookies_path.read_text(encoding="utf-8"))
                        if isinstance(cookies_payload, dict):
                            cookies_payload = list(cookies_payload.values())
                        if isinstance(cookies_payload, list):
                            for cookie in cookies_payload:
                                if not isinstance(cookie, dict):
                                    continue
                                name = str(cookie.get("name") or "").strip()
                                value = str(cookie.get("value") or "").strip()
                                domain = str(cookie.get("domain") or "").strip()
                                if name and value and domain:
                                    browser.set_cookie(name, value, domain)
                    except Exception:
                        pass
            browser.navigate(url, wait_until=wait_until)
            if wait_for_selector:
                browser.wait_for_selector(wait_for_selector, timeout=timeout_ms)
            if wait_for_load_state:
                browser.wait_for_load_state(wait_for_load_state)
            html = browser.get_content()
            final_url = browser.get_url()
            if screenshot_path:
                browser.screenshot(screenshot_path)
        if html_path:
            html_target = Path(html_path)
            html_target.parent.mkdir(parents=True, exist_ok=True)
            html_target.write_text(html, encoding="utf-8")
        return Response(
            url=final_url,
            status_code=200,
            headers={"content-type": "text/html"},
            content=html.encode("utf-8"),
            text=html,
            request=request or Request(url=url),
            duration=time.perf_counter() - started,
            error=None,
        )
    finally:
        if request is not None and not close_browser:
            request.meta["_browser_instance"] = browser
        if close_browser and owned_browser:
            with contextlib.redirect_stdout(StringIO()):
                browser.close()


def _collect_reverse_summary(
    base_url: str,
    *,
    html: str,
    url: str,
    status_code: int | None = None,
):
    from pyspider.node_reverse.client import NodeReverseClient

    client = NodeReverseClient(base_url)
    payload = {
        "detect": client.detect_anti_bot(html=html, url=url, status_code=status_code),
        "profile": client.profile_anti_bot(html=html, url=url, status_code=status_code),
        "fingerprint_spoof": client.spoof_fingerprint("chrome", "windows"),
        "tls_fingerprint": client.generate_tls_fingerprint("chrome", "120"),
    }
    script_sample = _extract_script_sample(html)
    if script_sample.strip():
        payload["crypto_analysis"] = client.analyze_crypto(script_sample)
    return payload


def _extract_script_sample(html: str, limit: int = 32000) -> str:
    snippets = re.findall(r"<script[^>]*>(.*?)</script>", html or "", re.IGNORECASE | re.DOTALL)
    joined = "\n".join(snippet.strip() for snippet in snippets if snippet.strip())
    if joined:
        return joined[:limit]
    return (html or "")[:limit]


def _generate_totp(secret: str, digits: int = 6, period: int = 30, now: float | None = None) -> str:
    normalized = "".join(secret.strip().split()).upper()
    if not normalized:
        return ""
    padding = "=" * ((8 - len(normalized) % 8) % 8)
    try:
        key = base64.b32decode(normalized + padding, casefold=True)
    except binascii.Error:
        return ""
    counter = int((now if now is not None else time.time()) // max(period, 1))
    payload = struct.pack(">Q", counter)
    digest = hmac.new(key, payload, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    binary = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(binary % (10 ** max(digits, 1))).zfill(max(digits, 1))


def _resolve_otp_value(action: dict[str, Any]) -> str:
    value = str(action.get("value") or "").strip()
    if value:
        return value
    env_name = str(action.get("otp_env") or "").strip()
    if env_name:
        env_value = os.getenv(env_name, "").strip()
        if env_value:
            return env_value
    secret = str(action.get("totp_secret") or "").strip()
    if not secret:
        secret_env = str(action.get("totp_env") or "SPIDER_AUTH_TOTP_SECRET").strip()
        secret = os.getenv(secret_env, "").strip()
    if not secret:
        return ""
    digits = int(action.get("digits") or 6)
    period = int(action.get("period") or 30)
    return _generate_totp(secret, digits=digits, period=period)


def _resolve_site_challenge_fields(browser, action: dict[str, Any]) -> tuple[str, str, str, str]:
    selector = str(action.get("selector") or "").strip()
    site_key = str(action.get("site_key") or "").strip()
    action_name = str(action.get("captcha_action") or action.get("action") or "").strip()
    c_data = str(action.get("c_data") or "").strip()
    page_data = str(action.get("page_data") or "").strip()
    if not selector:
        return site_key, action_name, c_data, page_data

    locator = browser.page.locator(selector).first
    if not site_key:
        site_key = (
            locator.get_attribute("data-sitekey")
            or locator.get_attribute("sitekey")
            or locator.get_attribute("data-site-key")
            or ""
        )
    if not action_name:
        action_name = locator.get_attribute("data-action") or locator.get_attribute("action") or ""
    if not c_data:
        c_data = locator.get_attribute("data-cdata") or locator.get_attribute("cdata") or ""
    if not page_data:
        page_data = (
            locator.get_attribute("data-pagedata")
            or locator.get_attribute("pagedata")
            or locator.get_attribute("data-page-data")
            or ""
        )
    return site_key, action_name, c_data, page_data


def _default_auth_action_examples() -> list[dict[str, Any]]:
    return [
        {"type": "goto", "url": "https://example.com/login"},
        {"type": "type", "selector": "#username", "value": "demo"},
        {"type": "type", "selector": "#password", "value": "secret"},
        {
            "type": "if",
            "when": {"selector_exists": "#otp"},
            "then": [{"type": "mfa_totp", "selector": "#otp", "totp_env": "SPIDER_AUTH_TOTP_SECRET"}],
        },
        {
            "type": "if",
            "when": {"selector_exists": ".cf-turnstile,[data-sitekey]"},
            "then": [
                {
                    "type": "captcha_solve",
                    "challenge": "turnstile",
                    "selector": ".cf-turnstile,[data-sitekey]",
                    "provider": "anticaptcha",
                    "save_as": "captcha_token",
                }
            ],
        },
        {"type": "submit", "selector": "#password"},
        {"type": "wait_network_idle"},
        {"type": "reverse_profile", "save_as": "reverse_runtime"},
        {"type": "assert", "url_contains": "/dashboard"},
        {"type": "save_as", "value": "url", "save_as": "final_url"},
    ]


class BrowserDownloader:
    def __init__(self, browser_cfg: dict, project_root: Path | None = None):
        self.browser_cfg = dict(browser_cfg or {})
        self.project_root = project_root
        self._default_artifacts_written = False
        self._session_browsers: dict[str, Any] = {}

    def _artifact_path(self, request, key: str, meta_value: str | None) -> str | None:
        if isinstance(meta_value, str) and meta_value.strip():
            return _resolve_project_artifact_path(self.project_root, meta_value)
        if self._default_artifacts_written:
            return None
        return _resolve_project_artifact_path(
            self.project_root, self.browser_cfg.get(key)
        )

    def download(self, request):
        options = _resolve_browser_request_options(request)
        screenshot_path = self._artifact_path(
            request, "screenshot_path", options.get("screenshot_path")
        )
        html_path = self._artifact_path(request, "html_path", options.get("html_path"))
        session_key = options.get("session")
        browser = None
        close_browser = True
        if isinstance(session_key, str) and session_key.strip():
            session_key = session_key.strip()
            browser = self._session_browsers.get(session_key)
            close_browser = False
        fetch_kwargs = {
            "request": request,
            "browser": browser,
            "close_browser": close_browser,
            "wait_until": str(options.get("wait_until") or "networkidle"),
            "wait_for_selector": options.get("wait_for_selector"),
            "wait_for_load_state": options.get("wait_for_load_state"),
            "timeout_seconds": options.get("timeout_seconds"),
            "screenshot_path": screenshot_path,
            "html_path": html_path,
        }
        for option_name in ("storage_state_file", "cookies_file"):
            option_value = options.get(option_name)
            if isinstance(option_value, str) and option_value.strip():
                fetch_kwargs[option_name] = option_value
        response = _fetch_browser_response(
            request.url,
            self.browser_cfg,
            **fetch_kwargs,
        )
        if session_key and browser is None:
            response_browser = (
                response.request.meta.get("_browser_instance")
                if response.request
                else None
            )
            if response_browser is not None:
                self._session_browsers[session_key] = response_browser
        if screenshot_path or html_path:
            self._default_artifacts_written = True
        return response

    def close(self):
        for browser in list(self._session_browsers.values()):
            with contextlib.redirect_stdout(StringIO()):
                browser.close()
        self._session_browsers.clear()


def _resolve_request_runner(request, default_runner: str) -> str:
    def normalize(value: Any) -> str:
        return str(value).strip().lower() if isinstance(value, str) else ""

    meta = getattr(request, "meta", {}) or {}
    browser_meta = _extract_browser_meta(request)
    browser_runner = normalize(browser_meta.get("runner"))
    if browser_runner in {"browser", "http"}:
        return browser_runner
    meta_runner = normalize(meta.get("runner") or meta.get("scrapy_runner"))
    if meta_runner in {"browser", "http"}:
        return meta_runner
    if isinstance(meta.get("browser"), dict):
        return "browser"
    if isinstance(meta.get("browser"), bool):
        return "browser" if meta["browser"] else "http"
    return "http" if default_runner == "hybrid" else default_runner


class HybridDownloader:
    def __init__(
        self,
        browser_cfg: dict,
        project_root: Path | None = None,
        default_runner: str = "http",
    ):
        from pyspider.downloader.downloader import HTTPDownloader

        self.http_downloader = HTTPDownloader()
        self.browser_downloader = BrowserDownloader(
            browser_cfg, project_root=project_root
        )
        self.default_runner = default_runner

    def download(self, request):
        runner = _resolve_request_runner(request, self.default_runner)
        if runner == "browser":
            return self.browser_downloader.download(request)
        return self.http_downloader.download(request)

    def close(self):
        self.browser_downloader.close()
        closer = getattr(self.http_downloader, "close", None)
        if callable(closer):
            closer()


def _load_project_module(project_root: Path, module_name: str):
    file_path = _resolve_component_file(project_root, module_name)
    if file_path:
        return _load_module_from_path(
            _project_module_name(project_root, file_path), file_path
        )
    original_sys_path = list(sys.path)
    sys.path.insert(0, str(project_root))
    try:
        return importlib.import_module(module_name)
    finally:
        sys.path[:] = original_sys_path


def _discover_component_instances(project_root: Path, config: dict):
    from pyspider.spider.spider import (
        DownloaderMiddleware,
        ItemPipeline,
        SpiderMiddleware,
    )

    scrapy_cfg = (
        config.get("scrapy", {}) if isinstance(config.get("scrapy"), dict) else {}
    )

    def from_specs(key: str, base_class, default_modules: list[str]) -> list:
        items = []
        specs = scrapy_cfg.get(key)
        if isinstance(specs, list) and specs:
            for spec in specs:
                if not isinstance(spec, str) or ":" not in spec:
                    continue
                module_name, class_name = spec.split(":", 1)
                module = _load_project_module(project_root, module_name.strip())
                candidate = getattr(module, class_name.strip(), None)
                if inspect.isclass(candidate) and issubclass(candidate, base_class):
                    items.append(candidate())
            return items

        for module_name in default_modules:
            try:
                module = _load_project_module(project_root, module_name)
            except ModuleNotFoundError:
                continue
            for _, candidate in inspect.getmembers(module, inspect.isclass):
                if candidate in {
                    base_class,
                    ItemPipeline,
                    SpiderMiddleware,
                    DownloaderMiddleware,
                }:
                    continue
                if not issubclass(candidate, base_class):
                    continue
                if candidate.__module__ != module.__name__:
                    continue
                items.append(candidate())
        return items

    return {
        "pipelines": from_specs("pipelines", ItemPipeline, ["pipelines"]),
        "spider_middlewares": from_specs(
            "spider_middlewares", SpiderMiddleware, ["middlewares"]
        ),
        "downloader_middlewares": from_specs(
            "downloader_middlewares", DownloaderMiddleware, ["middlewares"]
        ),
    }


def _load_project_plugin_manifest(project_root: Path) -> list[str]:
    manifest_path = project_root / "scrapy-plugins.json"
    if not manifest_path.exists():
        return []
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    validate_scrapy_plugin_manifest(payload, manifest_path)
    if isinstance(payload, dict):
        payload = payload.get("plugins", [])
    names: list[str] = []
    if not isinstance(payload, list):
        return names
    for item in payload:
        if isinstance(item, str) and item.strip():
            names.append(item.strip())
        elif isinstance(item, dict) and item.get("enabled", True):
            name = str(item.get("name") or "").strip()
            if name:
                names.append(name)
    return names


def validate_scrapy_plugin_manifest(payload: Any, manifest_path: Path) -> None:
    if not isinstance(payload, dict):
        raise ValueError(f"plugin manifest must be an object: {manifest_path}")
    plugins = payload.get("plugins")
    if not isinstance(plugins, list):
        raise ValueError(
            f"plugin manifest must contain a plugins array: {manifest_path}"
        )
    version = payload.get("version")
    if version is not None and (not isinstance(version, int) or version < 1):
        raise ValueError(
            f"plugin manifest version must be an integer >= 1: {manifest_path}"
        )
    for item in plugins:
        if isinstance(item, str):
            if not item.strip():
                raise ValueError(
                    f"plugin name must be a non-empty string: {manifest_path}"
                )
            continue
        if not isinstance(item, dict):
            raise ValueError(
                f"plugin entries must be strings or objects: {manifest_path}"
            )
        name = item.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(
                f"plugin object must include a non-empty name: {manifest_path}"
            )
        enabled = item.get("enabled")
        if enabled is not None and not isinstance(enabled, bool):
            raise ValueError(f"plugin enabled must be a boolean: {manifest_path}")
        priority = item.get("priority")
        if priority is not None and not isinstance(priority, int):
            raise ValueError(f"plugin priority must be an integer: {manifest_path}")
        config = item.get("config")
        if config is not None and not isinstance(config, dict):
            raise ValueError(f"plugin config must be an object: {manifest_path}")


def _discover_plugin_instances(project_root: Path, config: dict):
    from pyspider.spider.plugins import (
        create_registered_plugin,
        registered_plugin_names,
    )
    from pyspider.spider.spider import ScrapyPlugin

    scrapy_cfg = (
        config.get("scrapy", {}) if isinstance(config.get("scrapy"), dict) else {}
    )
    specs = scrapy_cfg.get("plugins")
    if not isinstance(specs, list) or not specs:
        specs = _load_project_plugin_manifest(project_root) or ["plugins"]

    plugins = []
    seen: set[tuple[str, str]] = set()

    def collect_from_module(module):
        for _, candidate in inspect.getmembers(module, inspect.isclass):
            if candidate is ScrapyPlugin:
                continue
            if not issubclass(candidate, ScrapyPlugin):
                continue
            if candidate.__module__ != module.__name__:
                continue
            identity = (candidate.__module__, candidate.__name__)
            if identity in seen:
                continue
            seen.add(identity)
            plugins.append(candidate())

    for spec in specs:
        if not isinstance(spec, str) or not spec.strip():
            continue
        try:
            if ":" in spec:
                module_name, class_name = spec.split(":", 1)
                module = _load_project_module(project_root, module_name.strip())
                candidate = getattr(module, class_name.strip(), None)
                if inspect.isclass(candidate) and issubclass(candidate, ScrapyPlugin):
                    identity = (candidate.__module__, candidate.__name__)
                    if identity not in seen:
                        seen.add(identity)
                        plugins.append(candidate())
                continue
            if spec.strip() == "plugins":
                try:
                    _load_project_module(project_root, "plugins")
                except ModuleNotFoundError:
                    continue
                for plugin_name in registered_plugin_names():
                    plugin = create_registered_plugin(plugin_name)
                    if plugin is None:
                        continue
                    identity = (type(plugin).__module__, type(plugin).__name__)
                    if identity not in seen:
                        seen.add(identity)
                        plugins.append(plugin)
                continue
            try:
                _load_project_module(project_root, "plugins")
            except ModuleNotFoundError:
                pass
            registered = create_registered_plugin(spec.strip())
            if registered is not None:
                identity = (type(registered).__module__, type(registered).__name__)
                if identity not in seen:
                    seen.add(identity)
                    plugins.append(registered)
                continue
            module = _load_project_module(project_root, spec.strip())
            collect_from_module(module)
        except ModuleNotFoundError:
            continue
    return plugins


def _normalize_component_instances(items, base_class):
    normalized = []
    for item in items or []:
        candidate = (
            item() if inspect.isclass(item) and issubclass(item, base_class) else item
        )
        if isinstance(candidate, base_class):
            normalized.append(candidate)
    return normalized


def _merge_plugin_components(components: dict, plugins: list):
    from pyspider.spider.spider import (
        DownloaderMiddleware,
        ItemPipeline,
        SpiderMiddleware,
    )

    merged = {
        "pipelines": list(components.get("pipelines", [])),
        "spider_middlewares": list(components.get("spider_middlewares", [])),
        "downloader_middlewares": list(components.get("downloader_middlewares", [])),
    }
    for plugin in plugins:
        merged["pipelines"].extend(
            _normalize_component_instances(plugin.provide_pipelines(), ItemPipeline)
        )
        merged["spider_middlewares"].extend(
            _normalize_component_instances(
                plugin.provide_spider_middlewares(), SpiderMiddleware
            )
        )
        merged["downloader_middlewares"].extend(
            _normalize_component_instances(
                plugin.provide_downloader_middlewares(), DownloaderMiddleware
            )
        )
    return merged


def _parse_spider_metadata(path: Path) -> dict:
    metadata: dict[str, str] = {}
    if not path.exists():
        return metadata
    for line in path.read_text(encoding="utf-8").splitlines()[:8]:
        stripped = line.strip()
        if not stripped.startswith("# scrapy:"):
            continue
        payload = stripped.removeprefix("# scrapy:").strip()
        for part in payload.split():
            if "=" not in part:
                continue
            key, value = part.split("=", 1)
            metadata[key.strip()] = value.strip()
    return metadata


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pyspider",
        description="Python 爬虫框架 CLI",
    )
    subparsers = parser.add_subparsers(dest="command")

    crawl = subparsers.add_parser("crawl", help="真正执行一次页面抓取")
    crawl.add_argument("url", nargs="?", help="目标 URL")
    crawl.add_argument("--config", help="共享配置文件路径")
    crawl.add_argument("-t", "--threads", type=int, default=2, help="工作线程数")
    crawl.add_argument("-m", "--max-pages", type=int, default=1, help="最大抓取页数")
    crawl.add_argument("--timeout", type=int, default=30, help="请求超时（秒）")
    crawl.add_argument("--user-agent", help="覆盖默认 User-Agent")
    crawl.set_defaults(func=cmd_crawl)

    doctor = subparsers.add_parser("doctor", help="检查运行环境依赖")
    doctor.add_argument("--config", help="共享配置文件路径")
    doctor.add_argument("--redis-url", help="验证 Redis 连接")
    doctor.add_argument("--json", action="store_true", help="以 JSON 输出检查结果")
    doctor.set_defaults(func=cmd_doctor)

    preflight = subparsers.add_parser("preflight", help="运行前自检，等价于 doctor")
    preflight.add_argument("--config", help="共享配置文件路径")
    preflight.add_argument("--redis-url", help="验证 Redis 连接")
    preflight.add_argument("--json", action="store_true", help="以 JSON 输出检查结果")
    preflight.set_defaults(func=cmd_doctor)

    media = subparsers.add_parser("media", help="委托给媒体下载 CLI")
    media.add_argument("media_args", nargs=argparse.REMAINDER, help="媒体命令参数")
    media.set_defaults(func=cmd_media)

    web = subparsers.add_parser("web", help="启动 Web UI 或 REST API 服务")
    web.add_argument(
        "--mode", choices=["ui", "api"], default="ui", help="启动 UI 还是 API 服务"
    )
    web.add_argument("--host", default="0.0.0.0", help="监听地址")
    web.add_argument("--port", type=int, default=5000, help="监听端口")
    web.add_argument("--debug", action="store_true", help="启用调试模式")
    web.add_argument("--auth-token", default="", help="API 模式下可选的 Bearer token")
    web.set_defaults(func=cmd_web)

    version = subparsers.add_parser("version", help="显示版本")
    version.set_defaults(func=cmd_version)

    browser = subparsers.add_parser("browser", help="动态页面抓取")
    browser_sub = browser.add_subparsers(dest="browser_command")
    browser_fetch = browser_sub.add_parser("fetch", help="抓取动态页面")
    browser_fetch.add_argument("url", nargs="?", help="目标 URL")
    browser_fetch.add_argument("--config", help="共享配置文件路径")
    browser_fetch.add_argument("--screenshot", help="截图输出路径")
    browser_fetch.add_argument("--html", help="HTML 输出路径")
    browser_fetch.set_defaults(func=cmd_browser_fetch)
    browser_trace = browser_sub.add_parser("trace", help="生成 trace / HAR 工件")
    browser_trace.add_argument("--url", required=True, help="目标 URL")
    browser_trace.add_argument("--trace-path", required=True, help="trace 输出路径")
    browser_trace.add_argument("--har-path", default="", help="HAR 输出路径")
    browser_trace.add_argument("--html", default="", help="HTML 输出路径")
    browser_trace.add_argument("--screenshot", default="", help="截图输出路径")
    browser_trace.set_defaults(func=cmd_browser_tooling)
    browser_mock = browser_sub.add_parser(
        "mock", help="运行带 route mocking 的浏览器抓取"
    )
    browser_mock.add_argument("--url", required=True, help="目标 URL")
    browser_mock.add_argument(
        "--route-manifest", required=True, help="路由 mocking manifest"
    )
    browser_mock.add_argument("--html", default="", help="HTML 输出路径")
    browser_mock.add_argument("--screenshot", default="", help="截图输出路径")
    browser_mock.add_argument("--trace-path", default="", help="trace 输出路径")
    browser_mock.set_defaults(func=cmd_browser_tooling)
    browser_codegen = browser_sub.add_parser(
        "codegen", help="生成 Playwright 脚本与 locator 建议"
    )
    browser_codegen.add_argument("--url", required=True, help="目标 URL")
    browser_codegen.add_argument("--output", required=True, help="生成脚本输出路径")
    browser_codegen.add_argument(
        "--language", choices=["python", "javascript"], default="python"
    )
    browser_codegen.set_defaults(func=cmd_browser_tooling)

    export = subparsers.add_parser("export", help="统一导出接口")
    export.add_argument("--input", required=True, help="输入 JSON 文件")
    export.add_argument("--format", choices=["json", "csv", "md"], help="导出格式")
    export.add_argument("--output", required=True, help="输出文件路径")
    export.set_defaults(func=cmd_export)

    curl = subparsers.add_parser("curl", help="将 curl 命令转换为 Python 代码")
    curl_sub = curl.add_subparsers(dest="curl_command")
    curl_convert = curl_sub.add_parser("convert", help="转换 curl 命令")
    curl_convert.add_argument("--command", "-c", default="", help="curl 命令字符串")
    curl_convert.add_argument(
        "--target",
        choices=["aiohttp", "requests", "python"],
        default="aiohttp",
        help="输出代码风格",
    )
    curl_convert.set_defaults(func=cmd_curl)

    job = subparsers.add_parser("job", help="运行统一 JobSpec JSON 文件")
    job.add_argument("--file", required=True, help="JobSpec JSON 路径")
    job.add_argument("--content", default=None, help="离线注入内容")
    job.set_defaults(func=cmd_job)

    async_job = subparsers.add_parser(
        "async-job", help="通过异步 research runtime 运行 JobSpec"
    )
    async_job.add_argument("--file", required=True, help="JobSpec JSON 路径")
    async_job.add_argument("--content", default=None, help="离线注入内容")
    async_job.set_defaults(func=cmd_async_job)

    workflow = subparsers.add_parser("workflow", help="运行轻量工作流编排")
    workflow_sub = workflow.add_subparsers(dest="workflow_command")
    workflow_run = workflow_sub.add_parser("run", help="执行工作流 JSON")
    workflow_run.add_argument("--file", required=True, help="工作流 JSON 路径")
    workflow_run.set_defaults(func=cmd_workflow)

    capabilities = subparsers.add_parser("capabilities", help="输出聚合能力清单")
    capabilities.set_defaults(func=cmd_capabilities)

    sitemap = subparsers.add_parser("sitemap-discover", help="在抓取前发现 sitemap URL")
    sitemap.add_argument("--url", help="目标站点 URL")
    sitemap.add_argument("--sitemap-file", help="本地 sitemap XML 文件")
    sitemap.set_defaults(func=cmd_sitemap_discover)

    plugins = subparsers.add_parser("plugins", help="查看共享插件/集成清单")
    plugins_sub = plugins.add_subparsers(dest="plugins_command")
    plugins_list = plugins_sub.add_parser("list", help="列出 manifest 中的插件/入口")
    plugins_list.add_argument(
        "--manifest", default="contracts/integration-catalog.json", help="manifest 路径"
    )
    plugins_list.set_defaults(func=cmd_plugins)
    plugins_run = plugins_sub.add_parser("run", help="执行内置插件命令")
    plugins_run.add_argument("--plugin", required=True, help="插件 ID")
    plugins_run.add_argument(
        "--manifest", default="contracts/integration-catalog.json", help="manifest 路径"
    )
    plugins_run.add_argument("plugin_args", nargs=argparse.REMAINDER, help="插件参数")
    plugins_run.set_defaults(func=cmd_plugins)

    selector_studio = subparsers.add_parser(
        "selector-studio", help="调试选择器和抽取表达式"
    )
    selector_studio.add_argument("--url", help="目标 URL")
    selector_studio.add_argument("--html-file", help="本地 HTML 文件路径")
    selector_studio.add_argument(
        "--type", default="css", help="提取模式: css|css_attr|regex"
    )
    selector_studio.add_argument("--expr", required=True, help="选择器或表达式")
    selector_studio.add_argument("--attr", default="", help="css_attr 模式下的属性名")
    selector_studio.set_defaults(func=cmd_selector_studio)

    scrapy_cmd = subparsers.add_parser("scrapy", help="scrapy 风格 authoring 入口")
    scrapy_sub = scrapy_cmd.add_subparsers(dest="scrapy_command")
    scrapy_demo = scrapy_sub.add_parser("demo", help="运行 scrapy 风格 demo")
    scrapy_demo.add_argument("--url", default="https://example.com", help="目标 URL")
    scrapy_demo.add_argument("--html-file", help="本地 HTML 文件路径")
    scrapy_demo.add_argument(
        "--output",
        default="artifacts/exports/pyspider-scrapy-demo.json",
        help="导出文件路径",
    )
    scrapy_demo.set_defaults(func=cmd_scrapy)
    scrapy_run = scrapy_sub.add_parser("run", help="运行 scrapy project")
    scrapy_run.add_argument("--project", required=True, help="project 目录")
    scrapy_run.add_argument("--spider", help="spider 名称")
    scrapy_run.add_argument("--html-file", help="本地 HTML 文件路径")
    scrapy_run.add_argument("--output", help="覆盖导出文件路径")
    scrapy_run.set_defaults(func=cmd_scrapy)
    scrapy_export = scrapy_sub.add_parser("export", help="导出 scrapy project 结果")
    scrapy_export.add_argument("--project", required=True, help="project 目录")
    scrapy_export.add_argument("--spider", help="spider 名称")
    scrapy_export.add_argument(
        "--format", choices=["json", "csv", "md"], default="json", help="导出格式"
    )
    scrapy_export.add_argument("--output", help="输出文件路径")
    scrapy_export.set_defaults(func=cmd_scrapy)
    scrapy_profile = scrapy_sub.add_parser("profile", help="输出 scrapy 页面画像")
    scrapy_profile.add_argument("--project", help="project 目录")
    scrapy_profile.add_argument("--spider", help="spider 名称")
    scrapy_profile.add_argument("--url", help="目标 URL")
    scrapy_profile.add_argument("--html-file", help="本地 HTML 文件路径")
    scrapy_profile.set_defaults(func=cmd_scrapy)
    scrapy_doctor = scrapy_sub.add_parser("doctor", help="检查 scrapy project 健康状态")
    scrapy_doctor.add_argument("--project", required=True, help="project 目录")
    scrapy_doctor.set_defaults(func=cmd_scrapy)
    scrapy_bench = scrapy_sub.add_parser("bench", help="运行 scrapy 轻量基准")
    scrapy_bench.add_argument("--project", help="project 目录")
    scrapy_bench.add_argument("--spider", help="spider 名称")
    scrapy_bench.add_argument("--url", help="目标 URL")
    scrapy_bench.add_argument("--html-file", help="本地 HTML 文件路径")
    scrapy_bench.set_defaults(func=cmd_scrapy)
    scrapy_shell = scrapy_sub.add_parser("shell", help="调试 scrapy selector 表达式")
    scrapy_shell.add_argument("--url", help="目标 URL")
    scrapy_shell.add_argument("--html-file", help="本地 HTML 文件路径")
    scrapy_shell.add_argument(
        "--type", default="css", help="提取模式: css|css_attr|xpath|regex"
    )
    scrapy_shell.add_argument("--expr", required=True, help="选择器或表达式")
    scrapy_shell.add_argument("--attr", default="", help="css_attr 模式下的属性名")
    scrapy_shell.set_defaults(func=cmd_scrapy)
    scrapy_list = scrapy_sub.add_parser("list", help="列出 scrapy project 中的 spider")
    scrapy_list.add_argument("--project", required=True, help="project 目录")
    scrapy_list.set_defaults(func=cmd_scrapy)
    scrapy_validate = scrapy_sub.add_parser("validate", help="校验 scrapy project")
    scrapy_validate.add_argument("--project", required=True, help="project 目录")
    scrapy_validate.set_defaults(func=cmd_scrapy)
    scrapy_plan_ai = scrapy_sub.add_parser("plan-ai", help="生成 AI 爬虫规划和 schema")
    scrapy_plan_ai.add_argument("--project", help="project 目录")
    scrapy_plan_ai.add_argument("--spider", help="现有 spider 名称")
    scrapy_plan_ai.add_argument("--url", help="目标 URL")
    scrapy_plan_ai.add_argument("--html-file", help="本地 HTML 文件路径")
    scrapy_plan_ai.add_argument("--name", default="ai_spider", help="建议的 AI spider 名称")
    scrapy_plan_ai.add_argument("--output", help="规划输出路径")
    scrapy_plan_ai.set_defaults(func=cmd_scrapy)
    scrapy_sync_ai = scrapy_sub.add_parser("sync-ai", help="为已有项目补齐 AI blueprint/schema/prompt")
    scrapy_sync_ai.add_argument("--project", required=True, help="project 目录")
    scrapy_sync_ai.add_argument("--spider", help="现有 spider 名称")
    scrapy_sync_ai.add_argument("--url", help="目标 URL")
    scrapy_sync_ai.add_argument("--html-file", help="本地 HTML 文件路径")
    scrapy_sync_ai.add_argument("--name", default="ai_spider", help="建议的 AI spider 名称")
    scrapy_sync_ai.add_argument("--output", help="规划输出路径")
    scrapy_sync_ai.set_defaults(func=cmd_scrapy)
    scrapy_auth_validate = scrapy_sub.add_parser("auth-validate", help="校验 ai-auth/session 资产是否看起来有效")
    scrapy_auth_validate.add_argument("--project", required=True, help="project 目录")
    scrapy_auth_validate.add_argument("--spider", help="现有 spider 名称")
    scrapy_auth_validate.add_argument("--url", help="目标 URL")
    scrapy_auth_validate.add_argument("--html-file", help="本地 HTML 文件路径")
    scrapy_auth_validate.set_defaults(func=cmd_scrapy)
    scrapy_auth_capture = scrapy_sub.add_parser("auth-capture", help="采集并保存 browser session 资产")
    scrapy_auth_capture.add_argument("--project", required=True, help="project 目录")
    scrapy_auth_capture.add_argument("--spider", help="现有 spider 名称")
    scrapy_auth_capture.add_argument("--url", help="目标 URL")
    scrapy_auth_capture.add_argument("--html-file", help="本地 HTML 文件路径")
    scrapy_auth_capture.add_argument("--session", default="auth", help="session 名称")
    scrapy_auth_capture.set_defaults(func=cmd_scrapy)
    scrapy_scaffold_ai = scrapy_sub.add_parser("scaffold-ai", help="一键生成 AI 规划、schema 和 spider 模板")
    scrapy_scaffold_ai.add_argument("--project", required=True, help="project 目录")
    scrapy_scaffold_ai.add_argument("--spider", help="现有 spider 名称")
    scrapy_scaffold_ai.add_argument("--url", help="目标 URL")
    scrapy_scaffold_ai.add_argument("--html-file", help="本地 HTML 文件路径")
    scrapy_scaffold_ai.add_argument("--name", default="ai_spider", help="生成的 AI spider 名称")
    scrapy_scaffold_ai.add_argument("--output", help="规划输出路径")
    scrapy_scaffold_ai.set_defaults(func=cmd_scrapy)
    scrapy_genspider = scrapy_sub.add_parser("genspider", help="生成新的 spider 模板")
    scrapy_genspider.add_argument("name", help="spider 名称")
    scrapy_genspider.add_argument("domain", help="目标域名")
    scrapy_genspider.add_argument("--project", required=True, help="project 目录")
    scrapy_genspider.add_argument("--ai", action="store_true", help="生成 AI 抽取模板")
    scrapy_genspider.set_defaults(func=cmd_scrapy)
    scrapy_init = scrapy_sub.add_parser("init", help="生成 scrapy project")
    scrapy_init.add_argument("--path", required=True, help="project 目录")
    scrapy_init.set_defaults(func=cmd_scrapy)
    scrapy_contracts = scrapy_sub.add_parser(
        "contracts", help="初始化或校验 spider contracts"
    )
    scrapy_contracts.add_argument("contracts_command", choices=["init", "validate"])
    scrapy_contracts.add_argument("--project", required=True, help="project 目录")
    scrapy_contracts.set_defaults(func=cmd_scrapy)

    profile_site = subparsers.add_parser("profile-site", help="在抓取前对站点做画像")
    profile_site.add_argument("--url", help="目标 URL")
    profile_site.add_argument("--html-file", help="本地 HTML 文件路径")
    profile_site.add_argument(
        "--base-url", default="http://localhost:3000", help="NodeReverse 服务地址"
    )
    profile_site.set_defaults(func=cmd_profile_site)

    ultimate = subparsers.add_parser("ultimate", help="运行高级终极爬虫")
    ultimate.add_argument("urls", nargs="+", help="目标 URL 列表")
    ultimate.add_argument("--config", help="共享配置文件路径")
    ultimate.add_argument(
        "--reverse-service-url", default="", help="NodeReverse 服务地址"
    )
    ultimate.add_argument("--concurrency", type=int, default=3, help="最大并发数")
    ultimate.add_argument(
        "--json", action="store_true", help="仅输出最终 JSON envelope"
    )
    ultimate.add_argument("--quiet", action="store_true", help="抑制进度日志")
    ultimate.set_defaults(func=cmd_ultimate)

    ai_cmd = subparsers.add_parser("ai", help="运行 AI 辅助提取、理解和爬虫配置生成")
    ai_cmd.add_argument("--url", help="目标 URL")
    ai_cmd.add_argument("--html-file", help="本地 HTML 文件路径")
    ai_cmd.add_argument("--config", help="共享配置文件路径")
    ai_cmd.add_argument("--instructions", help="结构化提取指令")
    ai_cmd.add_argument("--schema-file", help="JSON Schema 文件路径")
    ai_cmd.add_argument("--schema-json", help="内联 JSON Schema")
    ai_cmd.add_argument("--question", help="页面理解问题")
    ai_cmd.add_argument("--description", help="自然语言爬虫描述")
    ai_cmd.add_argument("--output", help="可选输出 JSON 文件路径")
    ai_cmd.set_defaults(func=cmd_ai)

    anti_bot = subparsers.add_parser("anti-bot", help="反反爬诊断接口")
    anti_bot_sub = anti_bot.add_subparsers(dest="anti_bot_command")

    anti_bot_headers = anti_bot_sub.add_parser("headers", help="生成反反爬请求头")
    anti_bot_headers.add_argument(
        "--profile", default="default", help="headers 配置: default|cloudflare|akamai"
    )
    anti_bot_headers.set_defaults(func=cmd_anti_bot)

    anti_bot_profile = anti_bot_sub.add_parser(
        "profile", help="本地分析页面的反爬拦截特征"
    )
    anti_bot_profile.add_argument("--url", help="目标 URL")
    anti_bot_profile.add_argument("--html-file", help="本地 HTML 文件路径")
    anti_bot_profile.add_argument(
        "--status-code", type=int, default=200, help="HTTP 状态码"
    )
    anti_bot_profile.set_defaults(func=cmd_anti_bot)

    node_reverse = subparsers.add_parser("node-reverse", help="NodeReverse 诊断接口")
    node_reverse_sub = node_reverse.add_subparsers(dest="node_reverse_command")

    node_reverse_health = node_reverse_sub.add_parser(
        "health", help="检查 NodeReverse 服务"
    )
    node_reverse_health.add_argument(
        "--base-url", default="http://localhost:3000", help="NodeReverse 服务地址"
    )
    node_reverse_health.set_defaults(func=cmd_node_reverse)

    node_reverse_profile = node_reverse_sub.add_parser(
        "profile", help="分析页面反爬画像"
    )
    node_reverse_profile.add_argument(
        "--base-url", default="http://localhost:3000", help="NodeReverse 服务地址"
    )
    node_reverse_profile.add_argument("--url", help="目标 URL")
    node_reverse_profile.add_argument("--html-file", help="本地 HTML 文件路径")
    node_reverse_profile.add_argument(
        "--status-code", type=int, default=0, help="HTTP 状态码"
    )
    node_reverse_profile.set_defaults(func=cmd_node_reverse)

    node_reverse_detect = node_reverse_sub.add_parser("detect", help="检测页面反爬特征")
    node_reverse_detect.add_argument(
        "--base-url", default="http://localhost:3000", help="NodeReverse 服务地址"
    )
    node_reverse_detect.add_argument("--url", help="目标 URL")
    node_reverse_detect.add_argument("--html-file", help="本地 HTML 文件路径")
    node_reverse_detect.add_argument(
        "--status-code", type=int, default=0, help="HTTP 状态码"
    )
    node_reverse_detect.set_defaults(func=cmd_node_reverse)

    node_reverse_spoof = node_reverse_sub.add_parser(
        "fingerprint-spoof", help="生成伪造浏览器指纹"
    )
    node_reverse_spoof.add_argument(
        "--base-url", default="http://localhost:3000", help="NodeReverse 服务地址"
    )
    node_reverse_spoof.add_argument("--browser", default="chrome", help="浏览器类型")
    node_reverse_spoof.add_argument("--platform", default="windows", help="平台类型")
    node_reverse_spoof.set_defaults(func=cmd_node_reverse)

    node_reverse_tls = node_reverse_sub.add_parser(
        "tls-fingerprint", help="生成 TLS 指纹"
    )
    node_reverse_tls.add_argument(
        "--base-url", default="http://localhost:3000", help="NodeReverse 服务地址"
    )
    node_reverse_tls.add_argument("--browser", default="chrome", help="浏览器类型")
    node_reverse_tls.add_argument("--version", default="120", help="浏览器版本")
    node_reverse_tls.set_defaults(func=cmd_node_reverse)

    node_reverse_analyze = node_reverse_sub.add_parser(
        "analyze-crypto", help="分析本地 JS/HTML 中的加密特征"
    )
    node_reverse_analyze.add_argument(
        "--base-url", default="http://localhost:3000", help="NodeReverse 服务地址"
    )
    node_reverse_analyze.add_argument(
        "--code-file", required=True, help="本地代码文件路径"
    )
    node_reverse_analyze.set_defaults(func=cmd_node_reverse)

    node_reverse_canvas = node_reverse_sub.add_parser(
        "canvas-fingerprint", help="生成 Canvas 指纹"
    )
    node_reverse_canvas.add_argument(
        "--base-url", default="http://localhost:3000", help="NodeReverse 服务地址"
    )
    node_reverse_canvas.set_defaults(func=cmd_node_reverse)

    node_reverse_signature = node_reverse_sub.add_parser(
        "signature-reverse", help="逆向本地 JS 文件中的签名逻辑"
    )
    node_reverse_signature.add_argument(
        "--base-url", default="http://localhost:3000", help="NodeReverse 服务地址"
    )
    node_reverse_signature.add_argument(
        "--code-file", required=True, help="本地代码文件路径"
    )
    node_reverse_signature.add_argument(
        "--input-data", required=True, help="样本输入"
    )
    node_reverse_signature.add_argument(
        "--expected-output", required=True, help="期望输出"
    )
    node_reverse_signature.set_defaults(func=cmd_node_reverse)

    node_reverse_ast = node_reverse_sub.add_parser("ast", help="分析本地 JS/HTML 的 AST 特征")
    node_reverse_ast.add_argument(
        "--base-url", default="http://localhost:3000", help="NodeReverse 服务地址"
    )
    node_reverse_ast.add_argument(
        "--code-file", required=True, help="本地代码文件路径"
    )
    node_reverse_ast.add_argument(
        "--analysis",
        default="crypto,obfuscation,anti-debug",
        help="逗号分隔的分析项",
    )
    node_reverse_ast.set_defaults(func=cmd_node_reverse)

    node_reverse_webpack = node_reverse_sub.add_parser(
        "webpack", help="分析本地 Webpack bundle"
    )
    node_reverse_webpack.add_argument(
        "--base-url", default="http://localhost:3000", help="NodeReverse 服务地址"
    )
    node_reverse_webpack.add_argument(
        "--code-file", required=True, help="本地代码文件路径"
    )
    node_reverse_webpack.set_defaults(func=cmd_node_reverse)

    node_reverse_function = node_reverse_sub.add_parser(
        "function-call", help="调用本地 JS 文件中的函数"
    )
    node_reverse_function.add_argument(
        "--base-url", default="http://localhost:3000", help="NodeReverse 服务地址"
    )
    node_reverse_function.add_argument(
        "--code-file", required=True, help="本地代码文件路径"
    )
    node_reverse_function.add_argument(
        "--function-name", required=True, help="目标函数名"
    )
    node_reverse_function.add_argument(
        "--arg", action="append", default=[], help="函数参数，可重复传入"
    )
    node_reverse_function.set_defaults(func=cmd_node_reverse)

    node_reverse_browser = node_reverse_sub.add_parser(
        "browser-simulate", help="模拟浏览器环境执行本地 JS 文件"
    )
    node_reverse_browser.add_argument(
        "--base-url", default="http://localhost:3000", help="NodeReverse 服务地址"
    )
    node_reverse_browser.add_argument(
        "--code-file", required=True, help="本地代码文件路径"
    )
    node_reverse_browser.add_argument(
        "--user-agent",
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        help="浏览器 User-Agent",
    )
    node_reverse_browser.add_argument(
        "--language", default="zh-CN", help="浏览器语言"
    )
    node_reverse_browser.add_argument(
        "--platform", default="Win32", help="浏览器平台"
    )
    node_reverse_browser.set_defaults(func=cmd_node_reverse)

    config = subparsers.add_parser("config", help="共享配置接口")
    config_sub = config.add_subparsers(dest="config_command")
    config_init = config_sub.add_parser("init", help="生成共享配置文件")
    config_init.add_argument("--output", help="输出文件路径")
    config_init.set_defaults(func=cmd_config_init)

    jobdir = subparsers.add_parser("jobdir", help="共享作业目录管理")
    jobdir.add_argument(
        "jobdir_command", choices=["init", "status", "pause", "resume", "clear"]
    )
    jobdir.add_argument("--path", required=True, help="jobdir 路径")
    jobdir.add_argument("--runtime", default="python", help="runtime 名称")
    jobdir.add_argument("--url", action="append", default=[], help="初始化时的 URL")
    jobdir.set_defaults(func=cmd_jobdir)

    http_cache = subparsers.add_parser("http-cache", help="共享 HTTP cache 管理")
    http_cache.add_argument("cache_command", choices=["status", "clear", "seed"])
    http_cache.add_argument("--path", required=True, help="cache store 路径")
    http_cache.add_argument("--url", default="", help="seed 时的 URL")
    http_cache.add_argument("--status-code", type=int, default=200)
    http_cache.add_argument("--etag", default="")
    http_cache.add_argument("--last-modified", default="")
    http_cache.add_argument("--content-hash", default="")
    http_cache.set_defaults(func=cmd_http_cache)

    console = subparsers.add_parser("console", help="共享运行时控制台")
    console.add_argument("console_command", choices=["snapshot", "tail"])
    console.add_argument("--control-plane", default="artifacts/control-plane")
    console.add_argument("--jobdir", default="")
    console.add_argument(
        "--stream", choices=["events", "results", "both"], default="both"
    )
    console.add_argument("--lines", type=int, default=20)
    console.set_defaults(func=cmd_console)

    audit = subparsers.add_parser("audit", help="共享审计控制台")
    audit.add_argument("audit_command", choices=["snapshot", "tail"])
    audit.add_argument("--control-plane", default="artifacts/control-plane")
    audit.add_argument("--job-name", default="")
    audit.add_argument(
        "--stream",
        choices=["events", "results", "audit", "connector", "all"],
        default="all",
    )
    audit.add_argument("--lines", type=int, default=20)
    audit.set_defaults(func=cmd_audit)

    return parser


def cmd_crawl(args: argparse.Namespace) -> int:
    from pyspider.core.spider import Spider
    from pyspider.parser.parser import HTMLParser
    from pyspider.antibot.antibot import AntiBotHandler
    from pyspider.node_reverse.client import NodeReverseClient
    from pyspider.dataset.writer import DatasetWriter

    cfg = load_contract_config(getattr(args, "config", None))
    crawl_cfg = cfg.get("crawl", {})
    sitemap_cfg = cfg.get("sitemap", {})
    anti_bot_cfg = cfg.get("anti_bot", {})
    node_reverse_cfg = cfg.get("node_reverse", {})
    middleware_cfg = cfg.get("middleware", {})
    pipeline_cfg = cfg.get("pipeline", {})
    auto_throttle_cfg = cfg.get("auto_throttle", {})
    target_url = args.url or (crawl_cfg.get("urls") or [None])[0]
    if not target_url:
        print("crawl requires a URL or a config with crawl.urls")
        return 2

    concurrency = max(1, int(crawl_cfg.get("concurrency", args.threads)))
    max_depth = max(1, int(crawl_cfg.get("max_depth", args.max_pages)))
    timeout = int(crawl_cfg.get("timeout_seconds", args.timeout))
    browser_cfg = cfg.get("browser", {})

    targets = [target_url]
    if sitemap_cfg.get("enabled"):
        targets = merge_targets(
            targets, discover_sitemap_targets(target_url, sitemap_cfg)
        )

    spider = Spider(cfg.get("project", {}).get("name", "pyspider-cli"))
    spider.set_start_urls(targets).set_thread_count(concurrency).set_max_pages(
        max_depth
    )
    spider.downloader.set_timeout(timeout)
    user_agent = args.user_agent or browser_cfg.get("user_agent")
    anti_bot = AntiBotHandler()
    if anti_bot_cfg.get("enabled"):
        profile = str(anti_bot_cfg.get("profile", "default")).lower()
        if profile == "cloudflare":
            spider.downloader.set_headers(
                anti_bot.bypass_cloudflare() | anti_bot.get_stealth_headers()
            )
            user_agent = anti_bot.bypass_cloudflare().get("User-Agent") or user_agent
        elif profile == "akamai":
            spider.downloader.set_headers(
                anti_bot.bypass_akamai() | anti_bot.get_stealth_headers()
            )
            user_agent = anti_bot.bypass_akamai().get("User-Agent") or user_agent
        else:
            spider.downloader.set_headers(anti_bot.get_random_headers())
            user_agent = anti_bot.get_random_headers().get("User-Agent") or user_agent
        proxy_pool_value = str(anti_bot_cfg.get("proxy_pool", "local"))
        if proxy_pool_value and proxy_pool_value != "local":
            for proxy in [
                item.strip() for item in proxy_pool_value.split(",") if item.strip()
            ]:
                spider.add_proxy_from_string(proxy)
    if user_agent:
        spider.downloader.set_user_agents([user_agent])
    min_interval_ms = max(
        int(middleware_cfg.get("min_request_interval_ms", 0)),
        (
            int(auto_throttle_cfg.get("start_delay_ms", 0))
            if auto_throttle_cfg.get("enabled")
            else 0
        ),
    )
    if min_interval_ms > 0:
        spider.set_min_request_interval(min_interval_ms / 1000.0)
    spider.set_respect_robots(bool(middleware_cfg.get("respect_robots_txt", True)))
    reverse_client = None
    if node_reverse_cfg.get("enabled"):
        reverse_client = NodeReverseClient(
            node_reverse_cfg.get("base_url") or "http://localhost:3000"
        )
    dataset_rows = []

    def pipeline(page):
        parser = HTMLParser(page.response.text or "")
        title = parser.title() or "<no title>"
        print(f"[{page.response.status_code}] {page.response.url}")
        print(f"title: {title}")
        row = {
            "url": page.response.url,
            "status_code": page.response.status_code,
            "title": title,
            "content_type": page.response.headers.get("Content-Type", ""),
        }
        if reverse_client is not None:
            try:
                profile = reverse_client.profile_anti_bot(
                    html=page.response.text or "",
                    headers={
                        "content-type": page.response.headers.get("Content-Type", "")
                    },
                    status_code=page.response.status_code,
                    url=page.response.url,
                )
                if profile.get("success"):
                    print(
                        f"anti-bot: level={profile.get('level', '')} signals={','.join(profile.get('signals', []))}"
                    )
                    row["anti_bot_level"] = profile.get("level", "")
                    row["anti_bot_signals"] = profile.get("signals", [])
            except Exception:
                pass
        dataset_rows.append(row)

    spider.add_pipeline(pipeline)
    spider.start()

    stats = spider.get_runtime_stats()["stats"]
    if pipeline_cfg.get("dataset") and pipeline_cfg.get("jsonl_path"):
        DatasetWriter().write(
            dataset_rows,
            {"format": "jsonl", "path": str(pipeline_cfg.get("jsonl_path"))},
        )
    return 0 if stats.get("success", 0) > 0 else 1


def cmd_doctor(args: argparse.Namespace) -> int:
    from pyspider.cli.dependencies import (
        dependency_report_to_dict,
        run_dependency_doctor,
    )

    command_name = str(getattr(args, "command", "doctor") or "doctor")
    cfg = load_contract_config(getattr(args, "config", None))
    doctor_cfg = cfg.get("doctor", {})
    redis_url = args.redis_url or doctor_cfg.get("redis_url")
    report = run_dependency_doctor(
        config_path=(
            str(resolve_config_path(getattr(args, "config", None)))
            if resolve_config_path(getattr(args, "config", None))
            else None
        ),
        redis_url=redis_url,
    )
    if args.json:
        payload = dependency_report_to_dict(report)
        payload["command"] = command_name
        payload["framework"] = "pyspider"
        payload["version"] = VERSION
        payload["shared_contracts"] = [
            "shared-cli",
            "shared-config",
            "scrapy-project",
            "scrapy-plugins-manifest",
            "web-control-plane",
        ]
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return report.exit_code

    labels = {
        "ok": "OK",
        "warn": "WARN",
        "fail": "FAIL",
        "skip": "SKIP",
    }
    print(f"pyspider {command_name}")
    print("================")
    for status in report.statuses:
        print(
            f"[{labels.get(status.level, status.level.upper())}] {status.name}: {status.message}"
        )
    print(f"Summary: {report.summary}")
    return report.exit_code


def cmd_media(args: argparse.Namespace) -> int:
    media_args = list(args.media_args)
    if media_args and media_args[0] == "--":
        media_args = media_args[1:]
    return _delegate_to_video_cli(media_args)


def cmd_web(args: argparse.Namespace) -> int:
    if args.mode == "ui":
        from pyspider.web import app as web_app

        web_app.init_db()
        web_app.app.run(
            host=args.host,
            port=args.port,
            debug=args.debug,
            use_reloader=False,
            use_debugger=args.debug,
        )
        return 0

    from pyspider.api.server import SpiderAPI

    api = SpiderAPI(
        host=args.host,
        port=args.port,
        debug=args.debug,
        auth_token=args.auth_token,
    )
    api.app.run(
        host=args.host,
        port=args.port,
        debug=args.debug,
        use_reloader=False,
        use_debugger=args.debug,
        threaded=True,
    )
    return 0


def cmd_version(_: argparse.Namespace) -> int:
    print(f"pyspider {VERSION}")
    return 0


def cmd_config_init(args: argparse.Namespace) -> int:
    target = write_contract_config(getattr(args, "output", None))
    print(f"Wrote shared config: {target}")
    return 0


def cmd_jobdir(args: argparse.Namespace) -> int:
    tool_args = [args.jobdir_command, "--path", args.path]
    if args.jobdir_command == "init":
        tool_args.extend(["--runtime", args.runtime])
        for url in getattr(args, "url", []) or []:
            tool_args.extend(["--url", url])
    return run_shared_python_tool("jobdir_tool.py", tool_args)


def cmd_http_cache(args: argparse.Namespace) -> int:
    tool_args = [args.cache_command, "--path", args.path]
    if args.cache_command == "seed":
        tool_args.extend(["--url", args.url, "--status-code", str(args.status_code)])
        if args.etag:
            tool_args.extend(["--etag", args.etag])
        if args.last_modified:
            tool_args.extend(["--last-modified", args.last_modified])
        if args.content_hash:
            tool_args.extend(["--content-hash", args.content_hash])
    return run_shared_python_tool("http_cache_tool.py", tool_args)


def cmd_console(args: argparse.Namespace) -> int:
    tool_args = [
        args.console_command,
        "--control-plane",
        args.control_plane,
        "--lines",
        str(args.lines),
    ]
    if args.console_command == "snapshot" and args.jobdir:
        tool_args.extend(["--jobdir", args.jobdir])
    if args.console_command == "tail":
        tool_args.extend(["--stream", args.stream])
    return run_shared_python_tool("runtime_console.py", tool_args)


def cmd_audit(args: argparse.Namespace) -> int:
    tool_args = [
        args.audit_command,
        "--control-plane",
        args.control_plane,
        "--job-name",
        args.job_name,
        "--lines",
        str(args.lines),
    ]
    if args.audit_command == "tail":
        tool_args.extend(["--stream", args.stream])
    return run_shared_python_tool("audit_console.py", tool_args)


def cmd_browser_fetch(args: argparse.Namespace) -> int:
    from pyspider.parser.parser import HTMLParser

    cfg = load_contract_config(getattr(args, "config", None))
    browser_cfg = cfg.get("browser", {})
    target_url = args.url or (cfg.get("crawl", {}).get("urls") or [None])[0]
    if not target_url:
        print("browser fetch requires a URL or a config with crawl.urls")
        return 2

    screenshot_path = args.screenshot or browser_cfg.get("screenshot_path")
    html_path = args.html or browser_cfg.get("html_path")
    response = _fetch_browser_response(
        target_url,
        browser_cfg,
        screenshot_path=screenshot_path,
        html_path=html_path,
    )
    print(f"title: {HTMLParser(response.text).title()}")
    print(f"url: {response.url}")
    return 0


def cmd_browser_tooling(args: argparse.Namespace) -> int:
    tool_args = ["--tooling-command", args.browser_command, "--url", args.url]
    if getattr(args, "trace_path", ""):
        tool_args.extend(["--trace-path", args.trace_path])
    if getattr(args, "har_path", ""):
        tool_args.extend(["--har-path", args.har_path])
    if getattr(args, "route_manifest", ""):
        tool_args.extend(["--route-manifest", args.route_manifest])
    if getattr(args, "html", ""):
        tool_args.extend(["--html", args.html])
    if getattr(args, "screenshot", ""):
        tool_args.extend(["--screenshot", args.screenshot])
    if getattr(args, "output", ""):
        tool_args.extend(["--codegen-out", args.output])
    if getattr(args, "language", ""):
        tool_args.extend(["--codegen-language", args.language])
    return run_shared_python_tool("playwright_fetch.py", tool_args)


def cmd_export(args: argparse.Namespace) -> int:
    from pyspider.exporter import Exporter

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"input not found: {input_path}")
        return 2

    raw = json.loads(input_path.read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        items = raw.get("items") or raw.get("data") or []
    else:
        items = raw

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    exporter = Exporter(str(output_path.parent))
    format_name = args.format or output_path.suffix.lstrip(".") or "json"
    filename = output_path.name

    if format_name == "json":
        exporter.export_json(items, filename)
    elif format_name == "csv":
        exporter.export_csv(items, filename)
    elif format_name == "md":
        exporter.export_md(items, filename)
    else:
        print(f"unsupported export format: {format_name}")
        return 2
    print(f"exported: {output_path}")
    return 0


def cmd_curl(args: argparse.Namespace) -> int:
    from pyspider.core.curlconverter import CurlToPythonConverter

    curl_command = str(getattr(args, "command", "") or "").strip()
    if not curl_command:
        print("curl convert requires --command", file=sys.stderr)
        return 2

    converter = CurlToPythonConverter()
    target = str(args.target).lower()
    if target == "aiohttp":
        code = converter.convert_to_aiohttp(curl_command)
    else:
        code = converter.convert_to_requests(curl_command)
        if code.strip().startswith("# 转换失败"):
            code = converter.convert_to_aiohttp(curl_command)
            target = "aiohttp"

    payload = {
        "command": "curl convert",
        "runtime": "python",
        "target": target,
        "curl": curl_command,
        "code": code,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def cmd_job(args: argparse.Namespace) -> int:
    from pyspider import __main__ as runtime_cli

    return runtime_cli._run_job_file(args.file, args.content)


def cmd_async_job(args: argparse.Namespace) -> int:
    from pyspider import __main__ as runtime_cli

    return asyncio.run(runtime_cli._run_async_job_file(args.file, args.content))


def cmd_workflow(args: argparse.Namespace) -> int:
    from pyspider.connectors import FileConnector
    from pyspider.events import FileEventBus
    from pyspider.workflow import FlowJob, WorkflowRunner

    spec_path = Path(args.file)
    payload = json.loads(spec_path.read_text(encoding="utf-8"))
    job = FlowJob.from_mapping(payload)

    control_plane = spec_path.parent / "artifacts" / "control-plane"
    event_path = control_plane / f"{job.name}-workflow-events.jsonl"
    connector_path = control_plane / f"{job.name}-workflow-connector.jsonl"
    runner = WorkflowRunner(
        event_bus=FileEventBus(event_path),
        connectors=[FileConnector(connector_path)],
    )
    result = runner.execute(job)
    print(
        json.dumps(
            {
                "command": "workflow run",
                "runtime": "python",
                "job_id": result.job_id,
                "run_id": result.run_id,
                "extract": result.extracted,
                "artifacts": result.artifacts,
                "events_path": str(event_path),
                "connector_path": str(connector_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def cmd_capabilities(_: argparse.Namespace) -> int:
    from pyspider import __main__ as runtime_cli

    return runtime_cli._print_capabilities()


def cmd_profile_site(args: argparse.Namespace) -> int:
    from pyspider.profiler.site_profiler import SiteProfiler
    from pyspider.node_reverse.client import NodeReverseClient

    url = args.url or ""
    if args.html_file:
        content = Path(args.html_file).read_text(encoding="utf-8")
    elif url:
        content = requests.get(url, timeout=30).text
    else:
        print("profile-site requires --url or --html-file", file=sys.stderr)
        return 2

    profiler = SiteProfiler()
    profile = profiler.profile(url or "", content)
    payload = {
        "command": "profile-site",
        "runtime": "python",
        "framework": "pyspider",
        "version": VERSION,
        **_site_profile_payload(profile),
        "recommended_framework": _recommended_framework_for_profile(profile),
        "recommended_runtime": _recommended_framework_for_profile(profile),
        "anti_bot_recommended": profile.risk_level != "low"
        or bool(profile.signals.get("has_login")),
        "node_reverse_recommended": profile.crawler_type
        in {"hydrated_spa", "api_bootstrap", "ecommerce_search"},
        "reverse": {},
    }
    try:
        client = NodeReverseClient(args.base_url)
        detect_payload = client.detect_anti_bot(html=content, url=url or "")
        reverse_payload = client.profile_anti_bot(html=content, url=url or "")
        spoof_payload = client.spoof_fingerprint("chrome", "windows")
        tls_payload = client.generate_tls_fingerprint("chrome", "120")
        payload["reverse"] = {
            "detect": detect_payload,
            "profile": reverse_payload,
            "fingerprint_spoof": spoof_payload,
            "tls_fingerprint": tls_payload,
            "canvas_fingerprint": client.canvas_fingerprint(),
            "crypto_analysis": client.analyze_crypto(content),
        }
        focus = _reverse_focus_payload(payload["reverse"])
        if focus:
            payload["reverse_focus"] = focus
        if reverse_payload.get("success"):
            payload["anti_bot_level"] = reverse_payload.get("level", "")
            payload["anti_bot_signals"] = reverse_payload.get("signals", [])
            payload["node_reverse_recommended"] = bool(reverse_payload.get("signals"))
    except Exception:
        pass

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _site_profile_payload(profile: Any) -> Dict[str, Any]:
    return {
        "url": profile.url,
        "page_type": profile.page_type,
        "site_family": getattr(profile, "site_family", "generic"),
        "crawler_type": getattr(profile, "crawler_type", "generic_http"),
        "signals": profile.signals,
        "candidate_fields": profile.candidate_fields,
        "risk_level": profile.risk_level,
        "runner_order": list(getattr(profile, "runner_order", []) or []),
        "strategy_hints": list(getattr(profile, "strategy_hints", []) or []),
        "job_templates": list(getattr(profile, "job_templates", []) or []),
    }


def _recommended_framework_for_profile(profile: Any) -> str:
    runner_order = list(getattr(profile, "runner_order", []) or [])
    first_runner = runner_order[0] if runner_order else "http"
    if first_runner == "browser" and profile.risk_level == "high":
        return "java"
    if first_runner == "browser":
        return "python"
    if profile.page_type == "list":
        return "go"
    return "python"


def _reverse_focus_payload(reverse_payload: Dict[str, Any]) -> Dict[str, Any]:
    crypto = reverse_payload.get("crypto_analysis") if isinstance(reverse_payload, dict) else {}
    analysis = crypto.get("analysis") if isinstance(crypto, dict) else {}
    chains = analysis.get("keyFlowChains") if isinstance(analysis, dict) else None
    if not isinstance(chains, list) or not chains:
        return {}
    ranked = sorted(
        [chain for chain in chains if isinstance(chain, dict)],
        key=lambda chain: (
            -float(chain.get("confidence") or 0.0),
            -len(chain.get("sinks") or []),
            -len(chain.get("derivations") or []),
        ),
    )
    if not ranked:
        return {}
    top = ranked[0]
    source = top.get("source") or {}
    source_kind = str(source.get("kind") or "unknown")
    sinks = [str(item) for item in (top.get("sinks") or []) if str(item).strip()]
    primary_sink = sinks[0] if sinks else "unknown-sink"
    next_steps = []
    if source_kind.startswith("storage."):
        next_steps.append("instrument browser storage reads first")
    if source_kind.startswith("network."):
        next_steps.append("capture response body before key derivation")
    if "crypto.subtle." in primary_sink:
        next_steps.append("hook WebCrypto at the sink boundary")
    if primary_sink.startswith("jwt.") or "HMAC" in json.dumps(crypto):
        next_steps.append("rebuild canonical signing input before reproducing the sink")
    if not next_steps:
        next_steps.append("trace the chain from source through derivations into the first sink")
    return {
        "priority_chain": top,
        "summary": f"trace `{top.get('variable')}` from `{source_kind}` into `{primary_sink}`",
        "next_steps": next_steps,
    }


def cmd_sitemap_discover(args: argparse.Namespace) -> int:
    import xml.etree.ElementTree as ET

    if args.sitemap_file:
        content = Path(args.sitemap_file).read_text(encoding="utf-8")
        source = args.sitemap_file
    elif args.url:
        source = args.url.rstrip("/") + "/sitemap.xml"
        content = requests.get(source, timeout=30).text
    else:
        print("sitemap-discover requires --url or --sitemap-file", file=sys.stderr)
        return 2

    urls = []
    try:
        root = ET.fromstring(content)
        for element in root.findall(".//{*}loc"):
            if element.text:
                urls.append(element.text.strip())
    except ET.ParseError:
        urls = []

    payload = {
        "command": "sitemap-discover",
        "runtime": "python",
        "source": source,
        "url_count": len(urls),
        "urls": urls,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def cmd_plugins(args: argparse.Namespace) -> int:
    command = getattr(args, "plugins_command", None)
    if command == "run":
        plugin_id = args.plugin
        plugin_args = list(args.plugin_args)
        if plugin_args and plugin_args[0] == "--":
            plugin_args = plugin_args[1:]
        if plugin_id == "profile-site":
            return cmd_profile_site(
                build_parser().parse_args(["profile-site", *plugin_args])
            )
        if plugin_id == "sitemap-discover":
            return cmd_sitemap_discover(
                build_parser().parse_args(["sitemap-discover", *plugin_args])
            )
        if plugin_id == "selector-studio":
            return cmd_selector_studio(
                build_parser().parse_args(["selector-studio", *plugin_args])
            )
        if plugin_id == "anti-bot":
            return cmd_anti_bot(build_parser().parse_args(["anti-bot", *plugin_args]))
        if plugin_id == "node-reverse":
            return cmd_node_reverse(
                build_parser().parse_args(["node-reverse", *plugin_args])
            )
        print(f"unknown plugin id: {plugin_id}", file=sys.stderr)
        return 2

    if command != "list":
        print("plugins requires a subcommand", file=sys.stderr)
        return 2
    payload = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    result = {
        "command": "plugins list",
        "runtime": "python",
        "manifest": args.manifest,
        "plugins": payload.get("plugins") or payload.get("entrypoints", []),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_selector_studio(args: argparse.Namespace) -> int:
    from pyspider.parser.parser import HTMLParser

    if args.html_file:
        content = Path(args.html_file).read_text(encoding="utf-8")
        source = args.html_file
    elif args.url:
        source = args.url
        content = requests.get(args.url, timeout=30).text
    else:
        print("selector-studio requires --url or --html-file", file=sys.stderr)
        return 2

    parser = HTMLParser(content)
    mode = str(args.type).lower()
    if mode == "css":
        values = parser.css(args.expr)
    elif mode == "css_attr":
        values = parser.css_attr(args.expr, args.attr)
    elif mode == "regex":
        import re

        compiled = re.compile(args.expr, re.DOTALL | re.MULTILINE)
        values = [
            match.group(1) if match.groups() else match.group(0)
            for match in compiled.finditer(content)
        ]
    else:
        values = []

    payload = {
        "command": "selector-studio",
        "runtime": "python",
        "framework": "pyspider",
        "version": VERSION,
        "source": source,
        "type": mode,
        "expr": args.expr,
        "attr": args.attr,
        "count": len(values),
        "values": values,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def cmd_scrapy(args: argparse.Namespace) -> int:
    command = getattr(args, "scrapy_command", None)
    if command not in {
        "demo",
        "run",
        "export",
        "plan-ai",
        "sync-ai",
        "auth-validate",
        "auth-capture",
        "scaffold-ai",
        "profile",
        "doctor",
        "bench",
        "shell",
        "init",
        "list",
        "validate",
        "genspider",
        "contracts",
    }:
        print("scrapy requires a subcommand", file=sys.stderr)
        return 2

    if command == "contracts":
        return run_shared_python_tool(
            "spider_contracts.py",
            [args.contracts_command, "--project", args.project],
        )

    def read_project_manifest(project_root: Path) -> dict:
        manifest_path = project_root / "scrapy-project.json"
        if not manifest_path.exists():
            raise ValueError(f"missing scrapy project manifest: {manifest_path}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("runtime") != "python":
            raise ValueError(f"runtime mismatch in {manifest_path}: expected 'python'")
        return manifest

    def resolve_project_output(
        project_root: Path, manifest: dict, spider_name: str | None
    ) -> Path:
        default_output = str(manifest.get("output") or "artifacts/exports/items.json")
        if spider_name and default_output.endswith("items.json"):
            return project_root / "artifacts" / "exports" / f"{spider_name}.json"
        return project_root / default_output

    if command == "list":
        project_root = Path(args.project)
        try:
            manifest = read_project_manifest(project_root)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        project_cfg = load_contract_config(project_root / "spider-framework.yaml")
        spiders = _attach_resolved_spider_runner(
            _discover_spider_classes(project_root, manifest), project_cfg
        )
        payload = {
            "command": "scrapy list",
            "runtime": "python",
            "project": str(project_root),
            "spiders": [
                {
                    key: value
                    for key, value in spider.items()
                    if key not in {"class", "module_name"}
                }
                for spider in spiders
            ],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if command == "shell":
        from pyspider.parser.parser import HTMLParser

        if args.html_file:
            content = Path(args.html_file).read_text(encoding="utf-8")
            source = args.html_file
        elif args.url:
            source = args.url
            content = requests.get(args.url, timeout=30).text
        else:
            print("scrapy shell requires --url or --html-file", file=sys.stderr)
            return 2

        parser = HTMLParser(content)
        mode = str(args.type).lower()
        if mode == "css":
            values = parser.css(args.expr)
        elif mode == "css_attr":
            values = parser.css_attr(args.expr, args.attr)
        elif mode == "xpath":
            values = parser.xpath(args.expr)
        elif mode == "regex":
            import re

            compiled = re.compile(args.expr, re.DOTALL | re.MULTILINE)
            values = [
                match.group(1) if match.groups() else match.group(0)
                for match in compiled.finditer(content)
            ]
        else:
            values = []

        payload = {
            "command": "scrapy shell",
            "runtime": "python",
            "source": source,
            "type": mode,
            "expr": args.expr,
            "attr": args.attr,
            "count": len(values),
            "values": values,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if command == "export":
        project_root = Path(args.project)
        try:
            manifest = read_project_manifest(project_root)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        selected_spider = getattr(args, "spider", None)
        if selected_spider:
            matches = [
                spider
                for spider in _discover_spider_classes(project_root, manifest)
                if spider["name"] == selected_spider
            ]
            if not matches:
                print(
                    f"unknown spider in {project_root}: {selected_spider}",
                    file=sys.stderr,
                )
                return 2
        from pyspider.exporter import Exporter

        input_path = resolve_project_output(project_root, manifest, selected_spider)
        if not input_path.exists():
            print(f"missing scrapy project output: {input_path}", file=sys.stderr)
            return 2
        raw = json.loads(input_path.read_text(encoding="utf-8"))
        items = raw.get("items") if isinstance(raw, dict) else raw
        output_path = (
            Path(args.output)
            if args.output
            else input_path.with_suffix(f".{args.format}")
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        exporter = Exporter(str(output_path.parent))
        if args.format == "json":
            exporter.export_json(items, output_path.name)
        elif args.format == "csv":
            exporter.export_csv(items, output_path.name)
        else:
            exporter.export_md(items, output_path.name)
        payload = {
            "command": "scrapy export",
            "runtime": "python",
            "project": str(project_root),
            "spider": selected_spider,
            "input": str(input_path),
            "output": str(output_path),
            "format": args.format,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if command == "profile":
        from pyspider.parser.parser import HTMLParser

        selected_spider = getattr(args, "spider", None)
        source = ""
        if args.project:
            project_root = Path(args.project)
            try:
                manifest = read_project_manifest(project_root)
            except ValueError as exc:
                print(str(exc), file=sys.stderr)
                return 2
            if selected_spider:
                matches = [
                    spider
                    for spider in _discover_spider_classes(project_root, manifest)
                    if spider["name"] == selected_spider
                ]
                if not matches:
                    print(
                        f"unknown spider in {project_root}: {selected_spider}",
                        file=sys.stderr,
                    )
                    return 2
                spider_meta = matches[0]
                args.url = spider_meta.get("url") or args.url
            elif not args.url:
                args.url = str(manifest.get("url") or "")

        if args.html_file:
            source = args.html_file
            content = Path(args.html_file).read_text(encoding="utf-8")
        elif args.url:
            source = args.url
            content = requests.get(args.url, timeout=30).text
        else:
            print(
                "scrapy profile requires --project, --url, or --html-file",
                file=sys.stderr,
            )
            return 2

        parser = HTMLParser(content)
        payload = {
            "command": "scrapy profile",
            "runtime": "python",
            "project": str(Path(args.project)) if args.project else None,
            "spider": selected_spider,
            "source": source,
            "title": parser.title(),
            "link_count": len(parser.links()),
            "image_count": len(parser.images()),
            "text_length": len(parser.text()),
            "html_length": len(content),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if command in {"plan-ai", "sync-ai"}:
        from pyspider.profiler.site_profiler import SiteProfiler

        selected_spider = getattr(args, "spider", None)
        source = ""
        resolved_url = args.url or ""
        if args.project:
            project_root = Path(args.project)
            try:
                manifest = read_project_manifest(project_root)
            except ValueError as exc:
                print(str(exc), file=sys.stderr)
                return 2
            if selected_spider:
                matches = [
                    spider
                    for spider in _discover_spider_classes(project_root, manifest)
                    if spider["name"] == selected_spider
                ]
                if not matches:
                    print(
                        f"unknown spider in {project_root}: {selected_spider}",
                        file=sys.stderr,
                    )
                    return 2
                spider_meta = matches[0]
                resolved_url = spider_meta.get("url") or resolved_url
            elif not resolved_url:
                resolved_url = str(manifest.get("url") or "")

        if args.html_file:
            source = args.html_file
            content = Path(args.html_file).read_text(encoding="utf-8")
            if not resolved_url:
                resolved_url = Path(args.html_file).resolve().as_uri()
        elif resolved_url:
            source = resolved_url
            content = requests.get(resolved_url, timeout=30).text
        else:
            print(
                f"scrapy {command} requires --project, --url, or --html-file",
                file=sys.stderr,
            )
            return 2

        profiler = SiteProfiler()
        profile = profiler.profile(resolved_url, content)
        schema = _schema_from_candidate_fields(profile.candidate_fields)
        spider_name = getattr(args, "name", "") or selected_spider or "ai_spider"
        blueprint = _build_ai_blueprint(
            resolved_url,
            spider_name,
            _site_profile_payload(profile),
            schema,
            content,
        )
        payload = {
            "command": f"scrapy {command}",
            "runtime": "python",
            "project": str(Path(args.project)) if args.project else None,
            "spider": selected_spider,
            "spider_name": spider_name,
            "source": source,
            "resolved_url": resolved_url,
            "recommended_runtime": _recommended_framework_for_profile(profile),
            "recommended_framework": _recommended_framework_for_profile(profile),
            "page_profile": _site_profile_payload(profile),
            "schema": schema,
            "blueprint": blueprint,
            "suggested_commands": [
                f"python -m pyspider scrapy genspider {spider_name} {resolved_url.split('/')[2] if '://' in resolved_url else 'example.com'} --project {args.project or '.'} --ai",
                f'python -m pyspider ai --url {resolved_url} --instructions "提取核心字段" --schema-file ai-schema.json',
            ],
            "written_files": [],
        }

        if args.project:
            project_root = Path(args.project)
            schema_path = project_root / "ai-schema.json"
            blueprint_path = project_root / "ai-blueprint.json"
            prompt_path = project_root / "ai-extract-prompt.txt"
            auth_path = project_root / "ai-auth.json"
            plan_path = Path(args.output) if args.output else project_root / "ai-plan.json"
            schema_path.write_text(
                json.dumps(schema, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            blueprint_path.write_text(
                json.dumps(blueprint, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            prompt_path.write_text(
                blueprint["extraction_prompt"] + "\n",
                encoding="utf-8",
            )
            auth_path.write_text(
                json.dumps(
                    {
                        "headers": {},
                        "cookies": {},
                        "storage_state_file": "",
                        "cookies_file": "",
                        "session": "auth",
                        "actions": [],
                        "action_examples": _default_auth_action_examples(),
                        "node_reverse_base_url": "http://localhost:3000",
                        "capture_reverse_profile": False,
                        "notes": "Fill session headers/cookies here when authentication is required.",
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            payload["written_files"] = [str(schema_path), str(blueprint_path), str(prompt_path), str(auth_path), str(plan_path)]
            plan_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        elif args.output:
            plan_path = Path(args.output)
            plan_path.parent.mkdir(parents=True, exist_ok=True)
            payload["written_files"] = [str(plan_path)]
            plan_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

        if command == "sync-ai" and args.project:
            project_root = Path(args.project)
            ai_job_path = project_root / "ai-job.json"
            ai_job_payload = {
                "name": f"{spider_name}-ai-job",
                "runtime": "ai",
                "target": {"url": resolved_url},
                "extract": [{"field": field, "type": "ai"} for field in schema.get("properties", {}).keys()],
                "output": {
                    "format": "json",
                    "path": "artifacts/exports/ai-job-output.json",
                },
                "metadata": {
                    "schema_file": "ai-schema.json",
                },
            }
            ai_job_path.write_text(
                json.dumps(ai_job_payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            payload["written_files"] = [*payload.get("written_files", []), str(ai_job_path)]

        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if command == "auth-validate":
        from pyspider.spider.spider import (
            ai_start_request_meta,
            apply_ai_request_strategy,
            load_ai_project_assets,
        )

        project_root = Path(args.project)
        try:
            manifest = read_project_manifest(project_root)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2

        selected_spider = getattr(args, "spider", None)
        resolved_url = args.url or ""
        if selected_spider:
            matches = [
                spider
                for spider in _discover_spider_classes(project_root, manifest)
                if spider["name"] == selected_spider
            ]
            if not matches:
                print(
                    f"unknown spider in {project_root}: {selected_spider}",
                    file=sys.stderr,
                )
                return 2
            resolved_url = matches[0].get("url") or resolved_url
        elif not resolved_url:
            resolved_url = str(manifest.get("url") or "")

        assets = load_ai_project_assets(project_root)
        if args.html_file:
            source = args.html_file
            html = Path(args.html_file).read_text(encoding="utf-8")
            if not resolved_url:
                resolved_url = Path(args.html_file).resolve().as_uri()
            runner_used = "fixture"
        elif resolved_url:
            source = resolved_url
            from pyspider.core.models import Request

            request = apply_ai_request_strategy(
                Request(url=resolved_url, callback=None, meta=ai_start_request_meta(assets)),
                assets,
            )
            response = _fetch_browser_response(
                resolved_url,
                load_contract_config(str(project_root / "spider-framework.yaml")).get("browser", {}),
                request=request,
                storage_state_file=(assets.get("browser_meta") or {}).get("storage_state_file"),
                cookies_file=(assets.get("browser_meta") or {}).get("cookies_file"),
            )
            html = response.text
            runner_used = "browser" if request.meta.get("runner") == "browser" else "http"
        else:
            print("scrapy auth-validate requires --project plus --url, manifest url, or --html-file", file=sys.stderr)
            return 2

        authenticated, indicators = _auth_validation_status(html)
        payload = {
            "command": "scrapy auth-validate",
            "runtime": "python",
            "project": str(project_root),
            "spider": selected_spider,
            "source": source,
            "resolved_url": resolved_url,
            "authentication_required": bool((assets.get("blueprint") or {}).get("authentication", {}).get("required")),
            "recommended_runner": assets.get("recommended_runner"),
            "runner_used": runner_used,
            "authenticated": authenticated,
            "indicators": indicators,
            "auth_assets": {
                "has_headers": bool(assets.get("request_headers")),
                "has_cookies": bool(assets.get("request_cookies")),
                "storage_state_file": (assets.get("browser_meta") or {}).get("storage_state_file", ""),
                "cookies_file": (assets.get("browser_meta") or {}).get("cookies_file", ""),
            },
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if command == "auth-capture":
        from pyspider.browser.playwright_browser import PlaywrightBrowser
        from pyspider.node_reverse.client import NodeReverseClient
        from pyspider.spider.spider import load_ai_project_assets

        project_root = Path(args.project)
        try:
            manifest = read_project_manifest(project_root)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2

        selected_spider = getattr(args, "spider", None)
        resolved_url = args.url or ""
        if selected_spider:
            matches = [
                spider
                for spider in _discover_spider_classes(project_root, manifest)
                if spider["name"] == selected_spider
            ]
            if not matches:
                print(
                    f"unknown spider in {project_root}: {selected_spider}",
                    file=sys.stderr,
                )
                return 2
            resolved_url = matches[0].get("url") or resolved_url
        elif not resolved_url:
            resolved_url = str(manifest.get("url") or "")

        if args.html_file:
            source = args.html_file
            resolved_url = Path(args.html_file).resolve().as_uri()
        elif resolved_url:
            source = resolved_url
        else:
            print(
                "scrapy auth-capture requires --project plus --url, manifest url, or --html-file",
                file=sys.stderr,
            )
            return 2

        assets = load_ai_project_assets(project_root)
        try:
            browser_cfg = load_contract_config(project_root / "spider-framework.yaml").get(
                "browser", {}
            )
        except Exception:
            browser_cfg = default_contract_config().get("browser", {})
        auth_path = project_root / "ai-auth.json"
        auth_payload = (
            json.loads(auth_path.read_text(encoding="utf-8"))
            if auth_path.exists()
            else {
                "headers": {},
                "cookies": {},
                "storage_state_file": "",
                "cookies_file": "",
                "session": args.session,
                "actions": [],
                "notes": "Fill session headers/cookies here when authentication is required.",
            }
        )
        state_rel = auth_payload.get("storage_state_file") or f"artifacts/auth/{args.session}-state.json"
        cookies_rel = auth_payload.get("cookies_file") or f"artifacts/auth/{args.session}-cookies.json"
        state_path = (project_root / state_rel).resolve()
        cookies_path = (project_root / cookies_rel).resolve()
        existing_state = state_path if state_path.exists() else None
        existing_cookies = cookies_path if cookies_path.exists() else None

        browser = PlaywrightBrowser(
            headless=bool(browser_cfg.get("headless", True)),
            timeout=int(browser_cfg.get("timeout_seconds", 30)) * 1000,
            user_agent=browser_cfg.get("user_agent") or None,
            storage_state=str(existing_state) if existing_state else None,
        )
        warnings: list[str] = []
        captures: dict[str, Any] = {}
        try:
            browser.start()
            if existing_cookies:
                browser.load_cookies_file(str(existing_cookies))
            browser.navigate(resolved_url)
            _run_auth_actions(
                browser,
                list(auth_payload.get("actions") or []),
                warnings,
                captures,
            )
            browser.save_storage_state(str(state_path))
            browser.save_cookies(str(cookies_path))
            if hasattr(browser, "get_content"):
                final_html = browser.get_content()
            elif args.html_file:
                final_html = Path(args.html_file).read_text(encoding="utf-8")
            else:
                final_html = ""
            final_url = browser.get_url() if hasattr(browser, "get_url") else resolved_url
        finally:
            with contextlib.redirect_stdout(StringIO()):
                browser.close()

        auth_payload["storage_state_file"] = os.path.relpath(state_path, project_root)
        auth_payload["cookies_file"] = os.path.relpath(cookies_path, project_root)
        auth_payload["session"] = args.session
        auth_payload.setdefault(
            "action_examples",
            _default_auth_action_examples(),
        )
        if captures:
            auth_payload["captures"] = captures
        reverse_url = str(auth_payload.get("node_reverse_base_url") or "").strip()
        if bool(auth_payload.get("capture_reverse_profile")) and reverse_url:
            try:
                client = NodeReverseClient(reverse_url)
                auth_payload["reverse_runtime"] = {
                    "detect": client.detect_anti_bot(html=final_html, url=final_url),
                    "profile": client.profile_anti_bot(html=final_html, url=final_url),
                }
                fingerprint_spoof = getattr(client, "spoof_fingerprint", None)
                if callable(fingerprint_spoof):
                    auth_payload["reverse_runtime"]["fingerprint_spoof"] = fingerprint_spoof("chrome", "windows")
                tls_fingerprint = getattr(client, "generate_tls_fingerprint", None)
                if callable(tls_fingerprint):
                    auth_payload["reverse_runtime"]["tls_fingerprint"] = tls_fingerprint("chrome", "120")
                script_sample = _extract_script_sample(final_html)
                analyze_crypto = getattr(client, "analyze_crypto", None)
                if script_sample.strip() and callable(analyze_crypto):
                    auth_payload["reverse_runtime"]["crypto_analysis"] = analyze_crypto(script_sample)
            except Exception as exc:
                warnings.append(f"reverse capture failed: {exc}")
        auth_path.write_text(
            json.dumps(auth_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        payload = {
            "command": "scrapy auth-capture",
            "runtime": "python",
            "project": str(project_root),
            "spider": selected_spider,
            "source": source,
            "resolved_url": resolved_url,
            "recommended_runner": assets.get("recommended_runner"),
            "captures": captures,
            "warnings": warnings,
            "written_files": [
                str(auth_path),
                str(state_path),
                str(cookies_path),
            ],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if command == "scaffold-ai":
        from pyspider.profiler.site_profiler import SiteProfiler

        project_root = Path(args.project)
        try:
            manifest = read_project_manifest(project_root)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2

        selected_spider = getattr(args, "spider", None)
        resolved_url = args.url or ""
        if selected_spider:
            matches = [
                spider
                for spider in _discover_spider_classes(project_root, manifest)
                if spider["name"] == selected_spider
            ]
            if not matches:
                print(
                    f"unknown spider in {project_root}: {selected_spider}",
                    file=sys.stderr,
                )
                return 2
            resolved_url = matches[0].get("url") or resolved_url
        elif not resolved_url:
            resolved_url = str(manifest.get("url") or "")

        if args.html_file:
            source = args.html_file
            content = Path(args.html_file).read_text(encoding="utf-8")
            if not resolved_url:
                resolved_url = Path(args.html_file).resolve().as_uri()
        elif resolved_url:
            source = resolved_url
            content = requests.get(resolved_url, timeout=30).text
        else:
            print(
                "scrapy scaffold-ai requires --project plus --url, manifest url, or --html-file",
                file=sys.stderr,
            )
            return 2

        profiler = SiteProfiler()
        profile = profiler.profile(resolved_url, content)
        schema = _schema_from_candidate_fields(profile.candidate_fields)
        spider_name = getattr(args, "name", "") or "ai_spider"
        domain = _derive_domain(resolved_url)
        spiders_dir = project_root / "spiders"
        spiders_dir.mkdir(parents=True, exist_ok=True)
        spider_path = spiders_dir / f"{spider_name}.py"
        spider_path.write_text(
            _render_py_ai_spider_module(spider_name, domain),
            encoding="utf-8",
        )
        schema_path = project_root / "ai-schema.json"
        schema_path.write_text(
            json.dumps(schema, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        blueprint = _build_ai_blueprint(
            resolved_url,
            spider_name,
            _site_profile_payload(profile),
            schema,
            content,
        )
        blueprint_path = project_root / "ai-blueprint.json"
        blueprint_path.write_text(
            json.dumps(blueprint, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        prompt_path = project_root / "ai-extract-prompt.txt"
        prompt_path.write_text(
            blueprint["extraction_prompt"] + "\n",
            encoding="utf-8",
        )
        auth_path = project_root / "ai-auth.json"
        auth_path.write_text(
            json.dumps(
                {
                    "headers": {},
                    "cookies": {},
                    "storage_state_file": "",
                    "cookies_file": "",
                    "session": "auth",
                    "actions": [],
                    "action_examples": _default_auth_action_examples(),
                    "node_reverse_base_url": "http://localhost:3000",
                    "capture_reverse_profile": False,
                    "notes": "Fill session headers/cookies here when authentication is required.",
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        payload = {
            "command": "scrapy scaffold-ai",
            "runtime": "python",
            "project": str(project_root),
            "spider": selected_spider,
            "spider_name": spider_name,
            "source": source,
            "resolved_url": resolved_url,
            "recommended_runtime": _recommended_framework_for_profile(profile),
            "recommended_framework": _recommended_framework_for_profile(profile),
            "page_profile": _site_profile_payload(profile),
            "schema": schema,
            "blueprint": blueprint,
            "written_files": [],
            "suggested_commands": [
                f"python -m pyspider scrapy run --project {project_root} --spider {spider_name}",
                f'python -m pyspider ai --url {resolved_url} --instructions "提取核心字段" --schema-file ai-schema.json',
            ],
        }
        plan_path = Path(args.output) if args.output else project_root / "ai-plan.json"
        payload["written_files"] = [str(schema_path), str(blueprint_path), str(prompt_path), str(auth_path), str(plan_path), str(spider_path)]
        plan_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if command == "doctor":
        project_root = Path(args.project)
        checks = []
        manifest_path = project_root / "scrapy-project.json"
        checks.append(
            {
                "name": "manifest",
                "status": "passed" if manifest_path.exists() else "failed",
                "details": str(manifest_path),
            }
        )
        manifest = None
        if manifest_path.exists():
            try:
                manifest = read_project_manifest(project_root)
                checks.append(
                    {"name": "runtime", "status": "passed", "details": "python"}
                )
            except ValueError as exc:
                checks.append(
                    {"name": "runtime", "status": "failed", "details": str(exc)}
                )

        spiders = []
        if manifest:
            try:
                project_cfg = load_scrapy_project_config(project_root)
                spiders = _attach_resolved_spider_runner(
                    _discover_spider_classes(project_root, manifest), project_cfg
                )
            except Exception as exc:
                checks.append(
                    {"name": "spider_loader", "status": "failed", "details": str(exc)}
                )
            if spiders:
                checks.append(
                    {
                        "name": "spider_loader",
                        "status": "passed",
                        "details": f"{len(spiders)} spiders discovered",
                    }
                )
                for spider in spiders:
                    checks.append(
                        {
                            "name": f"spider:{spider['name']}",
                            "status": "passed",
                            "details": f"{spider['path']} runner={spider.get('runner', 'http')} runner_source={spider.get('runner_source', 'default')} url={spider.get('url', '')} url_source={spider.get('url_source', 'default')}",
                        }
                    )
            else:
                checks.append(
                    {
                        "name": "spider_loader",
                        "status": "warning",
                        "details": "no spider classes discovered",
                    }
                )

        config_path = project_root / "spider-framework.yaml"
        checks.append(
            {
                "name": "config",
                "status": "passed" if config_path.exists() else "warning",
                "details": str(config_path),
            }
        )
        exports_dir = project_root / "artifacts" / "exports"
        checks.append(
            {
                "name": "exports_dir",
                "status": "passed" if exports_dir.exists() else "warning",
                "details": str(exports_dir),
            }
        )
        spiders_dir = project_root / "spiders"
        checks.append(
            {
                "name": "spiders_dir",
                "status": "passed" if spiders_dir.exists() else "warning",
                "details": str(spiders_dir),
            }
        )
        summary = "passed"
        if any(check["status"] == "failed" for check in checks):
            summary = "failed"
        elif any(check["status"] == "warning" for check in checks):
            summary = "warning"
        payload = {
            "command": "scrapy doctor",
            "runtime": "python",
            "project": str(project_root),
            "summary": summary,
            "checks": checks,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if summary != "failed" else 1

    if command == "bench":
        from pyspider.parser.parser import HTMLParser
        import time

        selected_spider = getattr(args, "spider", None)
        source = ""
        if args.project:
            project_root = Path(args.project)
            try:
                manifest = read_project_manifest(project_root)
            except ValueError as exc:
                print(str(exc), file=sys.stderr)
                return 2
            if selected_spider:
                matches = [
                    spider
                    for spider in _discover_spider_classes(project_root, manifest)
                    if spider["name"] == selected_spider
                ]
                if not matches:
                    print(
                        f"unknown spider in {project_root}: {selected_spider}",
                        file=sys.stderr,
                    )
                    return 2
                spider_meta = matches[0]
                args.url = spider_meta.get("url") or args.url
            elif not args.url:
                args.url = str(manifest.get("url") or "")

        if args.html_file:
            source = args.html_file
            content = Path(args.html_file).read_text(encoding="utf-8")
        elif args.url:
            source = args.url
            started_fetch = time.perf_counter()
            content = requests.get(args.url, timeout=30).text
            fetch_ms = round((time.perf_counter() - started_fetch) * 1000, 2)
        else:
            print(
                "scrapy bench requires --project, --url, or --html-file",
                file=sys.stderr,
            )
            return 2

        started = time.perf_counter()
        parser = HTMLParser(content)
        title = parser.title()
        links = parser.links()
        images = parser.images()
        text_length = len(parser.text())
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)

        payload = {
            "command": "scrapy bench",
            "runtime": "python",
            "project": str(Path(args.project)) if args.project else None,
            "spider": selected_spider,
            "source": source,
            "elapsed_ms": elapsed_ms,
            "fetch_ms": locals().get("fetch_ms"),
            "title": title,
            "link_count": len(links),
            "image_count": len(images),
            "text_length": text_length,
            "html_length": len(content),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if command == "validate":
        project_root = Path(args.project)
        checks = []
        manifest_path = project_root / "scrapy-project.json"
        checks.append(
            {
                "name": "manifest",
                "status": "passed" if manifest_path.exists() else "failed",
                "details": str(manifest_path),
            }
        )
        manifest = None
        if manifest_path.exists():
            try:
                manifest = read_project_manifest(project_root)
                checks.append(
                    {"name": "runtime", "status": "passed", "details": "python"}
                )
            except ValueError as exc:
                checks.append(
                    {"name": "runtime", "status": "failed", "details": str(exc)}
                )
        if manifest:
            entry = project_root / str(manifest.get("entry") or "scrapy_demo.py")
            checks.append(
                {
                    "name": "entry",
                    "status": "passed" if entry.exists() else "failed",
                    "details": str(entry),
                }
            )
            try:
                project_cfg = load_contract_config(
                    project_root / "spider-framework.yaml"
                )
                spiders = _attach_resolved_spider_runner(
                    _discover_spider_classes(project_root, manifest), project_cfg
                )
            except Exception as exc:
                checks.append(
                    {
                        "name": "spider-discovery",
                        "status": "failed",
                        "details": str(exc),
                    }
                )
                spiders = []
            for spider in spiders:
                checks.append(
                    {
                        "name": f"spider:{spider['name']}",
                        "status": "passed",
                        "details": f"{spider['class_name']} @ {spider['path']} runner={spider.get('runner', 'http')} runner_source={spider.get('runner_source', 'default')} url={spider.get('url', '')} url_source={spider.get('url_source', 'default')}",
                    }
                )
        config_path = project_root / "spider-framework.yaml"
        checks.append(
            {
                "name": "config",
                "status": "passed" if config_path.exists() else "warning",
                "details": str(config_path),
            }
        )
        summary = (
            "passed"
            if all(
                check["status"] == "passed"
                for check in checks
                if check["name"] != "config"
            )
            else "failed"
        )
        payload = {
            "command": "scrapy validate",
            "runtime": "python",
            "project": str(project_root),
            "summary": summary,
            "checks": checks,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if summary == "passed" else 1

    if command == "genspider":
        project_root = Path(args.project)
        try:
            read_project_manifest(project_root)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        spiders_dir = project_root / "spiders"
        spiders_dir.mkdir(parents=True, exist_ok=True)
        target = spiders_dir / f"{args.name}.py"
        if args.ai:
            module = _render_py_ai_spider_module(args.name, args.domain)
        else:
            module = (
                f"# scrapy: url=https://{args.domain}\n"
                "from pyspider.spider.spider import Item, Spider\n\n\n"
                f"class {args.name.title().replace('_', '')}Spider(Spider):\n"
                f'    name = "{args.name}"\n'
                f'    start_urls = ["https://{args.domain}"]\n\n'
                "    def parse(self, page):\n"
                "        yield Item(title=page.response.selector.title(), url=page.response.url)\n"
            )
        target.write_text(module, encoding="utf-8")
        payload = {
            "command": "scrapy genspider",
            "runtime": "python",
            "project": str(project_root),
            "spider": args.name,
            "path": str(target),
            "template": "ai" if args.ai else "standard",
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if command == "init":
        project_root = Path(args.path)
        project_root.mkdir(parents=True, exist_ok=True)
        config = default_contract_config()
        config["project"]["name"] = project_root.name or "pyspider-project"
        files = {
            "scrapy-project.json": json.dumps(
                {
                    "name": project_root.name or "pyspider-project",
                    "runtime": "python",
                    "entry": "scrapy_demo.py",
                    "url": "https://example.com",
                    "output": "artifacts/exports/items.json",
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            "scrapy_demo.py": (
                "# scrapy: url=https://example.com\n"
                "from pyspider.spider.spider import CrawlerProcess, FeedExporter, Item, Spider\n\n\n"
                "class DemoSpider(Spider):\n"
                '    name = "demo"\n'
                '    start_urls = ["https://example.com"]\n\n'
                "    def parse(self, page):\n"
                '        yield Item(title=page.response.selector.title(), url=page.response.url, framework="pyspider")\n\n\n'
                'if __name__ == "__main__":\n'
                "    items = CrawlerProcess(DemoSpider()).start()\n"
                '    exporter = FeedExporter.json("artifacts/exports/items.json")\n'
                "    exporter.export_items(items)\n"
                "    print(exporter.close())\n"
            ),
            "spiders/__init__.py": "",
            "plugins.py": (
                "from pyspider.spider.spider import ScrapyPlugin\n\n\n"
                "class ProjectPlugin(ScrapyPlugin):\n"
                '    name = "project-plugin"\n\n'
                "    def configure(self, config):\n"
                "        return config\n"
            ),
            "scrapy-plugins.json": json.dumps(
                {"plugins": ["project-plugin"]}, ensure_ascii=False, indent=2
            )
            + "\n",
            "run-scrapy.sh": "#!/usr/bin/env bash\nset -euo pipefail\n\npython -m pyspider scrapy run --project .\n",
            "run-scrapy.ps1": "python -m pyspider scrapy run --project .\n",
            "README.md": (
                f"# {project_root.name or 'pyspider-project'}\n\n"
                "## Quick Start\n\n"
                "```bash\npython -m pyspider scrapy run --project .\npython -m pyspider scrapy run --project . --spider demo\npython -m pyspider scrapy list --project .\npython -m pyspider scrapy genspider demo example.com --project .\n```\n\n"
                "## AI Starter\n\n"
                "```bash\npython -m pyspider ai --url https://example.com --instructions \"提取标题和摘要\" --schema-file ai-schema.json\npython -m pyspider job --file ai-job.json\n```\n\n"
                "## Plugin SDK\n\n"
                '在 `plugins.py` 中定义 `ScrapyPlugin` 子类，然后在 `spider-framework.yaml` 的 `scrapy.plugins` 中注册，例如 `plugins: ["plugins:ProjectPlugin"]`。\n'
            ),
            "ai-schema.json": json.dumps(
                {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "summary": {"type": "string"},
                        "url": {"type": "string"},
                    },
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            "ai-job.json": json.dumps(
                {
                    "name": "pyspider-ai-job",
                    "runtime": "ai",
                    "target": {"url": "https://example.com"},
                    "extract": [
                        {"field": "title", "type": "ai"},
                        {"field": "summary", "type": "ai"},
                        {"field": "url", "type": "ai"},
                    ],
                    "output": {
                        "format": "json",
                        "path": "artifacts/exports/ai-job-output.json",
                    },
                    "metadata": {
                        "content": "<title>Demo</title>",
                        "schema_file": "ai-schema.json",
                    },
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            "job.json": json.dumps(
                {
                    "name": "pyspider-job",
                    "runtime": "ai",
                    "target": {"url": "https://example.com"},
                    "extract": [{"field": "title", "type": "ai"}],
                    "output": {
                        "format": "json",
                        "path": "artifacts/exports/job-output.json",
                    },
                    "metadata": {"content": "<title>Demo</title>"},
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            "spider-framework.yaml": yaml.safe_dump(
                config, sort_keys=False, allow_unicode=True
            ),
        }
        for relative_path, content in files.items():
            file_path = project_root / relative_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")

        payload = {
            "command": "scrapy init",
            "runtime": "python",
            "project": str(project_root),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if command == "run":
        project_root = Path(args.project)
        plugins = []
        manifest_path = project_root / "scrapy-project.json"
        if not manifest_path.exists():
            print(f"missing scrapy project manifest: {manifest_path}", file=sys.stderr)
            return 2
        try:
            manifest = read_project_manifest(project_root)
            project_cfg = load_scrapy_project_config(project_root)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        plugins = _discover_plugin_instances(project_root, project_cfg)
        for plugin in plugins:
            updated = plugin.configure(project_cfg)
            if isinstance(updated, dict):
                project_cfg = updated
        selected_spider = getattr(args, "spider", None)
        try:
            spiders = _discover_spider_classes(project_root, manifest)
        except Exception as exc:
            print(
                f"failed to discover spiders in {project_root}: {exc}", file=sys.stderr
            )
            return 1

        selected_metadata = None
        if selected_spider:
            matches = [
                spider for spider in spiders if spider["name"] == selected_spider
            ]
            if not matches:
                print(
                    f"unknown spider in {project_root}: {selected_spider}",
                    file=sys.stderr,
                )
                return 2
            selected_metadata = matches[0]
        elif spiders:
            selected_metadata = spiders[0]

        url, url_source = _resolve_scrapy_url_detail(
            project_cfg,
            selected_metadata["name"] if selected_metadata else None,
            selected_metadata,
            str(manifest.get("url") or ""),
        )
        html_file = args.html_file
        default_output = str(manifest.get("output") or "artifacts/exports/items.json")
        if (
            selected_spider
            and default_output.endswith(".json")
            and default_output.endswith("items.json")
        ):
            default_output = f"artifacts/exports/{selected_spider}.json"
        output_path = (
            Path(args.output)
            if args.output
            else Path(project_root / default_output)
        )
        if not output_path.is_absolute():
            output_path = project_root / output_path
    else:
        plugins = []
        url = args.url
        url_source = "cli"
        html_file = args.html_file
        output_path = Path(args.output or "artifacts/exports/items.json")

    from pyspider.core.models import Page, Request, Response
    from pyspider.spider.spider import CrawlerProcess, FeedExporter, Item, _item_to_dict

    effective_settings = merge_contract_config(
        project_cfg if command == "run" else default_contract_config(),
        {
            "project": {
                "name": project_root.name if command == "run" else "pyspider-cli"
            }
        },
    )
    if command == "run" and selected_metadata:
        spider_override = _resolve_scrapy_spider_override(
            project_cfg, selected_metadata["name"]
        )
        if isinstance(spider_override.get("settings"), dict):
            effective_settings = merge_contract_config(
                effective_settings, spider_override["settings"]
            )
    spider = (
        _instantiate_spider(selected_metadata["class"], effective_settings)
        if command == "run"
        and selected_metadata
        and selected_metadata.get("class") is not None
        else None
    )
    if spider is None:
        from pyspider.spider.spider import Spider as ScrapySpider

        class DemoSpider(ScrapySpider):
            name = "pyspider-scrapy-demo"
            start_urls = [url]

            def parse(self, page: Page):
                return [
                    Item(
                        title=page.response.selector.title() or "",
                        url=page.response.url,
                        framework="pyspider",
                    )
                ]

        spider = DemoSpider()
        spider.settings = effective_settings

    if not getattr(spider, "start_urls", None):
        spider.start_urls = [url]

    components = (
        _merge_plugin_components(
            _discover_component_instances(project_root, project_cfg), plugins
        )
        if command == "run"
        else {
            "pipelines": [],
            "spider_middlewares": [],
            "downloader_middlewares": [],
        }
    )
    runner, runner_source = (
        _resolve_scrapy_runner_detail(
            project_cfg,
            selected_metadata["name"] if selected_metadata else None,
            selected_metadata,
        )
        if command == "run"
        else ("http", "default")
    )
    if html_file:
        html = Path(html_file).read_text(encoding="utf-8")
        response = Response(
            url=url,
            status_code=200,
            headers={},
            content=html.encode("utf-8"),
            text=html,
            request=Request(url=url, callback=spider.parse),
        )
        page = Page(response=response)
        raw_results = spider.parse(page)
        items = []
        for plugin in plugins:
            plugin.on_spider_opened(spider)
        for pipeline in components["pipelines"]:
            pipeline.open_spider(spider)
        for result in raw_results or []:
            item = result if isinstance(result, Item) else Item(**dict(result))
            for pipeline in components["pipelines"]:
                processed = pipeline.process_item(item, spider)
                if isinstance(processed, Item):
                    item = processed
                elif isinstance(processed, dict):
                    item = Item(**processed)
            for plugin in plugins:
                processed = plugin.process_item(item, spider)
                if isinstance(processed, Item):
                    item = processed
                elif isinstance(processed, dict):
                    item = Item(**processed)
            items.append(item)
        for pipeline in components["pipelines"]:
            pipeline.close_spider(spider)
        for plugin in plugins:
            plugin.on_spider_closed(spider)
    else:
        downloader = (
            HybridDownloader(
                project_cfg.get("browser", {}),
                project_root=project_root,
                default_runner=runner,
            )
            if command == "run"
            else None
        )
        items = CrawlerProcess(
            spider,
            downloader=downloader,
            pipelines=components["pipelines"],
            spider_middlewares=components["spider_middlewares"],
            downloader_middlewares=components["downloader_middlewares"],
            plugins=plugins,
        ).start()

    output_path = Path(output_path)
    exporter = FeedExporter.json(str(output_path))
    exporter.export_items(items)
    output = Path(exporter.close())
    if not output.exists():
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(
                [_item_to_dict(item) for item in items],
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    reverse_summary = None
    if command == "run":
        reverse_base_url = str(
            (project_cfg.get("node_reverse") or {}).get("base_url") or ""
        ).strip()
        if reverse_base_url:
            try:
                if html_file:
                    reverse_html = Path(html_file).read_text(encoding="utf-8")
                    reverse_status = 200
                else:
                    reverse_response = requests.get(url, timeout=30)
                    reverse_html = reverse_response.text
                    reverse_status = reverse_response.status_code
                reverse_summary = _collect_reverse_summary(
                    reverse_base_url,
                    html=reverse_html,
                    url=url,
                    status_code=reverse_status,
                )
            except Exception:
                reverse_summary = None

    payload = {
        "command": f"scrapy {command}",
        "runtime": "python",
        "spider": (
            selected_metadata["name"]
            if command == "run" and selected_metadata
            else getattr(args, "spider", None)
        ),
        "spider_class": (
            selected_metadata["class_name"]
            if command == "run" and selected_metadata
            else None
        ),
        "runner": "html-fixture" if html_file else runner,
        "runner_source": "html-fixture" if html_file else runner_source,
        "resolved_url": url,
        "url_source": "html-fixture" if html_file else url_source,
        "item_count": len(items),
        "output": str(output),
        "settings_source": (
            str(_resolve_project_config_file(project_root))
            if command == "run"
            else None
        ),
        "plugins": (
            [type(plugin).__name__ for plugin in plugins] if command == "run" else []
        ),
        "pipelines": [type(pipeline).__name__ for pipeline in components["pipelines"]],
        "spider_middlewares": [
            type(middleware).__name__ for middleware in components["spider_middlewares"]
        ],
        "downloader_middlewares": [
            type(middleware).__name__
            for middleware in components["downloader_middlewares"]
        ],
        "reverse": reverse_summary if command == "run" else None,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def discover_sitemap_targets(seed_url: str, sitemap_cfg: dict) -> list[str]:
    import xml.etree.ElementTree as ET

    source = str(sitemap_cfg.get("url") or "").strip()
    if not source and seed_url:
        source = seed_url.rstrip("/") + "/sitemap.xml"
    if not source:
        return []
    try:
        content = requests.get(source, timeout=30).text
        root = ET.fromstring(content)
        urls = [
            element.text.strip()
            for element in root.findall(".//{*}loc")
            if element.text and element.text.strip()
        ]
    except Exception:
        return []
    max_urls = int(sitemap_cfg.get("max_urls", 0) or 0)
    return urls[:max_urls] if max_urls and len(urls) > max_urls else urls


def merge_targets(base: list[str], extra: list[str]) -> list[str]:
    seen = set()
    merged = []
    for target in [*base, *extra]:
        if not target or target in seen:
            continue
        seen.add(target)
        merged.append(target)
    return merged


def _detect_ai_mode(args: argparse.Namespace) -> str:
    if getattr(args, "description", None):
        return "generate-config"
    if getattr(args, "question", None):
        return "understand"
    if getattr(args, "instructions", None) or getattr(args, "schema_file", None) or getattr(args, "schema_json", None):
        return "extract"
    return "understand"


def _default_ai_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "url": {"type": "string"},
            "summary": {"type": "string"},
        },
    }


def _load_ai_schema(schema_file: str | None, schema_json: str | None) -> dict[str, Any]:
    if schema_file:
        return json.loads(Path(schema_file).read_text(encoding="utf-8"))
    if schema_json:
        return json.loads(schema_json)
    return _default_ai_schema()


def _new_cli_ai_extractor():
    from pyspider.ai.ai_extractor import AIExtractor

    extractor = AIExtractor.from_env()
    if not extractor.api_key:
        return None, "AI_API_KEY / OPENAI_API_KEY 未设置，已回退到本地启发式提取"
    return extractor, ""


def _compact_ai_text(html: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", html or "", flags=re.IGNORECASE)
    return " ".join(without_tags.split())


def _truncate_ai_text(text: str, limit: int) -> str:
    compact = _compact_ai_text(text)
    if len(compact) <= limit:
        return compact
    return compact[:limit].rstrip() + "..."


def _truncate_ai_content(text: str, limit: int = 12000) -> str:
    return text if len(text) <= limit else text[:limit]


def _first_non_empty(*values: str) -> str:
    for value in values:
        if value and value.strip():
            return value.strip()
    return ""


def _html_meta(html: str, name: str, attr: str = "name") -> str:
    pattern = re.compile(
        rf'<meta[^>]*{attr}=["\']{re.escape(name)}["\'][^>]*content=["\']([^"\']+)["\']',
        re.IGNORECASE,
    )
    match = pattern.search(html or "")
    return match.group(1).strip() if match else ""


def _html_title(html: str) -> str:
    title_match = re.search(r"<title[^>]*>(.*?)</title>", html or "", re.IGNORECASE | re.DOTALL)
    h1_match = re.search(r"<h1[^>]*>(.*?)</h1>", html or "", re.IGNORECASE | re.DOTALL)
    return _first_non_empty(
        _html_meta(html, "og:title", "property"),
        re.sub(r"\s+", " ", title_match.group(1)).strip() if title_match else "",
        re.sub(r"\s+", " ", h1_match.group(1)).strip() if h1_match else "",
    )


def _html_attr(html: str, tag: str, attr: str) -> str:
    match = re.search(
        rf"<{tag}[^>]*{attr}=[\"']([^\"']+)[\"']",
        html or "",
        re.IGNORECASE,
    )
    return match.group(1).strip() if match else ""


def _find_token(text: str, tokens: list[str]) -> str:
    lowered = text.lower()
    for raw in lowered.split():
        for token in tokens:
            if token.lower() in raw:
                return raw.strip(".,;:!?()[]{}\"'")
    return ""


def _heuristic_ai_extract(url: str, html: str, schema: dict[str, Any]) -> dict[str, Any]:
    properties = schema.get("properties") if isinstance(schema, dict) else None
    if not isinstance(properties, dict) or not properties:
        properties = _default_ai_schema()["properties"]

    text = _compact_ai_text(html)
    result: dict[str, Any] = {}
    for field_name, spec in properties.items():
        spec = spec if isinstance(spec, dict) else {}
        expected_type = str(spec.get("type", "string"))
        key = field_name.lower()
        if "title" in key or "headline" in key:
            value: Any = _html_title(html)
        elif key == "url" or "link" in key:
            value = [url] if expected_type == "array" else url
        elif "summary" in key or "description" in key or key == "desc":
            value = _first_non_empty(
                _html_meta(html, "description"),
                _html_meta(html, "og:description", "property"),
                _truncate_ai_text(text, 220),
            )
        elif "content" in key or "body" in key or key == "text":
            value = _truncate_ai_text(text, 1200)
        elif "author" in key:
            value = _first_non_empty(
                _html_meta(html, "author"),
                _html_meta(html, "article:author", "property"),
            )
        elif "date" in key or "time" in key or "published" in key:
            value = _first_non_empty(
                _html_meta(html, "article:published_time", "property"),
                _html_meta(html, "pubdate"),
                _html_attr(html, "time", "datetime"),
            )
        elif "image" in key or "thumbnail" in key or "cover" in key:
            value = _first_non_empty(
                _html_meta(html, "og:image", "property"),
                _html_attr(html, "img", "src"),
            )
        elif "price" in key:
            value = _find_token(text, ["¥", "￥", "$", "usd", "rmb"])
        else:
            value = [] if expected_type == "array" else ""
        result[field_name] = value
    return result


def _heuristic_ai_generate_config(description: str) -> dict[str, Any]:
    fields = ["title", "url", "summary"]
    lowered = description.lower()
    if "price" in lowered or "价格" in description:
        fields.append("price")
    if "author" in lowered or "作者" in description:
        fields.append("author")
    if "date" in lowered or "时间" in description or "日期" in description:
        fields.append("published_at")
    if "content" in lowered or "正文" in description:
        fields.append("content")

    urls = ["https://example.com"]
    for token in description.split():
        cleaned = token.strip(" \t\r\n,.;'\"()[]{}")
        if cleaned.startswith(("http://", "https://")):
            urls = [cleaned]
            break

    return {
        "start_urls": urls,
        "rules": [
            {
                "name": "auto-generated",
                "pattern": ".*",
                "extract": fields,
                "follow_links": True,
            }
        ],
        "settings": {"concurrency": 3, "max_depth": 2, "delay": 500},
        "source_description": description,
    }


def _heuristic_ai_understand(url: str, html: str, question: str) -> dict[str, Any]:
    from pyspider.profiler.site_profiler import SiteProfiler

    profiler = SiteProfiler()
    profile = profiler.profile(url or "", html)
    question_text = question or "请总结页面类型、核心内容和推荐提取字段。"
    return {
        "answer": (
            f"页面类型={profile.page_type}，爬虫类型={profile.crawler_type}，"
            f"候选字段={profile.candidate_fields}，风险等级={profile.risk_level}，"
            f"优先 runner={profile.runner_order}。问题：{question_text}"
        ),
        "page_profile": _site_profile_payload(profile),
    }


def _schema_from_candidate_fields(fields: list[str]) -> dict[str, Any]:
    ordered_fields: list[str] = []
    for field in ["title", "summary", "url", *fields]:
        if field not in ordered_fields:
            ordered_fields.append(field)
    properties: dict[str, Any] = {}
    for field in ordered_fields:
        field_lower = field.lower()
        if any(token in field_lower for token in ["price", "amount", "score", "rating"]):
            properties[field] = {"type": "number"}
        elif any(token in field_lower for token in ["count", "total"]):
            properties[field] = {"type": "integer"}
        elif any(token in field_lower for token in ["images", "links", "tags", "items"]):
            properties[field] = {"type": "array", "items": {"type": "string"}}
        else:
            properties[field] = {"type": "string"}
    return {"type": "object", "properties": properties}


def _derive_domain(raw_url: str) -> str:
    from urllib.parse import urlparse

    try:
        parsed = urlparse(raw_url)
        if parsed.netloc:
            return parsed.netloc
    except Exception:
        pass
    return "example.com"


def _render_py_ai_spider_module(spider_name: str, domain: str) -> str:
    class_name = spider_name.title().replace("_", "")
    return (
        f"# scrapy: url=https://{domain}\n"
        "from pyspider.ai.ai_extractor import AIExtractor\n"
        "from pyspider.spider.spider import Item, Request, Spider, ai_start_request_meta, apply_ai_request_strategy, iter_ai_follow_requests, load_ai_project_assets\n\n\n"
        "AI_ASSETS = load_ai_project_assets()\n\n\n"
        f"class {class_name}Spider(Spider):\n"
        f'    name = "{spider_name}"\n'
        f'    start_urls = ["https://{domain}"]\n\n'
        "    def start_requests(self):\n"
        "        for url in self.start_urls:\n"
        "            meta = ai_start_request_meta(AI_ASSETS)\n"
        "            yield apply_ai_request_strategy(Request(url=url, callback=self.parse, meta=meta), AI_ASSETS)\n\n"
        "    def parse(self, page):\n"
        "        extractor = AIExtractor.from_env()\n"
        "        if extractor.api_key:\n"
        "            data = extractor.extract_structured(page.response.text, AI_ASSETS['extraction_prompt'], AI_ASSETS['schema'])\n"
        "        else:\n"
        "            data = {\n"
        '                "title": page.response.css("title::text").get(default=""),\n'
        '                "summary": page.response.css("meta[name=\"description\"]::attr(content)").get(default=""),\n'
        '                "url": page.response.url,\n'
        "            }\n"
        '        data.setdefault("url", page.response.url)\n'
        "        yield Item(**data)\n"
        "        for req in iter_ai_follow_requests(page, self.parse, AI_ASSETS):\n"
        "            yield req\n"
    )


def _build_ai_blueprint(
    resolved_url: str,
    spider_name: str,
    page_profile: dict[str, Any],
    schema: dict[str, Any],
    html: str,
) -> dict[str, Any]:
    candidate_fields = list(page_profile.get("candidate_fields") or [])
    extraction_prompt = (
        "请从页面中提取以下字段，并只返回 JSON："
        + ", ".join(schema.get("properties", {}).keys())
        + "。缺失字段返回空字符串或空数组。"
    )
    page_type = str(page_profile.get("page_type") or "generic")
    crawler_type = str(page_profile.get("crawler_type") or "generic_http")
    signals = dict(page_profile.get("signals") or {})
    risk_level = str(page_profile.get("risk_level") or "low")
    runner_order = list(page_profile.get("runner_order") or [])
    strategy_hints = list(page_profile.get("strategy_hints") or [])
    job_templates = list(page_profile.get("job_templates") or [])
    lowered = (html or "").lower()
    auth_required = any(token in lowered for token in ["type=\"password\"", "type='password'", "login", "sign in", "signin", "登录"])
    js_heavy = any(token in lowered for token in ["__next_data__", "window.__", "webpack", "fetch(", "graphql", "xhr"])
    reverse_required = any(token in lowered for token in ["crypto", "signature", "token", "webpack", "obfusc", "encrypt", "decrypt"])
    follow_rules = [
        {
            "name": "same-domain-content",
            "enabled": True,
            "description": "优先跟进同域详情页和内容页链接",
        }
    ]
    pagination = {
        "enabled": page_type in {"list", "generic"} or any(token in lowered for token in ["rel=\"next\"", "pagination", "page=", "next page", "下一页"]),
        "strategy": (
            "bounded scroll batches with repeated DOM/network snapshot checks"
            if crawler_type == "infinite_scroll_listing"
            else "follow next page or numbered pagination links"
        ),
        "selectors": ["a[rel='next']", ".next", ".pagination a"],
    }
    anti_bot = {
        "risk_level": risk_level,
        "signals": signals,
        "recommended_runner": runner_order[0] if runner_order else ("browser" if risk_level != "low" else "http"),
        "notes": "高风险页面建议先走浏览器模式并降低抓取速率",
    }
    return {
        "version": 1,
        "spider_name": spider_name,
        "resolved_url": resolved_url,
        "page_type": page_type,
        "crawler_type": crawler_type,
        "candidate_fields": candidate_fields,
        "schema": schema,
        "extraction_prompt": extraction_prompt,
        "runner_order": runner_order,
        "strategy_hints": strategy_hints,
        "job_templates": job_templates,
        "follow_rules": follow_rules,
        "pagination": pagination,
        "authentication": {
            "required": auth_required,
            "strategy": "capture session/login flow before crawl" if auth_required else "not required",
        },
        "javascript_runtime": {
            "required": js_heavy or crawler_type in {"hydrated_spa", "infinite_scroll_listing", "ecommerce_search"},
            "recommended_runner": "browser" if (js_heavy or (runner_order and runner_order[0] == "browser")) else "http",
        },
        "reverse_engineering": {
            "required": reverse_required,
            "notes": "inspect network/API signing or obfuscated scripts" if reverse_required else "not required",
        },
        "anti_bot_strategy": anti_bot,
    }


def _auth_validation_status(html: str) -> tuple[bool, list[str]]:
    lowered = (html or "").lower()
    indicators = []
    if any(token in lowered for token in ["type=\"password\"", "type='password'"]):
        indicators.append("password-input")
    if any(token in lowered for token in ["login", "sign in", "signin", "登录"]):
        indicators.append("login-marker")
    return (len(indicators) == 0, indicators)


def _run_auth_actions(
    browser,
    actions: list[dict[str, Any]],
    warnings: list[str],
    captures: dict[str, Any],
) -> None:
    def condition_matches(condition: dict[str, Any] | None) -> bool:
        if not isinstance(condition, dict) or not condition:
            return True
        if condition.get("all"):
            return all(condition_matches(item) for item in condition.get("all") or [])
        if condition.get("any"):
            return any(condition_matches(item) for item in condition.get("any") or [])
        if condition.get("not"):
            return not condition_matches(condition.get("not"))
        if condition.get("selector_exists"):
            if browser.page.locator(str(condition["selector_exists"])).count() == 0:
                return False
        if condition.get("selector_missing"):
            if browser.page.locator(str(condition["selector_missing"])).count() > 0:
                return False
        if condition.get("url_contains") is not None and str(condition["url_contains"]) not in browser.get_url():
            return False
        capture_name = str(condition.get("capture") or "").strip()
        if capture_name:
            captured = captures.get(capture_name)
            if condition.get("equals") is not None and str(captured) != str(condition.get("equals")):
                return False
            if condition.get("contains") is not None and str(condition.get("contains")) not in str(captured):
                return False
        return True

    def execute_single(action: dict[str, Any]) -> None:
        action_type = str(action.get("type") or "").strip()
        selector = str(action.get("selector") or "").strip()
        value = str(action.get("value") or "")
        timeout_ms = int(action.get("timeout_ms") or getattr(browser, "timeout", 30000))
        save_as = str(action.get("save_as") or action.get("field") or action.get("name") or "")

        if not condition_matches(action.get("when")):
            return

        if action_type == "if":
            branch = action.get("then") if condition_matches(action.get("when")) else action.get("else")
            if isinstance(branch, list):
                _run_auth_actions(browser, branch, warnings, captures)
            return

        if action_type == "goto":
            browser.navigate(str(action.get("url") or browser.get_url()), wait_until="networkidle")
        elif action_type == "wait":
            if selector:
                browser.wait_for_selector(selector, timeout=timeout_ms)
            else:
                browser.wait_for_load_state("networkidle")
        elif action_type == "click":
            browser.click(selector)
        elif action_type == "type":
            browser.fill(selector, value)
        elif action_type == "submit":
            if selector:
                browser.page.locator(selector).press("Enter", timeout=timeout_ms)
            else:
                browser.page.keyboard.press("Enter")
        elif action_type == "wait_network_idle":
            browser.wait_for_load_state("networkidle")
        elif action_type == "otp":
            otp_value = _resolve_otp_value(action)
            if not otp_value:
                raise AssertionError("otp action requires value, otp_env, totp_secret, or totp_env")
            browser.fill(selector, otp_value)
        elif action_type == "mfa_totp":
            totp_value = _resolve_otp_value(action)
            if not totp_value:
                raise AssertionError("mfa_totp action requires totp_secret or totp_env")
            browser.fill(selector, totp_value)
        elif action_type == "captcha_solve":
            from pyspider.captcha.solver import CaptchaSolver

            provider = str(action.get("provider") or "2captcha")
            api_key = str(action.get("api_key") or os.getenv(str(action.get("api_key_env") or "CAPTCHA_API_KEY"), ""))
            solver = CaptchaSolver(api_key=api_key, service=provider)
            challenge = str(action.get("challenge") or "image").strip().lower()
            token = ""
            if challenge in {"recaptcha", "hcaptcha", "turnstile"}:
                site_key, challenge_action, c_data, page_data = _resolve_site_challenge_fields(browser, action)
                if challenge == "recaptcha":
                    result = solver.solve_recaptcha(site_key, browser.get_url())
                elif challenge == "turnstile":
                    result = solver.solve_turnstile(
                        site_key,
                        browser.get_url(),
                        action=challenge_action,
                        c_data=c_data,
                        page_data=page_data,
                    )
                else:
                    result = solver.solve_hcaptcha(site_key, browser.get_url())
                token = result.text if result.success else ""
                if not result.success:
                    raise AssertionError(result.error or "captcha solve failed")
            elif challenge == "image":
                image_bytes = b""
                if selector:
                    image_bytes = browser.page.locator(selector).first.screenshot()
                elif action.get("image_base64"):
                    image_bytes = base64.b64decode(str(action.get("image_base64")))
                elif action.get("image_file"):
                    image_bytes = Path(str(action.get("image_file"))).read_bytes()
                result = solver.solve_image(image_bytes)
                token = result.text if result.success else ""
                if not result.success:
                    raise AssertionError(result.error or "image captcha solve failed")
            else:
                raise AssertionError("captcha_solve currently supports image/recaptcha/hcaptcha/turnstile challenges")
            if save_as:
                captures[save_as] = token
            if action.get("target_selector"):
                browser.fill(str(action.get("target_selector")), token)
        elif action_type == "captcha_wait":
            captcha_selector = selector or str(action.get("captcha_selector") or "iframe[title*='captcha'], [class*='captcha'], [id*='captcha']")
            browser.page.locator(captcha_selector).first.wait_for(state="hidden", timeout=timeout_ms)
        elif action_type == "select":
            browser.select_option(selector, value)
        elif action_type == "hover":
            browser.page.hover(selector, timeout=timeout_ms)
        elif action_type == "scroll":
            if selector:
                browser.page.locator(selector).scroll_into_view_if_needed(timeout=timeout_ms)
            elif value.strip().lower() == "top":
                browser.scroll_to(0, 0)
            else:
                browser.scroll_to_bottom()
        elif action_type == "eval":
            result = browser.evaluate(value)
            if save_as:
                captures[save_as] = result
        elif action_type == "assert":
            if selector:
                locator = browser.page.locator(selector).first
                attr = str(action.get("attr") or "").strip()
                observed = (
                    locator.get_attribute(attr) if attr else locator.text_content()
                ) or ""
                if action.get("equals") is not None and observed != str(action.get("equals")):
                    raise AssertionError(f"assert equals failed for {selector}: {observed!r}")
                if action.get("contains") is not None and str(action.get("contains")) not in observed:
                    raise AssertionError(f"assert contains failed for {selector}: {observed!r}")
                if action.get("exists") is True and not observed:
                    raise AssertionError(f"assert exists failed for {selector}")
            elif action.get("url_contains") is not None and str(action.get("url_contains")) not in browser.get_url():
                raise AssertionError(f"url assert failed: {browser.get_url()!r}")
        elif action_type == "save_as":
            field_name = save_as or f"value_{len(captures)}"
            attr = str(action.get("attr") or "").strip()
            capture_kind = value.strip().lower()
            if selector:
                locator = browser.page.locator(selector).first
                captures[field_name] = (
                    locator.get_attribute(attr) if attr else locator.text_content()
                ) or ""
            elif capture_kind == "url":
                captures[field_name] = browser.get_url()
            elif capture_kind == "html":
                captures[field_name] = browser.get_content()
            else:
                warnings.append(
                    f"unsupported save_as capture kind: {capture_kind or 'selector-required'}"
                )
        elif action_type == "reverse_profile":
            from pyspider.node_reverse.client import NodeReverseClient

            base_url = str(action.get("base_url") or "http://localhost:3000")
            client = NodeReverseClient(base_url)
            payload = {
                "detect": client.detect_anti_bot(html=browser.get_content(), url=browser.get_url()),
                "profile": client.profile_anti_bot(html=browser.get_content(), url=browser.get_url()),
            }
            fingerprint_spoof = getattr(client, "spoof_fingerprint", None)
            if callable(fingerprint_spoof):
                payload["fingerprint_spoof"] = fingerprint_spoof("chrome", "windows")
            tls_fingerprint = getattr(client, "generate_tls_fingerprint", None)
            if callable(tls_fingerprint):
                payload["tls_fingerprint"] = tls_fingerprint("chrome", "120")
            script_sample = _extract_script_sample(browser.get_content())
            analyze_crypto = getattr(client, "analyze_crypto", None)
            if script_sample.strip() and callable(analyze_crypto):
                payload["crypto_analysis"] = analyze_crypto(script_sample)
            captures[save_as or "reverse_runtime"] = payload
        elif action_type == "reverse_analyze_crypto":
            from pyspider.node_reverse.client import NodeReverseClient

            base_url = str(action.get("base_url") or "http://localhost:3000")
            client = NodeReverseClient(base_url)
            code = value
            if selector:
                code = browser.page.locator(selector).first.text_content() or ""
            captures[save_as or "reverse_crypto"] = client.analyze_crypto(code)
        else:
            warnings.append(f"unsupported auth action: {action_type}")

    for action in actions:
        attempts = max(1, int(action.get("retry") or 0) + 1)
        retry_delay_ms = int(action.get("retry_delay_ms") or 0)
        last_error: Exception | None = None
        for attempt in range(attempts):
            try:
                execute_single(action)
                last_error = None
                break
            except Exception as exc:
                last_error = exc
                if attempt + 1 < attempts and retry_delay_ms > 0:
                    time.sleep(retry_delay_ms / 1000)
        if last_error is not None:
            warnings.append(f"auth action failed ({action.get('type')}): {last_error}")


def cmd_ai(args: argparse.Namespace) -> int:
    cfg = load_contract_config(getattr(args, "config", None))
    mode = _detect_ai_mode(args)
    warnings: list[str] = []
    engine = "heuristic-fallback"
    source = "description"
    resolved_url = ""

    if mode == "generate-config":
        result: dict[str, Any] = _heuristic_ai_generate_config(args.description or "")
        extractor, warning = _new_cli_ai_extractor()
        if extractor is not None:
            try:
                result = extractor.generate_spider_config(args.description or "")
                engine = "llm"
            except Exception as exc:
                warnings.append(str(exc))
        elif warning:
            warnings.append(warning)
    else:
        target_url = args.url or (cfg.get("crawl", {}).get("urls") or [None])[0]
        if args.html_file:
            html = Path(args.html_file).read_text(encoding="utf-8")
            resolved_url = target_url or Path(args.html_file).resolve().as_uri()
            source = "html-file"
        elif target_url:
            html = requests.get(target_url, timeout=30).text
            resolved_url = target_url
            source = "url" if args.url else "config"
        else:
            print("ai requires --url, --html-file, or a config with crawl.urls", file=sys.stderr)
            return 2

        if mode == "extract":
            schema = _load_ai_schema(args.schema_file, args.schema_json)
            instructions = args.instructions or "提取页面中的核心结构化字段"
            result = _heuristic_ai_extract(resolved_url, html, schema)
            extractor, warning = _new_cli_ai_extractor()
            if extractor is not None:
                try:
                    result = extractor.extract_structured(
                        _truncate_ai_content(html), instructions, schema
                    )
                    engine = "llm"
                except Exception as exc:
                    warnings.append(str(exc))
            elif warning:
                warnings.append(warning)
        else:
            result = _heuristic_ai_understand(resolved_url, html, args.question or "")
            extractor, warning = _new_cli_ai_extractor()
            if extractor is not None:
                try:
                    answer = extractor.understand_page(
                        _truncate_ai_content(html),
                        args.question or "请总结页面类型、核心内容和推荐提取字段。",
                    )
                    result = {
                        "answer": answer,
                        "page_profile": result["page_profile"],
                    }
                    engine = "llm"
                except Exception as exc:
                    warnings.append(str(exc))
            elif warning:
                warnings.append(warning)

    payload = {
        "command": "ai",
        "runtime": "python",
        "mode": mode,
        "summary": "passed",
        "summary_text": f"{mode} mode completed with engine {engine}",
        "exit_code": 0,
        "engine": engine,
        "source": source,
        "warnings": warnings,
        "result": result,
    }
    if resolved_url:
        payload["url"] = resolved_url

    encoded = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(encoded, encoding="utf-8")
    print(encoded)
    return 0


def cmd_ultimate(args: argparse.Namespace) -> int:
    from pyspider.advanced.ultimate import UltimateConfig, create_ultimate_spider

    cfg = load_contract_config(getattr(args, "config", None))
    anti_bot_cfg = cfg.get("anti_bot", {})
    node_reverse_cfg = cfg.get("node_reverse", {})
    config = UltimateConfig(
        reverse_service_url=args.reverse_service_url
        or node_reverse_cfg.get("base_url", "http://localhost:3000"),
        max_concurrency=max(
            1, int(args.concurrency or cfg.get("crawl", {}).get("concurrency", 3))
        ),
        user_agent=cfg.get("browser", {}).get("user_agent")
        or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        proxy_servers=(
            []
            if anti_bot_cfg.get("proxy_pool", "local") == "local"
            else [
                item.strip()
                for item in str(anti_bot_cfg.get("proxy_pool", "")).split(",")
                if item.strip()
            ]
        ),
    )
    spider = create_ultimate_spider(config)
    if args.json or args.quiet:
        with contextlib.redirect_stdout(StringIO()):
            results = asyncio.run(spider.start(list(args.urls)))
    else:
        results = asyncio.run(spider.start(list(args.urls)))
    all_success = all(result.success for result in results)
    payload = {
        "command": "ultimate",
        "runtime": "python",
        "summary": "passed" if all_success else "failed",
        "summary_text": f"{len(results)} results, {sum(1 for result in results if not result.success)} failed",
        "exit_code": 0 if all_success else 1,
        "urls": list(args.urls),
        "url_count": len(args.urls),
        "result_count": len(results),
        "results": [
            {
                "task_id": result.task_id,
                "url": result.url,
                "success": result.success,
                "error": result.error,
                "duration": f"{result.duration:.4f}s",
                "anti_bot_level": result.anti_bot_level,
                "anti_bot_signals": result.anti_bot_signals,
                "reverse": getattr(result, "reverse_runtime", {}),
            }
            for result in results
        ],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    return payload["exit_code"]


def cmd_node_reverse(args: argparse.Namespace) -> int:
    from pyspider.node_reverse.client import NodeReverseClient

    client = NodeReverseClient(getattr(args, "base_url", None))
    command = getattr(args, "node_reverse_command", None)

    if command == "health":
        payload = {
            "command": "node-reverse health",
            "healthy": client.health_check(),
            "base_url": client.base_url,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if payload["healthy"] else 1

    if command == "profile":
        html = ""
        target_url = args.url or ""
        if args.html_file:
            html = Path(args.html_file).read_text(encoding="utf-8")
        elif target_url:
            response = requests.get(target_url, timeout=30)
            html = response.text
        else:
            print("node-reverse profile requires --url or --html-file", file=sys.stderr)
            return 2

        payload = client.profile_anti_bot(
            html=html,
            url=target_url,
            status_code=args.status_code or None,
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if payload.get("success") else 1

    if command == "detect":
        html = ""
        target_url = args.url or ""
        if args.html_file:
            html = Path(args.html_file).read_text(encoding="utf-8")
        elif target_url:
            response = requests.get(target_url, timeout=30)
            html = response.text
        else:
            print("node-reverse detect requires --url or --html-file", file=sys.stderr)
            return 2

        payload = client.detect_anti_bot(
            html=html,
            url=target_url,
            status_code=args.status_code or None,
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if payload.get("success") else 1

    if command == "fingerprint-spoof":
        payload = client.spoof_fingerprint(
            browser=args.browser,
            platform=args.platform,
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if payload.get("success") else 1

    if command == "tls-fingerprint":
        payload = client.generate_tls_fingerprint(
            browser=args.browser,
            version=args.version,
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if payload.get("success") else 1

    if command == "canvas-fingerprint":
        payload = client.canvas_fingerprint()
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if payload.get("success") else 1

    if command == "analyze-crypto":
        code = Path(args.code_file).read_text(encoding="utf-8")
        payload = client.analyze_crypto(code)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if payload.get("success") else 1

    if command == "signature-reverse":
        code = Path(args.code_file).read_text(encoding="utf-8")
        payload = client.reverse_signature(
            code,
            args.input_data,
            args.expected_output,
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if payload.get("success") else 1

    if command == "ast":
        code = Path(args.code_file).read_text(encoding="utf-8")
        analysis = [
            item.strip()
            for item in str(getattr(args, "analysis", "")).split(",")
            if item.strip()
        ]
        payload = client.analyze_ast(code, analysis or None)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if payload.get("success") else 1

    if command == "webpack":
        code = Path(args.code_file).read_text(encoding="utf-8")
        payload = client.analyze_webpack(code)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if payload.get("success") else 1

    if command == "function-call":
        code = Path(args.code_file).read_text(encoding="utf-8")
        payload = client.call_function(
            args.function_name,
            list(getattr(args, "arg", []) or []),
            code,
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if payload.get("success") else 1

    if command == "browser-simulate":
        code = Path(args.code_file).read_text(encoding="utf-8")
        payload = client.simulate_browser(
            code,
            {
                "userAgent": args.user_agent,
                "language": args.language,
                "platform": args.platform,
            },
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if payload.get("success") else 1

    print("node-reverse requires a subcommand", file=sys.stderr)
    return 2


def cmd_anti_bot(args: argparse.Namespace) -> int:
    from pyspider.antibot.antibot import AntiBotHandler

    handler = AntiBotHandler()
    command = getattr(args, "anti_bot_command", None)

    if command == "headers":
        profile = getattr(args, "profile", "default")
        if profile == "cloudflare":
            headers = handler.bypass_cloudflare()
            headers.update(handler.get_stealth_headers())
        elif profile == "akamai":
            headers = handler.bypass_akamai()
            headers.update(handler.get_stealth_headers())
        else:
            headers = handler.get_random_headers()
        payload = {
            "command": "anti-bot headers",
            "runtime": "python",
            "profile": profile,
            "headers": headers,
            "fingerprint": handler.generate_fingerprint(),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if command == "profile":
        html = ""
        if args.html_file:
            html = Path(args.html_file).read_text(encoding="utf-8")
        elif args.url:
            html = requests.get(args.url, timeout=30).text
        else:
            print("anti-bot profile requires --url or --html-file", file=sys.stderr)
            return 2
        blocked = handler.is_blocked(html, int(args.status_code))
        lower = html.lower()
        signals = []
        if "captcha" in lower:
            signals.append("captcha")
        if "cf-ray" in lower or "just a moment" in lower:
            signals.append("vendor:cloudflare")
        if "datadome" in lower:
            signals.append("vendor:datadome")
        if "akamai" in lower:
            signals.append("vendor:akamai")
        if int(args.status_code) == 403:
            signals.append("status:403")
        if int(args.status_code) == 429:
            signals.append("status:429")
        if not signals:
            signals.append("clear")
        payload = {
            "command": "anti-bot profile",
            "runtime": "python",
            "url": args.url or "",
            "blocked": blocked,
            "status_code": int(args.status_code),
            "signals": signals,
            "level": "medium" if blocked else "low",
            "fingerprint": handler.generate_fingerprint(),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if not blocked else 1

    print("anti-bot requires a subcommand", file=sys.stderr)
    return 2


def _delegate_to_video_cli(argv: Sequence[str]) -> int:
    from pyspider.cli import video_downloader

    original_argv = sys.argv[:]
    sys.argv = ["pyspider", *argv]
    try:
        return video_downloader.main()
    finally:
        sys.argv = original_argv


def main(argv: Sequence[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])

    # 兼容旧的媒体命令直连。
    if argv and argv[0] in MEDIA_COMMANDS:
        return _delegate_to_video_cli(argv)

    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 0

    try:
        return args.func(args)
    except ValueError as exc:
        print(f"config error: {exc}", file=sys.stderr)
        return 2


__all__ = ["main"]


if __name__ == "__main__":
    raise SystemExit(main())
