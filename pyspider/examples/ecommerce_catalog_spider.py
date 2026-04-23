from __future__ import annotations

import sys

from pyspider.spider.spider import CrawlerProcess, FeedExporter, Item, Request, Spider

from ecommerce_site_profile import (
    DEFAULT_SITE_FAMILY,
    best_title,
    build_jd_price_api_url,
    collect_image_links,
    collect_matches,
    collect_product_links,
    collect_video_links,
    extract_api_candidates,
    extract_embedded_json_blocks,
    extract_jd_catalog_products,
    extract_json_ld_products,
    first_link_with_keywords,
    first_match,
    get_profile,
    safe_json_loads,
    text_excerpt,
)


class EcommerceCatalogSpider(Spider):
    name = "ecommerce_catalog"
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
            url=profile["catalog_url"],
            callback=self.parse,
            headers=self.headers,
            meta={
                "site_family": self.site_family,
                "runner": profile["runner"],
                "browser": {
                    "session": f"{self.site_family}-catalog",
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
        summary_item = Item(
            kind=f"{family}_catalog_page" if family == "jd" else "ecommerce_catalog_page",
            site_family=family,
            runner=profile["runner"],
            title=best_title(selector),
            url=page.response.url,
            product_link_candidates=collect_product_links(page.response.url, links, profile),
            next_page=first_link_with_keywords(page.response.url, links, profile["next_link_keywords"]),
            sku_candidates=collect_matches(html, profile["item_id_patterns"]),
            price_excerpt=first_match(html, profile["price_patterns"]),
            image_candidates=collect_image_links(page.response.url, selector.css_attr("img", "src")),
            video_candidates=collect_video_links(
                page.response.url,
                selector.css_attr("video", "src") + selector.css_attr("source", "src"),
            ),
            script_sources=selector.css_attr("script", "src"),
            api_candidates=extract_api_candidates(html),
            embedded_json_blocks=extract_embedded_json_blocks(html),
            json_ld_products=extract_json_ld_products(html),
            page_excerpt=text_excerpt(html),
            note="Public universal ecommerce catalog page extraction.",
        )

        if family == "jd":
            products = extract_jd_catalog_products(html)
            if products:
                yield summary_item
                yield Request(
                    url=build_jd_price_api_url([product["product_id"] for product in products]),
                    callback=self.parse_prices,
                    headers={
                        "User-Agent": self.headers["User-Agent"],
                        "Referer": page.response.url,
                    },
                    meta={
                        "site_family": family,
                        "source_url": page.response.url,
                        "products": products,
                    },
                )
                return

        if family in self.FAST_PATH_FAMILIES and summary_item.get("json_ld_products"):
            yield summary_item
            fallback_links = summary_item.get("product_link_candidates", [])
            for index, product in enumerate(summary_item.get("json_ld_products", [])):
                yield Item(
                    kind=f"{family}_catalog_product",
                    site_family=family,
                    source_url=page.response.url,
                    product_id=product.get("sku", "") or (summary_item.get("sku_candidates", [""])[:1] or [""])[0],
                    name=product.get("name", ""),
                    url=product.get("url", "") or (fallback_links[index] if index < len(fallback_links) else ""),
                    image_url=product.get("image", ""),
                    brand=product.get("brand", ""),
                    category=product.get("category", ""),
                    price=product.get("price", ""),
                    currency=product.get("currency", ""),
                    rating=product.get("rating", ""),
                    review_count=product.get("review_count", ""),
                )
            return

        yield summary_item

    def parse_prices(self, page):
        request = getattr(page.response, "request", None)
        meta = request.meta if request else {}
        family = meta.get("site_family", self.site_family)
        products = meta.get("products", [])
        source_url = meta.get("source_url", "")
        payload = safe_json_loads(page.response.text) or []
        price_map = {}

        if isinstance(payload, list):
            for item in payload:
                if not isinstance(item, dict):
                    continue
                sku_id = str(item.get("id", "")).strip()
                if sku_id:
                    price_map[sku_id] = {
                        "price": str(item.get("p", "")).strip(),
                        "original_price": str(item.get("op", "")).strip(),
                    }

        for product in products:
            pricing = price_map.get(product["product_id"], {})
            yield Item(
                kind="jd_catalog_product",
                site_family=family,
                source_url=source_url,
                product_id=product["product_id"],
                name=product["name"],
                url=product["url"],
                image_url=product["image_url"],
                comment_count=product["comment_count"],
                price=pricing.get("price", ""),
                original_price=pricing.get("original_price", ""),
            )


if __name__ == "__main__":
    family = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SITE_FAMILY
    process = CrawlerProcess(EcommerceCatalogSpider(site_family=family))
    items = process.start()
    exporter = FeedExporter.json(f"artifacts/exports/pyspider-{family}-catalog.json")
    exporter.export_items(items)
    output = exporter.close()
    print(f"exported {len(items)} items to {output}")
