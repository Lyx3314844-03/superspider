from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable


EXPECTED_SCENARIOS = {"captcha", "proxy", "challenge"}
ALLOWED_SESSIONS = {"sticky", "rotating"}
ALLOWED_EVENT_PHASES = {"detect", "mitigate", "resume"}
ALLOWED_EVENT_STATUSES = {"passed", "failed", "skipped"}


def replay_root(root: Path) -> Path:
    return root / "replays" / "anti-bot"


def load_replay(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("replay root must be a JSON object")
    return data


def _require_string(data: dict, key: str, errors: list[str]) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{key} must be a non-empty string")
        return ""
    return value


def _validate_antibot(data: dict, errors: list[str]) -> None:
    anti_bot = data.get("anti_bot")
    if not isinstance(anti_bot, dict):
        errors.append("anti_bot must be an object")
        return
    _require_string(anti_bot, "challenge", errors)
    _require_string(anti_bot, "fingerprint_profile", errors)
    session_mode = anti_bot.get("session_mode")
    if session_mode not in ALLOWED_SESSIONS:
        errors.append(f"anti_bot.session_mode must be one of {sorted(ALLOWED_SESSIONS)!r}")
    if not isinstance(anti_bot.get("stealth"), bool):
        errors.append("anti_bot.stealth must be a boolean")
    proxy_id = anti_bot.get("proxy_id")
    if proxy_id is not None and (not isinstance(proxy_id, str) or not proxy_id.strip()):
        errors.append("anti_bot.proxy_id must be a non-empty string when present")


def _validate_recovery(data: dict, errors: list[str]) -> None:
    recovery = data.get("recovery")
    if not isinstance(recovery, dict):
        errors.append("recovery must be an object")
        return
    _require_string(recovery, "strategy", errors)
    if not isinstance(recovery.get("recovered"), bool):
        errors.append("recovery.recovered must be a boolean")
    events = recovery.get("events")
    if not isinstance(events, list) or not events:
        errors.append("recovery.events must be a non-empty array")
        return
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            errors.append(f"recovery.events[{index}] must be an object")
            continue
        phase = event.get("phase")
        if phase not in ALLOWED_EVENT_PHASES:
            errors.append(f"recovery.events[{index}].phase must be one of {sorted(ALLOWED_EVENT_PHASES)!r}")
        status = event.get("status")
        if status not in ALLOWED_EVENT_STATUSES:
            errors.append(f"recovery.events[{index}].status must be one of {sorted(ALLOWED_EVENT_STATUSES)!r}")
        if "signal" not in event and "action" not in event:
            errors.append(f"recovery.events[{index}] must contain signal or action")


def validate_replay(path: Path, root: Path) -> dict:
    if not path.exists():
        return {
            "name": path.stem,
            "status": "failed",
            "path": str(path),
            "details": "replay file not found",
        }

    try:
        data = load_replay(path)
    except Exception as exc:  # pragma: no cover - failure path
        return {
            "name": path.stem,
            "status": "failed",
            "path": str(path),
            "details": str(exc),
        }

    errors: list[str] = []
    name = _require_string(data, "name", errors) or path.stem
    fixture_path = _require_string(data, "fixture_path", errors)
    _require_string(data, "marker_title", errors)
    warning = data.get("warning")
    if not isinstance(warning, str) or not warning.strip():
        errors.append("warning must be a non-empty string")

    expected_tokens = data.get("expected_tokens")
    if not isinstance(expected_tokens, list) or not expected_tokens or not all(isinstance(token, str) and token.strip() for token in expected_tokens):
        errors.append("expected_tokens must be a non-empty string array")

    _validate_antibot(data, errors)
    _validate_recovery(data, errors)

    fixture = (root / fixture_path).resolve() if fixture_path else None
    if fixture_path:
        if fixture is None or not fixture.exists():
            errors.append(f"fixture_path not found: {fixture_path}")
        else:
            content = fixture.read_text(encoding="utf-8")
            if isinstance(expected_tokens, list):
                missing = [token for token in expected_tokens if token not in content]
                if missing:
                    errors.append(f"fixture missing expected tokens: {missing!r}")

    return {
        "name": name,
        "status": "failed" if errors else "passed",
        "path": str(path),
        "details": "; ".join(errors) if errors else "valid anti-bot replay",
    }


def discover_replays(root: Path) -> dict[str, Path]:
    base = replay_root(root)
    return {path.stem: path for path in sorted(base.glob("*.json"))}


def collect_antibot_replay_report(root: Path) -> dict:
    discovered = discover_replays(root)
    checks = [validate_replay(path, root) for _, path in sorted(discovered.items())]

    missing = sorted(EXPECTED_SCENARIOS - set(discovered))
    for name in missing:
        checks.append({
            "name": name,
            "status": "failed",
            "path": str(replay_root(root) / f"{name}.json"),
            "details": "required replay scenario is missing",
        })

    passed = sum(1 for check in checks if check["status"] == "passed")
    failed = len(checks) - passed
    exit_code = 1 if failed else 0
    return {
        "command": "validate-antibot-replays",
        "summary": "failed" if exit_code else "passed",
        "summary_text": f"{passed} passed, {failed} failed",
        "exit_code": exit_code,
        "checks": checks,
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate anti-bot replay corpus and fixture integrity")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent), help="repository root path")
    parser.add_argument("--json", action="store_true", help="print validation report as JSON")
    args = parser.parse_args(list(argv) if argv is not None else None)

    report = collect_antibot_replay_report(Path(args.root).resolve())
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("validate-antibot-replays summary:", report["summary"])
        for check in report["checks"]:
            print(f"- {check['name']}: {check['status']} ({check['details']})")
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
