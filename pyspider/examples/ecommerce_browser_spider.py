from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

from pyspider.browser.playwright_browser import PlaywrightBrowser

from ecommerce_site_profile import (
    DEFAULT_SITE_FAMILY,
    build_api_job_templates,
    collect_image_links,
    collect_matches,
    collect_product_links,
    detect_coupons_promotions,
    extract_api_candidates,
    extract_bootstrap_products,
    extract_embedded_json_blocks,
    extract_image_gallery,
    extract_json_ld_products,
    extract_parameter_table,
    extract_stock_status,
    get_profile,
    normalize_network_entries,
    extract_network_api_candidates,
)
from universal_ecommerce_detector import detect_ecommerce_site


class EcommerceBrowserSpider:
    """Playwright-backed ecommerce crawler that exports rendered HTML, network, and parsed product signals."""

    def __init__(
        self,
        site_family: str = DEFAULT_SITE_FAMILY,
        output_dir: str = "artifacts/browser",
        headless: bool | None = None,
        user_data_dir: str | None = None,
        manual_access_timeout: int | None = None,
    ):
        self.site_family = site_family
        self.output_dir = output_dir
        self.headless = _env_bool("ECOM_BROWSER_HEADLESS", not _is_high_friction_site(site_family)) if headless is None else headless
        self.user_data_dir = user_data_dir or os.getenv("ECOM_BROWSER_PROFILE") or str(Path(output_dir) / "profiles" / f"pyspider-{site_family}")
        self.manual_access_timeout = (
            int(os.getenv("ECOM_BROWSER_MANUAL_SECONDS", "180" if _is_high_friction_site(site_family) else "0"))
            if manual_access_timeout is None
            else manual_access_timeout
        )
        self.attempts = int(os.getenv("ECOM_BROWSER_ATTEMPTS", "2" if _is_high_friction_site(site_family) else "1"))

    def crawl(self, mode: str = "catalog") -> dict:
        profile = get_profile(self.site_family)
        target_url = profile.get(f"{mode}_url") or profile["catalog_url"]
        output = Path(self.output_dir)
        output.mkdir(parents=True, exist_ok=True)
        prefix = f"pyspider-{self.site_family}-{mode}"

        with PlaywrightBrowser(
            headless=self.headless,
            timeout=90000,
            user_data_dir=self.user_data_dir,
        ) as browser:
            capture = browser.ecommerce_capture(
                target_url,
                scroll_rounds=8 if mode == "catalog" else 4,
                screenshot_path=str(output / f"{prefix}.png"),
                manual_access_timeout=self.manual_access_timeout,
                warmup_url=_origin_url(target_url),
                attempts=self.attempts,
                retry_backoff_seconds=4.0,
            )
            browser.save_network_events(str(output / f"{prefix}-network.json"))
            browser.save_storage_state(str(output / f"{prefix}-storage.json"))

        html = capture["html"]
        links = _extract_links(html)
        image_sources = _extract_image_sources(html)
        network_entries = normalize_network_entries({"network_events": capture["network_events"]})
        api_candidates = extract_api_candidates(html) + extract_network_api_candidates(network_entries)
        detection = detect_ecommerce_site(capture["url"], html).__dict__

        result = {
            "kind": "ecommerce_browser_capture",
            "site_family": self.site_family,
            "mode": mode,
            "url": capture["url"],
            "title": capture["title"],
            "detector": detection,
            "product_link_candidates": collect_product_links(capture["url"], links, profile),
            "sku_candidates": collect_matches(html, profile["item_id_patterns"]),
            "image_candidates": collect_image_links(capture["url"], image_sources),
            "image_gallery": extract_image_gallery(capture["url"], image_sources),
            "json_ld_products": extract_json_ld_products(html),
            "bootstrap_products": extract_bootstrap_products(html),
            "embedded_json_blocks": extract_embedded_json_blocks(html),
            "api_candidates": api_candidates[:30],
            "network_entries": network_entries[:50],
            "network_api_candidates": extract_network_api_candidates(network_entries),
            "api_job_templates": build_api_job_templates(capture["url"], self.site_family, api_candidates[:30]),
            "access_challenge": capture["access_challenge"],
            "runtime": capture["runtime"],
            "parameter_table": extract_parameter_table(html),
            "coupons_promotions": detect_coupons_promotions(html),
            "stock_status": extract_stock_status(html),
            "artifacts": {
                "html": str(output / f"{prefix}.html"),
                "network": str(output / f"{prefix}-network.json"),
                "storage": str(output / f"{prefix}-storage.json"),
                "screenshot": capture["screenshot"],
                "json": str(output / f"{prefix}.json"),
            },
        }
        Path(result["artifacts"]["html"]).write_text(html, encoding="utf-8")
        Path(result["artifacts"]["json"]).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result


def capture_ecommerce_page(site_family: str, mode: str = "catalog", output_dir: str = "artifacts/browser") -> dict:
    return EcommerceBrowserSpider(site_family, output_dir).crawl(mode)


def _extract_links(html: str) -> list[str]:
    import re

    return re.findall(r"<a[^>]+href=[\"']([^\"']+)[\"']", html, flags=re.I)


def _extract_image_sources(html: str) -> list[str]:
    import re

    return re.findall(r"<img[^>]+(?:src|data-src|data-lazy-img)=[\"']([^\"']+)[\"']", html, flags=re.I)


def _is_high_friction_site(site_family: str) -> bool:
    return site_family.lower() in {"jd", "taobao", "tmall", "pdd", "amazon"}


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _origin_url(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}/"


if __name__ == "__main__":
    family = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SITE_FAMILY
    mode = sys.argv[2] if len(sys.argv) > 2 else "catalog"
    payload = capture_ecommerce_page(family, mode)
    print(json.dumps({"output": payload["artifacts"], "products": len(payload["json_ld_products"]) + len(payload["bootstrap_products"])}, ensure_ascii=False, indent=2))
