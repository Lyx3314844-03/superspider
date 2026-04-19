from __future__ import annotations

import os


_DEFAULTS = {
    "ai": True,
    "browser": True,
    "distributed": True,
    "media": True,
    "workflow": True,
    "crawlee": True,
}

_PROFILES = {
    "lite": ["browser", "workflow"],
    "ai": ["ai", "browser", "workflow"],
    "distributed": ["browser", "distributed", "workflow", "crawlee"],
    "full": ["ai", "browser", "distributed", "media", "workflow", "crawlee"],
}


def _env_name(name: str) -> str:
    return f"PYSPIDER_FEATURE_{name.upper().replace('-', '_').replace('.', '_')}"


def is_enabled(name: str) -> bool:
    normalized = name.strip().lower()
    raw = os.getenv(_env_name(normalized), "").strip().lower()
    if not raw:
        return _DEFAULTS.get(normalized, False)
    return raw in {"1", "true", "yes", "on"}


def catalog() -> dict[str, object]:
    return {
        "default_profile": "full",
        "profiles": _PROFILES,
        "env_prefix": "PYSPIDER_FEATURE_",
        "features": {name: is_enabled(name) for name in sorted(_DEFAULTS)},
    }
