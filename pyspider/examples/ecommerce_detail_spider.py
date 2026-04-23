from __future__ import annotations

import sys

from pyspider.spider.spider import CrawlerProcess, FeedExporter, Item, Request, Spider

from ecommerce_site_profile import (
    DEFAULT_SITE_FAMILY,
    best_title,
    build_jd_price_api_url,
    collect_image_links,
    collect_video_links,
    extract_jd_item_id,
    extract_api_candidates,
    extract_embedded_json_blocks,
    extract_json_ld_products,
    first_link_with_keywords,
    first_match,
    get_profile,
    safe_json_loads,
    text_excerpt,
)


class EcommerceDetailSpider(Spider):
    name = "ecommerce_detail"
    FAST_PATH_FAMILIES = {"taobao", "tmall", "pinduoduo", "amazon"}

    def __init__(self, site_family: str = DEFAULT_SITE_FAMILY):
        super().__init__()
        self.site_family = site_family
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": "https://www.jd.com/",
        }

    def start_requests(self):
        profile = get_profile(self.site_family)
        yield Request(
            url=profile["detail_url"],
            callback=self.parse,
            headers=self.headers,
            meta={
                "site_family": self.site_family,
                "runner": profile["runner"],
                "browser": {
                    "session": f"{self.site_family}-detail",
                    "wait_until": "networkidle",
                },
            },
        )

    def parse(self, page):
        request = getattr(page.response, "request", None)
        family = request.meta.get("site_family", self.site_family) if request else self.site_family
        profile = get_profile(family)
        selector = page.response.selector
        html = page.response.text
        links = selector.css_attr("a", "href")
        universal_fields = {
            "embedded_json_blocks": extract_embedded_json_blocks(html),
            "json_ld_products": extract_json_ld_products(html),
            "api_candidates": extract_api_candidates(html),
            "image_candidates": collect_image_links(page.response.url, selector.css_attr("img", "src")),
            "video_candidates": collect_video_links(
                page.response.url,
                selector.css_attr("video", "src") + selector.css_attr("source", "src"),
            ),
            "script_sources": selector.css_attr("script", "src"),
            "html_excerpt": text_excerpt(html),
        }

        if family == "jd":
            item_id = extract_jd_item_id(page.response.url, html)
            detail = {
                "kind": "jd_detail_product",
                "site_family": family,
                "title": best_title(selector),
                "url": page.response.url,
                "item_id": item_id,
                "shop": first_match(html, profile["shop_patterns"]),
                "review_count": first_match(html, profile["review_count_patterns"]),
                "review_url": first_link_with_keywords(page.response.url, links, profile["review_link_keywords"]),
                **universal_fields,
                "note": "Public universal ecommerce detail extraction with JD price fast path.",
            }
            if item_id:
                yield Request(
                    url=build_jd_price_api_url([item_id]),
                    callback=self.parse_price,
                    headers={
                        "User-Agent": self.headers["User-Agent"],
                        "Referer": page.response.url,
                    },
                    meta={"site_family": family, "detail": detail},
                )
                return
            yield Item(**detail)
            return

        if family in self.FAST_PATH_FAMILIES and universal_fields["json_ld_products"]:
            product = universal_fields["json_ld_products"][0]
            yield Item(
                kind=f"{family}_detail_product",
                site_family=family,
                title=product.get("name", "") or best_title(selector),
                url=product.get("url", "") or page.response.url,
                item_id=product.get("sku", "") or first_match(html, profile["item_id_patterns"]),
                price=product.get("price", "") or first_match(html, profile["price_patterns"]),
                currency=product.get("currency", ""),
                brand=product.get("brand", ""),
                category=product.get("category", ""),
                rating=product.get("rating", "") or first_match(html, profile["rating_patterns"]),
                review_count=product.get("review_count", "") or first_match(html, profile["review_count_patterns"]),
                shop=first_match(html, profile["shop_patterns"]),
                review_url=first_link_with_keywords(page.response.url, links, profile["review_link_keywords"]),
                **universal_fields,
                note="Public ecommerce detail fast path via JSON-LD product extraction.",
            )
            return

        yield Item(
            kind="ecommerce_detail",
            site_family=family,
            title=best_title(selector),
            url=page.response.url,
            item_id=first_match(html, profile["item_id_patterns"]),
            price=first_match(html, profile["price_patterns"]),
            shop=first_match(html, profile["shop_patterns"]),
            review_count=first_match(html, profile["review_count_patterns"]),
            review_url=first_link_with_keywords(page.response.url, links, profile["review_link_keywords"]),
            **universal_fields,
            note="Public universal ecommerce detail extraction.",
        )

    def parse_price(self, page):
        request = getattr(page.response, "request", None)
        meta = request.meta if request else {}
        detail = dict(meta.get("detail", {}))
        payload = safe_json_loads(page.response.text) or []
        if isinstance(payload, list) and payload:
            first = payload[0] if isinstance(payload[0], dict) else {}
            detail["price"] = str(first.get("p", "")).strip()
            detail["original_price"] = str(first.get("op", "")).strip()
        yield Item(**detail)


if __name__ == "__main__":
    family = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SITE_FAMILY
    process = CrawlerProcess(EcommerceDetailSpider(site_family=family))
    items = process.start()
    exporter = FeedExporter.json(f"artifacts/exports/pyspider-{family}-detail.json")
    exporter.export_items(items)
    output = exporter.close()
    print(f"exported {len(items)} items to {output}")
