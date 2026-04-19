use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct DiscoveredNode {
    pub address: String,
    pub source: String,
    #[serde(default)]
    pub meta: std::collections::BTreeMap<String, String>,
}

pub fn discover_nodes_from_env(env_var: &str) -> Vec<DiscoveredNode> {
    std::env::var(env_var)
        .unwrap_or_default()
        .split(',')
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .map(|address| DiscoveredNode {
            address: address.to_string(),
            source: "env".to_string(),
            meta: Default::default(),
        })
        .collect()
}

pub fn discover_nodes_from_file(
    path: &std::path::Path,
) -> Result<Vec<DiscoveredNode>, std::io::Error> {
    let content = std::fs::read_to_string(path)?;
    Ok(content
        .lines()
        .map(str::trim)
        .filter(|line| !line.is_empty() && !line.starts_with('#'))
        .map(|address| DiscoveredNode {
            address: address.to_string(),
            source: "file".to_string(),
            meta: Default::default(),
        })
        .collect())
}

pub fn discover_nodes_from_consul(
    endpoint: &str,
) -> Result<Vec<DiscoveredNode>, Box<dyn std::error::Error>> {
    let response = reqwest::blocking::get(endpoint)?;
    let payload: Vec<serde_json::Value> = response.json()?;
    Ok(payload
        .into_iter()
        .filter_map(|item| {
            Some(DiscoveredNode {
                address: format!(
                    "{}:{}",
                    item.get("Address")?.as_str()?,
                    item.get("ServicePort")?.as_u64()?
                ),
                source: "consul".to_string(),
                meta: Default::default(),
            })
        })
        .collect())
}

pub fn discover_nodes_from_etcd(
    endpoint: &str,
) -> Result<Vec<DiscoveredNode>, Box<dyn std::error::Error>> {
    let response = reqwest::blocking::get(endpoint)?;
    let payload: serde_json::Value = response.json()?;
    let nodes = payload
        .get("node")
        .and_then(|value| value.get("nodes"))
        .and_then(|value| value.as_array())
        .cloned()
        .unwrap_or_default();
    Ok(nodes
        .into_iter()
        .filter_map(|item| {
            item.get("value")
                .and_then(|value| value.as_str())
                .map(|value| DiscoveredNode {
                    address: value.to_string(),
                    source: "etcd".to_string(),
                    meta: Default::default(),
                })
        })
        .collect())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::{Read, Write};
    use std::net::TcpListener;
    use std::thread;

    #[test]
    fn env_and_file_discovery_work() {
        std::env::set_var("RUST_DISCOVERY", "node-a:9000,node-b:9001");
        let env = discover_nodes_from_env("RUST_DISCOVERY");
        assert_eq!(env.len(), 2);

        let path = std::env::temp_dir().join("rust-node-discovery.txt");
        std::fs::write(&path, "# comment\nnode-a:9000\nnode-b:9001\n").unwrap();
        let file = discover_nodes_from_file(&path).unwrap();
        assert_eq!(file.len(), 2);
        let _ = std::fs::remove_file(path);
    }

    #[test]
    fn consul_and_etcd_discovery_work() {
        let consul = start_mock_server(
            "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n[{\"Address\":\"10.0.0.2\",\"ServicePort\":9000}]",
        );
        let etcd = start_mock_server(
            "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n{\"node\":{\"nodes\":[{\"value\":\"10.0.0.4:9100\"}]}}",
        );

        let consul_nodes = discover_nodes_from_consul(&consul).unwrap();
        assert_eq!(consul_nodes[0].source, "consul");

        let etcd_nodes = discover_nodes_from_etcd(&etcd).unwrap();
        assert_eq!(etcd_nodes[0].source, "etcd");
    }

    fn start_mock_server(response: &'static str) -> String {
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let addr = listener.local_addr().unwrap();
        thread::spawn(move || {
            if let Ok((mut stream, _)) = listener.accept() {
                let mut buffer = [0_u8; 1024];
                let _ = stream.read(&mut buffer);
                let _ = stream.write_all(response.as_bytes());
            }
        });
        format!("http://{}", addr)
    }
}
