from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pyspider
from pyspider.core.spider import Spider


def test_top_level_import_exposes_core_symbols():
    assert pyspider.Spider is not None
    assert pyspider.Request is not None
    assert pyspider.HTMLParser is not None


def test_top_level_all_exports_exist():
    missing = [name for name in pyspider.__all__ if not hasattr(pyspider, name)]
    assert missing == []


def test_spider_chainable_configuration_methods():
    spider = Spider("smoke")
    pipeline = lambda page: None

    result = (
        spider.set_start_urls("https://example.com")
        .set_thread_count(2)
        .add_pipeline(pipeline)
    )

    assert result is spider
    assert spider.start_urls == ["https://example.com"]
    assert spider.thread_count == 2
    assert spider.pipelines == [pipeline]
