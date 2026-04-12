from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def _resolve_command(command: list[str]) -> list[str]:
    if not command:
        return command
    executable = (
        shutil.which(command[0])
        or shutil.which(f"{command[0]}.cmd")
        or shutil.which(f"{command[0]}.exe")
    )
    if executable:
        return [executable, *command[1:]]
    return command


def _run(command: list[str], cwd: Path, timeout: int = 900) -> dict:
    resolved = _resolve_command(command)
    completed = subprocess.run(
        resolved,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )
    details = "\n".join(
        part for part in (completed.stdout.strip(), completed.stderr.strip()) if part
    ).strip()
    return {
        "command": resolved,
        "exit_code": completed.returncode,
        "status": "passed" if completed.returncode == 0 else "failed",
        "details": details or "command completed",
    }


def collect_result_contracts_report(root: Path) -> dict:
    checks: list[dict] = []

    contracts = root / "contracts"
    required_contracts = (
        "graph.schema.json",
        "result-artifact.schema.json",
        "result-envelope.schema.json",
    )
    missing_contracts = [name for name in required_contracts if not (contracts / name).exists()]
    checks.append(
        {
            "name": "contract-schemas",
            "status": "passed" if not missing_contracts else "failed",
            "details": "graph/result schemas present"
            if not missing_contracts
            else f"missing schemas: {missing_contracts!r}",
        }
    )

    contract_doc = (root / "docs" / "web-control-plane-contract.md").read_text(encoding="utf-8")
    doc_tokens = [
        "contracts/result-envelope.schema.json",
        "contracts/result-artifact.schema.json",
        "contracts/graph.schema.json",
        "artifacts.graph",
        "artifact_refs.graph",
    ]
    missing_doc_tokens = [token for token in doc_tokens if token not in contract_doc]
    checks.append(
        {
            "name": "control-plane-doc",
            "status": "passed" if not missing_doc_tokens else "failed",
            "details": "web control-plane doc references result and graph contracts"
            if not missing_doc_tokens
            else f"missing doc tokens: {missing_doc_tokens!r}",
        }
    )

    runtime_checks = [
        (
            "gospider-web-result-contract",
            ["go", "test", "./web", "-run", "^TestServerTaskLifecycleProducesResultsAndLogs$"],
            root / "gospider",
        ),
        (
            "javaspider-web-result-contract",
            ["mvn", "-q", "clean", "-Dtest=SpiderControllerTest", "test"],
            root / "javaspider",
        ),
    ]

    for name, command, cwd in runtime_checks:
        result = _run(command, cwd)
        result["name"] = name
        checks.append(result)

    static_contract_checks = [
        (
            "pyspider-web-source-contract",
            root / "pyspider" / "web" / "app.py",
            ["artifact_refs", "build_graph_artifact", "'graph'"],
        ),
        (
            "rustspider-web-source-contract",
            root / "rustspider" / "src" / "web" / "mod.rs",
            ["artifact_refs", "persist_graph_artifact", "\"graph\""],
        ),
        (
            "go-web-source-contract",
            root / "gospider" / "web" / "server.go",
            ["ArtifactRefs", "buildGraphArtifact", "\"graph\""],
        ),
        (
            "java-web-source-contract",
            root / "javaspider" / "src" / "main" / "java" / "com" / "javaspider" / "web" / "controller" / "SpiderController.java",
            ["artifact_refs", "buildArtifactsPayload", "\"graph\""],
        ),
    ]
    for name, path, tokens in static_contract_checks:
        content = path.read_text(encoding="utf-8")
        missing = [token for token in tokens if token not in content]
        checks.append(
            {
                "name": name,
                "status": "passed" if not missing else "failed",
                "details": "runtime source carries graph artifact refs"
                if not missing
                else f"missing tokens: {missing!r}",
            }
        )

    passed = sum(1 for check in checks if check["status"] == "passed")
    failed = len(checks) - passed
    return {
        "command": "verify-result-contracts",
        "summary": "passed" if failed == 0 else "failed",
        "summary_text": f"{passed} passed, {failed} failed",
        "exit_code": 0 if failed == 0 else 1,
        "checks": checks,
    }


def render_markdown(report: dict) -> str:
    lines = [
        "# Result Contracts",
        "",
        f"Summary: {report['summary_text']}",
        "",
        "| Check | Status |",
        "| --- | --- |",
    ]
    for check in report["checks"]:
        lines.append(f"| {check['name']} | {check['status']} |")
    lines.append("")
    for check in report["checks"]:
        lines.append(f"## {check['name']}")
        lines.append("")
        lines.append(f"- Status: {check['status']}")
        if "command" in check:
            lines.append(f"- Command: `{' '.join(check['command'])}`")
        lines.append(f"- Details: {check['details']}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify graph/result/artifact contracts across schemas, docs, and runtime web surfaces")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent), help="repository root path")
    parser.add_argument("--json", action="store_true", help="print JSON report")
    parser.add_argument("--markdown-out", default="", help="optional markdown output path")
    args = parser.parse_args(argv)

    report = collect_result_contracts_report(Path(args.root).resolve())
    if args.markdown_out:
        Path(args.markdown_out).write_text(render_markdown(report), encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("verify-result-contracts:", report["summary"])
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
