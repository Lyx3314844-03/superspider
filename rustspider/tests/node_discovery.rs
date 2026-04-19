use rustspider::{
    discover_nodes_from_dns_srv_records, discover_nodes_from_env, discover_nodes_from_file,
};

#[test]
fn discovers_nodes_from_env() {
    std::env::set_var("RUSTSPIDER_CLUSTER_PEERS", "node-a:9000, node-b:9001");
    let nodes = discover_nodes_from_env("RUSTSPIDER_CLUSTER_PEERS");
    std::env::remove_var("RUSTSPIDER_CLUSTER_PEERS");

    assert_eq!(nodes.len(), 2);
    assert_eq!(nodes[0].address, "node-a:9000");
    assert_eq!(nodes[0].source, "env");
}

#[test]
fn discovers_nodes_from_file() {
    let path = std::env::temp_dir().join(format!("rustspider-nodes-{}.txt", std::process::id()));
    std::fs::write(&path, "# comment\nnode-a:9000\n\nnode-b:9001\n")
        .expect("fixture should be written");

    let nodes = discover_nodes_from_file(&path).expect("file discovery should succeed");
    let _ = std::fs::remove_file(&path);

    assert_eq!(nodes.len(), 2);
    assert_eq!(nodes[1].source, "file");
}

#[test]
fn parses_inline_and_nslookup_style_srv_records() {
    let nodes = discover_nodes_from_dns_srv_records(&[
        "10 5 8080 crawler-a.internal.".to_string(),
        "priority = 20".to_string(),
        "weight = 10".to_string(),
        "port = 9090".to_string(),
        "svr hostname = crawler-b.internal.".to_string(),
    ]);

    assert_eq!(nodes.len(), 2);
    assert_eq!(nodes[0].address, "crawler-a.internal:8080");
    assert_eq!(nodes[1].address, "crawler-b.internal:9090");
    assert_eq!(
        nodes[1].meta.get("priority").map(String::as_str),
        Some("20")
    );
}
