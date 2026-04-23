# scrapy: url=https://example.com/feed
from pyspider.spider.spider import Item, Request, Spider


class SocialFeedSpider(Spider):
    name = "social_feed"
    start_urls = ["https://example.com/feed"]

    def start_requests(self):
        for url in self.start_urls:
            yield Request(
                url=url,
                callback=self.parse,
                meta={
                    "runner": "browser",
                    "browser": {
                        "session": "social-feed",
                        "wait_until": "networkidle",
                        "html_path": "artifacts/browser/social-feed.html",
                    },
                },
            )

    def parse(self, page):
        yield Item(kind="social_feed", title=page.response.selector.title(), url=page.response.url)

