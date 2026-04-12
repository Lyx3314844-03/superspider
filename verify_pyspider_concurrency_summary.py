from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from pyspider.research.job import ResearchJob
from pyspider.runtime.async_runtime import AsyncResearchConfig, AsyncResearchRuntime


def _build_jobs(count: int, delay_ms: int) -> tuple[list[ResearchJob], list[str]]:
    jobs = [
        ResearchJob(
            seed_urls=[f"https://concurrency-{index}.example"],
            extract_schema={},
            policy={"simulate_delay_ms": delay_ms},
        )
        for index in range(count)
    ]
    contents = [f"<title>Concurrent {index}</title>" for index in range(count)]
    return jobs, contents


async def _collect_async_report() -> dict:
    runtime = AsyncResearchRuntime(config=AsyncResearchConfig(max_concurrent=4))

    jobs, contents = _build_jobs(12, 15)
    runtime.reset_metrics()
    multiple_results = await runtime.run_multiple(jobs, contents)
    concurrency_metrics = runtime.snapshot_metrics()
    bounded_ready = (
        len(multiple_results) == 12
        and all(result.error is None for result in multiple_results)
        and concurrency_metrics["tasks_completed"] == 12
        and concurrency_metrics["tasks_failed"] == 0
        and concurrency_metrics["peak_inflight"] <= concurrency_metrics["max_concurrent"]
    )

    stream_jobs, stream_contents = _build_jobs(6, 10)
    runtime.reset_metrics()
    streamed = []
    async for result in runtime.run_stream(stream_jobs, stream_contents):
        streamed.append(result)
    stream_metrics = runtime.snapshot_metrics()
    stream_ready = (
        len(streamed) == 6
        and all(result.error is None for result in streamed)
        and stream_metrics["tasks_completed"] == 6
        and stream_metrics["tasks_failed"] == 0
    )

    soak_jobs, soak_contents = _build_jobs(8, 12)
    soak_report = await runtime.run_soak(soak_jobs, soak_contents, rounds=3)
    soak_ready = bool(soak_report["stable"])

    checks = [
        {
            "name": "bounded-concurrency",
            "status": "passed" if bounded_ready else "failed",
            "details": f"peak={concurrency_metrics['peak_inflight']} max={concurrency_metrics['max_concurrent']} completed={concurrency_metrics['tasks_completed']}",
        },
        {
            "name": "stream-runtime",
            "status": "passed" if stream_ready else "failed",
            "details": f"streamed={len(streamed)} completed={stream_metrics['tasks_completed']} failed={stream_metrics['tasks_failed']}",
        },
        {
            "name": "synthetic-soak",
            "status": "passed" if soak_ready else "failed",
            "details": f"rounds={soak_report['rounds']} results={soak_report['results']} peak={soak_report['peak_inflight']}",
        },
    ]

    passed = sum(1 for check in checks if check["status"] == "passed")
    failed = len(checks) - passed
    return {
        "command": "verify-pyspider-concurrency-summary",
        "summary": "failed" if failed else "passed",
        "summary_text": f"{passed} passed, {failed} failed",
        "exit_code": 1 if failed else 0,
        "runtime": "python",
        "checks": checks,
        "metrics": {
            "checks_passed": passed,
            "checks_failed": failed,
            "checks_total": len(checks),
            "pass_rate": round(passed / len(checks), 4) if checks else 0.0,
            "bounded_concurrency_ready": bounded_ready,
            "stream_ready": stream_ready,
            "soak_ready": soak_ready,
            "peak_inflight": concurrency_metrics["peak_inflight"],
            "max_concurrent": concurrency_metrics["max_concurrent"],
            "soak_success_rate": soak_report["success_rate"],
        },
    }


def run_pyspider_concurrency_summary(_: Path) -> dict:
    return asyncio.run(_collect_async_report())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run PySpider concurrency and soak summary checks")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent), help="repository root path")
    parser.add_argument("--json", action="store_true", help="print summary as JSON")
    args = parser.parse_args(argv)

    report = run_pyspider_concurrency_summary(Path(args.root).resolve())
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("verify-pyspider-concurrency-summary:", report["summary"])
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
