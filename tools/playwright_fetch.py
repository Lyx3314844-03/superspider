from __future__ import annotations

import argparse
import json
from pathlib import Path

from _shared_runtime_tools import (
    fetch_text,
    utc_now,
    write_json,
    write_placeholder_png,
    write_text,
    write_trace_zip,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Shared browser tooling helper")
    parser.add_argument("--tooling-command", choices=("trace", "mock", "codegen"), required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--trace-path", default="")
    parser.add_argument("--har-path", default="")
    parser.add_argument("--route-manifest", default="")
    parser.add_argument("--html", default="")
    parser.add_argument("--screenshot", default="")
    parser.add_argument("--codegen-out", default="")
    parser.add_argument("--codegen-language", default="python")
    return parser


def render_codegen(url: str, language: str, route_manifest: str) -> str:
    if language.lower() in {"js", "javascript", "ts", "typescript"}:
        route_block = ""
        if route_manifest:
            route_block = (
                f"  // TODO: load and apply routes from {route_manifest}\n"
                "  // await page.route('**/*', async route => route.continue());\n"
            )
        return (
            "const { chromium } = require('playwright');\n\n"
            "(async () => {\n"
            "  const browser = await chromium.launch({ headless: true });\n"
            "  const page = await browser.newPage();\n"
            f"{route_block}"
            f"  await page.goto('{url}', {{ waitUntil: 'networkidle' }});\n"
            "  console.log(await page.title());\n"
            "  await browser.close();\n"
            "})();\n"
        )
    route_block = ""
    if route_manifest:
        route_block = (
            f"    # TODO: load and apply routes from {route_manifest}\n"
            "    # await page.route('**/*', lambda route: route.continue_())\n"
        )
    return (
        "from playwright.async_api import async_playwright\n"
        "import asyncio\n\n"
        "async def main() -> None:\n"
        "    async with async_playwright() as pw:\n"
        "        browser = await pw.chromium.launch(headless=True)\n"
        "        page = await browser.new_page()\n"
        f"{route_block}"
        f"        await page.goto('{url}', wait_until='networkidle')\n"
        "        print(await page.title())\n"
        "        await browser.close()\n\n"
        "asyncio.run(main())\n"
    )


def command_trace(args: argparse.Namespace) -> int:
    fetch_result = fetch_text(args.url)
    html_content = fetch_result["text"] or (
        "<html><head><title>Trace Placeholder</title></head>"
        "<body><p>Trace artifact placeholder.</p></body></html>"
    )

    artifact_paths: dict[str, str] = {}
    if args.html:
        artifact_paths["html"] = str(write_text(args.html, html_content))
    if args.screenshot:
        artifact_paths["screenshot"] = str(write_placeholder_png(args.screenshot))
    if args.har_path:
        har_payload = {
            "log": {
                "version": "1.2",
                "creator": {"name": "SuperSpider shared tooling", "version": "1.0"},
                "pages": [{"id": "page_1", "title": args.url, "startedDateTime": utc_now()}],
                "entries": [
                    {
                        "startedDateTime": utc_now(),
                        "request": {"method": "GET", "url": args.url},
                        "response": {"status": fetch_result["status"]},
                    }
                ],
            }
        }
        artifact_paths["har"] = str(write_json(args.har_path, har_payload))
    trace_payload = {
        "tooling_command": "trace",
        "url": args.url,
        "generated_at": utc_now(),
        "fetched": {
            "ok": fetch_result["ok"],
            "status": fetch_result["status"],
            "final_url": fetch_result["url"],
            "error": fetch_result["error"],
        },
        "artifacts": artifact_paths,
    }
    if args.trace_path:
        artifact_paths["trace"] = str(write_trace_zip(args.trace_path, trace_payload))
    print(
        json.dumps(
            {
                "command": "browser trace",
                "url": args.url,
                "artifacts": artifact_paths,
                "fetched": trace_payload["fetched"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def command_mock(args: argparse.Namespace) -> int:
    route_manifest = Path(args.route_manifest)
    if not route_manifest.exists():
        print(
            json.dumps(
                {
                    "command": "browser mock",
                    "url": args.url,
                    "error": f"route manifest not found: {route_manifest}",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2

    manifest = json.loads(route_manifest.read_text(encoding="utf-8"))
    fetch_result = fetch_text(args.url)
    if args.html:
        write_text(args.html, fetch_result["text"] or "<html><body>mock placeholder</body></html>")
    if args.screenshot:
        write_placeholder_png(args.screenshot)
    print(
        json.dumps(
            {
                "command": "browser mock",
                "url": args.url,
                "route_manifest": str(route_manifest),
                "route_count": len(manifest.get("routes", [])),
                "fetched": {
                    "ok": fetch_result["ok"],
                    "status": fetch_result["status"],
                    "error": fetch_result["error"],
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def command_codegen(args: argparse.Namespace) -> int:
    if not args.codegen_out.strip():
        print(json.dumps({"command": "browser codegen", "error": "missing --codegen-out"}))
        return 2
    output_path = Path(args.codegen_out)
    code = render_codegen(args.url, args.codegen_language, args.route_manifest)
    write_text(output_path, code)
    print(
        json.dumps(
            {
                "command": "browser codegen",
                "url": args.url,
                "language": args.codegen_language,
                "output": str(output_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.tooling_command == "trace":
        return command_trace(args)
    if args.tooling_command == "mock":
        return command_mock(args)
    return command_codegen(args)


if __name__ == "__main__":
    raise SystemExit(main())
