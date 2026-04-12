from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path


def _run(command: list[str], cwd: Path) -> dict:
    executable = shutil.which(command[0]) or shutil.which(f"{command[0]}.cmd")
    if executable:
        command = [executable, *command[1:]]
    completed = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "command": command,
        "exit_code": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
        "status": "passed" if completed.returncode == 0 else "failed",
    }


def _extract_json_payload(stdout: str) -> dict:
    stripped = stdout.strip()
    first_brace = stripped.find("{")
    if first_brace < 0:
        raise ValueError("workflow replay did not emit JSON payload")
    return json.loads(stripped[first_brace:])


def _action_prefixes_satisfied(actions: list[str], expected: list[str]) -> bool:
    return all(any(action.startswith(prefix) for action in actions) for prefix in expected)


def _artifact_candidates(payload: dict) -> list[str]:
    artifacts = payload.get("artifacts")
    if isinstance(artifacts, list):
        return [str(item) for item in artifacts if str(item).strip()]
    if isinstance(artifacts, dict):
        candidates: list[str] = []
        for value in artifacts.values():
            if isinstance(value, str) and value.strip():
                candidates.append(value)
            elif isinstance(value, dict):
                path = value.get("path")
                if isinstance(path, str) and path.strip():
                    candidates.append(path)
        return candidates
    return []


def run_javaspider_captcha_summary(root: Path) -> dict:
    java_root = root / "javaspider"
    replay_spec_path = root / "replays" / "workflow" / "java-captcha-recovery.json"
    replay_spec = json.loads(replay_spec_path.read_text(encoding="utf-8"))

    compile_check = _run(
        ["mvn", "-q", "-DskipTests", "compile", "dependency:copy-dependencies"],
        java_root,
    )
    workflow_tests = _run(
        ["mvn", "-q", "-Dtest=WorkflowSpiderTest,SeleniumWorkflowExecutionContextTest", "test"],
        java_root,
    )

    classpath = f"target/classes{os.pathsep}target/dependency/*"
    replay_check = _run(
        [
            "java",
            "-cp",
            classpath,
            "com.javaspider.cli.WorkflowReplayCLI",
            "--file",
            str(replay_spec_path),
        ],
        java_root,
    )

    payload = {}
    captcha_closed_loop_ready = False
    audit_ready = False
    artifact_ready = False
    replay_ready = replay_check["status"] == "passed"

    if replay_ready:
        payload = _extract_json_payload(replay_check["stdout"])
        audit_types = [event.get("type") for event in payload.get("audit_events", [])]
        actions = payload.get("actions", [])
        audit_ready = all(expected in audit_types for expected in replay_spec["expected_audit_types"])
        captcha_closed_loop_ready = (
            payload.get("state") == "succeeded"
            and _action_prefixes_satisfied(actions, replay_spec["expected_actions"])
            and "captcha.detected" in audit_types
            and "captcha.solved" in audit_types
            and "job.completed" in audit_types
        )

        output_path = java_root / replay_spec["output"]["path"]
        artifact_candidates = _artifact_candidates(payload)
        artifact_path = java_root / artifact_candidates[0] if artifact_candidates else java_root
        artifact_ready = (
            output_path.exists()
            and artifact_candidates
            and artifact_path.exists()
            and replay_spec["expected_artifact_contains"] in artifact_path.read_text(encoding="utf-8")
        )

    checks = [
        {
            "name": "compile-dependencies",
            "status": compile_check["status"],
            "details": compile_check["stderr"] or compile_check["stdout"] or "compile + dependency copy completed",
        },
        {
            "name": "workflow-tests",
            "status": workflow_tests["status"],
            "details": workflow_tests["stderr"] or workflow_tests["stdout"] or "workflow tests completed",
        },
        {
            "name": "workflow-replay",
            "status": replay_check["status"],
            "details": replay_check["stderr"] or replay_check["stdout"] or "workflow replay completed",
        },
        {
            "name": "captcha-closed-loop",
            "status": "passed" if captcha_closed_loop_ready else "failed",
            "details": "audit trail includes detect/solve/complete and replay actions resume the flow",
        },
        {
            "name": "replay-artifact",
            "status": "passed" if artifact_ready else "failed",
            "details": "workflow replay persisted JSON output and artifact content",
        },
    ]

    passed = sum(1 for check in checks if check["status"] == "passed")
    failed = len(checks) - passed
    return {
        "command": "verify-javaspider-captcha-summary",
        "summary": "failed" if failed else "passed",
        "summary_text": f"{passed} passed, {failed} failed",
        "exit_code": 1 if failed else 0,
        "runtime": "java",
        "checks": checks,
        "metrics": {
            "checks_passed": passed,
            "checks_failed": failed,
            "checks_total": len(checks),
            "pass_rate": round(passed / len(checks), 4) if checks else 0.0,
            "replay_ready": replay_ready,
            "audit_ready": audit_ready,
            "captcha_closed_loop_ready": captcha_closed_loop_ready,
            "artifact_ready": artifact_ready,
            "audit_event_count": len(payload.get("audit_events", [])),
            "action_count": len(payload.get("actions", [])),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run JavaSpider captcha recovery summary checks")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent), help="repository root path")
    parser.add_argument("--json", action="store_true", help="print summary as JSON")
    args = parser.parse_args(argv)

    report = run_javaspider_captcha_summary(Path(args.root).resolve())
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("verify-javaspider-captcha-summary:", report["summary"])
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
