from __future__ import annotations

import argparse
import json
from pathlib import Path


OBS_DOCS = (
    "docs/OBSERVABILITY.md",
    "docs/OPERATIONS.md",
    "docs/STABILITY_EVIDENCE.md",
    "docs/web-control-plane-contract.md",
)


def collect_observability_evidence_report(root: Path) -> dict:
    schema = json.loads((root / "contracts" / "runtime-core.schema.json").read_text(encoding="utf-8"))
    manifest = json.loads((root / "contracts" / "ecosystem-manifest.json").read_text(encoding="utf-8"))
    operations = (root / "docs" / "OPERATIONS.md").read_text(encoding="utf-8").lower()
    stability = (root / "docs" / "STABILITY_EVIDENCE.md").read_text(encoding="utf-8").lower()
    checks: list[dict] = []

    docs_present = all((root / relative).exists() for relative in OBS_DOCS)
    checks.append(
        {
            "name": "docs-surface",
            "status": "passed" if docs_present else "failed",
            "details": "observability docs are present" if docs_present else "missing one or more observability docs",
        }
    )

    observability = schema.get("properties", {}).get("observability", {})
    required_fields = set(observability.get("required") or [])
    expected_fields = {"structured_logs", "metrics", "trace", "failure_classification"}
    schema_ok = required_fields == expected_fields
    checks.append(
        {
            "name": "schema-observability-envelope",
            "status": "passed" if schema_ok else "failed",
            "details": "runtime-core schema exposes structured_logs / metrics / trace / failure_classification"
            if schema_ok
            else f"observability required fields={sorted(required_fields)!r}",
        }
    )

    manifest_ok = all("observability" in set(runtime.get("kernel_contracts") or []) for runtime in manifest.get("runtimes", []))
    checks.append(
        {
            "name": "runtime-manifest-observability",
            "status": "passed" if manifest_ok else "failed",
            "details": "all runtimes advertise observability in kernel contracts"
            if manifest_ok
            else "one or more runtimes are missing observability in kernel_contracts",
        }
    )

    tooling_ok = (root / "unified_monitor.py").exists() and (root / "monitoring").exists()
    checks.append(
        {
            "name": "monitoring-surface",
            "status": "passed" if tooling_ok else "failed",
            "details": "unified monitor tooling and monitoring directory exist"
            if tooling_ok
            else "missing unified_monitor.py or monitoring/",
        }
    )

    wording_ok = all(term in operations for term in ("metrics", "trace")) and any(term in stability for term in ("failure", "failed"))
    checks.append(
        {
            "name": "operations-language",
            "status": "passed" if wording_ok else "failed",
            "details": "operations and stability docs mention metrics / trace / failure evidence"
            if wording_ok
            else "operations/stability docs do not mention the required observability vocabulary",
        }
    )

    passed = sum(1 for check in checks if check["status"] == "passed")
    failed = len(checks) - passed
    return {
        "command": "verify-observability-evidence",
        "summary": "passed" if failed == 0 else "failed",
        "summary_text": f"{passed} passed, {failed} failed",
        "exit_code": 0 if failed == 0 else 1,
        "checks": checks,
    }


def render_markdown(report: dict) -> str:
    lines = [
        "# Observability Evidence",
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
    parser = argparse.ArgumentParser(description="Verify observability docs, schema, and suite tooling surfaces")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent), help="repository root path")
    parser.add_argument("--json", action="store_true", help="print JSON report")
    parser.add_argument("--markdown-out", default="", help="optional markdown output path")
    args = parser.parse_args(argv)

    report = collect_observability_evidence_report(Path(args.root).resolve())
    if args.markdown_out:
        Path(args.markdown_out).write_text(render_markdown(report), encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("verify-observability-evidence:", report["summary"])
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
