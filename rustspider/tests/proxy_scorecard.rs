use rustspider::{Proxy, ProxyPool};

#[test]
fn proxy_pool_formats_authenticated_proxy_urls() {
    let mut proxy = Proxy::new("127.0.0.1", 8080);
    proxy.username = Some("user".to_string());
    proxy.password = Some("pass".to_string());

    assert_eq!(proxy.url(), "http://user:pass@127.0.0.1:8080");
}

#[test]
fn proxy_pool_disables_proxy_after_repeated_failures() {
    let pool = ProxyPool::new("https://example.com", 1000);
    let proxy = Proxy::new("10.0.0.1", 8080);
    assert!(pool.add_proxy(proxy.clone()));

    for _ in 0..10 {
        pool.record_failure(&proxy);
    }

    assert_eq!(pool.available_count(), 0);
}
