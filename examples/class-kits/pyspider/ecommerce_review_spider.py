# scrapy: url=https://club.jd.com/comment/productPageComments.action?productId=100000000000
from pyspider.spider.spider import Item, Request, Spider

from ecommerce_site_profile import (
    DEFAULT_SITE_FAMILY,
    collect_matches,
    first_match,
    get_profile,
    text_excerpt,
)


class EcommerceReviewSpider(Spider):
    name = "ecommerce_review"
    custom_settings = {"site_family": DEFAULT_SITE_FAMILY}

    def start_requests(self):
        family = self.custom_settings.get("site_family", DEFAULT_SITE_FAMILY)
        profile = get_profile(family)
        yield Request(
            url=profile["review_url"],
            callback=self.parse,
            meta={"site_family": family, "runner": profile["runner"]},
        )

    def parse(self, page):
        request = getattr(page.response, "request", None)
        family = request.meta.get("site_family", DEFAULT_SITE_FAMILY) if request else DEFAULT_SITE_FAMILY
        profile = get_profile(family)
        html = page.response.text

        yield Item(
            kind="ecommerce_review",
            site_family=family,
            url=page.response.url,
            item_id=first_match(html, profile["item_id_patterns"]),
            rating=first_match(html, profile["rating_patterns"]),
            review_count=first_match(html, profile["review_count_patterns"]),
            review_id_candidates=collect_matches(
                html,
                [r"(?:commentId|reviewId|id)[\"'=:\\s]+([A-Za-z0-9_-]+)"],
            ),
            excerpt=text_excerpt(html),
            note="Template for public review pages or review APIs. Prefer stable JSON payloads over brittle DOM selectors.",
        )
