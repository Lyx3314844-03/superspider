#!/usr/bin/env python3
"""
Shared HTTP cache management helper for the spider framework suite.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _load(path: Path) -> dict:
    if not path.exists():
        return {
            "backend": "file-json",
            "strategy": "revalidate",
            "revalidate_seconds": 3600,
            "entries": {},
        }
    return json.loads(path.read_text(encoding="utf-8"))


def _save(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def cmd_status(args: argparse.Namespace) -> int:
    path = Path(args.path).resolve()
    payload = _load(path)
    entries = payload.get("entries")
    if not isinstance(entries, dict):
        entries = {}
    result = {
        "command": "http-cache status",
        "path": str(path),
        "backend": payload.get("backend", "file-json"),
        "strategy": payload.get("strategy", "revalidate"),
        "revalidate_seconds": payload.get("revalidate_seconds", 3600),
        "entries": len(entries),
        "keys": sorted(entries.keys())[:10],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_clear(args: argparse.Namespace) -> int:
    path = Path(args.path).resolve()
    if path.exists():
        path.unlink()
    print(json.dumps({"command": "http-cache clear", "path": str(path), "cleared": True}, ensure_ascii=False, indent=2))
    return 0


def cmd_seed(args: argparse.Namespace) -> int:
    path = Path(args.path).resolve()
    payload = _load(path)
    payload["backend"] = args.backend
    payload["strategy"] = args.strategy
    payload["revalidate_seconds"] = args.revalidate_seconds
    payload.setdefault("entries", {})[args.url] = {
        "url": args.url,
        "status_code": args.status_code,
        "etag": args.etag,
        "last_modified": args.last_modified,
        "content_hash": args.content_hash,
    }
    _save(path, payload)
    print(json.dumps({"command": "http-cache seed", "path": str(path), "url": args.url}, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage a shared incremental HTTP cache store")
    subparsers = parser.add_subparsers(dest="command", required=True)

    status = subparsers.add_parser("status", help="show cache stats")
    status.add_argument("--path", required=True)
    status.set_defaults(func=cmd_status)

    clear = subparsers.add_parser("clear", help="clear the cache store")
    clear.add_argument("--path", required=True)
    clear.set_defaults(func=cmd_clear)

    seed = subparsers.add_parser("seed", help="seed a cache store entry")
    seed.add_argument("--path", required=True)
    seed.add_argument("--url", required=True)
    seed.add_argument("--status-code", type=int, default=200)
    seed.add_argument("--backend", choices=["file-json", "memory"], default="file-json")
    seed.add_argument("--strategy", choices=["revalidate", "delta-fetch"], default="revalidate")
    seed.add_argument("--revalidate-seconds", type=int, default=3600)
    seed.add_argument("--etag", default="")
    seed.add_argument("--last-modified", default="")
    seed.add_argument("--content-hash", default="")
    seed.set_defaults(func=cmd_seed)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
