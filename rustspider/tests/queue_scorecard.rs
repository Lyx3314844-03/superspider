use rustspider::{PersistentPriorityQueue, QueueItem};

#[test]
fn persistent_queue_orders_by_priority_and_roundtrips_payload() {
    let queue = PersistentPriorityQueue::in_memory(8).expect("queue");
    let high = QueueItem::new("https://example.com/high".to_string())
        .with_priority(10)
        .with_data(vec![1, 2, 3]);
    let low = QueueItem::new("https://example.com/low".to_string()).with_priority(1);

    assert!(queue.put(low).expect("put low"));
    assert!(queue.put(high).expect("put high"));

    let item = queue.get().expect("get").expect("queue item");
    assert_eq!(item.url, "https://example.com/high");
    assert_eq!(item.request_data, Some(vec![1, 2, 3]));
}
