from pyspider.advanced.ultimate import UltimateConfig, UltimateSpider


class _FakeCookie:
    def __init__(self, name: str, value: str):
        self.name = name
        self.value = value


class _FakeResponse:
    def __init__(self):
        self.text = "<html><title>Ultimate Reverse</title></html>"
        self.headers = {"Content-Type": "text/html"}
        self.status_code = 403
        self.cookies = [_FakeCookie("__cf_bm", "token")]


def test_collect_reverse_runtime_aggregates_reverse_capabilities(monkeypatch):
    spider = UltimateSpider(UltimateConfig(reverse_service_url="http://127.0.0.1:3000"))

    monkeypatch.setattr(
        "pyspider.advanced.ultimate.requests.get",
        lambda *args, **kwargs: _FakeResponse(),
    )
    monkeypatch.setattr(
        spider.reverse_client,
        "detect_anti_bot",
        lambda **kwargs: {
            "success": True,
            "signals": ["vendor:cloudflare"],
            "level": "high",
        },
    )
    monkeypatch.setattr(
        spider.reverse_client,
        "profile_anti_bot",
        lambda **kwargs: {
            "success": True,
            "signals": ["vendor:cloudflare"],
            "level": "high",
        },
    )
    monkeypatch.setattr(
        spider.reverse_client,
        "spoof_fingerprint",
        lambda browser, platform: {
            "success": True,
            "browser": browser,
            "platform": platform,
        },
    )
    monkeypatch.setattr(
        spider.reverse_client,
        "generate_tls_fingerprint",
        lambda browser, version: {
            "success": True,
            "browser": browser,
            "version": version,
            "fingerprint": {"ja3": "mock-ja3"},
        },
    )

    payload = spider.collect_reverse_runtime("https://example.com")

    assert payload["success"] is True
    assert payload["detect"]["signals"] == ["vendor:cloudflare"]
    assert payload["profile"]["level"] == "high"
    assert payload["fingerprint_spoof"]["platform"] == "windows"
    assert payload["tls_fingerprint"]["fingerprint"]["ja3"] == "mock-ja3"
