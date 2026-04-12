from pyspider.spider.spider import CrawlerProcess, FeedExporter, Item, Spider


class DemoSpider(Spider):
    name = "demo"
    start_urls = ["https://example.com"]

    def parse(self, page):
        yield Item(title=page.response.selector.title(), url=page.response.url)


if __name__ == "__main__":
    process = CrawlerProcess(DemoSpider())
    items = process.start()

    exporter = FeedExporter.json("artifacts/exports/pyspider-scrapy-demo.json")
    exporter.export_items(items)
    output = exporter.close()

    print(f"exported {len(items)} items to {output}")
