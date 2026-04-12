#!/usr/bin/env python3
"""
Shared JOBDIR helper for the spider framework suite.
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _manifest_path(jobdir: Path) -> Path:
    return jobdir / "job-state.json"


def _default_manifest(jobdir: Path, runtime: str = "", urls: list[str] | None = None) -> dict:
    urls = list(urls or [])
    return {
        "schema_version": 1,
        "runtime": runtime,
        "state": "initialized",
        "jobdir": str(jobdir),
        "created_at": _now(),
        "updated_at": _now(),
        "crawl": {
            "urls": urls,
            "pending_urls": urls,
            "handled_urls": [],
        },
        "artifacts": {
            "checkpoints_dir": str(jobdir / "checkpoints"),
            "cache_dir": str(jobdir / "cache"),
            "exports_dir": str(jobdir / "exports"),
            "browser_dir": str(jobdir / "browser"),
            "control_plane_dir": str(jobdir / "control-plane"),
        },
        "pause_requests": 0,
        "resume_requests": 0,
        "notes": [],
    }


def _load_manifest(jobdir: Path) -> dict:
    path = _manifest_path(jobdir)
    if not path.exists():
        return _default_manifest(jobdir)
    return json.loads(path.read_text(encoding="utf-8"))


def _save_manifest(jobdir: Path, payload: dict) -> Path:
    jobdir.mkdir(parents=True, exist_ok=True)
    for key in ("checkpoints_dir", "cache_dir", "exports_dir", "browser_dir"):
        directory = payload.get("artifacts", {}).get(key)
        if directory:
            Path(directory).mkdir(parents=True, exist_ok=True)
    payload["updated_at"] = _now()
    path = _manifest_path(jobdir)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def cmd_init(args: argparse.Namespace) -> int:
    jobdir = Path(args.path).resolve()
    payload = _default_manifest(jobdir, runtime=args.runtime or "", urls=args.url or [])
    payload["state"] = "ready"
    path = _save_manifest(jobdir, payload)
    print(json.dumps({"command": "jobdir init", "path": str(path), "state": payload["state"]}, ensure_ascii=False, indent=2))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    jobdir = Path(args.path).resolve()
    payload = _load_manifest(jobdir)
    payload["command"] = "jobdir status"
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def cmd_pause(args: argparse.Namespace) -> int:
    jobdir = Path(args.path).resolve()
    payload = _load_manifest(jobdir)
    payload["state"] = "paused"
    payload["pause_requests"] = int(payload.get("pause_requests", 0)) + 1
    payload.setdefault("notes", []).append({"timestamp": _now(), "message": "pause requested"})
    _save_manifest(jobdir, payload)
    print(json.dumps({"command": "jobdir pause", "state": "paused", "path": str(jobdir)}, ensure_ascii=False, indent=2))
    return 0


def cmd_resume(args: argparse.Namespace) -> int:
    jobdir = Path(args.path).resolve()
    payload = _load_manifest(jobdir)
    payload["state"] = "running"
    payload["resume_requests"] = int(payload.get("resume_requests", 0)) + 1
    payload.setdefault("notes", []).append({"timestamp": _now(), "message": "resume requested"})
    _save_manifest(jobdir, payload)
    print(json.dumps({"command": "jobdir resume", "state": "running", "path": str(jobdir)}, ensure_ascii=False, indent=2))
    return 0


def cmd_clear(args: argparse.Namespace) -> int:
    jobdir = Path(args.path).resolve()
    if jobdir.exists():
        shutil.rmtree(jobdir)
    print(json.dumps({"command": "jobdir clear", "path": str(jobdir), "cleared": True}, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage a shared spider job directory")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="initialize a jobdir")
    init.add_argument("--path", required=True)
    init.add_argument("--runtime", default="")
    init.add_argument("--url", action="append", default=[])
    init.set_defaults(func=cmd_init)

    status = subparsers.add_parser("status", help="show jobdir status")
    status.add_argument("--path", required=True)
    status.set_defaults(func=cmd_status)

    pause = subparsers.add_parser("pause", help="mark a jobdir paused")
    pause.add_argument("--path", required=True)
    pause.set_defaults(func=cmd_pause)

    resume = subparsers.add_parser("resume", help="mark a jobdir resumed")
    resume.add_argument("--path", required=True)
    resume.set_defaults(func=cmd_resume)

    clear = subparsers.add_parser("clear", help="remove a jobdir")
    clear.add_argument("--path", required=True)
    clear.set_defaults(func=cmd_clear)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
