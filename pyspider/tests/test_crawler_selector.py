import json
from pathlib import Path

from pyspider.profiler import CrawlerSelectionRequest, CrawlerSelector


def test_selector_recommends_browser_for_ecommerce_listing():
    selector = CrawlerSelector()

    selection = selector.select(
        CrawlerSelectionRequest(
            url="https://shop.example.com/search?q=phone",
            content="""
            <html><script>window.__NEXT_DATA__ = {"items": []}</script>
            <body><input type="search"><div class="product-list">
            <div class="sku-item">SKU-1</div><span class="price">￥10</span>
            <button>加入购物车</button></div></body></html>
            """,
        )
    )

    assert selection.scenario == "ecommerce_listing"
    assert selection.crawler_type == "ecommerce_search"
    assert selection.recommended_runner == "browser"
    assert "commerce_fields" in selection.capabilities
    assert "signal:has_price" in selection.reason_codes
    assert selection.confidence >= 0.7
    payload = selection.to_dict()
    assert payload["recommended_runner"] == "browser"
    assert payload["profile"]["crawler_type"] == "ecommerce_search"


def test_selector_returns_stop_conditions_for_login_risk():
    selector = CrawlerSelector()

    selection = selector.select(
        "https://secure.example.com/login",
        '<form><input type="password"><div>验证码</div></form>',
    )

    assert selection.scenario == "authenticated_session"
    assert selection.risk_level == "high"
    assert "session_cookies" in selection.capabilities
    assert "anti_bot_evidence" in selection.capabilities
    assert any("captcha" in item.lower() for item in selection.fallback_plan)


def test_selector_matches_shared_ecommerce_golden_contract():
    root = Path(__file__).resolve().parents[2]
    html = (root / "examples/crawler-selection/ecommerce-search-input.html").read_text(encoding="utf-8")
    golden = json.loads(
        (root / "examples/crawler-selection/ecommerce-search-selection.json").read_text(encoding="utf-8")
    )

    selection = CrawlerSelector().select("https://shop.example.com/search?q=phone", html).to_dict()

    for field in (
        "scenario",
        "crawler_type",
        "recommended_runner",
        "runner_order",
        "site_family",
        "risk_level",
        "confidence",
    ):
        assert selection[field] == golden[field]
    for capability in golden["capabilities"]:
        assert capability in selection["capabilities"]
