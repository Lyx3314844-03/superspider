from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


EXPECTED_KERNEL_KEYS = (
    "request",
    "fingerprint",
    "frontier",
    "scheduler",
    "middleware",
    "artifact_store",
    "session_pool",
    "proxy_policy",
    "observability",
    "cache",
)

REQUIRED_SHARED_CONTRACTS = {
    "runtime-core",
    "autoscaled-frontier",
    "incremental-cache",
    "observability-envelope",
}

REQUIRED_CONTROL_PLANE_KEYS = (
    "task_api",
    "result_envelope",
    "artifact_refs",
    "graph_artifact",
    "graph_extract",
)


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


def _run(command: list[str], cwd: Path, timeout: int = 600) -> dict:
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
        "stdout": completed.stdout,
    }


def _extract_json_output(output: str) -> str:
    stripped = output.strip()
    if stripped.startswith("{"):
        return stripped
    first_brace = stripped.find("{")
    return stripped[first_brace:] if first_brace >= 0 else stripped


def _manifest_kernel_contracts(root: Path) -> dict[str, set[str]]:
    manifest = json.loads((root / "contracts" / "ecosystem-manifest.json").read_text(encoding="utf-8"))
    return {
        runtime["name"]: set(runtime.get("kernel_contracts") or [])
        for runtime in manifest["runtimes"]
    }


def _prepare_java(root: Path) -> dict:
    return _run(
        ["mvn", "-q", "-Dmaven.test.skip=true", "compile", "dependency:copy-dependencies"],
        root / "javaspider",
        timeout=900,
    )


def _capability_command(root: Path, framework: str) -> tuple[list[str], Path]:
    if framework == "javaspider":
        return (
            [
                "java",
                "-cp",
                f"{root / 'javaspider' / 'target' / 'classes'}{os.pathsep}{root / 'javaspider' / 'target' / 'dependency' / '*'}",
                "com.javaspider.EnhancedSpider",
                "capabilities",
            ],
            root / "javaspider",
        )
    if framework == "gospider":
        return (["go", "run", "./cmd/gospider", "capabilities"], root / "gospider")
    if framework == "rustspider":
        return (["cargo", "run", "--quiet", "--", "capabilities"], root / "rustspider")
    return ([sys.executable, "-m", "pyspider", "capabilities"], root)


def _validate_payload(
    payload: dict,
    *,
    framework: str,
    runtime: str,
    manifest_kernel_contracts: set[str],
) -> list[str]:
    errors: list[str] = []
    if payload.get("command") != "capabilities":
        errors.append(f"command expected 'capabilities', got {payload.get('command')!r}")
    if payload.get("runtime") != runtime:
        errors.append(f"runtime expected {runtime!r}, got {payload.get('runtime')!r}")

    shared_contracts = set(payload.get("shared_contracts") or [])
    missing_shared = sorted(REQUIRED_SHARED_CONTRACTS - shared_contracts)
    if missing_shared:
        errors.append(f"missing shared_contracts: {', '.join(missing_shared)}")

    kernel_contracts = payload.get("kernel_contracts")
    if not isinstance(kernel_contracts, dict):
        errors.append("kernel_contracts must be an object")
        return errors

    missing_kernel = [key for key in EXPECTED_KERNEL_KEYS if key not in kernel_contracts]
    if missing_kernel:
        errors.append(f"missing kernel_contracts keys: {', '.join(missing_kernel)}")

    for key in EXPECTED_KERNEL_KEYS:
        exports = kernel_contracts.get(key)
        if not isinstance(exports, list) or not exports:
            errors.append(f"kernel_contracts.{key} must be a non-empty list")
            continue
        if any(not isinstance(value, str) or not value.strip() for value in exports):
            errors.append(f"kernel_contracts.{key} must contain non-empty strings only")

    if manifest_kernel_contracts and manifest_kernel_contracts != set(kernel_contracts.keys()):
        errors.append(
            f"manifest kernel_contracts mismatch for {framework}: "
            f"manifest={sorted(manifest_kernel_contracts)!r} runtime={sorted(kernel_contracts.keys())!r}"
        )

    control_plane = payload.get("control_plane")
    if not isinstance(control_plane, dict):
        errors.append("control_plane must be an object")
        return errors

    missing_control_plane = [key for key in REQUIRED_CONTROL_PLANE_KEYS if control_plane.get(key) is not True]
    if missing_control_plane:
        errors.append(f"missing control_plane keys: {', '.join(missing_control_plane)}")

    return errors


def collect_runtime_core_capabilities_report(root: Path) -> dict:
    manifest_contracts = _manifest_kernel_contracts(root)
    frameworks = [
        ("javaspider", "java"),
        ("gospider", "go"),
        ("pyspider", "python"),
        ("rustspider", "rust"),
    ]
    checks: list[dict] = []

    for framework, runtime in frameworks:
        if framework == "javaspider":
            prepare = _prepare_java(root)
            prepare["name"] = f"{framework}-prepare"
            checks.append(prepare)
            if prepare["status"] != "passed":
                continue

        command, cwd = _capability_command(root, framework)
        result = _run(command, cwd, timeout=900)
        result["name"] = framework
        if result["status"] != "passed":
            checks.append(result)
            continue

        try:
            payload = json.loads(_extract_json_output(result["stdout"]))
        except json.JSONDecodeError as exc:
            result["status"] = "failed"
            result["exit_code"] = 1
            result["details"] = f"invalid JSON output: {exc}"
            checks.append(result)
            continue

        errors = _validate_payload(
            payload,
            framework=framework,
            runtime=runtime,
            manifest_kernel_contracts=manifest_contracts.get(framework, set()),
        )
        result["details"] = "kernel capability surface aligned" if not errors else "; ".join(errors)
        result["status"] = "passed" if not errors else "failed"
        result["exit_code"] = 0 if not errors else 1
        checks.append(result)

    passed = sum(1 for check in checks if check["status"] == "passed")
    failed = len(checks) - passed
    return {
        "command": "verify-runtime-core-capabilities",
        "summary": "passed" if failed == 0 else "failed",
        "summary_text": f"{passed} passed, {failed} failed",
        "exit_code": 0 if failed == 0 else 1,
        "checks": checks,
        "required_kernel_contracts": list(EXPECTED_KERNEL_KEYS),
    }


def render_markdown(report: dict) -> str:
    lines = [
        "# Runtime Core Capabilities",
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
    parser = argparse.ArgumentParser(description="Verify unified runtime core capability surfaces across all runtimes")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent), help="repository root path")
    parser.add_argument("--json", action="store_true", help="print JSON report")
    parser.add_argument("--markdown-out", default="", help="optional markdown output path")
    args = parser.parse_args(argv)

    report = collect_runtime_core_capabilities_report(Path(args.root).resolve())
    if args.markdown_out:
        Path(args.markdown_out).write_text(render_markdown(report), encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("verify-runtime-core-capabilities:", report["summary"])
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
