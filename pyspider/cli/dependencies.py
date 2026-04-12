"""
pyspider CLI runtime dependency checks.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from pyspider.core.config import ConfigLoader
from pyspider.media.ffmpeg_tools import FFmpegExecutor, FFmpegNotFoundError


@dataclass(frozen=True)
class DependencyStatus:
    level: str
    name: str
    message: str


@dataclass(frozen=True)
class DependencyReport:
    statuses: list[DependencyStatus]
    summary: str
    exit_code: int

    def to_dict(self) -> dict:
        return dependency_report_to_dict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


def resolve_ffmpeg_path(config_path: Optional[str] = None) -> Optional[str]:
    config = ConfigLoader(config_path) if config_path else ConfigLoader()
    configured_path = config.media.ffmpeg_path
    if configured_path:
        return configured_path

    env_path = os.getenv("FFMPEG_PATH")
    if env_path:
        return env_path

    return None


def run_dependency_doctor(
    config_path: Optional[str] = None,
    redis_url: Optional[str] = None,
) -> DependencyReport:
    statuses: list[DependencyStatus] = []
    statuses.append(_check_python())

    config_loader, config_statuses = _load_config_statuses(config_path)
    statuses.extend(config_statuses)
    statuses.append(_check_output_dir(config_loader.media.output_dir))

    ffmpeg_path = resolve_ffmpeg_path(config_path)
    statuses.extend(_check_ffmpeg(ffmpeg_path))
    statuses.append(_check_module("Redis client", "redis", optional=True))
    statuses.append(_check_redis_connection(redis_url))
    statuses.append(_check_module("Selenium", "selenium", optional=True))
    statuses.append(_check_module("Playwright", "playwright", optional=True))
    statuses.append(_check_browser_binary())

    summary = _build_summary(statuses)
    exit_code = 1 if any(status.level == "fail" for status in statuses) else 0
    return DependencyReport(statuses=statuses, summary=summary, exit_code=exit_code)


def _check_python() -> DependencyStatus:
    version = sys.version_info
    message = f"{version.major}.{version.minor}.{version.micro}"
    if version >= (3, 8):
        return DependencyStatus("ok", "Python", message)

    return DependencyStatus("fail", "Python", f"{message} is below required 3.8")


def _load_config_statuses(
    config_path: Optional[str],
) -> tuple[ConfigLoader, list[DependencyStatus]]:
    config_file = (
        Path(config_path) if config_path else Path(ConfigLoader.DEFAULT_CONFIG_FILE)
    )
    loader = ConfigLoader(str(config_file))
    statuses: list[DependencyStatus] = []

    if config_file.exists():
        statuses.append(
            DependencyStatus("ok", "Config file", str(config_file.resolve()))
        )
    elif config_path:
        statuses.append(
            DependencyStatus("fail", "Config file", f"missing: {config_file}")
        )
    else:
        statuses.append(
            DependencyStatus(
                "warn",
                "Config file",
                "spider-framework.yaml fallback chain not found, using defaults",
            )
        )

    validation_errors = loader.validate()
    if validation_errors:
        statuses.append(
            DependencyStatus("fail", "Config validation", "; ".join(validation_errors))
        )
    else:
        statuses.append(DependencyStatus("ok", "Config validation", "passed"))

    return loader, statuses


def _check_output_dir(output_dir: str) -> DependencyStatus:
    path = Path(output_dir)
    try:
        path.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=path, delete=True):
            pass
        return DependencyStatus("ok", "Output directory", f"writable: {path.resolve()}")
    except Exception as exc:
        return DependencyStatus(
            "fail", "Output directory", f"not writable: {path} ({exc})"
        )


def _check_ffmpeg(ffmpeg_path: Optional[str]) -> list[DependencyStatus]:
    try:
        executor = FFmpegExecutor(ffmpeg_path=ffmpeg_path)
    except FFmpegNotFoundError as exc:
        detail = str(exc).replace("\n", " ")
        if ffmpeg_path:
            detail = f"{detail} Configured path: {ffmpeg_path}"
        return [
            DependencyStatus("fail", "FFmpeg", detail),
            DependencyStatus(
                "warn", "ffprobe", "skipped because ffmpeg is unavailable"
            ),
        ]

    ffmpeg_status = DependencyStatus(
        "ok", "FFmpeg", f"available at {executor.ffmpeg_path}"
    )
    if executor.ffprobe_path:
        ffprobe_status = DependencyStatus(
            "ok", "ffprobe", f"available at {executor.ffprobe_path}"
        )
    else:
        ffprobe_status = DependencyStatus(
            "warn", "ffprobe", "not found, metadata features may be unavailable"
        )

    return [ffmpeg_status, ffprobe_status]


def _check_module(name: str, module_name: str, optional: bool) -> DependencyStatus:
    if importlib.util.find_spec(module_name):
        return DependencyStatus("ok", name, "module installed")

    level = "warn" if optional else "fail"
    suffix = (
        "optional feature unavailable" if optional else "required dependency missing"
    )
    return DependencyStatus(level, name, f"{module_name} not installed, {suffix}")


def _check_redis_connection(redis_url: Optional[str]) -> DependencyStatus:
    if not redis_url:
        return DependencyStatus(
            "skip",
            "Redis connection",
            "not checked, use --redis-url to verify connectivity",
        )

    if not importlib.util.find_spec("redis"):
        return DependencyStatus(
            "fail", "Redis connection", "redis package is not installed"
        )

    try:
        import redis

        client = redis.from_url(redis_url, decode_responses=True)
        response = client.ping()
        client.close()
        if response:
            return DependencyStatus(
                "ok", "Redis connection", f"ping succeeded: {redis_url}"
            )
        return DependencyStatus(
            "fail", "Redis connection", f"unexpected ping response: {response}"
        )
    except Exception as exc:
        return DependencyStatus("fail", "Redis connection", f"{redis_url} ({exc})")


def _check_browser_binary() -> DependencyStatus:
    candidates = _browser_candidates()
    for candidate in candidates:
        if os.path.isabs(candidate):
            if os.path.exists(candidate):
                return DependencyStatus("ok", "Browser binary", candidate)
        else:
            resolved = shutil.which(candidate)
            if resolved:
                return DependencyStatus("ok", "Browser binary", resolved)

    return DependencyStatus(
        "warn",
        "Browser binary",
        "no Chrome/Chromium/Edge executable found in PATH or common install locations",
    )


def _browser_candidates() -> Iterable[str]:
    return (
        "chrome",
        "chromium",
        "msedge",
        "google-chrome",
        "chromium-browser",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    )


def _build_summary(statuses: Iterable[DependencyStatus]) -> str:
    counts = {"ok": 0, "warn": 0, "fail": 0, "skip": 0}
    for status in statuses:
        counts[status.level] += 1
    return (
        f"{counts['ok']} passed, {counts['warn']} warnings, "
        f"{counts['fail']} failed, {counts['skip']} skipped"
    )


def dependency_report_to_dict(report) -> dict:
    return {
        "command": "doctor",
        "runtime": "python",
        "summary": "passed" if getattr(report, "exit_code") == 0 else "failed",
        "summary_text": getattr(report, "summary"),
        "exit_code": getattr(report, "exit_code"),
        "checks": [
            {
                "name": getattr(status, "name"),
                "status": _normalize_status(getattr(status, "level")),
                "details": getattr(status, "message"),
            }
            for status in getattr(report, "statuses")
        ],
    }


def _normalize_status(level: str) -> str:
    return {
        "ok": "passed",
        "warn": "warning",
        "fail": "failed",
        "skip": "skipped",
    }.get(level, level)
