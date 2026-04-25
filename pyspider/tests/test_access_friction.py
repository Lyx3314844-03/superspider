import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pyspider.antibot.friction import analyze_access_friction


def test_access_friction_classifies_rate_limit_retry_after():
    report = analyze_access_friction(
        status_code=429,
        headers={"Retry-After": "12"},
        html="<html>Too many requests</html>",
    )

    assert report.level == "high"
    assert report.retry_after_seconds == 12
    assert "rate-limited" in report.signals
    assert "honor-retry-after" in report.recommended_actions
    assert report.capability_plan["throttle"]["crawl_delay_seconds"] == 30
    assert report.capability_plan["retry_budget"] == 1
    assert report.blocked is True


def test_access_friction_recommends_browser_and_human_checkpoint_for_captcha():
    report = analyze_access_friction(
        status_code=200,
        html="<html><title>Security</title><div>hcaptcha 安全验证</div></html>",
        url="https://shop.example/challenge",
    )

    assert report.level == "high"
    assert report.should_upgrade_to_browser is True
    assert report.requires_human_access is True
    assert report.challenge_handoff["required"] is True
    assert report.challenge_handoff["method"] == "human-authorized-browser-session"
    assert "browser-render" in report.capability_plan["transport_order"]
    assert report.capability_plan["session"]["reuse_only_after_authorized_access"] is True
    assert "pause-for-human-access" in report.recommended_actions


def test_access_friction_routes_signature_and_fingerprint_pages_to_devtools_node_reverse():
    report = analyze_access_friction(
        status_code=200,
        html="""
        <script>
          window._signature = 'x';
          const token = CryptoJS.MD5(navigator.webdriver + 'x-bogus').toString();
        </script>
        """,
        url="https://example.com/api/list?X-Bogus=abc",
    )

    assert report.level == "medium"
    assert report.should_upgrade_to_browser is True
    assert "js-signature" in report.signals
    assert "fingerprint-required" in report.signals
    assert "capture-devtools-network" in report.recommended_actions
    assert "run-nodejs-reverse-analysis" in report.recommended_actions
    assert "devtools-analysis" in report.capability_plan["transport_order"]
    assert "node-reverse-analysis" in report.capability_plan["transport_order"]
