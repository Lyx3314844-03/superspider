use std::sync::Arc;

use rustspider::scrapy::project as projectruntime;
use rustspider::scrapy::{Item, Output, Response, Spider};

pub fn make_product_detail_spider() -> Spider {
    Spider::new(
        "product-detail",
        Arc::new(|response: &Response| {
            vec![Output::Item(
                Item::new()
                    .set("kind", "detail")
                    .set("title", response.css("title").get().unwrap_or_default())
                    .set("url", response.url.clone())
                    .set("html_excerpt", response.text.clone()),
            )]
        }),
    )
    .add_start_url("https://example.com/item/123")
}

pub fn register() {
    projectruntime::register_spider("product-detail", make_product_detail_spider);
}

