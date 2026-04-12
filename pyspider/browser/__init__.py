"""
Browser package exports.

使用懒加载，避免导入 Playwright 子模块时被 Selenium 依赖链阻断。
"""

from __future__ import annotations

import importlib

_EXPORTS = {
    "BrowserConfig": ("pyspider.browser.browser", "BrowserConfig"),
    "BrowserLauncher": ("pyspider.browser.browser", "BrowserLauncher"),
    "PlaywrightBrowser": ("pyspider.browser.playwright_browser", "PlaywrightBrowser"),
    "PlaywrightBrowserEnhanced": (
        "pyspider.browser.enhanced",
        "PlaywrightBrowserEnhanced",
    ),
}

__all__ = list(_EXPORTS.keys())


def __getattr__(name: str):
    target = _EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module 'pyspider.browser' has no attribute {name!r}")

    module_name, attr_name = target
    module = importlib.import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value


def __dir__():
    return sorted(list(globals().keys()) + __all__)
