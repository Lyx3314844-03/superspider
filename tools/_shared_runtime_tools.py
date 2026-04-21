from __future__ import annotations

import base64
import datetime as _dt
import json
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Any


_PLACEHOLDER_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4////fwAJ+wP+X9yT0QAAAABJRU5ErkJggg=="
)


def utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def ensure_dir(path: str | Path) -> Path:
    resolved = Path(path)
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def ensure_parent(path: str | Path) -> Path:
    resolved = Path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return resolved


def read_json(path: str | Path, default: Any) -> Any:
    resolved = Path(path)
    if not resolved.exists():
        return default
    try:
        return json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def write_json(path: str | Path, payload: Any) -> Path:
    resolved = ensure_parent(path)
    resolved.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return resolved


def tail_file_lines(path: str | Path, lines: int) -> list[str]:
    resolved = Path(path)
    if not resolved.exists():
        return []
    content = resolved.read_text(encoding="utf-8", errors="replace").splitlines()
    if lines <= 0:
        return []
    return content[-lines:]


def read_jsonl_tail(path: str | Path, lines: int) -> list[Any]:
    items: list[Any] = []
    for line in tail_file_lines(path, lines):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            items.append(json.loads(stripped))
        except json.JSONDecodeError:
            items.append({"raw": stripped})
    return items


def write_placeholder_png(path: str | Path) -> Path:
    resolved = ensure_parent(path)
    resolved.write_bytes(_PLACEHOLDER_PNG)
    return resolved


def write_text(path: str | Path, content: str) -> Path:
    resolved = ensure_parent(path)
    resolved.write_text(content, encoding="utf-8")
    return resolved


def write_trace_zip(path: str | Path, payload: dict[str, Any]) -> Path:
    resolved = ensure_parent(path)
    with zipfile.ZipFile(resolved, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "trace.json",
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        )
    return resolved


def fetch_text(url: str, timeout: int = 15) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 SuperSpiderSharedTools/1.0 "
                "(compatible; shared-runtime-tooling)"
            )
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
            return {
                "ok": True,
                "url": getattr(response, "geturl", lambda: url)(),
                "status": getattr(response, "status", 200),
                "headers": dict(response.headers.items()),
                "text": body.decode("utf-8", errors="replace"),
                "error": "",
            }
    except (urllib.error.URLError, ValueError) as exc:
        return {
            "ok": False,
            "url": url,
            "status": 0,
            "headers": {},
            "text": "",
            "error": str(exc),
        }

