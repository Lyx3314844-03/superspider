import tempfile
import unittest
from pathlib import Path

from pyspider.dataset.writer import DatasetWriter
from pyspider.extract.studio import ExtractionStudio
from pyspider.profiler.site_profiler import SiteProfiler
from pyspider.research.job import ResearchJob
from pyspider.runtime.orchestrator import ResearchRuntime


class SuperFrameworkTest(unittest.TestCase):
    def test_site_profiler_detects_detail_page(self):
        profiler = SiteProfiler()
        profile = profiler.profile(
            "https://example.com/article",
            "<html><title>X</title><article>author: Lan</article></html>",
        )
        self.assertEqual(profile.page_type, "detail")
        self.assertIn("title", profile.candidate_fields)

    def test_extraction_studio_extracts_schema_fields(self):
        studio = ExtractionStudio()
        result = studio.run(
            "<title>Demo</title>\nprice: 42",
            {"properties": {"title": {"type": "string"}, "price": {"type": "string"}}},
        )
        self.assertEqual(result["title"], "Demo")
        self.assertEqual(result["price"], "42")

    def test_dataset_writer_writes_jsonl(self):
        writer = DatasetWriter()
        with tempfile.TemporaryDirectory() as tmpdir:
            output = writer.write(
                [{"title": "Demo"}],
                {"format": "jsonl", "path": str(Path(tmpdir) / "rows.jsonl")},
            )
            self.assertTrue(Path(output.path).exists())

    def test_research_job_is_constructible(self):
        job = ResearchJob(seed_urls=["https://example.com"])
        self.assertEqual(job.seed_urls, ["https://example.com"])

    def test_research_runtime_runs_job(self):
        runtime = ResearchRuntime()
        job = ResearchJob(
            seed_urls=["https://example.com"],
            extract_schema={"properties": {"title": {"type": "string"}}},
        )
        result = runtime.run(job, content="<title>Runtime Demo</title>")
        self.assertEqual(result["extract"]["title"], "Runtime Demo")


if __name__ == "__main__":
    unittest.main()
