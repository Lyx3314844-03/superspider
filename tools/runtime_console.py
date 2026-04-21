from __future__ import annotations

import argparse
import json
from pathlib import Path

from _shared_runtime_tools import read_json, read_jsonl_tail


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Shared runtime console helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    snapshot = subparsers.add_parser("snapshot")
    snapshot.add_argument("--control-plane", required=True)
    snapshot.add_argument("--jobdir", default="")
    snapshot.add_argument("--lines", type=int, default=20)

    tail = subparsers.add_parser("tail")
    tail.add_argument("--control-plane", required=True)
    tail.add_argument("--stream", choices=("events", "results", "both"), default="both")
    tail.add_argument("--lines", type=int, default=20)

    return parser


def load_snapshot(control_plane: Path, lines: int, jobdir: str = "") -> dict:
    events_path = control_plane / "events.jsonl"
    results_path = control_plane / "results.jsonl"
    payload = {
        "control_plane": str(control_plane),
        "events": read_jsonl_tail(events_path, lines),
        "results": read_jsonl_tail(results_path, lines),
        "events_count": len(read_jsonl_tail(events_path, 10_000)),
        "results_count": len(read_jsonl_tail(results_path, 10_000)),
    }
    if jobdir:
        payload["job_state"] = read_json(Path(jobdir) / "job-state.json", {})
    return payload


def command_snapshot(args: argparse.Namespace) -> int:
    payload = {
        "command": "console snapshot",
        **load_snapshot(Path(args.control_plane), args.lines, args.jobdir),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def command_tail(args: argparse.Namespace) -> int:
    control_plane = Path(args.control_plane)
    snapshot = load_snapshot(control_plane, args.lines)
    payload = {
        "command": "console tail",
        "control_plane": str(control_plane),
        "stream": args.stream,
    }
    if args.stream in {"events", "both"}:
        payload["events"] = snapshot["events"]
    if args.stream in {"results", "both"}:
        payload["results"] = snapshot["results"]
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "snapshot":
        return command_snapshot(args)
    return command_tail(args)


if __name__ == "__main__":
    raise SystemExit(main())

