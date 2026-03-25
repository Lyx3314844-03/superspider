from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pyspider.core.models import Request
from pyspider.downloader.downloader import HTTPDownloader


class _FakeSuccessResponse:
    status_code = 200
    headers = {"Content-Type": "text/plain"}
    content = b"ok"
    text = "ok"


def test_http_downloader_maps_success_response():
    downloader = HTTPDownloader(timeout=5)
    request = Request(url="https://example.com", method="POST", body="payload")

    calls = {}

    def fake_request(**kwargs):
        calls.update(kwargs)
        return _FakeSuccessResponse()

    downloader.session.request = fake_request

    response = downloader.download(request)

    assert response.status_code == 200
    assert response.text == "ok"
    assert response.error is None
    assert calls["method"] == "POST"
    assert calls["url"] == "https://example.com"
    assert calls["data"] == "payload"
    assert calls["timeout"] == 5


def test_http_downloader_wraps_request_errors():
    downloader = HTTPDownloader(timeout=1)
    request = Request(url="https://example.com")

    def fake_request(**kwargs):
        raise TimeoutError("boom")

    downloader.session.request = fake_request

    response = downloader.download(request)

    assert response.status_code == 0
    assert response.text == ""
    assert isinstance(response.error, TimeoutError)
