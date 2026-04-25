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


class _FakeChallengeResponse:
    status_code = 429
    headers = {"Retry-After": "45", "CF-Ray": "demo"}
    content = b"checking your browser"
    text = "checking your browser"


class _FakeCaptchaRateLimitResponse:
    status_code = 429
    headers = {"Retry-After": "45"}
    content = b"hcaptcha security check"
    text = "hcaptcha security check"


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
    assert response.meta["access_friction"]["level"] == "none"


def test_http_downloader_attaches_access_friction_report():
    downloader = HTTPDownloader(timeout=5, max_retries=0)
    request = Request(url="https://example.com")

    downloader.session.request = lambda **kwargs: _FakeChallengeResponse()

    response = downloader.download(request)

    report = response.meta["access_friction"]
    assert report["level"] == "high"
    assert report["blocked"] is True
    assert report["retry_after_seconds"] == 45
    assert report["should_upgrade_to_browser"] is True


def test_http_downloader_does_not_retry_human_access_challenge(monkeypatch):
    downloader = HTTPDownloader(timeout=5, max_retries=3)
    request = Request(url="https://example.com")
    calls = []

    def fake_request(**kwargs):
        calls.append(kwargs)
        return _FakeCaptchaRateLimitResponse()

    monkeypatch.setattr("pyspider.downloader.downloader.time.sleep", lambda _seconds: None)
    downloader.session.request = fake_request

    response = downloader.download(request)

    assert response.status_code == 429
    assert response.meta["access_friction"]["requires_human_access"] is True
    assert len(calls) == 1


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
