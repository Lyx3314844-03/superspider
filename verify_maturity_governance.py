from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_DOCS = {
    "docs/API_COMPATIBILITY.md": ["kernel contract", "verify_runtime_core_capabilities.py"],
    "docs/COOKBOOK.md": ["verify_runtime_stability.py", "verify_public_install_chain.py"],
    "docs/PLUGIN_GOVERNANCE.md": ["plugin", "manifest"],
    "docs/DEPRECATION_POLICY.md": ["legacy", "migration"],
    "docs/STABILITY_EVIDENCE.md": ["verify_runtime_stability.py", "frontier-stress"],
}


def collect_maturity_governance_report(root: Path) -> dict:
    checks: list[dict] = []

    for relative_path, tokens in REQUIRED_DOCS.items():
        path = root / relative_path
        if not path.exists():
            checks.append(
                {
                    "name": f"doc:{relative_path}",
                    "status": "failed",
                    "details": "required maturity/governance document is missing",
                }
            )
            continue
        content = path.read_text(encoding="utf-8")
        missing = [token for token in tokens if token.lower() not in content.lower()]
        checks.append(
            {
                "name": f"doc:{relative_path}",
                "status": "passed" if not missing else "failed",
                "details": str(path) if not missing else f"missing tokens: {missing!r}",
            }
        )

    release_workflow = (root / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    nightly_workflow = (root / ".github" / "workflows" / "nightly-scale.yml").read_text(encoding="utf-8")
    workflow_tokens = {
        "release-runtime-stability": ("verify_runtime_stability.py", "runtime-stability.json"),
        "nightly-runtime-stability": ("verify_runtime_stability.py", "runtime-stability.json"),
    }
    for name, tokens in workflow_tokens.items():
        content = release_workflow if name.startswith("release") else nightly_workflow
        missing = [token for token in tokens if token not in content]
        checks.append(
            {
                "name": name,
                "status": "passed" if not missing else "failed",
                "details": "workflow includes maturity evidence lane" if not missing else f"missing tokens: {missing!r}",
            }
        )

    passed = sum(1 for check in checks if check["status"] == "passed")
    failed = len(checks) - passed
    return {
        "command": "verify-maturity-governance",
        "summary": "passed" if failed == 0 else "failed",
        "summary_text": f"{passed} passed, {failed} failed",
        "exit_code": 0 if failed == 0 else 1,
        "checks": checks,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify maturity and governance documentation plus workflow wiring")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent), help="repository root path")
    parser.add_argument("--json", action="store_true", help="print report as JSON")
    args = parser.parse_args(argv)

    report = collect_maturity_governance_report(Path(args.root).resolve())
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("verify-maturity-governance:", report["summary"])
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
