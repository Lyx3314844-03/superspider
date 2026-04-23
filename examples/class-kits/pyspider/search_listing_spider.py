# scrapy: url=https://example.com/search?q=demo
from pyspider.spider.spider import Item, Request, Spider


class SearchListingSpider(Spider):
    name = "search_listing"
    start_urls = ["https://example.com/search?q=demo"]

    def start_requests(self):
        for url in self.start_urls:
            yield Request(
                url=url,
                callback=self.parse,
                meta={
                    "runner": "browser",
                    "browser": {
                        "session": "search-listing",
                        "wait_until": "networkidle",
                        "html_path": "artifacts/browser/search-listing.html",
                    },
                },
            )

    def parse(self, page):
        yield Item(kind="listing", title=page.response.selector.title(), url=page.response.url)

