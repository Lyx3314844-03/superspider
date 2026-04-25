from pyspider.browser.locator_analyzer import LocatorAnalyzer, LocatorTarget
from pyspider.browser.devtools_analyzer import DevToolsAnalyzer


def test_locator_analyzer_builds_css_and_xpath_candidates():
    html = """
    <html><body>
      <form>
        <input id="search-box" name="q" placeholder="Search products">
        <button data-testid="submit-search">Search</button>
      </form>
    </body></html>
    """

    plan = LocatorAnalyzer().analyze(html, LocatorTarget.for_field("q"))
    expressions = {(candidate.kind, candidate.expr) for candidate in plan.candidates}

    assert ("css", "#search-box") in expressions
    assert ("xpath", "//input[@name='q']") in expressions

    button_plan = LocatorAnalyzer().analyze(html, LocatorTarget.for_text("Search", tag="button"))
    assert button_plan.best() is not None
    assert button_plan.best().kind in {"css", "xpath"}


def test_devtools_analyzer_snapshots_elements_and_selects_node_reverse_route():
    html = """
    <html><body>
      <input id="kw" name="q">
      <script src="/static/app.js"></script>
      <script>const token = CryptoJS.MD5(window.navigator.userAgent).toString();</script>
    </body></html>
    """

    report = DevToolsAnalyzer().analyze(
        html,
        network_events=[
            {"method": "GET", "url": "https://example.com/api/search?sign=abc", "resource_type": "xhr", "status": 200}
        ],
    )

    assert report.summary["element_count"] >= 3
    assert any(element.attrs.get("id") == "kw" for element in report.elements)
    assert report.best_reverse_route() is not None
    assert report.best_reverse_route().kind == "analyze_crypto"
