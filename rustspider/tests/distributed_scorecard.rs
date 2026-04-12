#![cfg(feature = "distributed")]

use rustspider::distributed::redis_distributed::{
    CrawlTask, RedisBloomFilter, RedisDistributedQueue, RedisDistributedScheduler,
};

#[test]
fn crawl_task_round_trips_with_priority_depth_and_metadata() {
    let task = CrawlTask::new("https://example.com".to_string())
        .with_priority(10)
        .with_depth(2)
        .with_spider_name("scorecard".to_string());

    let json = task.to_json().expect("task should serialize");
    let restored = CrawlTask::from_json(&json).expect("task should deserialize");

    assert_eq!(restored.url, "https://example.com");
    assert_eq!(restored.priority, 10);
    assert_eq!(restored.depth, 2);
    assert_eq!(restored.spider_name, "scorecard");
}

#[test]
fn distributed_queue_and_scheduler_construct_with_valid_redis_url() {
    let queue = RedisDistributedQueue::new("redis://127.0.0.1:6379", "scorecard", 1000)
        .expect("queue should accept syntactically valid redis url");
    let stats = queue.get_stats();
    assert!(
        stats.is_err(),
        "without a live Redis server, stats should fail at connection time"
    );

    let scheduler = RedisDistributedScheduler::new("redis://127.0.0.1:6379", "scorecard")
        .expect("scheduler should construct with valid redis url");
    let next = scheduler.next_task();
    assert!(
        next.is_err(),
        "without a live Redis server, next_task should fail at connection time"
    );
}

#[test]
fn bloom_filter_parameters_construct_for_expected_scale() {
    let filter = RedisBloomFilter::new("redis://127.0.0.1:6379", "scorecard", 10_000, 0.01)
        .expect("bloom filter should construct");
    let count = filter.count();
    assert!(
        count.is_err(),
        "count should require a live redis connection"
    );
}
