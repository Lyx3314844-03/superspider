#![cfg(feature = "distributed")]

use rustspider::distributed::redis_distributed::{CrawlTask, RedisDistributedQueue};
use std::time::{SystemTime, UNIX_EPOCH};

fn redis_available() -> bool {
    redis::Client::open("redis://127.0.0.1:6379")
        .ok()
        .and_then(|client| client.get_connection().ok())
        .is_some()
}

fn clear_keys() {
    if let Ok(client) = redis::Client::open("redis://127.0.0.1:6379") {
        if let Ok(mut conn) = client.get_connection() {
            let _: redis::RedisResult<()> = redis::cmd("DEL")
                .arg("spider:shared:queue")
                .arg("queue:integration:pending")
                .arg("queue:integration:processing")
                .arg("queue:integration:failed")
                .arg("spider:shared:visited")
                .query(&mut conn);
        }
    }
}

fn now_secs() -> f64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("clock")
        .as_secs_f64()
}

#[test]
fn rust_redis_queue_leases_and_dead_letters_against_real_redis() {
    if !redis_available() {
        return;
    }
    clear_keys();

    let queue =
        RedisDistributedQueue::new("redis://127.0.0.1:6379", "integration", 1000).expect("queue");
    let task = CrawlTask::new("https://example.com/integration".to_string()).with_priority(10);
    assert!(queue.push(&task).expect("push"));

    let leased = queue.lease("worker-1", 1).expect("lease");
    assert!(leased.is_some());
    assert!(queue
        .heartbeat("https://example.com/integration", 10)
        .expect("heartbeat"));
    let reaped = queue
        .reap_expired_leases(now_secs() + 20.0, 0)
        .expect("reap");
    assert_eq!(reaped, 1);
    assert_eq!(queue.failed_count().expect("failed count"), 1);

    clear_keys();
}
