import tempfile
import unittest
import importlib.util
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

    def test_site_profiler_detects_ecommerce_search_crawler_type(self):
        profiler = SiteProfiler()
        profile = profiler.profile(
            "https://shop.example.com/search?q=iphone",
            """
            <html>
              <head>
                <title>iPhone 搜索结果</title>
                <script>window.__NEXT_DATA__ = {"items":[{"sku":"SKU123","price":"6999"}]}</script>
              </head>
              <body>
                <div class="product-list">
                  <h1>搜索结果</h1>
                  <div class="sku-item">SKU123</div>
                  <div class="price">￥6999</div>
                  <button>加入购物车</button>
                </div>
              </body>
            </html>
            """,
        )
        self.assertEqual(profile.page_type, "list")
        self.assertEqual(profile.crawler_type, "ecommerce_search")
        self.assertEqual(profile.runner_order[0], "browser")
        self.assertIn("sku", profile.candidate_fields)
        self.assertIn(
            "examples/crawler-types/ecommerce-search-browser.json",
            profile.job_templates,
        )

    def test_site_profiler_detects_jd_site_family(self):
        profiler = SiteProfiler()
        profile = profiler.profile(
            "https://search.jd.com/Search?keyword=iphone",
            "<html><title>京东搜索</title><div class='sku-item'>sku</div><div class='price'>￥6999</div></html>",
        )
        self.assertEqual(profile.site_family, "jd")
        self.assertIn("examples/site-presets/jd-search-browser.json", profile.job_templates)

    def test_site_profiler_prefers_jd_detail_preset_for_detail_pages(self):
        profiler = SiteProfiler()
        profile = profiler.profile(
            "https://item.jd.com/100000000000.html",
            "<html><title>京东商品</title><h1>iPhone</h1><div>sku</div><div class='price'>￥6999</div><button>加入购物车</button></html>",
        )
        self.assertEqual(profile.site_family, "jd")
        self.assertEqual(profile.crawler_type, "ecommerce_detail")
        self.assertIn("examples/site-presets/jd-detail-browser.json", profile.job_templates)

    def test_shared_crawler_type_templates_exist(self):
        root = Path(__file__).resolve().parents[2]
        templates_dir = root / "examples" / "crawler-types"
        expected = {
            "README.md",
            "api-bootstrap-http.json",
            "hydrated-spa-browser.json",
            "infinite-scroll-browser.json",
            "ecommerce-search-browser.json",
            "login-session-browser.json",
        }
        self.assertTrue(templates_dir.exists())
        self.assertTrue(expected.issubset({path.name for path in templates_dir.iterdir()}))

    def test_site_preset_templates_exist(self):
        root = Path(__file__).resolve().parents[2]
        templates_dir = root / "examples" / "site-presets"
        expected = {
            "README.md",
            "jd-search-browser.json",
            "jd-detail-browser.json",
            "taobao-search-browser.json",
            "taobao-detail-browser.json",
        }
        self.assertTrue(templates_dir.exists())
        self.assertTrue(expected.issubset({path.name for path in templates_dir.iterdir()}))

    def test_spider_class_kits_exist(self):
        root = Path(__file__).resolve().parents[2]
        kit_root = root / "examples" / "class-kits"
        expected = {
            "README.md",
            "catalog.json",
        }
        self.assertTrue(kit_root.exists())
        self.assertTrue(expected.issubset({path.name for path in kit_root.iterdir()}))
        self.assertTrue((kit_root / "pyspider" / "search_listing_spider.py").exists())
        self.assertTrue((kit_root / "gospider" / "search_listing.go").exists())
        self.assertTrue((kit_root / "rustspider" / "search_listing.rs").exists())
        self.assertTrue((kit_root / "javaspider" / "SearchListingSpiderFactory.java").exists())

    def test_ecommerce_class_kits_exist_for_all_runtimes(self):
        root = Path(__file__).resolve().parents[2]
        kit_root = root / "examples" / "class-kits"
        catalog = (kit_root / "catalog.json").read_text(encoding="utf-8")

        self.assertIn("EcommerceCatalogSpider", catalog)
        self.assertIn("EcommerceDetailSpider", catalog)
        self.assertIn("EcommerceReviewSpider", catalog)

        self.assertTrue((kit_root / "pyspider" / "ecommerce_site_profile.py").exists())
        self.assertTrue((kit_root / "pyspider" / "ecommerce_catalog_spider.py").exists())
        self.assertTrue((kit_root / "pyspider" / "ecommerce_detail_spider.py").exists())
        self.assertTrue((kit_root / "pyspider" / "ecommerce_review_spider.py").exists())

        self.assertTrue((kit_root / "gospider" / "ecommerce_profile.go").exists())
        self.assertTrue((kit_root / "gospider" / "ecommerce_catalog.go").exists())
        self.assertTrue((kit_root / "gospider" / "ecommerce_detail.go").exists())
        self.assertTrue((kit_root / "gospider" / "ecommerce_review.go").exists())

        self.assertTrue((kit_root / "rustspider" / "ecommerce_profile.rs").exists())
        self.assertTrue((kit_root / "rustspider" / "ecommerce_catalog.rs").exists())
        self.assertTrue((kit_root / "rustspider" / "ecommerce_detail.rs").exists())
        self.assertTrue((kit_root / "rustspider" / "ecommerce_review.rs").exists())

        self.assertTrue((kit_root / "javaspider" / "EcommerceSiteProfiles.java").exists())
        self.assertTrue((kit_root / "javaspider" / "EcommerceCatalogSpiderFactory.java").exists())
        self.assertTrue((kit_root / "javaspider" / "EcommerceDetailSpiderFactory.java").exists())
        self.assertTrue((kit_root / "javaspider" / "EcommerceReviewSpiderFactory.java").exists())

    def test_native_runtime_ecommerce_examples_exist(self):
        root = Path(__file__).resolve().parents[2]

        self.assertTrue((root / "pyspider" / "examples" / "ecommerce_site_profile.py").exists())
        self.assertTrue((root / "pyspider" / "examples" / "ecommerce_catalog_spider.py").exists())
        self.assertTrue((root / "pyspider" / "examples" / "ecommerce_detail_spider.py").exists())
        self.assertTrue((root / "pyspider" / "examples" / "ecommerce_review_spider.py").exists())

        self.assertTrue((root / "gospider" / "examples" / "ecommerce" / "main.go").exists())
        self.assertTrue((root / "gospider" / "examples" / "ecommerce" / "profile.go").exists())
        self.assertTrue((root / "gospider" / "examples" / "ecommerce" / "catalog.go").exists())
        self.assertTrue((root / "gospider" / "examples" / "ecommerce" / "detail.go").exists())
        self.assertTrue((root / "gospider" / "examples" / "ecommerce" / "review.go").exists())

        self.assertTrue((root / "rustspider" / "examples" / "ecommerce" / "main.rs").exists())
        self.assertTrue((root / "rustspider" / "examples" / "ecommerce" / "profile.rs").exists())

        java_root = root / "javaspider" / "src" / "main" / "java" / "com" / "javaspider" / "examples" / "ecommerce"
        self.assertTrue((java_root / "EcommerceSiteProfiles.java").exists())
        self.assertTrue((java_root / "EcommerceCatalogSpider.java").exists())
        self.assertTrue((java_root / "EcommerceDetailSpider.java").exists())
        self.assertTrue((java_root / "EcommerceReviewSpider.java").exists())
        self.assertTrue((java_root / "EcommerceExampleRunner.java").exists())

    def test_pyspider_ecommerce_helper_extracts_json_and_api_candidates(self):
        root = Path(__file__).resolve().parents[2]
        module_path = root / "pyspider" / "examples" / "ecommerce_site_profile.py"
        spec = importlib.util.spec_from_file_location("ecommerce_site_profile", module_path)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)

        html = """
        <html>
          <head>
            <script type="application/ld+json">
            {"@context":"https://schema.org","@type":"Product","name":"Demo Phone","sku":"SKU-1","url":"https://shop.example.com/item/sku-1","image":["https://cdn.example.com/p1.jpg"],"offers":{"price":"6999","priceCurrency":"CNY"}}
            </script>
            <script>window.__NEXT_DATA__={"props":{"pageProps":{"api":"/api/item/detail?id=1"}}};</script>
          </head>
          <body>
            <video src="https://cdn.example.com/demo.mp4"></video>
          </body>
        </html>
        """

        products = module.extract_json_ld_products(html)
        self.assertTrue(products)
        self.assertEqual(products[0]["url"], "https://shop.example.com/item/sku-1")
        self.assertEqual(products[0]["image"], "https://cdn.example.com/p1.jpg")
        self.assertTrue(module.extract_api_candidates(html))
        self.assertTrue(module.extract_embedded_json_blocks(html))
        self.assertTrue(module.collect_video_links("https://shop.example.com", ["https://cdn.example.com/demo.mp4"]))
        self.assertEqual(module.get_profile("unknown-shop")["family"], "generic")

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
