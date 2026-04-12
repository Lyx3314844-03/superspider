from __future__ import annotations

import argparse
import importlib.util
import io
import json
from contextlib import redirect_stdout
from pathlib import Path


EXPECTED_OPERATOR_PRODUCTS = (
    "jobdir",
    "http_cache",
    "browser_tooling",
    "autoscaling_pools",
    "debug_console",
)


def _load_tool(root: Path, name: str):
    path = root / "tools" / name
    spec = importlib.util.spec_from_file_location(name.replace(".", "_"), path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _capture_json(func, *args):
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        exit_code = func(*args)
    return exit_code, json.loads(buffer.getvalue())


def collect_operator_products_report(root: Path) -> dict:
    checks: list[dict] = []

    manifest = json.loads((root / "contracts" / "ecosystem-manifest.json").read_text(encoding="utf-8"))
    runtimes = manifest.get("runtimes", [])
    for runtime in runtimes:
        products = set(runtime.get("operator_products") or [])
        missing = [name for name in EXPECTED_OPERATOR_PRODUCTS if name not in products]
        checks.append(
            {
                "name": f"manifest:{runtime['name']}",
                "status": "passed" if not missing else "failed",
                "details": "operator products declared" if not missing else f"missing operator products: {missing!r}",
            }
        )

    tool = _load_tool(root, "jobdir_tool.py")
    tmp_root = root / "artifacts" / "operator-products-check"
    jobdir = tmp_root / "jobdir"
    exit_code, payload = _capture_json(tool.main, ["init", "--path", str(jobdir), "--runtime", "python", "--url", "https://example.com"])
    checks.append(
        {
            "name": "jobdir-tool",
            "status": "passed" if exit_code == 0 and payload["state"] == "ready" else "failed",
            "details": f"jobdir init state={payload.get('state')!r}",
        }
    )

    cache_tool = _load_tool(root, "http_cache_tool.py")
    cache_path = tmp_root / "cache" / "incremental.json"
    _capture_json(
        cache_tool.main,
        [
            "seed",
            "--path",
            str(cache_path),
            "--url",
            "https://example.com",
            "--backend",
            "file-json",
            "--strategy",
            "delta-fetch",
            "--revalidate-seconds",
            "300",
        ],
    )
    exit_code, payload = _capture_json(cache_tool.main, ["status", "--path", str(cache_path)])
    checks.append(
        {
            "name": "http-cache-tool",
            "status": "passed"
            if exit_code == 0 and payload.get("backend") == "file-json" and payload.get("strategy") == "delta-fetch"
            else "failed",
            "details": f"backend={payload.get('backend')!r} strategy={payload.get('strategy')!r}",
        }
    )

    console_tool = _load_tool(root, "runtime_console.py")
    control_plane = tmp_root / "control-plane"
    control_plane.mkdir(parents=True, exist_ok=True)
    (control_plane / "results.jsonl").write_text('{"id":"r1"}\n', encoding="utf-8")
    (control_plane / "events.jsonl").write_text('{"event":"start"}\n', encoding="utf-8")
    exit_code, payload = _capture_json(
        console_tool.main,
        ["snapshot", "--control-plane", str(control_plane), "--jobdir", str(jobdir), "--lines", "1"],
    )
    checks.append(
        {
            "name": "runtime-console-tool",
            "status": "passed"
            if exit_code == 0 and payload.get("results_exists") and payload.get("events_exists")
            else "failed",
            "details": f"results_exists={payload.get('results_exists')} events_exists={payload.get('events_exists')}",
        }
    )

    helper = (root / "tools" / "playwright_fetch.py").read_text(encoding="utf-8")
    required_tokens = ["--tooling-command", "--trace-path", "--har-path", "--route-manifest", "--codegen-out"]
    missing_tokens = [token for token in required_tokens if token not in helper]
    checks.append(
        {
            "name": "playwright-tooling-helper",
            "status": "passed" if not missing_tokens else "failed",
            "details": "shared Playwright helper exposes trace/HAR/mock/codegen flags"
            if not missing_tokens
            else f"missing flags: {missing_tokens!r}",
        }
    )

    schema = json.loads((root / "contracts" / "job.schema.json").read_text(encoding="utf-8"))
    schema_ok = all(key in schema["properties"] for key in ("jobdir", "cache", "pools", "debug"))
    browser_props = schema["$defs"]["browser"]["properties"]
    browser_ok = all(
        key in browser_props
        for key in ("trace_path", "har_path", "har_replay", "route_manifest", "codegen_out", "codegen_language")
    )
    checks.append(
        {
            "name": "job-schema-operator-products",
            "status": "passed" if schema_ok and browser_ok else "failed",
            "details": "job schema exposes jobdir/cache/pools/debug and browser tooling fields"
            if schema_ok and browser_ok
            else "job schema is missing operator product fields",
        }
    )

    passed = sum(1 for check in checks if check["status"] == "passed")
    failed = len(checks) - passed
    return {
        "command": "verify-operator-products",
        "summary": "passed" if failed == 0 else "failed",
        "summary_text": f"{passed} passed, {failed} failed",
        "exit_code": 0 if failed == 0 else 1,
        "checks": checks,
        "required_operator_products": list(EXPECTED_OPERATOR_PRODUCTS),
    }


def render_markdown(report: dict) -> str:
    lines = [
        "# Operator Products",
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
    parser = argparse.ArgumentParser(description="Verify shared operator product surfaces across schema, tools, and runtime manifests")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent), help="repository root path")
    parser.add_argument("--json", action="store_true", help="print JSON report")
    parser.add_argument("--markdown-out", default="", help="optional markdown output path")
    args = parser.parse_args(argv)

    report = collect_operator_products_report(Path(args.root).resolve())
    if args.markdown_out:
        Path(args.markdown_out).write_text(render_markdown(report), encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("verify-operator-products:", report["summary"])
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
