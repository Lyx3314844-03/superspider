# scrapy: url=https://example.com/login
from pyspider.spider.spider import Item, Request, Spider


class LoginSessionSpider(Spider):
    name = "login_session"
    start_urls = ["https://example.com/login"]

    def start_requests(self):
        for url in self.start_urls:
            yield Request(
                url=url,
                callback=self.parse,
                meta={
                    "runner": "browser",
                    "browser": {
                        "session": "login-session",
                        "wait_until": "networkidle",
                        "html_path": "artifacts/browser/login-session.html",
                        "storage_state_file": "artifacts/auth/storage-state.json",
                    },
                },
            )

    def parse(self, page):
        yield Item(kind="login_session", title=page.response.selector.title(), url=page.response.url)

