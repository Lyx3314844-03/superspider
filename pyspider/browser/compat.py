"""Browser compatibility metadata for CLI capability output."""

from __future__ import annotations


def browser_compatibility_matrix() -> dict:
    return {
        "base_engine": "playwright-and-selenium",
        "bridge_style": "native-and-helper",
        "surfaces": {
            "playwright": {
                "supported": True,
                "mode": "native",
                "adapter_engine": "playwright",
            },
            "selenium": {
                "supported": True,
                "mode": "native",
                "adapter_engine": "selenium-webdriver",
            },
            "webdriver": {
                "supported": True,
                "mode": "compatibility-bridge",
                "adapter_engine": "selenium-webdriver",
            },
        },
        "artifacts": {
            "html": True,
            "screenshot": True,
            "har": True,
            "trace": True,
            "pdf": False,
        },
        "constraints": [
            "webdriver-compatible surface is routed through the existing selenium runtime",
        ],
    }
