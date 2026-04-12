from __future__ import annotations

import argparse
import json
from pathlib import Path

import verify_captcha_live_readiness
import verify_javaspider_ai_live
import verify_runtime_core_capabilities


CORE_ENTRYPOINTS = {
    "config",
    "crawl",
    "browser",
    "ai",
    "doctor",
    "export",
    "scrapy",
    "ultimate",
    "anti-bot",
    "node-reverse",
    "jobdir",
    "http-cache",
    "console",
    "version",
}

RUNTIME_BY_FRAMEWORK = {
    "javaspider": "java",
    "gospider": "go",
    "pyspider": "python",
    "rustspider": "rust",
}


def _extract_payload(stdout: str) -> dict:
    payload = verify_runtime_core_capabilities._extract_json_output(stdout)
    return json.loads(payload)


def _load_capabilities(root: Path, framework: str) -> dict:
    if framework == "javaspider":
        verify_runtime_core_capabilities._prepare_java(root)
    command, cwd = verify_runtime_core_capabilities._capability_command(root, framework)
    result = verify_runtime_core_capabilities._run(command, cwd)
    if result["status"] == "passed":
        payload = _extract_payload(result["stdout"])
        payload["_capability_status"] = "passed"
        payload["_capability_details"] = result["details"]
        return payload
    return _fallback_capabilities(root, framework, result["details"])


def _fallback_capabilities(root: Path, framework: str, details: str) -> dict:
    manifest = json.loads(
        (root / "contracts" / "ecosystem-manifest.json").read_text(encoding="utf-8")
    )
    runtime_entry = next(
        (item for item in manifest.get("runtimes", []) if item.get("name") == framework),
        {},
    )
    operator_products = {
        name: {} for name in runtime_entry.get("operator_products", [])
    }
    kernel_contracts = {
        name: []
        for name in runtime_entry.get("kernel_contracts", [])
    }
    control_plane = {
        "task_api": "cli" in runtime_entry.get("operator_surfaces", []),
        "result_envelope": True,
        "artifact_refs": True,
        "graph_artifact": True,
        "graph_extract": True,
    }
    return {
        "command": "capabilities",
        "framework": framework,
        "runtime": RUNTIME_BY_FRAMEWORK[framework],
        "entrypoints": runtime_entry.get("entrypoints", []),
        "modules": [],
        "operator_products": operator_products,
        "control_plane": control_plane,
        "observability": [],
        "runtimes": [],
        "shared_contracts": [],
        "kernel_contracts": kernel_contracts,
        "_capability_status": "failed",
        "_capability_details": details,
    }


def collect_report(root: Path) -> dict:
    captcha_live = verify_captcha_live_readiness.collect_captcha_live_readiness_report(root)
    java_ai_live = verify_javaspider_ai_live.run_javaspider_ai_live(root)

    frameworks: dict[str, dict] = {}
    for framework in ("javaspider", "gospider", "pyspider", "rustspider"):
        payload = _load_capabilities(root, framework)
        entrypoints = payload.get("entrypoints") or []
        modules = payload.get("modules") or []
        operator_products = payload.get("operator_products") or {}
        control_plane = payload.get("control_plane") or {}
        observability = payload.get("observability") or []
        runtimes = payload.get("runtimes") or []
        shared_contracts = payload.get("shared_contracts") or []
        kernel_contracts = payload.get("kernel_contracts") or {}
        live_surfaces = []
        captcha_payload = captcha_live.get("frameworks", {}).get(framework)
        if isinstance(captcha_payload, dict):
            live_surfaces.append(
                {
                    "name": "captcha-live-readiness",
                    "summary": captcha_payload.get("summary", "unknown"),
                    "details": captcha_payload.get("summary_text", ""),
                }
            )
        if framework == "javaspider":
            live_surfaces.append(
                {
                    "name": "ai-live-readiness",
                    "summary": java_ai_live.get("summary", "unknown"),
                    "details": java_ai_live.get("summary_text", ""),
                }
            )

        frameworks[framework] = {
            "runtime": payload.get("runtime"),
            "capability_status": payload.get("_capability_status", "passed"),
            "capability_details": payload.get("_capability_details", ""),
            "entrypoints": entrypoints,
            "extended_entrypoints": [item for item in entrypoints if item not in CORE_ENTRYPOINTS],
            "modules": modules,
            "operator_products": sorted(operator_products.keys()),
            "control_plane_keys": sorted(
                key for key, value in control_plane.items() if value is True
            ),
            "observability": observability,
            "runtimes": runtimes,
            "shared_contracts": shared_contracts,
            "kernel_contracts": sorted(kernel_contracts.keys()),
            "live_surfaces": live_surfaces,
        }

    return {
        "command": "generate-framework-deep-surfaces-report",
        "summary": "passed",
        "summary_text": "deep surfaces collected from runtime capability payloads",
        "exit_code": 0,
        "frameworks": frameworks,
    }


def render_markdown(report: dict) -> str:
    lines = [
        "# Framework Deep Surfaces Report",
        "",
        f"Summary: {report['summary_text']}",
        "",
    ]

    for framework, payload in report["frameworks"].items():
        lines.extend(
            [
                f"## {framework}",
                "",
                f"- runtime: `{payload['runtime']}`",
                f"- capability status: `{payload['capability_status']}`",
                f"- capability details: `{payload['capability_details']}`",
                f"- runtimes: `{', '.join(payload['runtimes'])}`",
                f"- entrypoints: `{', '.join(payload['entrypoints'])}`",
                f"- extended entrypoints: `{', '.join(payload['extended_entrypoints'])}`",
                f"- modules: `{', '.join(payload['modules'])}`",
                f"- operator products: `{', '.join(payload['operator_products'])}`",
                f"- control plane keys: `{', '.join(payload['control_plane_keys'])}`",
                f"- shared contracts: `{', '.join(payload['shared_contracts'])}`",
                f"- kernel contracts: `{', '.join(payload['kernel_contracts'])}`",
                f"- observability: `{', '.join(payload['observability'])}`",
            ]
        )
        if payload["live_surfaces"]:
            lines.append("- live surfaces:")
            for item in payload["live_surfaces"]:
                lines.append(
                    f"  - `{item['name']}`: `{item['summary']}` | {item['details']}"
                )
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate a machine-derived report of the deep capability surfaces across the framework runtimes"
    )
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent), help="repository root path")
    parser.add_argument("--json", action="store_true", help="print JSON report")
    parser.add_argument("--markdown-out", default="", help="optional markdown output path")
    args = parser.parse_args(argv)

    report = collect_report(Path(args.root).resolve())
    if args.markdown_out:
        Path(args.markdown_out).write_text(render_markdown(report), encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("generate-framework-deep-surfaces-report:", report["summary"])
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
