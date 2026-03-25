//! rustspider 基准测试
//! 
//! 运行：cargo bench --all

#![feature(test)]
extern crate test;

use test::Bencher;
use rustspider::spider::{SpiderConfig, SpiderEngine};
use rustspider::performance::{RateLimiter, CircuitBreaker, ContentFingerprinter};
use rustspider::parser::HTMLParser;

/// 爬虫引擎基准测试
#[bench]
fn bench_spider_engine_creation(b: &mut Bencher) {
    b.iter(|| {
        let config = SpiderConfig::default();
        let _engine = SpiderEngine::new(config);
    });
}

#[bench]
fn bench_spider_add_url(b: &mut Bencher) {
    let config = SpiderConfig::default();
    let mut engine = SpiderEngine::new(config);
    
    b.iter(|| {
        engine.add_url("https://example.com");
    });
}

/// 速率限制器基准测试
#[bench]
fn bench_rate_limiter_wait(b: &mut Bencher) {
    let limiter = RateLimiter::new(10000, 1); // 高频率
    
    b.iter(|| {
        limiter.wait();
    });
}

/// 熔断器基准测试
#[bench]
fn bench_circuit_breaker_allow(b: &mut Bencher) {
    let cb = CircuitBreaker::new(1000, 100, 60);
    
    b.iter(|| {
        cb.allow();
        cb.record_success();
    });
}

#[bench]
fn bench_circuit_breaker_failure(b: &mut Bencher) {
    let cb = CircuitBreaker::new(1000, 100, 60);
    
    b.iter(|| {
        cb.allow();
        cb.record_failure();
    });
}

/// 内容指纹基准测试
#[bench]
fn bench_content_fingerprint(b: &mut Bencher) {
    let fingerprinter = ContentFingerprinter::new();
    let content = "This is a test content for fingerprinting. ".repeat(100);
    
    b.iter(|| {
        fingerprinter.is_duplicate(&content);
    });
}

/// HTML 解析器基准测试
#[bench]
fn bench_html_parser_title(b: &mut Bencher) {
    let html = r#"
        <!DOCTYPE html>
        <html>
        <head><title>Test Page Title</title></head>
        <body>
            <h1>Hello World</h1>
            <p>Some content here</p>
        </body>
        </html>
    "#;
    
    b.iter(|| {
        let parser = HTMLParser::new(html);
        let _title = parser.title();
    });
}

#[bench]
fn bench_html_parser_css(b: &mut Bencher) {
    let html = r#"
        <!DOCTYPE html>
        <html>
        <body>
            <div class="content">
                <h1>Title</h1>
                <p>Paragraph 1</p>
                <p>Paragraph 2</p>
            </div>
        </body>
        </html>
    "#;
    
    b.iter(|| {
        let parser = HTMLParser::new(html);
        let _elements = parser.css(".content");
    });
}

#[bench]
fn bench_html_parser_links(b: &mut Bencher) {
    let html = r#"
        <!DOCTYPE html>
        <html>
        <body>
            <a href="/link1">Link 1</a>
            <a href="/link2">Link 2</a>
            <a href="/link3">Link 3</a>
            <a href="/link4">Link 4</a>
            <a href="/link5">Link 5</a>
        </body>
        </html>
    "#;
    
    b.iter(|| {
        let parser = HTMLParser::new(html);
        let _links = parser.links();
    });
}

/// 队列操作基准测试
#[bench]
fn bench_queue_push_pop(b: &mut Bencher) {
    use rustspider::queue::PersistentPriorityQueue;
    
    let queue = PersistentPriorityQueue::new("bench_queue");
    
    b.iter(|| {
        let item = rustspider::queue::QueueItem {
            id: "test".to_string(),
            priority: 1,
            ..Default::default()
        };
        queue.push(&item).unwrap();
        let _ = queue.pop().unwrap();
    });
}

/// Cookie 操作基准测试
#[bench]
fn bench_cookie_jar(b: &mut Bencher) {
    use rustspider::cookie::{Cookie, CookieJar};
    
    b.iter(|| {
        let mut jar = CookieJar::new();
        for i in 0..100 {
            jar.add(Cookie::new(&format!("cookie_{}", i), &format!("value_{}", i)));
        }
        for i in 0..100 {
            let _ = jar.get(&format!("cookie_{}", i));
        }
    });
}

/// 内存分配基准测试
#[bench]
fn bench_memory_allocation(b: &mut Bencher) {
    b.iter(|| {
        let _data = vec![0u8; 1024]; // 1KB
    });
}

/// 字符串操作基准测试
#[bench]
fn bench_string_operations(b: &mut Bencher) {
    let base = "test_string_";
    
    b.iter(|| {
        let mut s = String::new();
        for i in 0..100 {
            s.push_str(base);
            s.push_str(&i.to_string());
        }
    });
}

/// 哈希计算基准测试
#[bench]
fn bench_hash_calculation(b: &mut Bencher) {
    use std::collections::hash_map::DefaultHasher;
    use std::hash::{Hash, Hasher};
    
    let data = "test data for hashing".repeat(100);
    
    b.iter(|| {
        let mut hasher = DefaultHasher::new();
        data.hash(&mut hasher);
        let _hash = hasher.finish();
    });
}
