from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import validate_workflow_replays

ALLOWED_CHECK_STATUSES = {"passed", "failed", "skipped"}
FRAMEWORKS = ("javaspider", "pyspider", "gospider", "rustspider")
REPLAY_ROOT = Path(__file__).resolve().parent / "replays" / "anti-bot"


def build_pyspider_job_command(system_name: str | None = None) -> list[str]:
    system_name = system_name or platform.system()
    executable = Path(sys.executable)
    script_name = "pyspider.exe" if system_name == "Windows" else "pyspider"
    console_script = executable.with_name(script_name)
    if console_script.exists():
        return [str(console_script), "job"]
    return [sys.executable, "-m", "pyspider", "job"]


def framework_runtime(framework: str) -> str:
    return {
        "javaspider": "java",
        "pyspider": "python",
        "gospider": "go",
        "rustspider": "rust",
    }[framework]


def framework_cwd(root: Path, framework: str) -> Path:
    return root / (framework if framework != "pyspider" else ".")


def _run_process(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def _extract_json_payload(stdout: str) -> str:
    stripped = stdout.strip()
    if stripped.startswith("{"):
        return stripped
    first_brace = stripped.find("{")
    if first_brace >= 0:
        return stripped[first_brace:]
    return stripped


def load_antibot_replay_scenarios(root: Path | None = None) -> dict[str, dict]:
    replay_root = root or REPLAY_ROOT
    scenarios: dict[str, dict] = {}
    for path in sorted(replay_root.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        name = data["name"]
        scenarios[name] = data
    return scenarios


def load_replay_fixture_text(scenario_config: dict) -> str:
    fixture_path = Path(__file__).resolve().parent / scenario_config["fixture_path"]
    return fixture_path.read_text(encoding="utf-8")


def derive_fixture_title(scenario_config: dict) -> str:
    content = load_replay_fixture_text(scenario_config)
    start = content.lower().find("<title>")
    end = content.lower().find("</title>")
    if start >= 0 and end > start:
        title = content[start + len("<title>"):end].strip()
        if title:
            return title
    return scenario_config.get("marker_title", scenario_config["name"])


def _build_success_job(framework: str, tmpdir: Path, *, suffix: str = "", scenario: str = "captcha") -> tuple[dict, str, dict, dict, str]:
    output_path = tmpdir / f"{framework}-readiness-output{suffix}.json"
    scenario_config = load_antibot_replay_scenarios()[scenario]
    anti_bot = dict(scenario_config["anti_bot"])
    recovery = dict(scenario_config["recovery"])
    warnings = [scenario_config["warning"]]
    base_title = derive_fixture_title(scenario_config)
    if framework == "gospider":
        return (
            {
                "name": "go-readiness-job",
                "runtime": "ai",
                "target": {"url": "https://example.com"},
                "output": {"format": "json", "path": str(output_path)},
                "metadata": {
                    "mock_extract": {"title": f"Go {base_title}"},
                    "mock_antibot": anti_bot,
                    "mock_recovery": recovery,
                    "mock_warnings": warnings,
                },
            },
            f"Go {base_title}",
            anti_bot,
            recovery,
            warnings[0],
        )
    if framework == "pyspider":
        return (
            {
                "name": "py-readiness-job",
                "runtime": "ai",
                "target": {"url": "https://example.com"},
                "extract": [{"field": "title", "type": "ai"}],
                "output": {"format": "json", "path": str(output_path)},
                "metadata": {
                    "content": f"<title>Py {base_title}</title>",
                    "mock_antibot": anti_bot,
                    "mock_recovery": recovery,
                    "mock_warnings": warnings,
                },
            },
            f"Py {base_title}",
            anti_bot,
            recovery,
            warnings[0],
        )
    if framework == "rustspider":
        return (
            {
                "name": "rust-readiness-job",
                "runtime": "media",
                "target": {"url": "https://example.com", "body": "playlist.m3u8"},
                "output": {"format": "json", "path": str(output_path)},
                "metadata": {
                    "mock_antibot": anti_bot,
                    "mock_recovery": recovery,
                    "mock_warnings": warnings,
                },
            },
            "\"state\": \"succeeded\"",
            anti_bot,
            recovery,
            warnings[0],
        )
    return (
        {
            "name": "java-readiness-job",
            "runtime": "browser",
            "target": {"url": "https://example.com"},
            "extract": [{"field": "title", "type": "css", "expr": "title"}],
            "output": {"format": "json", "path": str(output_path)},
            "metadata": {
                "mock_extract": {"title": f"Java {base_title}"},
                "mock_antibot": anti_bot,
                "mock_recovery": recovery,
                "mock_warnings": warnings,
            },
        },
        f"Java {base_title}",
        anti_bot,
        recovery,
        warnings[0],
    )


def _build_failure_job(framework: str, tmpdir: Path, reason: str) -> dict:
    runtime = {
        "gospider": "ai",
        "pyspider": "ai",
        "rustspider": "media",
        "javaspider": "browser",
    }[framework]
    return {
        "name": f"{framework}-failure-job",
        "runtime": runtime,
        "target": {"url": "https://example.com"},
        "output": {"format": "json", "path": str(tmpdir / f"{framework}-failure-output.json")},
        "metadata": {"fail_job": reason},
    }


def _framework_command(root: Path, framework: str, job_path: Path) -> list[str]:
    if framework == "gospider":
        return ["go", "run", "./cmd/gospider", "job", "--file", str(job_path)]
    if framework == "pyspider":
        return build_pyspider_job_command() + ["--file", str(job_path)]
    if framework == "rustspider":
        return ["cargo", "run", "--quiet", "--", "job", "--file", str(job_path)]
    classpath = f"target/classes{os.pathsep}target/dependency/*"
    return ["java", "-cp", classpath, "com.javaspider.cli.SuperSpiderCLI", "job", "--file", str(job_path)]


def _prepare_framework(root: Path, framework: str) -> tuple[bool, str]:
    if framework != "javaspider":
        return True, ""
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


def _make_check(name: str, status: str, details: str) -> dict:
    return {
        "name": name,
        "status": status if status in ALLOWED_CHECK_STATUSES else "failed",
        "details": details,
    }


def _check_name(prefix: str, base: str) -> str:
    return f"{prefix}{base}" if prefix else base


def _fixture_checks(scenario_config: dict, *, prefix: str = "") -> list[dict]:
    fixture_path = Path(__file__).resolve().parent / scenario_config["fixture_path"]
    checks: list[dict] = []
    if not fixture_path.exists():
        checks.append(_make_check(_check_name(prefix, "fixture-source"), "failed", f"missing fixture: {fixture_path}"))
        checks.append(_make_check(_check_name(prefix, "fixture-token-assertion"), "failed", "fixture file was not found"))
        return checks

    checks.append(_make_check(_check_name(prefix, "fixture-source"), "passed", str(fixture_path)))
    content = fixture_path.read_text(encoding="utf-8")
    tokens = scenario_config.get("expected_tokens") or []
    if all(token in content for token in tokens):
        checks.append(_make_check(_check_name(prefix, "fixture-token-assertion"), "passed", "fixture contains all expected scenario tokens"))
    else:
        checks.append(_make_check(_check_name(prefix, "fixture-token-assertion"), "failed", f"fixture missing one of {tokens!r}"))
    return checks


def _success_result_checks(
    payload: dict,
    output_path: Path,
    marker: str,
    expected_antibot: dict,
    expected_recovery: dict,
    expected_warning: str,
    *,
    prefix: str = "",
) -> list[dict]:
    checks: list[dict] = []
    state = payload.get("state")
    if state != "succeeded":
        checks.append(_make_check(_check_name(prefix, "success-job"), "failed", f"expected state 'succeeded', got {state!r}"))
    else:
        checks.append(_make_check(_check_name(prefix, "success-job"), "passed", "job returned succeeded state"))

    if output_path.exists():
        checks.append(_make_check(_check_name(prefix, "output-persisted"), "passed", str(output_path)))
        content = output_path.read_text(encoding="utf-8")
        if marker in content:
            checks.append(_make_check(_check_name(prefix, "content-assertion"), "passed", f"output contains marker {marker!r}"))
        else:
            checks.append(_make_check(_check_name(prefix, "content-assertion"), "failed", f"output missing marker {marker!r}"))
    else:
        checks.append(_make_check(_check_name(prefix, "output-persisted"), "failed", f"expected output file at {output_path}"))
        checks.append(_make_check(_check_name(prefix, "content-assertion"), "failed", "output file was not created"))
    anti_bot = payload.get("anti_bot")
    if isinstance(anti_bot, dict) and all(anti_bot.get(key) == value for key, value in expected_antibot.items()):
        checks.append(_make_check(_check_name(prefix, "anti-bot-envelope"), "passed", "anti_bot envelope preserved synthetic challenge context"))
    else:
        checks.append(_make_check(_check_name(prefix, "anti-bot-envelope"), "failed", f"unexpected anti_bot payload: {anti_bot!r}"))
    recovery = payload.get("recovery")
    if isinstance(recovery, dict) and _normalize_json_like(recovery) == _normalize_json_like(expected_recovery):
        checks.append(_make_check(_check_name(prefix, "recovery-envelope"), "passed", "recovery envelope preserved synthetic mitigation trace"))
    else:
        checks.append(_make_check(_check_name(prefix, "recovery-envelope"), "failed", f"unexpected recovery payload: {recovery!r}"))
    warnings = payload.get("warnings")
    if isinstance(warnings, list) and expected_warning in warnings:
        checks.append(_make_check(_check_name(prefix, "warning-envelope"), "passed", "warnings envelope preserved synthetic recovery signal"))
    else:
        checks.append(_make_check(_check_name(prefix, "warning-envelope"), "failed", f"unexpected warnings payload: {warnings!r}"))
    return checks


def _normalize_payload_for_comparison(payload: dict) -> dict:
    return _normalize_json_like(payload)


def _normalize_json_like(value):
    if isinstance(value, dict):
        normalized = {}
        for key, item in value.items():
            if key in {"job_id", "run_id", "started_at", "finished_at", "duration"}:
                continue
            if key == "path":
                continue
            if key == "artifacts" and isinstance(item, list):
                normalized[key] = [f"<artifact:{len(item)}>"]
                continue
            if key == "latency_ms":
                normalized[key] = 0
                continue
            normalized[key] = _normalize_json_like(item)
        return normalized
    if isinstance(value, list):
        return [_normalize_json_like(item) for item in value]
    return value


def _ratio(passed: int, total: int) -> float:
    return round(passed / total, 4) if total else 0.0


def _rate_for_checks(checks: list[dict]) -> float:
    considered = [check for check in checks if check["status"] != "skipped"]
    passed = sum(1 for check in considered if check["status"] == "passed")
    return _ratio(passed, len(considered))


def _workflow_replay_check(root: Path, framework: str) -> dict:
    for _, path in sorted(validate_workflow_replays.discover_workflow_replays(root).items()):
        replay = validate_workflow_replays.load_replay(path)
        if replay.get("framework") == framework:
            check = validate_workflow_replays.validate_workflow_replay(root, path)
            return {
                "name": "workflow-replay",
                "status": check["status"],
                "path": check["path"],
                "details": f"{check['name']}: {check['details']}",
            }
    return _make_check("workflow-replay", "skipped", "no workflow replay defined for this framework")


def _control_plane_command(root: Path, framework: str) -> tuple[list[str], Path]:
    if framework == "pyspider":
        return [sys.executable, "-m", "pytest", "pyspider/tests/test_web_app.py", "-q", "--no-cov"], root
    if framework == "gospider":
        return [
            "go",
            "test",
            "./web",
            "-run",
            "TestServerTaskLifecycleProducesResultsAndLogs|TestServerTaskCanBeStopped|TestTaskLifecycleMutationResponsesExposeDataMessage",
            "-count=1",
        ], root / "gospider"
    if framework == "rustspider":
        return ["cargo", "test", "--quiet", "--bin", "rustspider", "--", "--nocapture"], root / "rustspider"
    command = ["mvn", "-q", "-Dtest=SpiderControllerTest", "test"]
    if platform.system() == "Windows":
        command = ["cmd", "/c", *command]
    return command, root / "javaspider"


def _control_plane_check(root: Path, framework: str) -> tuple[dict, int]:
    command, cwd = _control_plane_command(root, framework)
    started = time.perf_counter()
    try:
        completed = _run_process(command, cwd)
    except FileNotFoundError as exc:
        duration_ms = int((time.perf_counter() - started) * 1000)
        return _make_check("control-plane-probe", "failed", f"command not found: {exc}"), duration_ms
    duration_ms = int((time.perf_counter() - started) * 1000)
    if completed.returncode == 0:
        return _make_check("control-plane-probe", "passed", "web control-plane probe passed"), duration_ms
    combined = "\n".join(
        part for part in (completed.stdout.strip(), completed.stderr.strip()) if part
    ).strip()
    return _make_check("control-plane-probe", "failed", combined or "web control-plane probe failed"), duration_ms


def run_framework_readiness(root: Path, framework: str) -> dict:
    runtime = framework_runtime(framework)
    checks: list[dict] = []
    durations_ms: dict[str, int] = {}

    started = time.perf_counter()
    prepared, prepare_details = _prepare_framework(root, framework)
    durations_ms["prepare"] = int((time.perf_counter() - started) * 1000)
    if not prepared:
        checks.append(_make_check("prepare-runtime", "failed", prepare_details))
        return _framework_report(framework, runtime, checks, durations_ms)
    if framework == "javaspider":
        checks.append(_make_check("prepare-runtime", "passed", "compiled java CLI dependencies"))

    started = time.perf_counter()
    workflow_replay = _workflow_replay_check(root, framework)
    durations_ms["workflow_replay"] = int((time.perf_counter() - started) * 1000)
    checks.append(workflow_replay)
    control_plane_check, control_plane_duration = _control_plane_check(root, framework)
    durations_ms["control_plane_probe"] = control_plane_duration
    checks.append(control_plane_check)

    with tempfile.TemporaryDirectory() as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        scenario_catalog = load_antibot_replay_scenarios()
        checks.extend(_fixture_checks(scenario_catalog["captcha"]))
        success_job, marker, expected_antibot, expected_recovery, expected_warning = _build_success_job(framework, tmpdir)
        success_path = tmpdir / f"{framework}-success-job.json"
        success_path.write_text(json.dumps(success_job), encoding="utf-8")
        success_output = Path(success_job["output"]["path"])
        success_payload: dict | None = None

        started = time.perf_counter()
        try:
            success_completed = _run_process(_framework_command(root, framework, success_path), framework_cwd(root, framework))
        except FileNotFoundError as exc:
            checks.append(_make_check("success-job", "failed", f"command not found: {exc}"))
            success_completed = None
        durations_ms["success_job"] = int((time.perf_counter() - started) * 1000)
        if success_completed is None:
            checks.append(_make_check("output-persisted", "failed", "success job command could not be launched"))
            checks.append(_make_check("content-assertion", "failed", "success job command could not be launched"))
        elif success_completed.returncode != 0:
            combined = "\n".join(part for part in (success_completed.stdout.strip(), success_completed.stderr.strip()) if part).strip()
            checks.append(_make_check("success-job", "failed", combined or "success job exited non-zero"))
        else:
            try:
                success_payload = json.loads(_extract_json_payload(success_completed.stdout))
                checks.extend(
                    _success_result_checks(
                        success_payload,
                        success_output,
                        marker,
                        expected_antibot,
                        expected_recovery,
                        expected_warning,
                    )
                )
            except json.JSONDecodeError as exc:
                checks.append(_make_check("success-job", "failed", f"invalid json payload: {exc}"))

        repeat_job, _, _, _, _ = _build_success_job(framework, tmpdir, suffix="-repeat")
        repeat_path = tmpdir / f"{framework}-success-repeat-job.json"
        repeat_path.write_text(json.dumps(repeat_job), encoding="utf-8")
        repeat_output = Path(repeat_job["output"]["path"])
        repeat_payload: dict | None = None

        started = time.perf_counter()
        try:
            repeat_completed = _run_process(_framework_command(root, framework, repeat_path), framework_cwd(root, framework))
        except FileNotFoundError as exc:
            checks.append(_make_check("repeat-success-job", "failed", f"command not found: {exc}"))
            repeat_completed = None
        durations_ms["repeat_success_job"] = int((time.perf_counter() - started) * 1000)
        if repeat_completed is None:
            checks.append(_make_check("repeat-output-persisted", "failed", "repeat success job command could not be launched"))
            checks.append(_make_check("consistency-assertion", "failed", "repeat success job command could not be launched"))
        elif repeat_completed.returncode != 0:
            combined = "\n".join(part for part in (repeat_completed.stdout.strip(), repeat_completed.stderr.strip()) if part).strip()
            checks.append(_make_check("repeat-success-job", "failed", combined or "repeat success job exited non-zero"))
            checks.append(_make_check("repeat-output-persisted", "failed", "repeat success job did not persist output"))
            checks.append(_make_check("consistency-assertion", "failed", "repeat success job did not produce comparable output"))
        else:
            try:
                repeat_payload = json.loads(_extract_json_payload(repeat_completed.stdout))
                if repeat_payload.get("state") == "succeeded":
                    checks.append(_make_check("repeat-success-job", "passed", "repeat success job returned succeeded state"))
                else:
                    checks.append(_make_check("repeat-success-job", "failed", f"expected state 'succeeded', got {repeat_payload.get('state')!r}"))

                if repeat_output.exists():
                    checks.append(_make_check("repeat-output-persisted", "passed", str(repeat_output)))
                else:
                    checks.append(_make_check("repeat-output-persisted", "failed", f"expected repeat output file at {repeat_output}"))

                if success_payload is None or not success_output.exists() or not repeat_output.exists():
                    checks.append(_make_check("consistency-assertion", "failed", "missing success payload or persisted outputs"))
                else:
                    first_output = success_output.read_text(encoding="utf-8")
                    second_output = repeat_output.read_text(encoding="utf-8")
                    normalized_first = _normalize_payload_for_comparison(success_payload)
                    normalized_second = _normalize_payload_for_comparison(repeat_payload)
                    try:
                        normalized_first_output = _normalize_json_like(json.loads(first_output))
                        normalized_second_output = _normalize_json_like(json.loads(second_output))
                    except json.JSONDecodeError:
                        normalized_first_output = first_output
                        normalized_second_output = second_output
                    if normalized_first == normalized_second and normalized_first_output == normalized_second_output:
                        checks.append(_make_check("consistency-assertion", "passed", "repeat success job matched normalized payload and artifact content"))
                    else:
                        checks.append(_make_check("consistency-assertion", "failed", "repeat success job drifted from the initial normalized payload or artifact content"))
            except json.JSONDecodeError as exc:
                checks.append(_make_check("repeat-success-job", "failed", f"invalid repeat json payload: {exc}"))
                checks.append(_make_check("repeat-output-persisted", "failed", "repeat success job payload could not be parsed"))
                checks.append(_make_check("consistency-assertion", "failed", "repeat success job payload could not be parsed"))

        for scenario in ("proxy", "challenge"):
            checks.extend(_fixture_checks(scenario_catalog[scenario], prefix=f"{scenario}-"))
            scenario_job, scenario_marker, scenario_antibot, scenario_recovery, scenario_warning = _build_success_job(
                framework,
                tmpdir,
                suffix=f"-{scenario}",
                scenario=scenario,
            )
            scenario_path = tmpdir / f"{framework}-{scenario}-job.json"
            scenario_path.write_text(json.dumps(scenario_job), encoding="utf-8")
            scenario_output = Path(scenario_job["output"]["path"])

            started = time.perf_counter()
            try:
                scenario_completed = _run_process(_framework_command(root, framework, scenario_path), framework_cwd(root, framework))
            except FileNotFoundError as exc:
                checks.append(_make_check(f"{scenario}-success-job", "failed", f"command not found: {exc}"))
                checks.append(_make_check(f"{scenario}-output-persisted", "failed", f"{scenario} job command could not be launched"))
                checks.append(_make_check(f"{scenario}-content-assertion", "failed", f"{scenario} job command could not be launched"))
                checks.append(_make_check(f"{scenario}-anti-bot-envelope", "failed", f"{scenario} job command could not be launched"))
                checks.append(_make_check(f"{scenario}-warning-envelope", "failed", f"{scenario} job command could not be launched"))
                continue
            durations_ms[f"{scenario}_job"] = int((time.perf_counter() - started) * 1000)
            if scenario_completed.returncode != 0:
                combined = "\n".join(part for part in (scenario_completed.stdout.strip(), scenario_completed.stderr.strip()) if part).strip()
                checks.append(_make_check(f"{scenario}-success-job", "failed", combined or f"{scenario} job exited non-zero"))
                checks.append(_make_check(f"{scenario}-output-persisted", "failed", f"{scenario} job did not persist output"))
                checks.append(_make_check(f"{scenario}-content-assertion", "failed", f"{scenario} job did not produce content"))
                checks.append(_make_check(f"{scenario}-anti-bot-envelope", "failed", f"{scenario} job did not preserve anti_bot envelope"))
                checks.append(_make_check(f"{scenario}-warning-envelope", "failed", f"{scenario} job did not preserve warnings"))
                continue
            try:
                scenario_payload = json.loads(_extract_json_payload(scenario_completed.stdout))
                checks.extend(
                    _success_result_checks(
                        scenario_payload,
                        scenario_output,
                        scenario_marker,
                        scenario_antibot,
                        scenario_recovery,
                        scenario_warning,
                        prefix=f"{scenario}-",
                    )
                )
            except json.JSONDecodeError as exc:
                checks.append(_make_check(f"{scenario}-success-job", "failed", f"invalid {scenario} json payload: {exc}"))
                checks.append(_make_check(f"{scenario}-output-persisted", "failed", f"{scenario} payload could not be parsed"))
                checks.append(_make_check(f"{scenario}-content-assertion", "failed", f"{scenario} payload could not be parsed"))
                checks.append(_make_check(f"{scenario}-anti-bot-envelope", "failed", f"{scenario} payload could not be parsed"))
                checks.append(_make_check(f"{scenario}-warning-envelope", "failed", f"{scenario} payload could not be parsed"))

        failure_reason = "synthetic readiness failure"
        failure_job = _build_failure_job(framework, tmpdir, failure_reason)
        failure_path = tmpdir / f"{framework}-failure-job.json"
        failure_path.write_text(json.dumps(failure_job), encoding="utf-8")

        started = time.perf_counter()
        try:
            failure_completed = _run_process(_framework_command(root, framework, failure_path), framework_cwd(root, framework))
        except FileNotFoundError as exc:
            checks.append(_make_check("failure-injection", "failed", f"command not found: {exc}"))
            failure_completed = None
        durations_ms["failure_job"] = int((time.perf_counter() - started) * 1000)
        combined_failure = ""
        if failure_completed is not None:
            combined_failure = "\n".join(part for part in (failure_completed.stdout.strip(), failure_completed.stderr.strip()) if part).strip()
        if failure_completed is None:
            pass
        elif failure_completed.returncode == 0:
            checks.append(_make_check("failure-injection", "failed", "failure job unexpectedly succeeded"))
        elif failure_reason in combined_failure:
            checks.append(_make_check("failure-injection", "passed", "failure injection contract triggered"))
        else:
            checks.append(_make_check("failure-injection", "failed", combined_failure or "failure reason not surfaced"))

        if failure_completed is None:
            checks.append(_make_check("failure-envelope", "failed", "failure job command could not be launched"))
        else:
            try:
                failure_payload = json.loads(_extract_json_payload(failure_completed.stdout))
                if failure_payload.get("state") != "failed":
                    checks.append(_make_check("failure-envelope", "failed", f"expected failure state, got {failure_payload.get('state')!r}"))
                elif failure_reason not in str(failure_payload.get("error", "")):
                    checks.append(_make_check("failure-envelope", "failed", "failure payload error did not preserve injected reason"))
                else:
                    checks.append(_make_check("failure-envelope", "passed", "failure job emitted structured failure envelope"))
            except json.JSONDecodeError as exc:
                checks.append(_make_check("failure-envelope", "failed", f"invalid failure json payload: {exc}"))

    return _framework_report(framework, runtime, checks, durations_ms)


def _framework_report(framework: str, runtime: str, checks: list[dict], durations_ms: dict[str, int]) -> dict:
    passed = sum(1 for check in checks if check["status"] == "passed")
    failed = sum(1 for check in checks if check["status"] == "failed")
    total = passed + failed
    resilience_checks = [check for check in checks if check["name"].startswith("failure-")]
    consistency_checks = [check for check in checks if check["name"] in {"repeat-success-job", "repeat-output-persisted", "consistency-assertion"}]
    artifact_checks = [check for check in checks if "persisted" in check["name"] or check["name"] == "content-assertion"]
    scenario_checks = [check for check in checks if check["name"].startswith("proxy-") or check["name"].startswith("challenge-")]
    recovery_checks = [check for check in checks if check["name"].endswith("recovery-envelope")]
    workflow_replay_checks = [check for check in checks if check["name"] == "workflow-replay"]
    control_plane_checks = [check for check in checks if check["name"] == "control-plane-probe"]
    summary = "failed" if failed else "passed"
    return {
        "name": framework,
        "runtime": runtime,
        "summary": summary,
        "exit_code": 1 if failed else 0,
        "metrics": {
            "checks_passed": passed,
            "checks_failed": failed,
            "checks_total": total,
            "success_rate": _ratio(passed, total),
            "resilience_rate": _ratio(sum(1 for check in resilience_checks if check["status"] == "passed"), len(resilience_checks)),
            "consistency_rate": _ratio(sum(1 for check in consistency_checks if check["status"] == "passed"), len(consistency_checks)),
            "artifact_integrity_rate": _ratio(sum(1 for check in artifact_checks if check["status"] == "passed"), len(artifact_checks)),
            "anti_bot_scenario_rate": _ratio(sum(1 for check in scenario_checks if check["status"] == "passed"), len(scenario_checks)),
            "recovery_signal_rate": _ratio(sum(1 for check in recovery_checks if check["status"] == "passed"), len(recovery_checks)),
            "workflow_replay_rate": _rate_for_checks(workflow_replay_checks),
            "control_plane_rate": _rate_for_checks(control_plane_checks),
            "durations_ms": durations_ms,
        },
        "checks": checks,
    }


def collect_runtime_readiness_report(root: Path) -> dict:
    frameworks = [run_framework_readiness(root, framework) for framework in FRAMEWORKS]
    exit_code = 1 if any(item["exit_code"] != 0 for item in frameworks) else 0
    passed = sum(1 for item in frameworks if item["summary"] == "passed")
    failed = len(frameworks) - passed
    return {
        "command": "verify-runtime-readiness",
        "summary": "failed" if exit_code else "passed",
        "summary_text": f"{passed} frameworks passed, {failed} frameworks failed",
        "exit_code": exit_code,
        "frameworks": frameworks,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run synthetic production-readiness checks across all four spider frameworks")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent), help="repository root path")
    parser.add_argument("--json", action="store_true", help="print runtime readiness report as JSON")
    args = parser.parse_args(argv)

    report = collect_runtime_readiness_report(Path(args.root).resolve())
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("verify-runtime-readiness summary:", report["summary"])
        for framework in report["frameworks"]:
            print(f"- {framework['name']}: {framework['summary']}")

    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
