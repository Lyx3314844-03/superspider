from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pyspider.captcha.solver import CaptchaSolver


class _TextResponse:
    def __init__(self, text: str):
        self.text = text


class _JsonResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def test_solve_recaptcha_uses_2captcha_protocol(monkeypatch):
    solver = CaptchaSolver("demo-key", service="2captcha")
    calls = {"post": [], "get": []}

    def fake_post(url, data=None, timeout=None, **kwargs):
        calls["post"].append((url, data))
        return _TextResponse("OK|task-123")

    def fake_get(url, params=None, timeout=None, **kwargs):
        calls["get"].append((url, params))
        return _TextResponse("OK|recaptcha-token")

    monkeypatch.setattr(solver.session, "post", fake_post)
    monkeypatch.setattr(solver.session, "get", fake_get)
    monkeypatch.setattr("pyspider.captcha.solver.time.sleep", lambda _seconds: None)

    result = solver.solve_recaptcha("site-key", "https://example.com/recaptcha")

    assert result.success is True
    assert result.text == "recaptcha-token"
    assert calls["post"][0][1]["method"] == "userrecaptcha"
    assert calls["post"][0][1]["googlekey"] == "site-key"
    assert calls["post"][0][1]["pageurl"] == "https://example.com/recaptcha"


def test_solve_hcaptcha_uses_anticaptcha_protocol(monkeypatch):
    solver = CaptchaSolver("demo-key", service="anticaptcha")
    responses = iter(
        [
            _JsonResponse({"errorId": 0, "taskId": 77}),
            _JsonResponse({"errorId": 0, "status": "processing"}),
            _JsonResponse(
                {
                    "errorId": 0,
                    "status": "ready",
                    "solution": {"gRecaptchaResponse": "hcaptcha-token"},
                }
            ),
        ]
    )
    post_calls = []

    def fake_post(url, json=None, timeout=None, **kwargs):
        post_calls.append((url, json))
        return next(responses)

    monkeypatch.setattr(solver.session, "post", fake_post)
    monkeypatch.setattr("pyspider.captcha.solver.time.sleep", lambda _seconds: None)

    result = solver.solve_hcaptcha("site-key", "https://example.com/hcaptcha")

    assert result.success is True
    assert result.text == "hcaptcha-token"
    assert post_calls[0][1]["task"]["type"] == "HCaptchaTaskProxyless"
    assert post_calls[0][1]["task"]["websiteURL"] == "https://example.com/hcaptcha"
    assert post_calls[0][1]["task"]["websiteKey"] == "site-key"


def test_solve_turnstile_uses_anticaptcha_protocol(monkeypatch):
    solver = CaptchaSolver("demo-key", service="anticaptcha")
    responses = iter(
        [
            _JsonResponse({"errorId": 0, "taskId": 88}),
            _JsonResponse({"errorId": 0, "status": "processing"}),
            _JsonResponse(
                {
                    "errorId": 0,
                    "status": "ready",
                    "solution": {"token": "turnstile-token"},
                }
            ),
        ]
    )
    post_calls = []

    def fake_post(url, json=None, timeout=None, **kwargs):
        post_calls.append((url, json))
        return next(responses)

    monkeypatch.setattr(solver.session, "post", fake_post)
    monkeypatch.setattr("pyspider.captcha.solver.time.sleep", lambda _seconds: None)

    result = solver.solve_turnstile(
        "site-key",
        "https://example.com/turnstile",
        action="login",
        c_data="demo-cdata",
        page_data="demo-page",
    )

    assert result.success is True
    assert result.text == "turnstile-token"
    assert post_calls[0][1]["task"]["type"] == "TurnstileTaskProxyless"
    assert post_calls[0][1]["task"]["action"] == "login"
    assert post_calls[0][1]["task"]["cData"] == "demo-cdata"
    assert post_calls[0][1]["task"]["chlPageData"] == "demo-page"


def test_solve_image_uses_capmonster_protocol(monkeypatch):
    solver = CaptchaSolver("", service="capmonster")
    responses = iter(
        [
            _JsonResponse({"errorId": 0, "taskId": 99}),
            _JsonResponse({"status": "ready", "solution": {"text": "capmonster-text"}}),
        ]
    )
    post_calls = []

    def fake_post(url, json=None, timeout=None, **kwargs):
        post_calls.append((url, json))
        return next(responses)

    monkeypatch.setattr(solver.session, "post", fake_post)
    monkeypatch.setattr("pyspider.captcha.solver.time.sleep", lambda _seconds: None)

    result = solver.solve_image(b"image-bytes")

    assert result.success is True
    assert result.text == "capmonster-text"
    assert post_calls[0][0] == "http://localhost:24999/createTask"
    assert post_calls[0][1]["task"]["type"] == "ImageToTextTask"
