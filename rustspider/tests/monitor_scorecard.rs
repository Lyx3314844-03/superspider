use rustspider::monitor::MonitorCenter;
use rustspider::SpiderMonitor;

#[test]
fn monitor_center_registers_and_summarizes_spiders() {
    let center = MonitorCenter::new();
    let mut monitor = center.register("scorecard");
    monitor.start();
    monitor.record_page_crawled("https://example.com", 200, 1024);
    monitor.record_item_extracted(3);
    monitor.stop();

    let summary = center.get_summary();
    assert_eq!(summary["total_spiders"], 0);

    let dashboard = monitor.get_dashboard_data();
    assert_eq!(dashboard["spider_name"], "scorecard");
    assert_eq!(dashboard["pages_crawled"], 1);
}

#[test]
fn monitor_stats_report_success_rate_fields() {
    let mut monitor = SpiderMonitor::new("stats");
    monitor.start();
    monitor.record_page_crawled("https://example.com/a", 200, 512);
    monitor.record_page_failed("https://example.com/b", "boom");

    let stats = monitor.get_stats();
    assert_eq!(stats["stats"]["pages_crawled"], 1);
    assert_eq!(stats["stats"]["pages_failed"], 1);
    assert_eq!(stats["stats"]["success_rate"], 0.5);
}
