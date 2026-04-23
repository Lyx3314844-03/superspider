use std::sync::Arc;

use rustspider::scrapy::project as projectruntime;
use rustspider::scrapy::{Item, Output, Response, Spider};

pub fn make_login_session_spider() -> Spider {
    Spider::new(
        "login-session",
        Arc::new(|response: &Response| {
            vec![Output::Item(
                Item::new()
                    .set("kind", "login_session")
                    .set("title", response.css("title").get().unwrap_or_default())
                    .set("url", response.url.clone()),
            )]
        }),
    )
    .add_start_url("https://example.com/login")
    .with_start_meta("runner", "browser")
}

pub fn register() {
    projectruntime::register_spider("login-session", make_login_session_spider);
}

