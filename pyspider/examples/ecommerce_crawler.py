from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pyspider.spider.spider import CrawlerProcess, FeedExporter, Spider

from ecommerce_browser_spider import EcommerceBrowserSpider
from ecommerce_catalog_spider import EcommerceCatalogSpider
from ecommerce_detail_spider import EcommerceDetailSpider
from ecommerce_review_spider import EcommerceReviewSpider
from ecommerce_site_profile import DEFAULT_SITE_FAMILY


@dataclass
class EcommerceCrawlerResult:
    mode: str
    item_count: int
    output_path: str
    payload: dict[str, Any] | None = None


class EcommerceCrawler:
    """Unified ecommerce crawler class for static and browser-backed modes."""

    def __init__(self, site_family: str = DEFAULT_SITE_FAMILY, output_dir: str = "artifacts/exports"):
        self.site_family = site_family
        self.output_dir = output_dir

    def build_spider(self, mode: str) -> tuple[Spider, str]:
        normalized = self.normalize_mode(mode)
        if normalized == "detail":
            return EcommerceDetailSpider(site_family=self.site_family), normalized
        if normalized == "review":
            return EcommerceReviewSpider(site_family=self.site_family), normalized
        return EcommerceCatalogSpider(site_family=self.site_family), "catalog"

    def run(self, mode: str = "catalog") -> EcommerceCrawlerResult:
        if mode in {"browser", "selenium", "playwright"}:
            return self.run_browser("catalog")

        spider, normalized_mode = self.build_spider(mode)
        items = CrawlerProcess(spider).start()
        output = Path(self.output_dir)
        output.mkdir(parents=True, exist_ok=True)
        output_path = str(output / f"pyspider-{self.site_family}-{normalized_mode}.json")
        exporter = FeedExporter.json(output_path)
        exporter.export_items(items)
        exported = exporter.close()
        return EcommerceCrawlerResult(mode=normalized_mode, item_count=len(items), output_path=exported)

    def run_browser(self, mode: str = "catalog", output_dir: str = "artifacts/browser") -> EcommerceCrawlerResult:
        normalized_mode = self.normalize_mode(mode)
        payload = EcommerceBrowserSpider(site_family=self.site_family, output_dir=output_dir).crawl(normalized_mode)
        json_path = payload.get("artifacts", {}).get("json", "")
        product_count = len(payload.get("json_ld_products", [])) + len(payload.get("bootstrap_products", []))
        return EcommerceCrawlerResult(
            mode=normalized_mode,
            item_count=product_count,
            output_path=json_path,
            payload=payload,
        )

    @staticmethod
    def normalize_mode(mode: str) -> str:
        return mode if mode in {"catalog", "detail", "review"} else "catalog"


if __name__ == "__main__":
    selected_mode = sys.argv[1] if len(sys.argv) > 1 else "catalog"
    selected_family = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_SITE_FAMILY
    crawler = EcommerceCrawler(site_family=selected_family)
    if selected_mode in {"browser", "selenium", "playwright"}:
        browser_mode = sys.argv[3] if len(sys.argv) > 3 else "catalog"
        result = crawler.run_browser(browser_mode)
    else:
        result = crawler.run(selected_mode)
    print(f"exported {result.item_count} items to {result.output_path}")
