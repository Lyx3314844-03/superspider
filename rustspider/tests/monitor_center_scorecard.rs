use rustspider::monitor::MonitorCenter;

#[test]
fn monitor_center_registers_monitors_and_exposes_summary_shape() {
    let center = MonitorCenter::new();
    let monitor = center.register("rust-scorecard");

    assert_eq!(monitor.stats.spider_name, "rust-scorecard");
    assert_eq!(center.get_summary()["total_spiders"], 0);
}
