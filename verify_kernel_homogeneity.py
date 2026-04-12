from __future__ import annotations

import argparse
import json
from pathlib import Path

import verify_runtime_core_capabilities


def collect_kernel_homogeneity_report(root: Path) -> dict:
    schema = json.loads((root / "contracts" / "runtime-core.schema.json").read_text(encoding="utf-8"))
    manifest = json.loads((root / "contracts" / "ecosystem-manifest.json").read_text(encoding="utf-8"))
    contract_doc = (root / "docs" / "framework-contract.md").read_text(encoding="utf-8")
    checks: list[dict] = []

    docs_present = (root / "docs" / "KERNEL_HOMOGENEITY.md").exists()
    checks.append(
        {
            "name": "docs-surface",
            "status": "passed" if docs_present else "failed",
            "details": "kernel homogeneity guide is present" if docs_present else "missing docs/KERNEL_HOMOGENEITY.md",
        }
    )

    required_keys = set(schema.get("required") or [])
    expected_keys = set(verify_runtime_core_capabilities.EXPECTED_KERNEL_KEYS)
    schema_ok = required_keys == expected_keys and expected_keys.issubset(set(schema.get("properties", {}).keys()))
    checks.append(
        {
            "name": "runtime-core-schema",
            "status": "passed" if schema_ok else "failed",
            "details": "runtime-core schema matches canonical kernel keys"
            if schema_ok
            else f"schema keys={sorted(required_keys)!r} expected={sorted(expected_keys)!r}",
        }
    )

    manifest_sets = {
        runtime["name"]: set(runtime.get("kernel_contracts") or [])
        for runtime in manifest.get("runtimes", [])
    }
    manifest_ok = bool(manifest_sets) and all(kernel_set == expected_keys for kernel_set in manifest_sets.values())
    checks.append(
        {
            "name": "manifest-alignment",
            "status": "passed" if manifest_ok else "failed",
            "details": "all runtimes advertise the same kernel contract set"
            if manifest_ok
            else f"manifest kernel sets={ {name: sorted(values) for name, values in manifest_sets.items()}!r }",
        }
    )

    normalized_contract = contract_doc.lower()
    documented_terms = ("frontier", "scheduler", "artifact_store", "session_pool", "proxy_policy", "observability", "cache")
    documentation_ok = all(term in normalized_contract for term in documented_terms)
    checks.append(
        {
            "name": "contract-documentation",
            "status": "passed" if documentation_ok else "failed",
            "details": "framework contract documents the shared kernel vocabulary"
            if documentation_ok
            else "framework contract is missing one or more shared kernel terms",
        }
    )

    vendored_surface_ok = all(
        (root / "superspider_control_plane" / relative).exists()
        for relative in ("catalog.py", "compiler.py", "dispatcher.py", "models.py")
    )
    checks.append(
        {
            "name": "control-plane-vendor-surface",
            "status": "passed" if vendored_surface_ok else "failed",
            "details": "vendored control-plane helpers are present for cross-runtime routing"
            if vendored_surface_ok
            else "missing vendored superspider control-plane helper modules",
        }
    )

    passed = sum(1 for check in checks if check["status"] == "passed")
    failed = len(checks) - passed
    return {
        "command": "verify-kernel-homogeneity",
        "summary": "passed" if failed == 0 else "failed",
        "summary_text": f"{passed} passed, {failed} failed",
        "exit_code": 0 if failed == 0 else 1,
        "checks": checks,
        "expected_kernel_keys": list(verify_runtime_core_capabilities.EXPECTED_KERNEL_KEYS),
    }


def render_markdown(report: dict) -> str:
    lines = [
        "# Kernel Homogeneity",
        "",
        f"Summary: {report['summary_text']}",
        "",
        "| Check | Status | Details |",
        "| --- | --- | --- |",
    ]
    for check in report["checks"]:
        lines.append(f"| {check['name']} | {check['status']} | {check['details']} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify that all runtimes expose the same shared kernel contract surface")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent), help="repository root path")
    parser.add_argument("--json", action="store_true", help="print JSON report")
    parser.add_argument("--markdown-out", default="", help="optional markdown output path")
    args = parser.parse_args(argv)

    report = collect_kernel_homogeneity_report(Path(args.root).resolve())
    if args.markdown_out:
        Path(args.markdown_out).write_text(render_markdown(report), encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("verify-kernel-homogeneity:", report["summary"])
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
