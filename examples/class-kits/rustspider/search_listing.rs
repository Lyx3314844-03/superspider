use std::sync::Arc;

use rustspider::scrapy::project as projectruntime;
use rustspider::scrapy::{Item, Output, Response, Spider};

pub fn make_search_listing_spider() -> Spider {
    Spider::new(
        "search-listing",
        Arc::new(|response: &Response| {
            vec![Output::Item(
                Item::new()
                    .set("kind", "listing")
                    .set("title", response.css("title").get().unwrap_or_default())
                    .set("url", response.url.clone()),
            )]
        }),
    )
    .add_start_url("https://example.com/search?q=demo")
    .with_start_meta("runner", "browser")
}

pub fn register() {
    projectruntime::register_spider("search-listing", make_search_listing_spider);
}

