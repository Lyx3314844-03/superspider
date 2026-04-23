# scrapy: url=https://search.jd.com/Search?keyword=iphone
from pyspider.spider.spider import Item, Request, Spider

from ecommerce_site_profile import (
    DEFAULT_SITE_FAMILY,
    best_title,
    collect_matches,
    collect_product_links,
    first_link_with_keywords,
    first_match,
    get_profile,
)


class EcommerceCatalogSpider(Spider):
    name = "ecommerce_catalog"
    custom_settings = {"site_family": DEFAULT_SITE_FAMILY}

    def start_requests(self):
        family = self.custom_settings.get("site_family", DEFAULT_SITE_FAMILY)
        profile = get_profile(family)
        yield Request(
            url=profile["catalog_url"],
            callback=self.parse,
            meta={
                "site_family": family,
                "runner": profile["runner"],
                "browser": {
                    "session": f"{family}-catalog",
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
            kind="ecommerce_catalog",
            site_family=family,
            runner=profile["runner"],
            title=best_title(selector),
            url=page.response.url,
            product_link_candidates=collect_product_links(page.response.url, links, profile),
            next_page=first_link_with_keywords(
                page.response.url,
                links,
                profile["next_link_keywords"],
            ),
            sku_candidates=collect_matches(html, profile["item_id_patterns"]),
            price_excerpt=first_match(html, profile["price_patterns"]),
            note="Template for public category/search pages. Tune the site profile before production crawling.",
        )
