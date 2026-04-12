from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

import yaml

ALLOWED_RUNTIMES = {"java", "go", "rust", "python"}
ALLOWED_EXPORT_FORMATS = {"json", "csv", "md"}


def default_config_candidates(root: Path) -> dict[str, list[Path]]:
    return {
        "java": [root / "artifacts" / "java-contract.yaml"],
        "go": [root / "artifacts" / "go-contract.yaml"],
        "rust": [root / "artifacts" / "rust-contract.yaml"],
        "python": [
            root / "pyspider" / "artifacts" / "py-contract.yaml",
            root / "artifacts" / "py-contract.yaml",
        ],
    }


def parse_config_args(entries: Iterable[str], root: Path) -> dict[str, Path]:
    configs: dict[str, Path] = {}
    for entry in entries:
        runtime, separator, raw_path = entry.partition("=")
        if separator != "=" or not runtime or not raw_path:
            raise ValueError(f"invalid --config entry: {entry!r}")
        runtime = runtime.strip().lower()
        if runtime not in ALLOWED_RUNTIMES:
            raise ValueError(f"unsupported runtime in --config: {runtime!r}")
        configs[runtime] = (root / raw_path).resolve() if not Path(raw_path).is_absolute() else Path(raw_path)
    return configs


def resolve_default_configs(root: Path) -> dict[str, Path]:
    resolved: dict[str, Path] = {}
    for runtime, candidates in default_config_candidates(root).items():
        for candidate in candidates:
            if candidate.exists():
                resolved[runtime] = candidate
                break
    return resolved


def load_config(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        data = json.loads(raw)
    else:
        data = yaml.safe_load(raw)
    if not isinstance(data, dict):
        raise ValueError("config root must be an object")
    return data


def validate_contract_config(runtime: str, path: Path) -> dict:
    if not path.exists():
        return _failed_check(runtime, path, "config file not found")

    try:
        data = load_config(path)
        errors = list(_collect_validation_errors(runtime, data))
    except Exception as exc:  # pragma: no cover - exercised via failure path tests
        return _failed_check(runtime, path, str(exc))

    if errors:
        return _failed_check(runtime, path, "; ".join(errors))

    return {
        "name": runtime,
        "status": "passed",
        "path": str(path),
        "details": "valid shared contract config",
    }


def _failed_check(runtime: str, path: Path, details: str) -> dict:
    return {
        "name": runtime,
        "status": "failed",
        "path": str(path),
        "details": details,
    }


def _collect_validation_errors(expected_runtime: str, data: dict) -> Iterable[str]:
    version = data.get("version")
    if not isinstance(version, int) or version < 1:
        yield "version must be an integer >= 1"

    project = data.get("project")
    if not isinstance(project, dict) or not isinstance(project.get("name"), str) or not project["name"].strip():
        yield "project.name must be a non-empty string"

    runtime = data.get("runtime")
    if runtime not in ALLOWED_RUNTIMES:
        yield f"runtime must be one of {sorted(ALLOWED_RUNTIMES)!r}"
    elif runtime != expected_runtime:
        yield f"runtime mismatch: expected {expected_runtime!r}, got {runtime!r}"

    crawl = data.get("crawl")
    if not isinstance(crawl, dict):
        yield "crawl must be an object"
    else:
        urls = crawl.get("urls")
        if not isinstance(urls, list) or not urls or not all(isinstance(url, str) and url.strip() for url in urls):
            yield "crawl.urls must be a non-empty string array"
        for error in _require_int(crawl, "concurrency", 1, "crawl"):
            yield error
        for error in _require_int(crawl, "max_requests", 1, "crawl"):
            yield error
        for error in _require_int(crawl, "max_depth", 0, "crawl"):
            yield error
        for error in _require_int(crawl, "timeout_seconds", 1, "crawl"):
            yield error

    browser = data.get("browser")
    if not isinstance(browser, dict):
        yield "browser must be an object"
    else:
        for error in _require_bool(browser, "enabled", "browser"):
            yield error
        for error in _require_bool(browser, "headless", "browser"):
            yield error
        for error in _require_int(browser, "timeout_seconds", 1, "browser"):
            yield error
        for error in _require_str(browser, "user_agent", "browser", allow_empty=True):
            yield error
        for error in _require_str(browser, "screenshot_path", "browser", allow_empty=False):
            yield error
        for error in _require_str(browser, "html_path", "browser", allow_empty=False):
            yield error

    storage = data.get("storage")
    if not isinstance(storage, dict):
        yield "storage must be an object"
    else:
        for error in _require_str(storage, "checkpoint_dir", "storage", allow_empty=False):
            yield error
        for error in _require_str(storage, "dataset_dir", "storage", allow_empty=False):
            yield error
        for error in _require_str(storage, "export_dir", "storage", allow_empty=False):
            yield error

    export = data.get("export")
    if not isinstance(export, dict):
        yield "export must be an object"
    else:
        format_name = export.get("format")
        if format_name not in ALLOWED_EXPORT_FORMATS:
            yield f"export.format must be one of {sorted(ALLOWED_EXPORT_FORMATS)!r}"
        for error in _require_str(export, "output_path", "export", allow_empty=False):
            yield error

    doctor = data.get("doctor")
    if doctor is not None:
        if not isinstance(doctor, dict):
            yield "doctor must be an object when present"
        else:
            targets = doctor.get("network_targets")
            if targets is not None and (
                not isinstance(targets, list)
                or not all(isinstance(target, str) and target.strip() for target in targets)
            ):
                yield "doctor.network_targets must be a string array when present"
            redis_url = doctor.get("redis_url")
            if redis_url is not None and not isinstance(redis_url, str):
                yield "doctor.redis_url must be a string when present"


def _require_int(data: dict, key: str, minimum: int, section: str) -> list[str]:
    value = data.get(key)
    if not isinstance(value, int) or value < minimum:
        return [f"{section}.{key} must be an integer >= {minimum}"]
    return []


def _require_bool(data: dict, key: str, section: str) -> list[str]:
    value = data.get(key)
    if not isinstance(value, bool):
        return [f"{section}.{key} must be a boolean"]
    return []


def _require_str(data: dict, key: str, section: str, allow_empty: bool) -> list[str]:
    value = data.get(key)
    if not isinstance(value, str):
        return [f"{section}.{key} must be a string"]
    if not allow_empty and not value.strip():
        return [f"{section}.{key} must be a non-empty string"]
    return []


def collect_contract_config_report(root: Path, config_paths: dict[str, Path] | None = None) -> dict:
    targets = config_paths or resolve_default_configs(root)
    checks = [validate_contract_config(runtime, path) for runtime, path in sorted(targets.items())]

    missing_runtimes = sorted(ALLOWED_RUNTIMES - set(targets))
    for runtime in missing_runtimes:
        checks.append(_failed_check(runtime, root / "<missing>", "no config path resolved"))

    passed = sum(1 for check in checks if check["status"] == "passed")
    failed = len(checks) - passed
    exit_code = 1 if failed else 0
    return {
        "command": "validate-contract-configs",
        "summary": "failed" if exit_code else "passed",
        "summary_text": f"{passed} passed, {failed} failed",
        "exit_code": exit_code,
        "checks": checks,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate shared spider framework config artifacts")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent), help="repository root path")
    parser.add_argument(
        "--config",
        action="append",
        default=[],
        help="runtime=path mapping, for example --config java=artifacts/java-contract.yaml",
    )
    parser.add_argument("--json", action="store_true", help="print validation report as JSON")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    config_paths = parse_config_args(args.config, root) if args.config else None
    report = collect_contract_config_report(root, config_paths)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("validate-contract-configs summary:", report["summary"])
        for check in report["checks"]:
            print(f"- {check['name']}: {check['status']} ({check['details']})")

    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
