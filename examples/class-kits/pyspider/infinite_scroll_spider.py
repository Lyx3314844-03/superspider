# scrapy: url=https://example.com/discover
from pyspider.spider.spider import Item, Request, Spider


class InfiniteScrollSpider(Spider):
    name = "infinite_scroll"
    start_urls = ["https://example.com/discover"]

    def start_requests(self):
        for url in self.start_urls:
            yield Request(
                url=url,
                callback=self.parse,
                meta={
                    "runner": "browser",
                    "browser": {
                        "session": "infinite-scroll",
                        "wait_until": "networkidle",
                        "html_path": "artifacts/browser/infinite-scroll.html",
                    },
                },
            )

    def parse(self, page):
        yield Item(kind="infinite_scroll", title=page.response.selector.title(), url=page.response.url)

