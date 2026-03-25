from pyspider.cli.dependencies import _browser_candidates


def test_pyspider_browser_candidates_include_linux_chrome_binary():
    assert "chrome" in tuple(_browser_candidates())
