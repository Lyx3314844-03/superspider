use std::sync::Arc;

use rustspider::scrapy::project as projectruntime;
use rustspider::scrapy::{Item, Output, Response, Spider};

pub fn make_infinite_scroll_spider() -> Spider {
    Spider::new(
        "infinite-scroll",
        Arc::new(|response: &Response| {
            vec![Output::Item(
                Item::new()
                    .set("kind", "infinite_scroll")
                    .set("title", response.css("title").get().unwrap_or_default())
                    .set("url", response.url.clone()),
            )]
        }),
    )
    .add_start_url("https://example.com/discover")
    .with_start_meta("runner", "browser")
}

pub fn register() {
    projectruntime::register_spider("infinite-scroll", make_infinite_scroll_spider);
}

