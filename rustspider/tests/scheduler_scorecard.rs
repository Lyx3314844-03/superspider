use rustspider::exporter::{Scheduler, SpiderTask};

#[test]
fn scheduler_adds_lists_and_removes_tasks() {
    let mut scheduler = Scheduler::new();
    scheduler.add_task(SpiderTask {
        id: "task-1".to_string(),
        name: "crawl".to_string(),
        url: "https://example.com".to_string(),
        engine: "rust".to_string(),
        interval: 60,
        enabled: true,
        run_count: 0,
    });

    assert_eq!(scheduler.list_tasks().len(), 1);
    assert_eq!(scheduler.list_tasks()[0].name, "crawl");

    scheduler.remove_task("task-1");
    assert!(scheduler.list_tasks().is_empty());
}
