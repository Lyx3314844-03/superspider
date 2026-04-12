// rustspider 增强版使用示例

use rustspider::{
    AdaptiveRateLimiter, CircuitBreaker, ContentFingerprinter, DynamicWait, RateLimiter,
    ScrollLoader, SpiderBuilder,
};
use std::sync::atomic::{AtomicI64, AtomicUsize, Ordering};
use std::sync::Arc;

fn main() {
    println!("rustspider 增强版示例");

    basic_spider();
    rate_limited_spider();
    circuit_breaker_spider();
    adaptive_spider();
    dedup_spider();
    dynamic_wait_example();
    scroll_loader_example();
}

fn basic_spider() {
    println!("\n=== 基础爬虫示例 ===");

    let spider = SpiderBuilder::new()
        .name("BasicSpider")
        .concurrency(3)
        .max_requests(20)
        .build()
        .expect("failed to build basic spider");

    println!("已创建爬虫：{}", spider.get_stats().name);
}

fn rate_limited_spider() {
    println!("\n=== 速率限制爬虫示例 ===");

    let rate_limiter = RateLimiter::new(10, 1);
    rate_limiter.wait();

    let spider = SpiderBuilder::new()
        .name("RateLimitedSpider")
        .concurrency(5)
        .build()
        .expect("failed to build rate-limited spider");

    println!("已创建带速率限制策略的爬虫：{}", spider.get_stats().name);
}

fn circuit_breaker_spider() {
    println!("\n=== 熔断器爬虫示例 ===");

    let circuit_breaker = Arc::new(CircuitBreaker::new(3, 2, 60));
    println!("初始状态：{:?}", circuit_breaker.state());

    for _ in 0..3 {
        circuit_breaker.record_failure();
    }

    println!("是否允许请求：{}", circuit_breaker.allow());
    println!("当前状态：{:?}", circuit_breaker.state());
}

fn adaptive_spider() {
    println!("\n=== 自适应速率限制示例 ===");

    let rate_limiter = AdaptiveRateLimiter::new(1.0, 0.1, 60.0, 2.0);

    for url in [
        "https://www.example.com/page1",
        "https://www.example.com/page2",
    ] {
        rate_limiter.wait(url);
        rate_limiter.adjust(url, 1.5, 200);
        println!("访问：{}", url);
    }
}

fn dedup_spider() {
    println!("\n=== 内容去重示例 ===");

    let fingerprinter = ContentFingerprinter::new();

    for content in ["这是内容 1", "这是内容 2", "这是内容 1", "这是内容 3"] {
        if fingerprinter.is_duplicate(content) {
            println!("重复内容：{}", content);
        } else {
            println!("新内容：{}", content);
        }
    }
}

fn dynamic_wait_example() {
    println!("\n=== 动态等待示例 ===");

    let wait = DynamicWait::new(1, 10);
    let mut counter = 0;
    let result = wait.wait_for(|| {
        counter += 1;
        counter >= 3
    });

    println!("等待结果：{}, 计数：{}", result, counter);
}

fn scroll_loader_example() {
    println!("\n=== 滚动加载示例 ===");

    let height = Arc::new(AtomicI64::new(1000));
    let scroll_count = Arc::new(AtomicUsize::new(0));

    let height_for_scroll = Arc::clone(&height);
    let scroll_count_for_scroll = Arc::clone(&scroll_count);
    let height_for_read = Arc::clone(&height);

    let mut loader = ScrollLoader::new(
        move || {
            let current = scroll_count_for_scroll.fetch_add(1, Ordering::SeqCst) + 1;
            println!("滚动 {}", current);
            if current < 5 {
                height_for_scroll.fetch_add(500, Ordering::SeqCst);
            }
        },
        move || height_for_read.load(Ordering::SeqCst),
    );

    let total = loader.scroll_to_bottom(1, 10);
    println!("总滚动次数：{}", total);
}
