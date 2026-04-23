# scrapy: url=https://example.com/app/page
from pyspider.spider.spider import Item, Spider


class ApiBootstrapSpider(Spider):
    name = "api_bootstrap"
    start_urls = ["https://example.com/app/page"]

    def parse(self, page):
        yield Item(
            kind="api_bootstrap",
            title=page.response.selector.title(),
            url=page.response.url,
            bootstrap_excerpt=page.response.text[:800],
        )

