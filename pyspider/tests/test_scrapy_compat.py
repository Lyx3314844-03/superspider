from pathlib import Path

from pyspider.core.models import Page, Request, Response
from pyspider.spider.spider import (
    CrawlerProcess,
    FeedExporter,
    Item,
    ItemPipeline,
    Spider,
)


def test_html_parser_xpath_supports_simple_queries():
    from pyspider.parser.parser import HTMLParser

    parser = HTMLParser(
        "<html><body><h1>Demo</h1><a href='/next'>Next</a></body></html>"
    )

    assert parser.xpath_first("//h1/text()") == "Demo"
    assert parser.xpath("//a/@href") == ["/next"]


def test_crawler_process_collects_items_and_follow_requests():
    class DemoSpider(Spider):
        name = "demo"
        start_urls = ["https://example.com"]

        def parse(self, page: Page):
            yield Item(title=page.response.selector.title())
            yield page.follow("/next", self.parse_next)

        def parse_next(self, page: Page):
            return Item(url=page.response.url, title=page.response.selector.title())

    responses = {
        "https://example.com": Response(
            url="https://example.com",
            status_code=200,
            headers={},
            content=b"<html><title>Home</title></html>",
            text="<html><title>Home</title></html>",
            request=Request(url="https://example.com"),
        ),
        "https://example.com/next": Response(
            url="https://example.com/next",
            status_code=200,
            headers={},
            content=b"<html><title>Next</title></html>",
            text="<html><title>Next</title></html>",
            request=Request(url="https://example.com/next"),
        ),
    }

    process = CrawlerProcess(DemoSpider())
    process.downloader.download = lambda request: responses[request.url]

    items = process.start()

    assert [item["title"] for item in items] == ["Home", "Next"]
    assert items[1]["url"] == "https://example.com/next"


def test_feed_exporter_and_pipeline_roundtrip(tmp_path: Path):
    class UpperPipeline(ItemPipeline):
        def process_item(self, item: Item, spider: Spider):
            item["title"] = item["title"].upper()
            return item

    class DemoSpider(Spider):
        name = "demo"
        start_urls = ["https://example.com"]

        def parse(self, page: Page):
            return Item(title="demo", url=page.response.url)

    process = CrawlerProcess(DemoSpider(), pipelines=[UpperPipeline()])
    process.downloader.download = lambda request: Response(
        url=request.url,
        status_code=200,
        headers={},
        content=b"",
        text="<html><title>ignored</title></html>",
        request=request,
    )

    items = process.start()
    exporter = FeedExporter.json(tmp_path / "items.json")
    exporter.export_items(items)
    output = exporter.close()

    assert items[0]["title"] == "DEMO"
    assert output.exists()
    assert "DEMO" in output.read_text(encoding="utf-8")


def test_crawler_process_closes_custom_downloader():
    class DemoSpider(Spider):
        name = "demo"
        start_urls = ["https://example.com"]

        def parse(self, page: Page):
            return Item(title=page.response.selector.title())

    class ClosingDownloader:
        def __init__(self):
            self.closed = False

        def download(self, request):
            return Response(
                url=request.url,
                status_code=200,
                headers={"content-type": "text/html"},
                content=b"<html><title>close</title></html>",
                text="<html><title>close</title></html>",
                request=request,
            )

        def close(self):
            self.closed = True

    downloader = ClosingDownloader()
    process = CrawlerProcess(DemoSpider(), downloader=downloader)
    items = process.start()

    assert items[0]["title"] == "close"
    assert downloader.closed is True
