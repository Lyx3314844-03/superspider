#[derive(Clone, Debug, PartialEq, Eq)]
struct Task {
    url: &'static str,
    retry_count: i32,
}

fn reap_expired(
    tasks: &mut std::collections::BTreeMap<&'static str, (u64, Task)>,
    now: u64,
    max_retries: i32,
) -> (usize, Vec<Task>, Vec<Task>) {
    let mut reaped = 0usize;
    let mut requeued = Vec::new();
    let mut dead = Vec::new();
    let snapshot: Vec<_> = tasks.iter().map(|(k, v)| (*k, v.clone())).collect();
    for (key, (expires_at, mut task)) in snapshot {
        if expires_at > now {
            continue;
        }
        reaped += 1;
        tasks.remove(key);
        task.retry_count += 1;
        if task.retry_count > max_retries {
            dead.push(task);
        } else {
            requeued.push(task);
        }
    }
    (reaped, requeued, dead)
}

#[test]
fn rust_distributed_expired_lease_requeues_until_budget_is_exhausted() {
    let mut processing = std::collections::BTreeMap::new();
    processing.insert(
        "https://example.com",
        (
            10,
            Task {
                url: "https://example.com",
                retry_count: 0,
            },
        ),
    );

    let (reaped, requeued, dead) = reap_expired(&mut processing, 20, 2);
    assert_eq!(reaped, 1);
    assert_eq!(
        requeued,
        vec![Task {
            url: "https://example.com",
            retry_count: 1
        }]
    );
    assert!(dead.is_empty());
    assert!(processing.is_empty());
}

#[test]
fn rust_distributed_expired_lease_dead_letters_after_retry_budget() {
    let mut processing = std::collections::BTreeMap::new();
    processing.insert(
        "https://example.com",
        (
            10,
            Task {
                url: "https://example.com",
                retry_count: 2,
            },
        ),
    );

    let (reaped, requeued, dead) = reap_expired(&mut processing, 20, 2);
    assert_eq!(reaped, 1);
    assert!(requeued.is_empty());
    assert_eq!(
        dead,
        vec![Task {
            url: "https://example.com",
            retry_count: 3
        }]
    );
    assert!(processing.is_empty());
}
