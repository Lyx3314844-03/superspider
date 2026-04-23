# scrapy: url=https://example.com/item/123
from pyspider.spider.spider import Item, Spider


class ProductDetailSpider(Spider):
    name = "product_detail"
    start_urls = ["https://example.com/item/123"]

    def parse(self, page):
        yield Item(
            kind="detail",
            title=page.response.selector.title(),
            url=page.response.url,
            source_html=page.response.text[:500],
        )

