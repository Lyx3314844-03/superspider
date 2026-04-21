from __future__ import annotations

import argparse
import json
from pathlib import Path

from _shared_runtime_tools import read_jsonl_tail


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Shared runtime audit helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    snapshot = subparsers.add_parser("snapshot")
    snapshot.add_argument("--control-plane", required=True)
    snapshot.add_argument("--job-name", default="")
    snapshot.add_argument("--lines", type=int, default=20)

    tail = subparsers.add_parser("tail")
    tail.add_argument("--control-plane", required=True)
    tail.add_argument("--job-name", default="")
    tail.add_argument(
        "--stream",
        choices=("events", "results", "audit", "connector", "all"),
        default="all",
    )
    tail.add_argument("--lines", type=int, default=20)

    return parser


def _count_jsonl_records(path: Path) -> int:
    if not path.exists():
        return 0
    return len(path.read_text(encoding="utf-8", errors="replace").splitlines())


def _load_stream_file(path: Path, lines: int) -> dict:
    return {
        "path": str(path),
        "name": path.name,
        "count": _count_jsonl_records(path),
        "records": read_jsonl_tail(path, lines),
    }


def _matching_files(control_plane: Path, suffix: str, job_name: str) -> list[Path]:
    pattern = f"{job_name}-{suffix}.jsonl" if job_name else f"*-{suffix}.jsonl"
    return sorted(control_plane.glob(pattern))


def load_snapshot(control_plane: Path, lines: int, job_name: str = "") -> dict:
    return {
        "control_plane": str(control_plane),
        "job_name": job_name,
        "events": read_jsonl_tail(control_plane / "events.jsonl", lines),
        "results": read_jsonl_tail(control_plane / "results.jsonl", lines),
        "audit_files": [
            _load_stream_file(path, lines)
            for path in _matching_files(control_plane, "audit", job_name)
        ],
        "connector_files": [
            _load_stream_file(path, lines)
            for path in _matching_files(control_plane, "connector", job_name)
        ],
    }


def command_snapshot(args: argparse.Namespace) -> int:
    payload = {
        "command": "audit snapshot",
        **load_snapshot(Path(args.control_plane), args.lines, args.job_name),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def command_tail(args: argparse.Namespace) -> int:
    snapshot = load_snapshot(Path(args.control_plane), args.lines, args.job_name)
    payload = {
        "command": "audit tail",
        "control_plane": snapshot["control_plane"],
        "job_name": snapshot["job_name"],
        "stream": args.stream,
    }

    if args.stream in {"events", "all"}:
        payload["events"] = snapshot["events"]
    if args.stream in {"results", "all"}:
        payload["results"] = snapshot["results"]
    if args.stream in {"audit", "all"}:
        payload["audit_files"] = snapshot["audit_files"]
    if args.stream in {"connector", "all"}:
        payload["connector_files"] = snapshot["connector_files"]

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "snapshot":
        return command_snapshot(args)
    return command_tail(args)


if __name__ == "__main__":
    raise SystemExit(main())
