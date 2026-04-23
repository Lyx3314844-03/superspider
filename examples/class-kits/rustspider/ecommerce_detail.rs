use std::sync::Arc;

use rustspider::scrapy::project as projectruntime;
use rustspider::scrapy::{Item, Output, Response, Spider};

use super::ecommerce_profile::{
    best_title, collect_image_links, first_link_with_keywords, first_match, profile_for_family,
    site_family_from_response, text_excerpt, DEFAULT_SITE_FAMILY,
};

pub fn make_ecommerce_detail_spider() -> Spider {
    let profile = profile_for_family(DEFAULT_SITE_FAMILY);
    Spider::new(
        "ecommerce-detail",
        Arc::new(|response: &Response| {
            let family = site_family_from_response(response);
            let current = profile_for_family(&family);
            let links = response.xpath("//a/@href").get_all();
            vec![Output::Item(
                Item::new()
                    .set("kind", "ecommerce_detail")
                    .set("site_family", family)
                    .set("title", best_title(response))
                    .set("url", response.url.clone())
                    .set("item_id", first_match(&response.text, current.item_id_patterns))
                    .set("price", first_match(&response.text, current.price_patterns))
                    .set("shop", first_match(&response.text, current.shop_patterns))
                    .set(
                        "review_count",
                        first_match(&response.text, current.review_count_patterns),
                    )
                    .set(
                        "image_candidates",
                        collect_image_links(&response.url, response.xpath("//img/@src").get_all(), 10),
                    )
                    .set(
                        "review_url",
                        first_link_with_keywords(&response.url, links, current.review_link_keywords),
                    )
                    .set("html_excerpt", text_excerpt(&response.text, 800))
                    .set(
                        "note",
                        "Template for public product detail pages. Extend with site-specific JSON/bootstrap extraction when available.",
                    ),
            )]
        }),
    )
    .add_start_url(profile.detail_url)
    .with_start_meta("site_family", DEFAULT_SITE_FAMILY)
    .with_start_meta("runner", profile.runner)
}

pub fn register() {
    projectruntime::register_spider("ecommerce-detail", make_ecommerce_detail_spider);
}
