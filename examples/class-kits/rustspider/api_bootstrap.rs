use std::sync::Arc;

use rustspider::scrapy::project as projectruntime;
use rustspider::scrapy::{Item, Output, Response, Spider};

pub fn make_api_bootstrap_spider() -> Spider {
    Spider::new(
        "api-bootstrap",
        Arc::new(|response: &Response| {
            vec![Output::Item(
                Item::new()
                    .set("kind", "api_bootstrap")
                    .set("title", response.css("title").get().unwrap_or_default())
                    .set("url", response.url.clone())
                    .set("bootstrap_excerpt", response.text.clone()),
            )]
        }),
    )
    .add_start_url("https://example.com/app/page")
}

pub fn register() {
    projectruntime::register_spider("api-bootstrap", make_api_bootstrap_spider);
}

