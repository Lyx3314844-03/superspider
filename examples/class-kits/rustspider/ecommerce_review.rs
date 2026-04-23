use std::sync::Arc;

use rustspider::scrapy::project as projectruntime;
use rustspider::scrapy::{Item, Output, Response, Spider};

use super::ecommerce_profile::{
    collect_matches, first_match, profile_for_family, site_family_from_response, text_excerpt,
    DEFAULT_SITE_FAMILY,
};

pub fn make_ecommerce_review_spider() -> Spider {
    let profile = profile_for_family(DEFAULT_SITE_FAMILY);
    Spider::new(
        "ecommerce-review",
        Arc::new(|response: &Response| {
            let family = site_family_from_response(response);
            let current = profile_for_family(&family);
            vec![Output::Item(
                Item::new()
                    .set("kind", "ecommerce_review")
                    .set("site_family", family)
                    .set("url", response.url.clone())
                    .set("item_id", first_match(&response.text, current.item_id_patterns))
                    .set("rating", first_match(&response.text, current.rating_patterns))
                    .set(
                        "review_count",
                        first_match(&response.text, current.review_count_patterns),
                    )
                    .set(
                        "review_id_candidates",
                        collect_matches(
                            &response.text,
                            &[r#"(?:commentId|reviewId|id)["'=:\s]+([A-Za-z0-9_-]+)"#],
                            10,
                        ),
                    )
                    .set("excerpt", text_excerpt(&response.text, 800))
                    .set(
                        "note",
                        "Template for public review pages or review APIs. Prefer stable JSON payloads over brittle DOM selectors.",
                    ),
            )]
        }),
    )
    .add_start_url(profile.review_url)
    .with_start_meta("site_family", DEFAULT_SITE_FAMILY)
    .with_start_meta("runner", profile.runner)
}

pub fn register() {
    projectruntime::register_spider("ecommerce-review", make_ecommerce_review_spider);
}
