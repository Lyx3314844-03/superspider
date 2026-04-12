from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .catalog import build_worker_catalog
from .compiler import compile_job
from .dispatcher import dispatch_job
from .models import WorkerCapability


def _load_json(path: str) -> object:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _load_workers(path: str) -> list[WorkerCapability]:
    payload = _load_json(path)
    if isinstance(payload, list) and payload and isinstance(payload[0], dict) and "worker_id" in payload[0]:
        return [WorkerCapability(**item) for item in payload]
    if isinstance(payload, list):
        catalog_input = {}
        for item in payload:
            if not isinstance(item, dict):
                continue
            if "name" in item and "payload" in item:
                catalog_input[str(item["name"])] = dict(item["payload"])
        return build_worker_catalog(catalog_input)
    if isinstance(payload, dict):
        return build_worker_catalog({str(name): dict(value) for name, value in payload.items()})
    raise ValueError("workers file must be a list of workers, a framework->payload map, or a list of {name, payload}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the vendored SuperSpider control-plane compiler and dispatcher")
    subparsers = parser.add_subparsers(dest="command", required=True)

    compile_parser = subparsers.add_parser("compile", help="compile a job spec")
    compile_parser.add_argument("--job", required=True, help="path to a Spider JobSpec JSON file")

    dispatch_parser = subparsers.add_parser("dispatch", help="dispatch a job spec against a worker catalog")
    dispatch_parser.add_argument("--job", required=True, help="path to a Spider JobSpec JSON file")
    dispatch_parser.add_argument("--workers", required=True, help="path to worker or capability catalog JSON")

    args = parser.parse_args(argv)
    job = _load_json(args.job)
    if not isinstance(job, dict):
        raise SystemExit("job file must contain a JSON object")

    if args.command == "compile":
        print(json.dumps(asdict(compile_job(job)), ensure_ascii=False, indent=2))
        return 0

    workers = _load_workers(args.workers)
    print(json.dumps(asdict(dispatch_job(job, workers)), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
