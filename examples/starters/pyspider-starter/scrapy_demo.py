from pyspider.spider.spider import CrawlerProcess, FeedExporter, Item, Spider


class StarterSpider(Spider):
    name = "starter"
    start_urls = ["https://example.com"]

    def parse(self, page):
        yield Item(
            title=page.response.selector.title(),
            url=page.response.url,
            framework="pyspider",
        )


if __name__ == "__main__":
    items = CrawlerProcess(StarterSpider()).start()
    exporter = FeedExporter.json("artifacts/exports/pyspider-starter-items.json")
    exporter.export_items(items)
    output = exporter.close()
    print(f"exported {len(items)} items to {output}")
