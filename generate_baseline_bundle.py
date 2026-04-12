from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import generate_framework_scorecard
import verify_framework_standards
import verify_quality_events
import verify_quality_policy_governance
import verify_quality_thresholds
import verify_replay_dashboard
import verify_replay_trends


def _digest(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _component(name: str, report: dict) -> dict:
    return {
        "name": name,
        "summary": report.get("summary"),
        "exit_code": report.get("exit_code"),
        "digest": _digest(report),
    }


def collect_baseline_bundle(root: Path, *, quality_profile: str = "strict") -> dict:
    dashboard = verify_replay_dashboard.collect_replay_dashboard(root)
    scorecard = generate_framework_scorecard.collect_framework_scorecard(root, dashboard=dashboard)
    quality = verify_quality_thresholds.collect_quality_threshold_report(
        root,
        verify_quality_thresholds.load_threshold_policy(profile=quality_profile),
        profile=quality_profile,
        dashboard=dashboard,
        scorecard=scorecard,
    )
    governance = verify_quality_policy_governance.collect_quality_policy_governance_report(root)
    trends = verify_replay_trends.collect_replay_trend_report_with_current(
        root,
        current_dashboard=dashboard,
        current_scorecard=scorecard,
        current_quality=quality,
        current_governance=governance,
    )
    quality_events = verify_quality_events.collect_quality_events_report(root, trend=trends)
    standards = verify_framework_standards.collect_framework_standards(root, scorecard=scorecard)

    reports = {
        "dashboard": dashboard,
        "trends": trends,
        "quality_thresholds": quality,
        "quality_events": quality_events,
        "quality_policy_governance": governance,
        "framework_scorecard": scorecard,
        "framework_standards": standards,
    }
    components = [_component(name, report) for name, report in reports.items()]
    passed = sum(1 for component in components if component["summary"] == "passed")
    failed = len(components) - passed
    exit_code = 1 if failed else 0

    return {
        "command": "generate-baseline-bundle",
        "summary": "failed" if exit_code else "passed",
        "summary_text": f"{passed} bundle components passed, {failed} failed",
        "exit_code": exit_code,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "quality_profile": quality_profile,
        "components": components,
        "reports": reports,
        "framework_scores": scorecard["frameworks"],
    }


def render_markdown(bundle: dict) -> str:
    lines = [
        "# Baseline Bundle",
        "",
        f"- Summary: **{bundle['summary']}**",
        f"- Profile: `{bundle['quality_profile']}`",
        f"- Generated At: `{bundle['generated_at']}`",
        "",
        "## Components",
        "",
        "| Component | Summary | Exit Code | Digest |",
        "| --- | --- | --- | --- |",
    ]
    for component in bundle["components"]:
        lines.append(
            f"| {component['name']} | {component['summary']} | {component['exit_code']} | `{component['digest']}` |"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a release-grade baseline bundle from the current quality evidence chain")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent), help="repository root path")
    parser.add_argument("--quality-profile", default="strict", help="quality threshold profile used for the bundle")
    parser.add_argument("--json", action="store_true", help="print bundle as JSON")
    parser.add_argument("--markdown-out", default="", help="optional markdown output path")
    args = parser.parse_args(argv)

    bundle = collect_baseline_bundle(Path(args.root).resolve(), quality_profile=args.quality_profile)
    if args.markdown_out:
        Path(args.markdown_out).write_text(render_markdown(bundle), encoding="utf-8")
    if args.json:
        print(json.dumps(bundle, ensure_ascii=False, indent=2))
    else:
        print("generate-baseline-bundle:", bundle["summary"])
    return int(bundle["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
