from __future__ import annotations

from typing import Callable, Dict, Type

from pyspider.spider.spider import ScrapyPlugin

PLUGIN_REGISTRY: Dict[str, Type[ScrapyPlugin]] = {}


def register_plugin(
    name: str | None = None,
) -> Callable[[Type[ScrapyPlugin]], Type[ScrapyPlugin]]:
    def decorator(plugin_class: Type[ScrapyPlugin]) -> Type[ScrapyPlugin]:
        plugin_name = (
            name or getattr(plugin_class, "name", "") or plugin_class.__name__
        ).strip()
        if plugin_name:
            PLUGIN_REGISTRY[plugin_name] = plugin_class
        return plugin_class

    return decorator


def get_registered_plugin(name: str) -> Type[ScrapyPlugin] | None:
    return PLUGIN_REGISTRY.get(name.strip())


def create_registered_plugin(name: str) -> ScrapyPlugin | None:
    plugin_class = get_registered_plugin(name)
    return plugin_class() if plugin_class else None


def registered_plugin_names() -> list[str]:
    return sorted(PLUGIN_REGISTRY.keys())


def clear_registry_for_tests() -> None:
    PLUGIN_REGISTRY.clear()
