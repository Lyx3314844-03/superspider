use std::sync::Arc;

use rustspider::scrapy::project as projectruntime;
use rustspider::scrapy::{Item, Output, Response, Spider};

pub fn make_social_feed_spider() -> Spider {
    Spider::new(
        "social-feed",
        Arc::new(|response: &Response| {
            vec![Output::Item(
                Item::new()
                    .set("kind", "social_feed")
                    .set("title", response.css("title").get().unwrap_or_default())
                    .set("url", response.url.clone()),
            )]
        }),
    )
    .add_start_url("https://example.com/feed")
    .with_start_meta("runner", "browser")
}

pub fn register() {
    projectruntime::register_spider("social-feed", make_social_feed_spider);
}

