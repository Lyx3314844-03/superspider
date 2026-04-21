from __future__ import annotations

import argparse
import json
from pathlib import Path

from _shared_runtime_tools import ensure_dir, read_json, utc_now, write_json


STATE_FILE = "job-state.json"
MANIFEST_FILE = "job-manifest.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Shared jobdir state helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init")
    init.add_argument("--path", required=True)
    init.add_argument("--runtime", required=True)
    init.add_argument("--url", action="append", default=[])

    for name in ("status", "pause", "resume", "clear"):
        cmd = subparsers.add_parser(name)
        cmd.add_argument("--path", required=True)

    return parser


def state_path(root: Path) -> Path:
    return root / STATE_FILE


def manifest_path(root: Path) -> Path:
    return root / MANIFEST_FILE


def load_state(root: Path) -> dict:
    return read_json(
        state_path(root),
        {
            "version": 1,
            "state": "missing",
            "runtime": "",
            "urls": [],
            "created_at": "",
            "updated_at": "",
        },
    )


def command_init(args: argparse.Namespace) -> int:
    root = ensure_dir(args.path)
    timestamp = utc_now()
    manifest = {
        "version": 1,
        "runtime": args.runtime,
        "urls": list(args.url or []),
        "created_at": timestamp,
    }
    state = {
        "version": 1,
        "state": "running",
        "runtime": args.runtime,
        "urls": list(args.url or []),
        "paused": False,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    write_json(manifest_path(root), manifest)
    write_json(state_path(root), state)
    print(
        json.dumps(
            {
                "command": "jobdir init",
                "path": str(root),
                "state": state["state"],
                "runtime": args.runtime,
                "url_count": len(state["urls"]),
                "urls": state["urls"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def command_status(args: argparse.Namespace) -> int:
    root = Path(args.path)
    state = load_state(root)
    manifest = read_json(manifest_path(root), {})
    print(
        json.dumps(
            {
                "command": "jobdir status",
                "path": str(root),
                "exists": root.exists(),
                "state": state.get("state", "missing"),
                "runtime": state.get("runtime") or manifest.get("runtime", ""),
                "urls": state.get("urls") or manifest.get("urls", []),
                "created_at": state.get("created_at") or manifest.get("created_at", ""),
                "updated_at": state.get("updated_at", ""),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def command_transition(args: argparse.Namespace, next_state: str, paused: bool) -> int:
    root = ensure_dir(args.path)
    state = load_state(root)
    if state.get("created_at", "") == "":
        state["created_at"] = utc_now()
    state["state"] = next_state
    state["paused"] = paused
    state["updated_at"] = utc_now()
    write_json(state_path(root), state)
    print(
        json.dumps(
            {
                "command": f"jobdir {args.command}",
                "path": str(root),
                "state": next_state,
                "paused": paused,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def command_clear(args: argparse.Namespace) -> int:
    root = ensure_dir(args.path)
    removed = []
    for candidate in (state_path(root), manifest_path(root)):
        if candidate.exists():
            candidate.unlink()
            removed.append(str(candidate))
    print(
        json.dumps(
            {
                "command": "jobdir clear",
                "path": str(root),
                "removed": removed,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "init":
        return command_init(args)
    if args.command == "status":
        return command_status(args)
    if args.command == "pause":
        return command_transition(args, "paused", True)
    if args.command == "resume":
        return command_transition(args, "running", False)
    return command_clear(args)


if __name__ == "__main__":
    raise SystemExit(main())

