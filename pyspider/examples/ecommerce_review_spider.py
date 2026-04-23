from __future__ import annotations

import sys

from pyspider.spider.spider import CrawlerProcess, FeedExporter, Item, Request, Spider

from ecommerce_site_profile import (
    DEFAULT_SITE_FAMILY,
    build_jd_review_api_url,
    collect_matches,
    collect_video_links,
    extract_jd_item_id,
    extract_api_candidates,
    extract_embedded_json_blocks,
    extract_json_ld_products,
    first_match,
    get_profile,
    safe_json_loads,
    text_excerpt,
)


class EcommerceReviewSpider(Spider):
    name = "ecommerce_review"
    FAST_PATH_FAMILIES = {"taobao", "tmall", "pinduoduo", "amazon"}

    def __init__(self, site_family: str = DEFAULT_SITE_FAMILY):
        super().__init__()
        self.site_family = site_family
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json,text/plain,*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": "https://item.jd.com/100000000000.html",
        }

    def start_requests(self):
        profile = get_profile(self.site_family)
        yield Request(
            url=profile["review_url"],
            callback=self.parse,
            headers=self.headers,
            meta={"site_family": self.site_family, "runner": profile["runner"]},
        )

    def parse(self, page):
        request = getattr(page.response, "request", None)
        family = request.meta.get("site_family", self.site_family) if request else self.site_family
        profile = get_profile(family)
        html = page.response.text
        selector = page.response.selector
        universal_fields = {
            "embedded_json_blocks": extract_embedded_json_blocks(html),
            "json_ld_products": extract_json_ld_products(html),
            "api_candidates": extract_api_candidates(html),
            "script_sources": selector.css_attr("script", "src"),
            "video_candidates": collect_video_links(
                page.response.url,
                selector.css_attr("video", "src") + selector.css_attr("source", "src"),
            ),
            "excerpt": text_excerpt(html),
        }

        if family == "jd":
            payload = safe_json_loads(html) or {}
            product_id = ""
            comments_preview = []
            review_count = ""
            max_page = 0

            if isinstance(payload, dict):
                comments = payload.get("comments", [])
                if isinstance(comments, list):
                    for comment in comments[:5]:
                        if not isinstance(comment, dict):
                            continue
                        comments_preview.append(
                            {
                                "id": comment.get("id"),
                                "score": comment.get("score"),
                                "nickname": comment.get("nickname"),
                                "content": text_excerpt(str(comment.get("content", "")), 120),
                            }
                        )
                product_id = (
                    str(payload.get("productId", "")).strip()
                    or str(payload.get("skuId", "")).strip()
                    or extract_jd_item_id(page.response.url, html)
                )
                review_count = str(payload.get("maxPage", "")).strip()
                max_page = int(payload.get("maxPage", 0) or 0)

            if product_id and "productPageComments.action" in page.response.url and "pageSize" not in page.response.url:
                yield Request(
                    url=build_jd_review_api_url(product_id),
                    callback=self.parse,
                    headers={
                        "User-Agent": self.headers["User-Agent"],
                        "Referer": f"https://item.jd.com/{product_id}.html",
                    },
                    meta={"site_family": family, "runner": profile["runner"]},
                )
                return

            yield Item(
                kind="jd_review_summary",
                site_family=family,
                url=page.response.url,
                item_id=product_id,
                rating=first_match(html, profile["rating_patterns"]),
                review_count=review_count,
                max_page=max_page,
                comments_preview=comments_preview,
                **universal_fields,
                note="Public universal ecommerce review extraction with JD review fast path.",
            )
            return

        if family in self.FAST_PATH_FAMILIES and universal_fields["json_ld_products"]:
            product = universal_fields["json_ld_products"][0]
            yield Item(
                kind=f"{family}_review_summary",
                site_family=family,
                url=page.response.url,
                item_id=product.get("sku", "") or first_match(html, profile["item_id_patterns"]),
                rating=product.get("rating", "") or first_match(html, profile["rating_patterns"]),
                review_count=product.get("review_count", "") or first_match(html, profile["review_count_patterns"]),
                brand=product.get("brand", ""),
                category=product.get("category", ""),
                **universal_fields,
                note="Public ecommerce review fast path via JSON-LD aggregate rating extraction.",
            )
            return

        yield Item(
            kind="ecommerce_review",
            site_family=family,
            url=page.response.url,
            item_id=first_match(html, profile["item_id_patterns"]),
            rating=first_match(html, profile["rating_patterns"]),
            review_count=first_match(html, profile["review_count_patterns"]),
            review_id_candidates=collect_matches(html, [r"(?:commentId|reviewId|id)[\"'=:\\s]+([A-Za-z0-9_-]+)"]),
            **universal_fields,
            note="Public universal ecommerce review extraction.",
        )


if __name__ == "__main__":
    family = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SITE_FAMILY
    process = CrawlerProcess(EcommerceReviewSpider(site_family=family))
    items = process.start()
    exporter = FeedExporter.json(f"artifacts/exports/pyspider-{family}-review.json")
    exporter.export_items(items)
    output = exporter.close()
    print(f"exported {len(items)} items to {output}")
