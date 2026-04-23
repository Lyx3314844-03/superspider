use std::sync::Arc;

use rustspider::scrapy::project as projectruntime;
use rustspider::scrapy::{Item, Output, Response, Spider};

use super::ecommerce_profile::{
    best_title, collect_matches, collect_product_links, first_link_with_keywords, first_match,
    profile_for_family, site_family_from_response, DEFAULT_SITE_FAMILY,
};

pub fn make_ecommerce_catalog_spider() -> Spider {
    let profile = profile_for_family(DEFAULT_SITE_FAMILY);
    Spider::new(
        "ecommerce-catalog",
        Arc::new(|response: &Response| {
            let family = site_family_from_response(response);
            let current = profile_for_family(&family);
            let links = response.xpath("//a/@href").get_all();
            vec![Output::Item(
                Item::new()
                    .set("kind", "ecommerce_catalog")
                    .set("site_family", family)
                    .set("runner", current.runner)
                    .set("title", best_title(response))
                    .set("url", response.url.clone())
                    .set(
                        "product_link_candidates",
                        collect_product_links(&response.url, links.clone(), &current, 20),
                    )
                    .set(
                        "next_page",
                        first_link_with_keywords(&response.url, links, current.next_link_keywords),
                    )
                    .set(
                        "sku_candidates",
                        collect_matches(&response.text, current.item_id_patterns, 10),
                    )
                    .set("price_excerpt", first_match(&response.text, current.price_patterns))
                    .set(
                        "note",
                        "Template for public category/search pages. Tune the site profile before production crawling.",
                    ),
            )]
        }),
    )
    .add_start_url(profile.catalog_url)
    .with_start_meta("site_family", DEFAULT_SITE_FAMILY)
    .with_start_meta("runner", profile.runner)
}

pub fn register() {
    projectruntime::register_spider("ecommerce-catalog", make_ecommerce_catalog_spider);
}
