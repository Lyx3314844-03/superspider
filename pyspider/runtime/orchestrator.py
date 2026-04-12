from typing import Any, Dict, Optional

from pyspider.dataset.writer import DatasetWriter
from pyspider.extract.studio import ExtractionStudio
from pyspider.profiler.site_profiler import SiteProfiler
from pyspider.research.job import ResearchJob


class ResearchRuntime:
    def __init__(self) -> None:
        self.profiler = SiteProfiler()
        self.studio = ExtractionStudio()
        self.writer = DatasetWriter()

    def run(self, job: ResearchJob, content: Optional[str] = None) -> Dict[str, Any]:
        seed = job.seed_urls[0]
        content = content or f"<title>{seed}</title>"
        profile = self.profiler.profile(seed, content)
        extracted = self.studio.run(content, job.extract_schema, job.extract_specs)

        result: Dict[str, Any] = {
            "seed": seed,
            "profile": profile,
            "extract": extracted,
        }

        output_target = job.output or {}
        if output_target.get("path"):
            dataset = self.writer.write([extracted], output_target)
            result["dataset"] = dataset

        return result
