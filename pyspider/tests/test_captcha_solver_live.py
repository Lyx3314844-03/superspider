from pathlib import Path
import os
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pyspider.captcha.solver import CaptchaSolver


def _enabled() -> bool:
    value = os.getenv("PYSPIDER_LIVE_CAPTCHA_SMOKE", "")
    return value in {"1", "true", "TRUE", "True"}


def _first_non_blank(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return None


@pytest.mark.skipif(not _enabled(), reason="live captcha smoke is disabled")
def test_live_recaptcha_with_2captcha_if_configured():
    api_key = _first_non_blank("TWO_CAPTCHA_API_KEY", "CAPTCHA_API_KEY")
    site_key = os.getenv("PYSPIDER_LIVE_RECAPTCHA_SITE_KEY", "").strip()
    page_url = os.getenv("PYSPIDER_LIVE_RECAPTCHA_PAGE_URL", "").strip()
    if not api_key or not site_key or not page_url:
        pytest.skip("2captcha recaptcha live target is not configured")

    solver = CaptchaSolver(api_key, service="2captcha")
    result = solver.solve_recaptcha(site_key, page_url)

    assert result.success is True, result.error
    assert result.text


@pytest.mark.skipif(not _enabled(), reason="live captcha smoke is disabled")
def test_live_hcaptcha_with_anticaptcha_if_configured():
    api_key = _first_non_blank("ANTI_CAPTCHA_API_KEY")
    site_key = os.getenv("PYSPIDER_LIVE_HCAPTCHA_SITE_KEY", "").strip()
    page_url = os.getenv("PYSPIDER_LIVE_HCAPTCHA_PAGE_URL", "").strip()
    if not api_key or not site_key or not page_url:
        pytest.skip("anti-captcha hcaptcha live target is not configured")

    solver = CaptchaSolver(api_key, service="anticaptcha")
    result = solver.solve_hcaptcha(site_key, page_url)

    assert result.success is True, result.error
    assert result.text
