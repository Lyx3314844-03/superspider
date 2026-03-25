use rustspider::async_runtime::{DedupQueue, PriorityQueue, Request, RequestQueue};
use rustspider::multithread::WorkerPool;
use rustspider::retry::{RetryConfig, RetryHandler, RetryStrategy};
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;
use std::time::Duration;

#[test]
fn queue_retry_and_worker_pool_remain_stable_under_repeated_load() {
    let unique_requests = 64;
    let queue = Arc::new(DedupQueue::new(Arc::new(PriorityQueue::new())));

    for idx in 0..unique_requests {
        let url = format!("https://example.com/item/{idx}");
        queue.push(Request::new(url.clone())).unwrap();
        queue.push(Request::new(url)).unwrap();
    }

    assert_eq!(queue.size(), unique_requests);

    let pool = WorkerPool::new(4, unique_requests);
    let processed = Arc::new(AtomicUsize::new(0));
    let attempts = Arc::new(AtomicUsize::new(0));

    for _ in 0..4 {
        let queue = Arc::clone(&queue);
        let processed = Arc::clone(&processed);
        let attempts = Arc::clone(&attempts);

        let submitted = pool.submit(move || {
            let retry_handler = RetryHandler::new(RetryConfig {
                max_retries: 1,
                strategy: RetryStrategy::Fixed,
                base_delay: Duration::from_millis(1),
                max_delay: Duration::from_millis(1),
                jitter_factor: 0.0,
                retry_on_status_codes: vec![],
            });

            while let Some(request) = queue.pop() {
                let mut should_fail_once = true;
                let result = retry_handler.execute_with_retry(|| {
                    attempts.fetch_add(1, Ordering::SeqCst);
                    if should_fail_once {
                        should_fail_once = false;
                        Err::<(), _>(format!("transient failure for {}", request.url))
                    } else {
                        Ok(())
                    }
                });

                assert!(result.success, "request should succeed after one retry");
                assert_eq!(result.attempts, 2);
                processed.fetch_add(1, Ordering::SeqCst);
            }
        });

        assert!(submitted);
    }

    pool.wait_all();

    assert_eq!(processed.load(Ordering::SeqCst), unique_requests);
    assert_eq!(attempts.load(Ordering::SeqCst), unique_requests * 2);
    assert_eq!(queue.size(), 0);
}
