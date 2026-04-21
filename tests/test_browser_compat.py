import json
from contextlib import redirect_stdout
from io import StringIO


def test_pyspider_browser_compatibility_matrix_reports_native_surfaces():
    from pyspider.browser.compat import browser_compatibility_matrix

    payload = browser_compatibility_matrix()

    assert payload["base_engine"] == "playwright-and-selenium"
    assert payload["surfaces"]["playwright"]["adapter_engine"] == "playwright"
    assert payload["surfaces"]["selenium"]["adapter_engine"] == "selenium-webdriver"


def test_pyspider_capabilities_include_browser_compatibility_matrix():
    from pyspider import __main__ as runtime_cli

    buffer = StringIO()
    with redirect_stdout(buffer):
        exit_code = runtime_cli.main(["capabilities"])

    payload = json.loads(buffer.getvalue())
    assert exit_code == 0
    assert "browser_compatibility" in payload
    assert payload["browser_compatibility"]["surfaces"]["playwright"]["supported"] is True


def test_pyspider_capabilities_report_webdriver_bridge_engine():
    from pyspider import __main__ as runtime_cli

    buffer = StringIO()
    with redirect_stdout(buffer):
        runtime_cli.main(["capabilities"])

    payload = json.loads(buffer.getvalue())
    webdriver_surface = payload["browser_compatibility"]["surfaces"]["webdriver"]
    assert webdriver_surface["mode"] == "compatibility-bridge"
    assert webdriver_surface["adapter_engine"] == "selenium-webdriver"
