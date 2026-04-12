"""测试异步 runtime 和 notebook 输出模块"""

import asyncio
import unittest
from pyspider.research.job import ResearchJob
from pyspider.runtime.async_runtime import AsyncResearchRuntime, AsyncResearchConfig
from pyspider.runtime.notebook_output import ExperimentTracker


class TestAsyncRuntime(unittest.TestCase):
    """测试异步运行时"""

    def test_async_research_runtime_instantiation(self):
        """测试异步运行时实例化"""
        runtime = AsyncResearchRuntime()
        self.assertIsNotNone(runtime)
        self.assertEqual(runtime.config.max_concurrent, 5)

    def test_async_research_runtime_custom_config(self):
        """测试自定义配置"""
        config = AsyncResearchConfig(max_concurrent=3, timeout_seconds=10.0)
        runtime = AsyncResearchRuntime(config=config)
        self.assertEqual(runtime.config.max_concurrent, 3)
        self.assertEqual(runtime.config.timeout_seconds, 10.0)

    def test_run_single_with_inline_content(self):
        """测试执行单个任务"""

        async def _test():
            runtime = AsyncResearchRuntime()
            job = ResearchJob(
                seed_urls=["https://example.com"],
                extract_schema={
                    "type": "object",
                    "properties": {"title": {"type": "string"}},
                },
            )
            content = "<title>Test Page</title>"

            result = await runtime.run_single(job, content)

            self.assertEqual(result.seed, "https://example.com")
            self.assertIsNotNone(result.profile)
            self.assertIsNotNone(result.extract)
            self.assertIsNone(result.error)
            self.assertGreater(result.duration_ms, 0)

        asyncio.run(_test())

    def test_run_multiple_concurrent(self):
        """测试并发执行多个任务"""

        async def _test():
            runtime = AsyncResearchRuntime(config=AsyncResearchConfig(max_concurrent=3))

            jobs = [
                ResearchJob(
                    seed_urls=[f"https://example{i}.com"],
                    extract_schema={},
                )
                for i in range(3)
            ]
            contents = [f"<title>Page {i}</title>" for i in range(3)]

            results = await runtime.run_multiple(jobs, contents)

            self.assertEqual(len(results), 3)
            for result in results:
                self.assertIsNone(result.error)
                self.assertGreater(result.duration_ms, 0)

        asyncio.run(_test())

    def test_run_stream(self):
        """测试流式执行"""

        async def _test():
            runtime = AsyncResearchRuntime(config=AsyncResearchConfig(max_concurrent=2))

            jobs = [
                ResearchJob(
                    seed_urls=[f"https://example{i}.com"],
                    extract_schema={},
                )
                for i in range(3)
            ]
            contents = [f"<title>Page {i}</title>" for i in range(3)]

            results = []
            async for result in runtime.run_stream(jobs, contents):
                results.append(result)

            self.assertEqual(len(results), 3)

        asyncio.run(_test())

    def test_runtime_metrics_bound_peak_concurrency(self):
        """测试并发峰值被 semaphore 正确限制"""

        async def _test():
            runtime = AsyncResearchRuntime(config=AsyncResearchConfig(max_concurrent=3))

            jobs = [
                ResearchJob(
                    seed_urls=[f"https://concurrency{i}.example"],
                    extract_schema={},
                    policy={"simulate_delay_ms": 20},
                )
                for i in range(8)
            ]
            contents = [f"<title>Concurrent {i}</title>" for i in range(8)]

            results = await runtime.run_multiple(jobs, contents)
            metrics = runtime.snapshot_metrics()

            self.assertEqual(len(results), 8)
            self.assertEqual(metrics["tasks_completed"], 8)
            self.assertEqual(metrics["tasks_failed"], 0)
            self.assertLessEqual(metrics["peak_inflight"], 3)
            self.assertGreaterEqual(metrics["peak_inflight"], 2)

        asyncio.run(_test())

    def test_run_soak_reports_stable_high_concurrency(self):
        """测试 synthetic soak 报告"""

        async def _test():
            runtime = AsyncResearchRuntime(config=AsyncResearchConfig(max_concurrent=2))

            jobs = [
                ResearchJob(
                    seed_urls=[f"https://soak{i}.example"],
                    extract_schema={},
                    policy={"simulate_delay_ms": 10},
                )
                for i in range(6)
            ]
            contents = [f"<title>Soak {i}</title>" for i in range(6)]

            report = await runtime.run_soak(jobs, contents, rounds=3)

            self.assertTrue(report["stable"])
            self.assertEqual(report["results"], 18)
            self.assertEqual(report["failures"], 0)
            self.assertEqual(report["success_rate"], 1.0)
            self.assertLessEqual(report["peak_inflight"], 2)

        asyncio.run(_test())

    def test_error_handling(self):
        """测试错误处理"""

        async def _test():
            runtime = AsyncResearchRuntime()
            job = ResearchJob(
                seed_urls=["https://example.com"],
                extract_schema={},
            )

            # 不提供内容，应该使用默认内容
            result = await runtime.run_single(job)

            self.assertEqual(result.seed, "https://example.com")
            self.assertIsNotNone(result.extract)

        asyncio.run(_test())


class TestNotebookOutput(unittest.TestCase):
    """测试 notebook 输出"""

    def test_experiment_tracker(self):
        """测试实验跟踪器"""
        tracker = ExperimentTracker()
        self.assertEqual(len(tracker.experiments), 0)

    def test_record_experiment(self):
        """测试记录实验"""
        tracker = ExperimentTracker()

        results = [
            {
                "seed": "https://example.com",
                "extract": {"title": "Test"},
                "duration_ms": 100,
            },
            {
                "seed": "https://example2.com",
                "extract": {"title": "Test2"},
                "duration_ms": 150,
            },
        ]

        record = tracker.record(
            name="test-experiment",
            urls=["https://example.com", "https://example2.com"],
            results=results,
            schema={"type": "object"},
        )

        self.assertEqual(record.name, "test-experiment")
        self.assertEqual(record.id, "exp-001")
        self.assertEqual(len(record.urls), 2)
        self.assertEqual(len(record.results), 2)
        self.assertEqual(len(tracker.experiments), 1)

    def test_compare_experiments(self):
        """测试实验对比"""
        tracker = ExperimentTracker()

        # 添加两个实验
        tracker.record(
            name="exp-1",
            urls=["https://example.com"],
            results=[
                {"seed": "https://example.com", "extract": {}, "duration_ms": 100}
            ],
        )
        tracker.record(
            name="exp-2",
            urls=["https://example.com", "https://example2.com"],
            results=[
                {"seed": "https://example.com", "extract": {}, "duration_ms": 100},
                {
                    "seed": "https://example2.com",
                    "extract": {},
                    "duration_ms": 150,
                    "error": "timeout",
                },
            ],
        )

        comparison = tracker.compare()

        self.assertEqual(comparison["summary"]["total_experiments"], 2)
        self.assertEqual(comparison["summary"]["total_urls"], 3)
        self.assertEqual(len(comparison["experiments"]), 2)

    def test_to_dataframe(self):
        """测试转换为 DataFrame"""
        try:
            import pandas as pd
        except ImportError:
            self.skipTest("pandas not available")

        tracker = ExperimentTracker()
        tracker.record(
            name="test",
            urls=["https://example.com"],
            results=[
                {
                    "seed": "https://example.com",
                    "extract": {"title": "Test"},
                    "duration_ms": 100,
                }
            ],
        )

        df = tracker.to_dataframe()

        self.assertEqual(len(df), 1)
        self.assertIn("experiment_name", df.columns)
        self.assertIn("seed", df.columns)
        self.assertIn("extract", df.columns)


if __name__ == "__main__":
    unittest.main()
