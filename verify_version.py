from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path


TARGET_SPECS = (
    {
        "path": "javaspider/pom.xml",
        "pattern": r"<version>([^<]+)</version>",
    },
    {
        "path": "pyspider/__init__.py",
        "pattern": r'__version__\s*=\s*"([^"]+)"',
    },
    {
        "path": "pyspider/setup.py",
        "pattern": r'version\s*=\s*"([^"]+)"',
    },
    {
        "path": "rustspider/Cargo.toml",
        "pattern": r'^version\s*=\s*"([^"]+)"',
    },
    {
        "path": "helm/superspider/Chart.yaml",
        "label": "helm/superspider/Chart.yaml:version",
        "pattern": r"^version:\s*([^\s]+)",
    },
    {
        "path": "helm/superspider/Chart.yaml",
        "label": "helm/superspider/Chart.yaml:appVersion",
        "pattern": r'^appVersion:\s*"([^"]+)"',
    },
)


def read_expected_version(root: Path) -> str:
    return (root / "VERSION").read_text(encoding="utf-8").strip()


def extract_version(path: Path, pattern: str) -> str | None:
    match = re.search(pattern, path.read_text(encoding="utf-8"), re.MULTILINE)
    return match.group(1).strip() if match else None


def _extract_tag_version(git_ref: str | None) -> str | None:
    if not git_ref or not git_ref.startswith("refs/tags/"):
        return None
    tag = git_ref.removeprefix("refs/tags/")
    if not tag.startswith("v"):
        return None
    return tag[1:]


def collect_version_report(root: Path, git_ref: str | None = None) -> dict:
    expected_version = read_expected_version(root)
    targets = []
    checks = [
        {
            "name": "root-version",
            "status": "passed" if expected_version else "failed",
            "details": expected_version or "missing VERSION value",
        }
    ]

    has_failure = not bool(expected_version)

    for spec in TARGET_SPECS:
        path = root / spec["path"]
        actual_version = extract_version(path, spec["pattern"]) if path.exists() else None
        status = "passed" if actual_version == expected_version else "failed"
        target_label = spec.get("label", spec["path"])
        targets.append(
            {
                "path": target_label,
                "expected": expected_version,
                "actual": actual_version,
                "status": status,
            }
        )
        if status != "passed":
            has_failure = True

    tag_version = _extract_tag_version(git_ref)
    if git_ref:
        if git_ref.startswith("refs/tags/") and tag_version is None:
            checks.append(
                {
                    "name": "git-tag",
                    "status": "failed",
                    "details": f"unsupported git ref: {git_ref}",
                }
            )
            has_failure = True
        elif tag_version is not None:
            tag_matches = tag_version == expected_version
            checks.append(
                {
                    "name": "git-tag",
                    "status": "passed" if tag_matches else "failed",
                    "details": f"expected v{expected_version}, got v{tag_version}",
                }
            )
            if not tag_matches:
                has_failure = True
        else:
            checks.append(
                {
                    "name": "git-tag",
                    "status": "skipped",
                    "details": f"non-tag ref: {git_ref}",
                }
            )

    exit_code = 1 if has_failure else 0
    return {
        "command": "verify-version",
        "summary": "failed" if has_failure else "passed",
        "exit_code": exit_code,
        "expected_version": expected_version,
        "checks": checks,
        "targets": targets,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate single-repository release version consistency")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent), help="repository root path")
    parser.add_argument("--json", action="store_true", help="print JSON report")
    parser.add_argument("--git-ref", default=os.environ.get("GITHUB_REF"), help="Git ref to validate against VERSION")
    args = parser.parse_args(argv)

    report = collect_version_report(Path(args.root), git_ref=args.git_ref)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("verify-version summary:", report["summary"])
        print("expected version:", report["expected_version"])
        for target in report["targets"]:
            print(f"- {target['path']}: {target['status']} ({target['actual']})")

    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
