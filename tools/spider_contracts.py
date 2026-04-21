from __future__ import annotations

import argparse
import json
from pathlib import Path

from _shared_runtime_tools import read_json, utc_now, write_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Shared scrapy contracts helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for name in ("init", "validate"):
        cmd = subparsers.add_parser(name)
        cmd.add_argument("--project", required=True)

    return parser


def manifest_path(project: Path) -> Path:
    return project / "scrapy-project.json"


def config_path(project: Path) -> Path:
    return project / "spider-framework.yaml"


def contracts_dir(project: Path) -> Path:
    return project / "contracts"


def contracts_manifest_path(project: Path) -> Path:
    return contracts_dir(project) / "spider-contracts.json"


def route_manifest_path(project: Path) -> Path:
    return contracts_dir(project) / "routes.json"


def command_init(args: argparse.Namespace) -> int:
    project = Path(args.project)
    project.mkdir(parents=True, exist_ok=True)
    manifest = read_json(manifest_path(project), {})
    contract_payload = {
        "version": 1,
        "generated_at": utc_now(),
        "project": manifest.get("name", project.name),
        "runtime": manifest.get("runtime", "unknown"),
        "required_files": ["scrapy-project.json", "spider-framework.yaml"],
    }
    write_json(contracts_manifest_path(project), contract_payload)
    write_json(
        route_manifest_path(project),
        {
            "version": 1,
            "routes": [],
        },
    )
    print(
        json.dumps(
            {
                "command": "scrapy contracts init",
                "project": str(project),
                "contracts_manifest": str(contracts_manifest_path(project)),
                "routes_manifest": str(route_manifest_path(project)),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def command_validate(args: argparse.Namespace) -> int:
    project = Path(args.project)
    checks = [
        {
            "name": "scrapy-project.json",
            "path": str(manifest_path(project)),
            "ok": manifest_path(project).exists(),
        },
        {
            "name": "spider-framework.yaml",
            "path": str(config_path(project)),
            "ok": config_path(project).exists(),
        },
        {
            "name": "contracts/spider-contracts.json",
            "path": str(contracts_manifest_path(project)),
            "ok": contracts_manifest_path(project).exists(),
        },
    ]
    summary = "passed" if all(check["ok"] for check in checks) else "failed"
    print(
        json.dumps(
            {
                "command": "scrapy contracts validate",
                "project": str(project),
                "summary": summary,
                "checks": checks,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if summary == "passed" else 1


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "init":
        return command_init(args)
    return command_validate(args)


if __name__ == "__main__":
    raise SystemExit(main())

