pub mod api_bootstrap;
pub mod ecommerce_catalog;
pub mod ecommerce_detail;
pub mod ecommerce_profile;
pub mod ecommerce_review;
pub mod infinite_scroll;
pub mod login_session;
pub mod product_detail;
pub mod search_listing;
pub mod social_feed;

pub fn register_catalog() {
    api_bootstrap::register();
    ecommerce_catalog::register();
    ecommerce_detail::register();
    ecommerce_review::register();
    infinite_scroll::register();
    login_session::register();
    product_detail::register();
    search_listing::register();
    social_feed::register();
}
