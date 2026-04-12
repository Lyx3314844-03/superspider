from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import generate_framework_scorecard
import verify_replay_dashboard

DEFAULT_POLICIES = {
    "dev": {
        "hard_rate_keys": [
            "success_rate",
            "resilience_rate",
            "consistency_rate",
            "artifact_integrity_rate",
            "anti_bot_scenario_rate",
            "recovery_signal_rate",
            "workflow_replay_rate",
            "control_plane_rate",
        ],
        "hard_thresholds": {
            "default_rate": 1.0,
            "rust_preflight_pass_rate": 1.0,
        },
        "minimums": {
            "test_status": "thin",
            "distributed": "verified-local",
        },
        "warning_policies": {
            "thin_test_status": False,
            "verified_local_distributed": False,
        },
    },
    "default": {
        "hard_rate_keys": [
            "success_rate",
            "resilience_rate",
            "consistency_rate",
            "artifact_integrity_rate",
            "anti_bot_scenario_rate",
            "recovery_signal_rate",
            "workflow_replay_rate",
            "control_plane_rate",
        ],
        "hard_thresholds": {
            "default_rate": 1.0,
            "rust_preflight_pass_rate": 1.0,
        },
        "minimums": {
            "test_status": "thin",
            "distributed": "verified-local",
        },
        "warning_policies": {
            "thin_test_status": True,
            "verified_local_distributed": True,
        },
    },
    "strict": {
        "hard_rate_keys": [
            "success_rate",
            "resilience_rate",
            "consistency_rate",
            "artifact_integrity_rate",
            "anti_bot_scenario_rate",
            "recovery_signal_rate",
            "workflow_replay_rate",
            "control_plane_rate",
        ],
        "hard_thresholds": {
            "default_rate": 1.0,
            "rust_preflight_pass_rate": 1.0,
        },
        "minimums": {
            "test_status": "moderate",
            "distributed": "verified",
        },
        "warning_policies": {
            "thin_test_status": False,
            "verified_local_distributed": False,
        },
    },
}


def _check(framework: str, name: str, status: str, details: str) -> dict:
    return {
        "framework": framework,
        "name": name,
        "status": status,
        "details": details,
    }


def load_threshold_policy(path: Path | None = None, profile: str = "default") -> dict:
    if path is None:
        path = Path(__file__).resolve().parent / "quality-thresholds.json"
    profiles = DEFAULT_POLICIES
    if path.exists():
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict) and "profiles" in loaded:
            profiles = dict(DEFAULT_POLICIES)
            for name, defaults in DEFAULT_POLICIES.items():
                merged = {
                    "hard_rate_keys": list(defaults["hard_rate_keys"]),
                    "hard_thresholds": dict(defaults["hard_thresholds"]),
                    "minimums": dict(defaults["minimums"]),
                    "warning_policies": dict(defaults["warning_policies"]),
                }
                if name in loaded["profiles"]:
                    override = loaded["profiles"][name]
                    for key in ("hard_rate_keys", "hard_thresholds", "minimums", "warning_policies"):
                        if key in override:
                            if isinstance(merged[key], dict):
                                merged[key].update(override[key])
                            else:
                                merged[key] = override[key]
                profiles[name] = merged
        else:
            profiles = {
                "default": {
                    "hard_rate_keys": loaded.get("hard_rate_keys", DEFAULT_POLICIES["default"]["hard_rate_keys"]),
                    "hard_thresholds": {**DEFAULT_POLICIES["default"]["hard_thresholds"], **loaded.get("hard_thresholds", {})},
                    "minimums": dict(DEFAULT_POLICIES["default"]["minimums"]),
                    "warning_policies": {**DEFAULT_POLICIES["default"]["warning_policies"], **loaded.get("warning_policies", {})},
                }
            }
    if profile not in profiles:
        raise ValueError(f"unknown quality threshold profile: {profile}")
    return profiles[profile]


def policy_digest(policy: dict) -> str:
    canonical = json.dumps(policy, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


STATUS_RANK = {
    "thin": 0,
    "moderate": 1,
    "strong": 2,
    "verified-local": 0,
    "verified": 1,
}

FRAMEWORK_BOOL_REQUIREMENTS = {
    "javaspider": ["captcha_closed_loop_ready", "audit_ready", "artifact_ready"],
    "pyspider": ["bounded_concurrency_ready", "stream_ready", "soak_ready"],
    "gospider": ["lease_ready", "heartbeat_ready", "dead_letter_ready", "soak_ready"],
    "rustspider": ["browser_proof_ready"],
}


def collect_quality_threshold_report(
    root: Path,
    policy: dict | None = None,
    *,
    profile: str = "default",
    policy_path: Path | None = None,
    dashboard: dict | None = None,
    scorecard: dict | None = None,
) -> dict:
    policy = policy or load_threshold_policy(policy_path, profile=profile)
    dashboard = dashboard or verify_replay_dashboard.collect_replay_dashboard(root)
    if scorecard is None:
        try:
            scorecard = generate_framework_scorecard.collect_framework_scorecard(root, dashboard=dashboard)
        except TypeError:
            scorecard = generate_framework_scorecard.collect_framework_scorecard(root)

    checks: list[dict] = []

    for framework, info in scorecard["frameworks"].items():
        evidence = info["evidence"]
        scores = info["scores"]

        if not evidence["readme_present"]:
            checks.append(_check(framework, "readme", "failed", "README.md is missing"))
        else:
            checks.append(_check(framework, "readme", "passed", "README.md is present"))

        if not evidence["deploy_verified"]:
            checks.append(_check(framework, "deploy", "failed", "deploy path is not verified"))
        else:
            checks.append(_check(framework, "deploy", "passed", "deploy path is verified"))

        if not evidence["monitor_verified"]:
            checks.append(_check(framework, "monitor", "failed", "monitoring evidence is missing"))
        else:
            checks.append(_check(framework, "monitor", "passed", "monitoring evidence is present"))

        if not evidence["browser_verified"]:
            checks.append(_check(framework, "browser", "failed", "browser/workflow replay evidence is missing"))
        else:
            checks.append(_check(framework, "browser", "passed", "browser/workflow replay evidence is present"))

        if not evidence["anti_bot_verified"]:
            checks.append(_check(framework, "anti-bot", "failed", "anti-bot scenario or recovery evidence is missing"))
        else:
            checks.append(_check(framework, "anti-bot", "passed", "anti-bot scenario and recovery evidence is present"))

        distributed = evidence["distributed"]
        distributed_minimum = policy["minimums"].get("distributed", "verified-local")
        if STATUS_RANK.get(distributed, -1) < STATUS_RANK.get(distributed_minimum, -1):
            checks.append(_check(framework, "distributed", "failed", f"distributed capability {distributed!r} is below required {distributed_minimum!r}"))
        elif distributed == "verified":
            checks.append(_check(framework, "distributed", "passed", "distributed capability is verified"))
        elif distributed == "verified-local" and policy["warning_policies"].get("verified_local_distributed", True):
            checks.append(_check(framework, "distributed", "warning", "distributed capability is verified locally but not against a live cluster"))
        else:
            checks.append(_check(framework, "distributed", "passed", f"distributed capability is {distributed}"))

        test_status = evidence["test_status"]
        test_files = evidence["test_files"]
        test_minimum = policy["minimums"].get("test_status", "thin")
        if STATUS_RANK.get(test_status, -1) < STATUS_RANK.get(test_minimum, -1):
            checks.append(_check(framework, "tests", "failed", f"test_status {test_status!r} is below required {test_minimum!r} ({test_files} files)"))
        elif test_status == "thin" and policy["warning_policies"].get("thin_test_status", True):
            checks.append(_check(framework, "tests", "warning", f"only {test_files} test files; increase coverage depth"))
        else:
            checks.append(_check(framework, "tests", "passed", f"{test_files} test files with {test_status} coverage depth"))

        for key in policy["hard_rate_keys"]:
            value = scores.get(key)
            threshold = policy["hard_thresholds"].get("default_rate", 1.0)
            if value != threshold:
                checks.append(_check(framework, key, "failed", f"expected {threshold}, got {value!r}"))
            else:
                checks.append(_check(framework, key, "passed", f"meets threshold {threshold}"))

        for key in FRAMEWORK_BOOL_REQUIREMENTS.get(framework, []):
            if key not in scores:
                continue
            if not scores.get(key, False):
                checks.append(_check(framework, key, "failed", f"{key} is not satisfied"))
            else:
                checks.append(_check(framework, key, "passed", f"{key} is satisfied"))

        if framework == "rustspider":
            rust_preflight_threshold = policy["hard_thresholds"].get("rust_preflight_pass_rate", 1.0)
            if scores.get("preflight_pass_rate") != rust_preflight_threshold:
                checks.append(_check(framework, "preflight_pass_rate", "failed", f"expected {rust_preflight_threshold}, got {scores.get('preflight_pass_rate')!r}"))
            else:
                checks.append(_check(framework, "preflight_pass_rate", "passed", f"meets threshold {rust_preflight_threshold}"))

            if not scores.get("browser_ready", False):
                checks.append(_check(framework, "browser_ready", "failed", "rust preflight browser requirement is not satisfied"))
            else:
                checks.append(_check(framework, "browser_ready", "passed", "rust preflight browser requirement is satisfied"))

            if not scores.get("ffmpeg_ready", False):
                checks.append(_check(framework, "ffmpeg_ready", "failed", "rust preflight ffmpeg requirement is not satisfied"))
            else:
                checks.append(_check(framework, "ffmpeg_ready", "passed", "rust preflight ffmpeg requirement is satisfied"))

    failed = sum(1 for check in checks if check["status"] == "failed")
    warnings = sum(1 for check in checks if check["status"] == "warning")
    passed = sum(1 for check in checks if check["status"] == "passed")

    if failed:
        summary = "failed"
        exit_code = 1
    elif warnings:
        summary = "warning"
        exit_code = 0
    else:
        summary = "passed"
        exit_code = 0

    return {
        "command": "verify-quality-thresholds",
        "summary": summary,
        "summary_text": f"{passed} passed, {warnings} warnings, {failed} failed",
        "exit_code": exit_code,
        "policy": {
            "profile": profile,
            "path": str(policy_path) if policy_path is not None else str((Path(__file__).resolve().parent / "quality-thresholds.json")),
            "digest": policy_digest(policy),
            "effective": policy,
        },
        "checks": checks,
        "dashboard_summary": dashboard["summary"],
        "scorecard_summary": scorecard["summary"],
    }


def render_markdown(report: dict) -> str:
    lines = [
        "# Quality Threshold Report",
        "",
        f"- Summary: **{report['summary']}**",
        f"- Details: {report['summary_text']}",
        "",
        "| Framework | Check | Status | Details |",
        "| --- | --- | --- | --- |",
    ]
    for check in report["checks"]:
        lines.append(
            f"| {check['framework']} | {check['name']} | {check['status']} | {check['details']} |"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate quality redlines from the replay dashboard and framework scorecard")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent), help="repository root path")
    parser.add_argument("--policy", default="", help="optional JSON threshold policy path")
    parser.add_argument("--profile", default="default", help="threshold profile name: dev, default, or strict")
    parser.add_argument("--markdown-out", default="", help="optional markdown diagnostics output path")
    parser.add_argument("--json", action="store_true", help="print threshold report as JSON")
    args = parser.parse_args(argv)

    resolved_policy_path = Path(args.policy).resolve() if args.policy else (Path(__file__).resolve().parent / "quality-thresholds.json")
    policy = load_threshold_policy(resolved_policy_path, profile=args.profile)
    report = collect_quality_threshold_report(
        Path(args.root).resolve(),
        policy,
        profile=args.profile,
        policy_path=resolved_policy_path,
    )
    if args.markdown_out:
        Path(args.markdown_out).write_text(render_markdown(report), encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("verify-quality-thresholds:", report["summary"])
        print(report["summary_text"])
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
