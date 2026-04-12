from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def _resolve_superspider_root(root: Path) -> Path:
    override = os.environ.get("SUPERSPIDER_ROOT", "").strip()
    if override:
        return Path(override).resolve()
    return (root.parent / "superspider").resolve()


def collect_report(root: Path) -> dict:
    superspider_root = _resolve_superspider_root(root)
    script = superspider_root / "verify_control_plane_postgres_backend.py"
    if not script.exists():
        return {
            "command": "verify-superspider-control-plane-postgres-backend",
            "summary": "failed",
            "summary_text": f"missing script: {script}",
            "exit_code": 1,
            "checks": [],
        }

    completed = subprocess.run(
        [sys.executable, str(script), "--root", str(superspider_root), "--json"],
        cwd=superspider_root,
        capture_output=True,
        text=True,
        check=False,
    )
    payload = None
    if completed.stdout.strip():
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError:
            payload = None
    if isinstance(payload, dict):
        payload = dict(payload)
        payload["command"] = "verify-superspider-control-plane-postgres-backend"
        return payload
    details = "\n".join(part for part in (completed.stdout.strip(), completed.stderr.strip()) if part).strip()
    return {
        "command": "verify-superspider-control-plane-postgres-backend",
        "summary": "passed" if completed.returncode == 0 else "failed",
        "summary_text": details or "superspider control-plane postgres backend gate",
        "exit_code": completed.returncode,
        "checks": [],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the superspider Postgres backend gate from the spider repo")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent), help="spider repository root path")
    parser.add_argument("--json", action="store_true", help="print JSON report")
    args = parser.parse_args(argv)

    report = collect_report(Path(args.root).resolve())
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("verify-superspider-control-plane-postgres-backend:", report["summary"])
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
