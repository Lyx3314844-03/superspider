from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pyspider.core.models import Request, Response
from pyspider.core.spider import Spider


def test_spider_start_processes_multiple_same_priority_urls():
    spider = Spider("queue-order")
    spider.set_start_urls("https://example.com/1", "https://example.com/2")
    spider.set_thread_count(1)

    processed = []

    def fake_download(req):
        return Response(
            url=req.url,
            status_code=200,
            headers={},
            content=b"",
            text=req.url,
            request=req,
            duration=0.01,
            error=None,
        )

    spider.downloader.download = fake_download
    spider.add_pipeline(lambda page: processed.append(page.response.url))

    spider.start()

    assert processed == [
        "https://example.com/1",
        "https://example.com/2",
    ]


def test_spider_add_request_deduplicates_urls():
    spider = Spider("dedupe")

    spider.add_request(Request(url="https://example.com"))
    spider.add_request(Request(url="https://example.com"))

    assert spider.request_queue.qsize() == 1


def test_spider_does_not_process_blocked_access_friction():
    spider = Spider("blocked-friction", max_retries=0)
    processed = []

    def fake_download(req):
        return Response(
            url=req.url,
            status_code=200,
            headers={"Content-Type": "text/html"},
            content=b"<html>hcaptcha</html>",
            text="<html>hcaptcha</html>",
            request=req,
            duration=0.01,
            error=None,
            meta={
                "access_friction": {
                    "level": "high",
                    "signals": ["captcha"],
                    "blocked": True,
                    "requires_human_access": True,
                }
            },
        )

    spider.downloader.download = fake_download
    spider.add_pipeline(lambda page: processed.append(page.response.url))

    result = spider._process_request(Request(url="https://example.com/challenge"))

    assert result is False
    assert processed == []
    assert spider.stats.failed_requests == 1
