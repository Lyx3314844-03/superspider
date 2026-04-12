#!/usr/bin/env python3
"""
Shared runtime console helper for control-plane and jobdir inspection.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _tail(path: Path, lines: int) -> list[str]:
    if not path.exists():
        return []
    content = path.read_text(encoding="utf-8").splitlines()
    return content[-lines:]


def cmd_snapshot(args: argparse.Namespace) -> int:
    control_plane = Path(args.control_plane).resolve()
    jobdir = Path(args.jobdir).resolve() if args.jobdir else None
    payload = {
        "command": "console snapshot",
        "control_plane": str(control_plane),
        "results_exists": (control_plane / "results.jsonl").exists(),
        "events_exists": (control_plane / "events.jsonl").exists(),
        "results_tail": _tail(control_plane / "results.jsonl", args.lines),
        "events_tail": _tail(control_plane / "events.jsonl", args.lines),
        "jobdir": None,
    }
    if jobdir:
        manifest = jobdir / "job-state.json"
        if manifest.exists():
            payload["jobdir"] = json.loads(manifest.read_text(encoding="utf-8"))
        else:
            payload["jobdir"] = {"path": str(jobdir), "state": "missing"}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def cmd_tail(args: argparse.Namespace) -> int:
    control_plane = Path(args.control_plane).resolve()
    targets = []
    if args.stream in {"events", "both"}:
        targets.append(("events", control_plane / "events.jsonl"))
    if args.stream in {"results", "both"}:
        targets.append(("results", control_plane / "results.jsonl"))
    payload = {"command": "console tail", "streams": {}}
    for name, path in targets:
        payload["streams"][name] = _tail(path, args.lines)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect shared runtime control-plane artifacts")
    subparsers = parser.add_subparsers(dest="command", required=True)

    snapshot = subparsers.add_parser("snapshot", help="show a point-in-time console snapshot")
    snapshot.add_argument("--control-plane", default="artifacts/control-plane")
    snapshot.add_argument("--jobdir", default="")
    snapshot.add_argument("--lines", type=int, default=10)
    snapshot.set_defaults(func=cmd_snapshot)

    tail = subparsers.add_parser("tail", help="tail control-plane streams")
    tail.add_argument("--control-plane", default="artifacts/control-plane")
    tail.add_argument("--stream", choices=["events", "results", "both"], default="both")
    tail.add_argument("--lines", type=int, default=20)
    tail.set_defaults(func=cmd_tail)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
