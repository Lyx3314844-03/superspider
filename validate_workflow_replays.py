from __future__ import annotations

import argparse
import json
import os
import platform
import re
import subprocess
import tempfile
from pathlib import Path


SUPPORTED_FRAMEWORKS = {"javaspider", "gospider", "pyspider", "rustspider"}


def replay_root(root: Path) -> Path:
    return root / "replays" / "workflow"


def load_replay(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("workflow replay root must be a JSON object")
    return data


def discover_workflow_replays(root: Path) -> dict[str, Path]:
    return {path.stem: path for path in sorted(replay_root(root).glob("*.json"))}


def _extract_json_payload(stdout: str) -> str:
    stripped = stdout.strip()
    first_brace = stripped.find("{")
    return stripped[first_brace:] if first_brace >= 0 else stripped


def _run_process(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)


def _check(name: str, status: str, path: Path, details: str) -> dict:
    return {
        "name": name,
        "status": status,
        "path": str(path),
        "details": details,
    }


def _fixture_contains_selector(content: str, selector: str) -> bool:
    if not selector:
        return True
    if selector.startswith("#"):
        token = selector[1:]
        return f'id="{token}"' in content or f"id='{token}'" in content
    if selector.startswith("."):
        token = selector[1:]
        return re.search(r'class=["\'][^"\']*\b' + re.escape(token) + r'\b[^"\']*["\']', content) is not None
    if selector.startswith("[name=") and selector.endswith("]"):
        token = selector[len("[name="):-1].strip("\"'")
        return f'name="{token}"' in content or f"name='{token}'" in content
    if selector.startswith("[id=") and selector.endswith("]"):
        token = selector[len("[id="):-1].strip("\"'")
        return f'id="{token}"' in content or f"id='{token}'" in content
    return f"<{selector}" in content


def _prepare_java(root: Path) -> tuple[bool, str]:
    command = ["mvn", "-q", "compile", "dependency:copy-dependencies"]
    if platform.system() == "Windows":
        command = ["cmd", "/c", *command]
    try:
        completed = _run_process(command, root / "javaspider")
    except FileNotFoundError as exc:
        return False, f"command not found: {exc}"
    if completed.returncode == 0:
        return True, completed.stdout.strip()
    details = "\n".join(part for part in (completed.stdout.strip(), completed.stderr.strip()) if part).strip()
    return False, details or "java compile failed"


def _run_java_replay(root: Path, replay: dict, replay_path: Path) -> dict:
    prepared, details = _prepare_java(root)
    if not prepared:
        return _check(replay["name"], "failed", replay_path, details)

    fixture_content = (root / replay["fixture_path"]).read_text(encoding="utf-8")
    for step in replay.get("steps", []):
        if step.get("type") not in {"TYPE", "CLICK"}:
            continue
        selector = step.get("selector", "")
        if not _fixture_contains_selector(fixture_content, selector):
            return _check(replay["name"], "failed", replay_path, f"fixture missing selector {selector!r}")
    with tempfile.TemporaryDirectory() as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        artifact_path = tmpdir / "workflow-artifact.txt"
        output_path = tmpdir / "workflow-output.json"

        spec = json.loads(json.dumps(replay))
        spec["output"]["path"] = str(output_path)
        spec.setdefault("metadata", {})["mock_html"] = fixture_content
        for step in spec.get("steps", []):
            metadata = step.get("metadata")
            if isinstance(metadata, dict) and "artifact" in metadata:
                metadata["artifact"] = str(artifact_path)
            if step.get("type") == "SCREENSHOT":
                step["value"] = str(artifact_path)

        spec_path = tmpdir / "workflow-replay.json"
        spec_path.write_text(json.dumps(spec), encoding="utf-8")

        classpath = f"target/classes{os.pathsep}target/dependency/*"
        completed = _run_process(
            ["java", "-cp", classpath, "com.javaspider.cli.WorkflowReplayCLI", "--file", str(spec_path)],
            root / "javaspider",
        )
        if completed.returncode != 0:
            details = "\n".join(part for part in (completed.stdout.strip(), completed.stderr.strip()) if part).strip()
            return _check(replay["name"], "failed", replay_path, details or "workflow replay exited non-zero")

        payload = json.loads(_extract_json_payload(completed.stdout))
        audit_types = [event["type"] for event in payload.get("audit_events", [])]
        missing_audit = [event for event in replay.get("expected_audit_types", []) if event not in audit_types]
        actions = payload.get("actions", [])
        if payload.get("state") != "succeeded":
            return _check(replay["name"], "failed", replay_path, f"expected succeeded state, got {payload.get('state')!r}")
        if payload.get("extract") != replay.get("expected_extract"):
            return _check(replay["name"], "failed", replay_path, f"unexpected extract payload: {payload.get('extract')!r}")
        if missing_audit:
            return _check(replay["name"], "failed", replay_path, f"missing audit events: {missing_audit!r}")
        for expected_action in replay.get("expected_actions", []):
            if not any(str(action).startswith(expected_action) for action in actions):
                return _check(replay["name"], "failed", replay_path, f"missing workflow action prefix: {expected_action!r}")
        if not artifact_path.exists():
            return _check(replay["name"], "failed", replay_path, "workflow replay artifact was not created")
        if replay.get("expected_artifact_contains") not in artifact_path.read_text(encoding="utf-8"):
            return _check(replay["name"], "failed", replay_path, "workflow replay artifact content mismatch")
        return _check(replay["name"], "passed", replay_path, "valid java workflow replay")


def _run_go_replay(root: Path, replay: dict, replay_path: Path) -> dict:
    with tempfile.TemporaryDirectory() as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        spec = json.loads(json.dumps(replay))
        spec.setdefault("output", {})["directory"] = str(tmpdir)
        spec["output"]["path"] = str(tmpdir / "browser-result.json")
        spec["output"]["artifact_prefix"] = "browser-replay"
        mock_browser = spec.setdefault("metadata", {}).setdefault("mock_browser", {})
        fixture_path = root / mock_browser["html_fixture_path"]
        mock_browser["html_fixture_path"] = str(fixture_path)

        spec_path = tmpdir / "go-browser-replay.json"
        spec_path.write_text(json.dumps(spec), encoding="utf-8")

        completed = _run_process(
            ["go", "run", "./cmd/gospider", "job", "--file", str(spec_path)],
            root / "gospider",
        )
        if completed.returncode != 0:
            details = "\n".join(part for part in (completed.stdout.strip(), completed.stderr.strip()) if part).strip()
            return _check(replay["name"], "failed", replay_path, details or "browser replay exited non-zero")

        payload = json.loads(_extract_json_payload(completed.stdout))
        if payload.get("state") != "succeeded":
            return _check(replay["name"], "failed", replay_path, f"expected succeeded state, got {payload.get('state')!r}")
        if replay["expected_recovery_strategy"] != payload.get("recovery", {}).get("strategy"):
            return _check(replay["name"], "failed", replay_path, f"unexpected recovery payload: {payload.get('recovery')!r}")
        warnings = payload.get("warnings", [])
        if replay["expected_warning"] not in warnings:
            return _check(replay["name"], "failed", replay_path, f"warning not preserved: {warnings!r}")
        text = payload.get("text", "")
        for token in replay.get("expected_text_tokens", []):
            if token not in text:
                return _check(replay["name"], "failed", replay_path, f"missing text token: {token!r}")

        artifact_refs = payload.get("artifact_refs", {})
        console_path = artifact_refs.get("console", {}).get("path", "")
        network_path = artifact_refs.get("network", {}).get("path", "")
        har_path = artifact_refs.get("har", {}).get("path", "")
        if not console_path or not Path(console_path).exists():
            return _check(replay["name"], "failed", replay_path, "console artifact missing")
        if replay["expected_console_text"] not in Path(console_path).read_text(encoding="utf-8"):
            return _check(replay["name"], "failed", replay_path, "console artifact content mismatch")
        if not network_path or not Path(network_path).exists():
            return _check(replay["name"], "failed", replay_path, "network artifact missing")
        if replay["expected_network_url"] not in Path(network_path).read_text(encoding="utf-8"):
            return _check(replay["name"], "failed", replay_path, "network artifact content mismatch")
        if not har_path or not Path(har_path).exists():
            return _check(replay["name"], "failed", replay_path, "har artifact missing")
        if replay["expected_har_url"] not in Path(har_path).read_text(encoding="utf-8"):
            return _check(replay["name"], "failed", replay_path, "har artifact content mismatch")
        actions = payload.get("metadata", {}).get("browser_actions", [])
        for expected_action in replay.get("expected_actions", []):
            if expected_action not in actions:
                return _check(replay["name"], "failed", replay_path, f"missing browser action: {expected_action!r}")
        return _check(replay["name"], "passed", replay_path, "valid go browser replay")


def _run_py_replay(root: Path, replay: dict, replay_path: Path) -> dict:
    with tempfile.TemporaryDirectory() as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        spec = json.loads(json.dumps(replay))
        spec["output"]["path"] = str(tmpdir / "py-replay-output.json")
        spec_path = tmpdir / "py-replay.json"
        spec_path.write_text(json.dumps(spec), encoding="utf-8")

        completed = _run_process(
            [os.fspath(Path(os.sys.executable)), "-m", "pyspider", "job", "--file", str(spec_path)],
            root,
        )
        if completed.returncode != 0:
            details = "\n".join(part for part in (completed.stdout.strip(), completed.stderr.strip()) if part).strip()
            return _check(replay["name"], "failed", replay_path, details or "py replay exited non-zero")

        payload = json.loads(_extract_json_payload(completed.stdout))
        if payload.get("state") != "succeeded":
            return _check(replay["name"], "failed", replay_path, f"expected succeeded state, got {payload.get('state')!r}")
        if payload.get("extract") != replay.get("expected_extract"):
            return _check(replay["name"], "failed", replay_path, f"unexpected extract payload: {payload.get('extract')!r}")
        if replay["expected_warning"] not in payload.get("warnings", []):
            return _check(replay["name"], "failed", replay_path, f"warning not preserved: {payload.get('warnings')!r}")
        if replay["expected_recovery_strategy"] != payload.get("recovery", {}).get("strategy"):
            return _check(replay["name"], "failed", replay_path, f"unexpected recovery payload: {payload.get('recovery')!r}")
        output_path = Path(payload.get("output", {}).get("path", ""))
        if not output_path.exists():
            return _check(replay["name"], "failed", replay_path, "py replay output file missing")
        if replay["expected_extract"]["title"] not in output_path.read_text(encoding="utf-8"):
            return _check(replay["name"], "failed", replay_path, "py replay output content mismatch")
        return _check(replay["name"], "passed", replay_path, "valid py replay")


def _run_rust_replay(root: Path, replay: dict, replay_path: Path) -> dict:
    with tempfile.TemporaryDirectory() as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        spec = json.loads(json.dumps(replay))
        spec["output"]["path"] = str(tmpdir / "rust-replay-output.json")
        spec_path = tmpdir / "rust-replay.json"
        spec_path.write_text(json.dumps(spec), encoding="utf-8")

        completed = _run_process(
            ["cargo", "run", "--quiet", "--", "job", "--file", str(spec_path)],
            root / "rustspider",
        )
        if completed.returncode != 0:
            details = "\n".join(part for part in (completed.stdout.strip(), completed.stderr.strip()) if part).strip()
            return _check(replay["name"], "failed", replay_path, details or "rust replay exited non-zero")

        payload = json.loads(_extract_json_payload(completed.stdout))
        if payload.get("state") != "succeeded":
            return _check(replay["name"], "failed", replay_path, f"expected succeeded state, got {payload.get('state')!r}")
        if replay["expected_detected_media"] not in payload.get("detected_media", []):
            return _check(replay["name"], "failed", replay_path, f"unexpected detected media: {payload.get('detected_media')!r}")
        if replay["expected_warning"] not in payload.get("warnings", []):
            return _check(replay["name"], "failed", replay_path, f"warning not preserved: {payload.get('warnings')!r}")
        if replay["expected_recovery_strategy"] != payload.get("recovery", {}).get("strategy"):
            return _check(replay["name"], "failed", replay_path, f"unexpected recovery payload: {payload.get('recovery')!r}")
        output_path = Path(payload.get("output", {}).get("path", ""))
        if not output_path.exists():
            return _check(replay["name"], "failed", replay_path, "rust replay output file missing")
        if replay["expected_detected_media"] not in output_path.read_text(encoding="utf-8"):
            return _check(replay["name"], "failed", replay_path, "rust replay output content mismatch")
        return _check(replay["name"], "passed", replay_path, "valid rust replay")


def validate_workflow_replay(root: Path, path: Path) -> dict:
    if not path.exists():
        return _check(path.stem, "failed", path, "workflow replay file not found")
    try:
        replay = load_replay(path)
    except Exception as exc:  # pragma: no cover
        return _check(path.stem, "failed", path, str(exc))

    framework = replay.get("framework")
    if framework not in SUPPORTED_FRAMEWORKS:
        return _check(path.stem, "failed", path, f"unsupported workflow replay framework: {framework!r}")
    fixture_path = root / replay.get("fixture_path", "")
    if not fixture_path.exists():
        return _check(path.stem, "failed", path, f"fixture_path not found: {fixture_path}")

    if framework == "javaspider":
        return _run_java_replay(root, replay, path)
    if framework == "gospider":
        return _run_go_replay(root, replay, path)
    if framework == "pyspider":
        return _run_py_replay(root, replay, path)
    return _run_rust_replay(root, replay, path)


def collect_workflow_replay_report(root: Path) -> dict:
    checks = [validate_workflow_replay(root, path) for _, path in sorted(discover_workflow_replays(root).items())]
    passed = sum(1 for check in checks if check["status"] == "passed")
    failed = len(checks) - passed
    exit_code = 1 if failed else 0
    return {
        "command": "validate-workflow-replays",
        "summary": "failed" if exit_code else "passed",
        "summary_text": f"{passed} passed, {failed} failed",
        "exit_code": exit_code,
        "checks": checks,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate workflow replay corpus against local CLI runners")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent), help="repository root path")
    parser.add_argument("--json", action="store_true", help="print report as JSON")
    args = parser.parse_args(argv)

    report = collect_workflow_replay_report(Path(args.root).resolve())
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("validate-workflow-replays summary:", report["summary"])
        for check in report["checks"]:
            print(f"- {check['name']}: {check['status']} ({check['details']})")
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
