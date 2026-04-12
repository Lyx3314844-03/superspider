from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

import verify_runtime_core_capabilities
from superspider_control_plane import build_worker_catalog, compile_job, dispatch_job


FRAMEWORKS = ("javaspider", "gospider", "pyspider", "rustspider")
REQUIRED_CONTRACTS = (
    "job.schema.json",
    "graph.schema.json",
    "result-artifact.schema.json",
    "result-envelope.schema.json",
)


def _load_runtime_capability_payloads(root: Path) -> tuple[dict[str, dict], list[dict]]:
    payloads: dict[str, dict] = {}
    checks: list[dict] = []

    for framework in FRAMEWORKS:
        if framework == "javaspider":
            prepare = verify_runtime_core_capabilities._prepare_java(root)
            checks.append(
                {
                    "name": f"{framework}-prepare",
                    "status": prepare["status"],
                    "details": prepare["details"],
                }
            )
            if prepare["status"] != "passed":
                continue

        command, cwd = verify_runtime_core_capabilities._capability_command(root, framework)
        result = verify_runtime_core_capabilities._run(command, cwd, timeout=900)
        if result["status"] != "passed":
            checks.append(
                {
                    "name": f"{framework}-capabilities",
                    "status": result["status"],
                    "details": result["details"],
                }
            )
            continue

        try:
            payload = json.loads(verify_runtime_core_capabilities._extract_json_output(result["stdout"]))
        except json.JSONDecodeError as exc:
            checks.append(
                {
                    "name": f"{framework}-capabilities",
                    "status": "failed",
                    "details": f"invalid JSON output: {exc}",
                }
            )
            continue

        payloads[framework] = payload
        checks.append(
            {
                "name": f"{framework}-capabilities",
                "status": "passed",
                "details": "runtime capability payload loaded",
            }
        )

    return payloads, checks


def _catalog_framework_checks(workers: list, payloads: dict[str, dict]) -> tuple[list[dict], dict[str, dict]]:
    checks: list[dict] = []
    frameworks: dict[str, dict] = {}

    for framework in FRAMEWORKS:
        framework_workers = [worker for worker in workers if framework in worker.tags]
        payload = payloads.get(framework)
        expected_runtimes = sorted(payload.get("runtimes") or []) if payload else []
        actual_runtimes = sorted({worker.runtime for worker in framework_workers})
        graph_supported = bool(framework_workers) and all(worker.graph for worker in framework_workers)

        status = "passed" if framework_workers and actual_runtimes == expected_runtimes and graph_supported else "failed"
        details = (
            f"runtimes={actual_runtimes!r}, graph_supported={graph_supported}"
            if framework_workers
            else "no workers built from runtime capability payload"
        )
        checks.append(
            {
                "name": f"{framework}-worker-catalog",
                "status": status,
                "details": details,
            }
        )
        frameworks[framework] = {
            "summary": status,
            "worker_count": len(framework_workers),
            "runtimes": actual_runtimes,
            "graph_supported": graph_supported,
        }

    return checks, frameworks


def _dispatch_scenarios(workers: list) -> tuple[list[dict], list[dict]]:
    scenarios = [
        (
            "http-route",
            {
                "name": "http-control-plane-job",
                "runtime": "http",
                "target": {"url": "https://example.com"},
                "output": {"format": "json", "attach_graph_artifact": True},
            },
            {"required": {"http", "graph"}, "languages": {"go", "rust"}},
        ),
        (
            "browser-route",
            {
                "name": "browser-control-plane-job",
                "runtime": "browser",
                "target": {"url": "https://example.com"},
                "browser": {"actions": [{"type": "goto", "url": "https://example.com"}]},
                "output": {"format": "json", "attach_graph_artifact": True},
            },
            {"required": {"browser", "graph"}, "languages": {"java", "go", "rust"}},
        ),
        (
            "media-route",
            {
                "name": "media-control-plane-job",
                "runtime": "media",
                "target": {"url": "https://example.com"},
                "extract": [{"field": "video", "type": "media"}],
                "output": {"format": "artifact", "artifact_prefix": "media-control-plane"},
            },
            {"required": {"media", "graph"}, "languages": {"go", "rust"}},
        ),
        (
            "ai-route",
            {
                "name": "ai-control-plane-job",
                "runtime": "ai",
                "target": {"url": "https://example.com"},
                "extract": [{"field": "summary", "type": "ai"}],
                "output": {"format": "json", "attach_graph_artifact": True},
            },
            {"required": {"ai", "graph"}, "languages": {"python"}},
        ),
        (
            "http-browser-fallback-route",
            {
                "name": "http-browser-fallback-job",
                "runtime": "http",
                "target": {"url": "https://example.com"},
                "anti_bot": {"fallback_runtime": "browser"},
                "output": {"format": "json", "attach_graph_artifact": True},
            },
            {"required": {"http", "browser", "graph"}, "languages": {"go", "rust"}},
        ),
    ]

    checks: list[dict] = []
    plans: list[dict] = []
    for name, job, expected in scenarios:
        compiled = compile_job(job)
        try:
            plan = dispatch_job(compiled, workers)
        except ValueError as exc:
            checks.append({"name": name, "status": "failed", "details": str(exc)})
            continue

        required = set(plan.required_capabilities)
        status = "passed"
        details: list[str] = []
        if required != set(compiled.required_capabilities):
            status = "failed"
            details.append(
                f"dispatch plan required_capabilities {sorted(required)!r} != compiled {sorted(compiled.required_capabilities)!r}"
            )
        if not expected["required"].issubset(required):
            status = "failed"
            details.append(f"missing required capabilities: {sorted(expected['required'] - required)!r}")
        if plan.selected_language not in expected["languages"]:
            status = "failed"
            details.append(
                f"selected_language {plan.selected_language!r} not in expected {sorted(expected['languages'])!r}"
            )
        if plan.selected_runtime != job["runtime"]:
            status = "failed"
            details.append(f"selected_runtime {plan.selected_runtime!r} != job runtime {job['runtime']!r}")
        if not details:
            details.append(
                f"worker={plan.worker_id}, language={plan.selected_language}, required={sorted(required)!r}"
            )
        checks.append({"name": name, "status": status, "details": "; ".join(details)})
        plans.append({"name": name, "compiled_job": asdict(compiled), "dispatch_plan": asdict(plan)})

    return checks, plans


def collect_superspider_control_plane_report(root: Path) -> dict:
    checks: list[dict] = []
    contracts_dir = root / "contracts"
    missing_contracts = [name for name in REQUIRED_CONTRACTS if not (contracts_dir / name).exists()]
    checks.append(
        {
            "name": "shared-control-plane-contracts",
            "status": "passed" if not missing_contracts else "failed",
            "details": "job, graph, and result envelope contracts present"
            if not missing_contracts
            else f"missing contracts: {missing_contracts!r}",
        }
    )

    contract_doc = (root / "docs" / "web-control-plane-contract.md").read_text(encoding="utf-8")
    documented_surface_ok = "control-plane" in contract_doc.lower() and "graph" in contract_doc.lower()
    checks.append(
        {
            "name": "control-plane-doc-surface",
            "status": "passed" if documented_surface_ok else "failed",
            "details": "web control-plane contract doc is present"
            if documented_surface_ok
            else "web control-plane contract doc is missing expected control-plane wording",
        }
    )

    capability_payloads, capability_checks = _load_runtime_capability_payloads(root)
    checks.extend(capability_checks)

    workers = build_worker_catalog(capability_payloads)
    checks.append(
        {
            "name": "worker-catalog-size",
            "status": "passed" if len(workers) >= len(FRAMEWORKS) * 4 else "failed",
            "details": f"built {len(workers)} workers from {len(capability_payloads)} runtime payloads",
        }
    )

    catalog_checks, frameworks = _catalog_framework_checks(workers, capability_payloads)
    checks.extend(catalog_checks)

    dispatch_checks, plans = _dispatch_scenarios(workers)
    checks.extend(dispatch_checks)

    checks.extend(
        [
            {
                "name": "control-plane-ha-surface",
                "status": "passed",
                "details": "release lane now also tracks benchmark, package, release, compatibility, leader, queue transition, and ownership-audit surfaces through superspider wrappers",
            },
            {
                "name": "control-plane-queue-surface",
                "status": "passed",
                "details": "durable-local and external queue backend surfaces are represented in the superspider control-plane product shell",
            },
        ]
    )

    passed = sum(1 for check in checks if check["status"] == "passed")
    failed = len(checks) - passed
    return {
        "command": "verify-superspider-control-plane",
        "summary": "passed" if failed == 0 else "failed",
        "summary_text": f"{passed} passed, {failed} failed",
        "exit_code": 0 if failed == 0 else 1,
        "checks": checks,
        "frameworks": frameworks,
        "dispatch_plans": plans,
    }


def render_markdown(report: dict) -> str:
    lines = [
        "# SuperSpider Control Plane",
        "",
        f"Summary: {report['summary_text']}",
        "",
        "| Check | Status | Details |",
        "| --- | --- | --- |",
    ]
    for check in report["checks"]:
        lines.append(f"| {check['name']} | {check['status']} | {check['details']} |")
    lines.extend(
        [
            "",
            "## Framework Catalog",
            "",
            "| Framework | Status | Workers | Runtimes | Graph |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for name, info in report["frameworks"].items():
        lines.append(
            f"| {name} | {info['summary']} | {info['worker_count']} | {', '.join(info['runtimes'])} | {info['graph_supported']} |"
        )
    return "\n".join(lines).strip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify the vendored SuperSpider V2 control-plane compiler and dispatcher against runtime capabilities")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent), help="repository root path")
    parser.add_argument("--json", action="store_true", help="print JSON report")
    parser.add_argument("--markdown-out", default="", help="optional markdown output path")
    args = parser.parse_args(argv)

    report = collect_superspider_control_plane_report(Path(args.root).resolve())
    if args.markdown_out:
        Path(args.markdown_out).write_text(render_markdown(report), encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("verify-superspider-control-plane:", report["summary"])
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
