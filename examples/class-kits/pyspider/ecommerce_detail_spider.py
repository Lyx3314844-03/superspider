# scrapy: url=https://item.jd.com/100000000000.html
from pyspider.spider.spider import Item, Request, Spider

from ecommerce_site_profile import (
    DEFAULT_SITE_FAMILY,
    best_title,
    collect_image_links,
    first_link_with_keywords,
    first_match,
    get_profile,
    text_excerpt,
)


class EcommerceDetailSpider(Spider):
    name = "ecommerce_detail"
    custom_settings = {"site_family": DEFAULT_SITE_FAMILY}

    def start_requests(self):
        family = self.custom_settings.get("site_family", DEFAULT_SITE_FAMILY)
        profile = get_profile(family)
        yield Request(
            url=profile["detail_url"],
            callback=self.parse,
            meta={
                "site_family": family,
                "runner": profile["runner"],
                "browser": {
                    "session": f"{family}-detail",
                    "wait_until": "networkidle",
                },
            },
        )

    def parse(self, page):
        request = getattr(page.response, "request", None)
        family = request.meta.get("site_family", DEFAULT_SITE_FAMILY) if request else DEFAULT_SITE_FAMILY
        profile = get_profile(family)
        selector = page.response.selector
        html = page.response.text
        links = selector.css_attr("a", "href")

        yield Item(
            kind="ecommerce_detail",
            site_family=family,
            title=best_title(selector),
            url=page.response.url,
            item_id=first_match(html, profile["item_id_patterns"]),
            price=first_match(html, profile["price_patterns"]),
            shop=first_match(html, profile["shop_patterns"]),
            review_count=first_match(html, profile["review_count_patterns"]),
            image_candidates=collect_image_links(page.response.url, selector.css_attr("img", "src")),
            review_url=first_link_with_keywords(
                page.response.url,
                links,
                profile["review_link_keywords"],
            ),
            html_excerpt=text_excerpt(html),
            note="Template for public product detail pages. Extend with site-specific JSON/bootstrap extraction when available.",
        )
