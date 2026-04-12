"""异步 Runtime 接桥模块

提供基于 asyncio 的异步研究运行时，支持：
- 并发执行多个研究任务
- 异步 HTTP 请求
- 流式输出
- 与 Jupyter notebook 集成
"""

import asyncio
import json
import threading
import time
from dataclasses import dataclass
from typing import Any, AsyncIterator, Callable, Dict, List, Optional

from pyspider.dataset.writer import DatasetWriter
from pyspider.extract.studio import ExtractionStudio
from pyspider.profiler.site_profiler import SiteProfiler
from pyspider.research.job import ResearchJob


@dataclass
class AsyncResearchResult:
    """异步研究结果"""

    seed: str
    profile: Any
    extract: Dict[str, Any]
    duration_ms: float
    dataset: Optional[Any] = None
    error: Optional[str] = None


@dataclass
class AsyncResearchConfig:
    """异步研究配置"""

    max_concurrent: int = 5
    timeout_seconds: float = 30.0
    enable_streaming: bool = False
    output_callback: Optional[Callable[[AsyncResearchResult], None]] = None


@dataclass
class AsyncRuntimeMetrics:
    """异步 runtime 观测指标"""

    max_concurrent: int
    tasks_started: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    current_inflight: int = 0
    peak_inflight: int = 0
    total_duration_ms: float = 0.0
    max_duration_ms: float = 0.0
    last_error: str = ""


class AsyncResearchRuntime:
    """异步研究运行时

    支持并发执行、流式输出和 notebook 集成。

    使用示例:
        runtime = AsyncResearchRuntime(max_concurrent=3)

        # 并发执行
        results = await runtime.run_multiple([job1, job2, job3])

        # 流式执行
        async for result in runtime.run_stream(jobs):
            print(f"Completed: {result.seed}")
    """

    def __init__(self, config: Optional[AsyncResearchConfig] = None) -> None:
        self.config = config or AsyncResearchConfig()
        self.profiler = SiteProfiler()
        self.studio = ExtractionStudio()
        self.writer = DatasetWriter()
        self._semaphore = asyncio.Semaphore(self.config.max_concurrent)
        self._metrics_lock = threading.Lock()
        self._metrics = AsyncRuntimeMetrics(max_concurrent=self.config.max_concurrent)

    async def run_single(
        self,
        job: ResearchJob,
        content: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> AsyncResearchResult:
        """执行单个研究任务

        Args:
            job: 研究任务
            content: 可选的页面内容
            timeout: 超时时间（秒）

        Returns:
            AsyncResearchResult: 研究结果
        """
        timeout = timeout or self.config.timeout_seconds
        start_time = time.time()

        async with self._semaphore:
            self._record_task_start()
            try:
                seed = job.seed_urls[0]
                content = content or f"<title>{seed}</title>"
                simulate_delay_ms = self._simulate_delay_ms(job)
                if simulate_delay_ms > 0:
                    await asyncio.sleep(simulate_delay_ms / 1000)

                # 异步执行分析和提取
                profile = await asyncio.to_thread(self.profiler.profile, seed, content)
                extracted = await asyncio.to_thread(
                    self.studio.run, content, job.extract_schema, job.extract_specs
                )

                result = AsyncResearchResult(
                    seed=seed,
                    profile=profile,
                    extract=extracted,
                    duration_ms=(time.time() - start_time) * 1000,
                )

                # 可选：写入数据集
                output_target = job.output or {}
                if output_target.get("path"):
                    dataset = await asyncio.to_thread(
                        self.writer.write, [extracted], output_target
                    )
                    result.dataset = dataset

                # 可选：回调
                if self.config.output_callback:
                    self.config.output_callback(result)

                self._record_task_finish(result.duration_ms, error=None)
                return result

            except Exception as e:
                result = AsyncResearchResult(
                    seed=job.seed_urls[0] if job.seed_urls else "unknown",
                    profile=None,
                    extract={},
                    duration_ms=(time.time() - start_time) * 1000,
                    error=str(e),
                )
                self._record_task_finish(result.duration_ms, error=result.error)
                return result

    async def run_multiple(
        self,
        jobs: List[ResearchJob],
        contents: Optional[List[str]] = None,
    ) -> List[AsyncResearchResult]:
        """并发执行多个研究任务

        Args:
            jobs: 研究任务列表
            contents: 可选的页面内容列表

        Returns:
            List[AsyncResearchResult]: 研究结果列表
        """
        contents = contents or [None] * len(jobs)
        tasks = [self.run_single(job, content) for job, content in zip(jobs, contents)]
        return await asyncio.gather(*tasks)

    async def run_stream(
        self,
        jobs: List[ResearchJob],
        contents: Optional[List[str]] = None,
    ) -> AsyncIterator[AsyncResearchResult]:
        """流式执行研究任务

        每完成一个任务就 yield 一个结果，适合 notebook 中的实时展示。

        Args:
            jobs: 研究任务列表
            contents: 可选的页面内容列表

        Yields:
            AsyncResearchResult: 研究结果
        """
        contents = contents or [None] * len(jobs)

        # 创建任务
        async def run_with_index(index: int) -> tuple:
            result = await self.run_single(
                jobs[index], contents[index] if contents else None
            )
            return (index, result)

        tasks = [asyncio.create_task(run_with_index(i)) for i in range(len(jobs))]

        # 按完成顺序 yield
        for coro in asyncio.as_completed(tasks):
            index, result = await coro
            yield result

    async def run_soak(
        self,
        jobs: List[ResearchJob],
        contents: Optional[List[str]] = None,
        rounds: int = 1,
    ) -> Dict[str, Any]:
        """运行 synthetic 高并发 soak，用于长稳和背压证明。"""
        rounds = max(rounds, 1)
        contents = contents or [None] * len(jobs)
        started = time.time()
        self.reset_metrics()

        all_results: List[AsyncResearchResult] = []
        for _ in range(rounds):
            all_results.extend(await self.run_multiple(jobs, contents))

        metrics = self.snapshot_metrics()
        total = len(all_results)
        failures = sum(1 for result in all_results if result.error)
        successes = total - failures
        success_rate = successes / total if total else 0.0

        return {
            "jobs": len(jobs),
            "rounds": rounds,
            "results": total,
            "successes": successes,
            "failures": failures,
            "success_rate": round(success_rate, 4),
            "duration_ms": round((time.time() - started) * 1000, 2),
            "peak_inflight": metrics["peak_inflight"],
            "max_concurrent": self.config.max_concurrent,
            "stable": (
                metrics["current_inflight"] == 0
                and failures == 0
                and metrics["tasks_completed"] == total
                and metrics["peak_inflight"] <= self.config.max_concurrent
            ),
        }

    def reset_metrics(self) -> None:
        """重置 runtime 观测指标。"""
        with self._metrics_lock:
            self._metrics = AsyncRuntimeMetrics(
                max_concurrent=self.config.max_concurrent
            )

    def snapshot_metrics(self) -> Dict[str, Any]:
        """返回当前 runtime 指标快照。"""
        with self._metrics_lock:
            average = (
                self._metrics.total_duration_ms / self._metrics.tasks_completed
                if self._metrics.tasks_completed
                else 0.0
            )
            return {
                "max_concurrent": self._metrics.max_concurrent,
                "tasks_started": self._metrics.tasks_started,
                "tasks_completed": self._metrics.tasks_completed,
                "tasks_failed": self._metrics.tasks_failed,
                "current_inflight": self._metrics.current_inflight,
                "peak_inflight": self._metrics.peak_inflight,
                "average_duration_ms": round(average, 2),
                "max_duration_ms": round(self._metrics.max_duration_ms, 2),
                "last_error": self._metrics.last_error,
            }

    def to_notebook_display(self, result: AsyncResearchResult) -> Dict[str, Any]:
        """转换为 notebook 可展示格式

        Args:
            result: 研究结果

        Returns:
            Dict: 可展示的数据格式
        """
        display_data = {
            "seed": result.seed,
            "duration_ms": round(result.duration_ms, 2),
            "extract": result.extract,
        }

        if result.profile:
            display_data["profile"] = {
                "url": result.profile.url,
                "page_type": result.profile.page_type,
                "risk_level": result.profile.risk_level,
            }

        if result.error:
            display_data["error"] = result.error

        return display_data

    def _record_task_start(self) -> None:
        with self._metrics_lock:
            self._metrics.tasks_started += 1
            self._metrics.current_inflight += 1
            if self._metrics.current_inflight > self._metrics.peak_inflight:
                self._metrics.peak_inflight = self._metrics.current_inflight

    def _record_task_finish(self, duration_ms: float, error: Optional[str]) -> None:
        with self._metrics_lock:
            self._metrics.current_inflight = max(self._metrics.current_inflight - 1, 0)
            self._metrics.total_duration_ms += duration_ms
            if duration_ms > self._metrics.max_duration_ms:
                self._metrics.max_duration_ms = duration_ms
            if error:
                self._metrics.tasks_failed += 1
                self._metrics.last_error = error
            else:
                self._metrics.tasks_completed += 1

    def _simulate_delay_ms(self, job: ResearchJob) -> float:
        value = job.policy.get("simulate_delay_ms", 0)
        try:
            return max(float(value), 0.0)
        except (TypeError, ValueError):
            return 0.0


# Notebook 集成辅助函数


def display_result_in_notebook(result: AsyncResearchResult) -> None:
    """在 Jupyter notebook 中展示结果

    Args:
        result: 研究结果
    """
    try:
        from IPython.display import display, HTML

        runtime = AsyncResearchRuntime()
        data = runtime.to_notebook_display(result)

        html = f"""
        <div style="border: 1px solid #ddd; padding: 10px; border-radius: 5px; margin: 5px 0;">
            <h3 style="margin: 0 0 10px 0;">🔬 Research Result</h3>
            <p><b>Seed:</b> {data['seed']}</p>
            <p><b>Duration:</b> {data['duration_ms']}ms</p>
            <p><b>Extract:</b></p>
            <pre style="background: #f5f5f5; padding: 5px;">{json.dumps(data['extract'], indent=2, ensure_ascii=False)}</pre>
        </div>
        """
        display(HTML(html))
    except ImportError:
        print(json.dumps(result.extract, indent=2, ensure_ascii=False))


async def research_batch(
    urls: List[str],
    schema: Optional[Dict[str, Any]] = None,
    max_concurrent: int = 5,
    timeout: float = 30.0,
) -> List[Dict[str, Any]]:
    """批量研究 URLs（适合 notebook 使用）

    Args:
        urls: URL 列表
        schema: 提取 schema
        max_concurrent: 最大并发数
        timeout: 超时时间

    Returns:
        List[Dict]: 研究结果列表
    """
    runtime = AsyncResearchRuntime(
        config=AsyncResearchConfig(max_concurrent=max_concurrent)
    )

    jobs = [
        ResearchJob(
            seed_urls=[url],
            extract_schema=schema or {},
        )
        for url in urls
    ]

    results = await runtime.run_multiple(jobs)

    return [
        {
            "seed": r.seed,
            "extract": r.extract,
            "duration_ms": r.duration_ms,
            "error": r.error,
        }
        for r in results
    ]


async def research_stream(
    urls: List[str],
    schema: Optional[Dict[str, Any]] = None,
    max_concurrent: int = 5,
) -> AsyncIterator[Dict[str, Any]]:
    """流式研究 URLs（适合 notebook 实时展示）

    Args:
        urls: URL 列表
        schema: 提取 schema
        max_concurrent: 最大并发数

    Yields:
        Dict: 研究结果
    """
    runtime = AsyncResearchRuntime(
        config=AsyncResearchConfig(max_concurrent=max_concurrent)
    )

    jobs = [
        ResearchJob(
            seed_urls=[url],
            extract_schema=schema or {},
        )
        for url in urls
    ]

    async for result in runtime.run_stream(jobs):
        yield {
            "seed": result.seed,
            "extract": result.extract,
            "duration_ms": result.duration_ms,
            "error": result.error,
        }
