from __future__ import annotations

import argparse
import json
from pathlib import Path

from _shared_runtime_tools import read_json, utc_now, write_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Shared HTTP cache store helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for name in ("status", "clear"):
        cmd = subparsers.add_parser(name)
        cmd.add_argument("--path", required=True)

    seed = subparsers.add_parser("seed")
    seed.add_argument("--path", required=True)
    seed.add_argument("--url", required=True)
    seed.add_argument("--status-code", type=int, default=200)
    seed.add_argument("--etag", default="")
    seed.add_argument("--last-modified", default="")
    seed.add_argument("--content-hash", default="")

    return parser


def load_cache(path: Path) -> dict:
    return read_json(path, {"version": 1, "entries": {}})


def command_status(args: argparse.Namespace) -> int:
    path = Path(args.path)
    payload = load_cache(path)
    entries = payload.get("entries", {})
    print(
        json.dumps(
            {
                "command": "http-cache status",
                "path": str(path),
                "entry_count": len(entries),
                "urls": sorted(entries.keys()),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def command_seed(args: argparse.Namespace) -> int:
    path = Path(args.path)
    payload = load_cache(path)
    entries = payload.setdefault("entries", {})
    entries[args.url] = {
        "status_code": args.status_code,
        "etag": args.etag,
        "last_modified": args.last_modified,
        "content_hash": args.content_hash,
        "updated_at": utc_now(),
    }
    write_json(path, payload)
    print(
        json.dumps(
            {
                "command": "http-cache seed",
                "path": str(path),
                "url": args.url,
                "status_code": args.status_code,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def command_clear(args: argparse.Namespace) -> int:
    path = Path(args.path)
    write_json(path, {"version": 1, "entries": {}})
    print(
        json.dumps(
            {
                "command": "http-cache clear",
                "path": str(path),
                "entry_count": 0,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "status":
        return command_status(args)
    if args.command == "seed":
        return command_seed(args)
    return command_clear(args)


if __name__ == "__main__":
    raise SystemExit(main())

