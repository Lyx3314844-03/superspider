#!/usr/bin/env python3
"""
Shared spider contracts helper for scrapy-style projects.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _contracts_path(project: Path) -> Path:
    return project / "spider-contracts.json"


def cmd_init(args: argparse.Namespace) -> int:
    project = Path(args.project).resolve()
    project.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "contracts": [
            {
                "name": "demo",
                "url": "https://example.com",
                "scrapes": ["title", "url"],
                "notes": "Fill this with project-specific extraction expectations.",
            }
        ],
    }
    path = _contracts_path(project)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"command": "scrapy contracts init", "path": str(path)}, ensure_ascii=False, indent=2))
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    project = Path(args.project).resolve()
    path = _contracts_path(project)
    if not path.exists():
        print(json.dumps({"command": "scrapy contracts validate", "summary": "failed", "details": f"missing {path}"}, ensure_ascii=False, indent=2))
        return 1
    payload = json.loads(path.read_text(encoding="utf-8"))
    contracts = payload.get("contracts")
    checks = []
    if not isinstance(contracts, list) or not contracts:
        checks.append({"name": "contracts", "status": "failed", "details": "contracts array is required"})
    else:
        for index, contract in enumerate(contracts):
            status = "passed"
            details = "valid"
            if not contract.get("name") or not contract.get("url") or not contract.get("scrapes"):
                status = "failed"
                details = "name, url, and scrapes are required"
            checks.append({"name": f"contract:{index}", "status": status, "details": details})
    summary = "failed" if any(check["status"] == "failed" for check in checks) else "passed"
    print(json.dumps({"command": "scrapy contracts validate", "summary": summary, "checks": checks}, ensure_ascii=False, indent=2))
    return 0 if summary == "passed" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage shared spider contracts for scrapy-style projects")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="create spider-contracts.json")
    init.add_argument("--project", required=True)
    init.set_defaults(func=cmd_init)

    validate = subparsers.add_parser("validate", help="validate spider-contracts.json")
    validate.add_argument("--project", required=True)
    validate.set_defaults(func=cmd_validate)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
