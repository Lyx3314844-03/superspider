use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;
use std::fs::File;
use std::io::{self, BufRead, BufReader};
use std::path::Path;
use std::process::Command;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct DiscoveredNode {
    pub address: String,
    pub source: String,
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    pub meta: BTreeMap<String, String>,
}

pub fn discover_nodes_from_env(env_var: &str) -> Vec<DiscoveredNode> {
    let raw = std::env::var(env_var).unwrap_or_default();
    parse_address_list(&raw, "env")
}

pub fn discover_nodes_from_file(path: impl AsRef<Path>) -> io::Result<Vec<DiscoveredNode>> {
    let file = File::open(path)?;
    let mut nodes = Vec::new();
    for line in BufReader::new(file).lines() {
        let line = line?;
        let trimmed = line.trim();
        if trimmed.is_empty() || trimmed.starts_with('#') {
            continue;
        }
        nodes.push(DiscoveredNode {
            address: trimmed.to_string(),
            source: "file".to_string(),
            meta: BTreeMap::new(),
        });
    }
    Ok(nodes)
}

pub fn discover_nodes_from_dns_srv(
    service: &str,
    proto: &str,
    name: &str,
) -> Result<Vec<DiscoveredNode>, String> {
    let query = normalize_srv_query(service, proto, name);
    let lines = dns_srv_record_lines(&query)?;
    let nodes = discover_nodes_from_dns_srv_records(&lines);
    if nodes.is_empty() {
        return Err(format!("no dns-srv records found for {query}"));
    }
    Ok(nodes)
}

pub fn discover_nodes_from_dns_srv_records(records: &[String]) -> Vec<DiscoveredNode> {
    let mut nodes = Vec::new();
    let mut pending_priority: Option<String> = None;
    let mut pending_weight: Option<String> = None;
    let mut pending_port: Option<String> = None;

    for record in records {
        let trimmed = record.trim();
        if trimmed.is_empty() {
            continue;
        }
        if let Some(node) = parse_inline_srv_record(trimmed) {
            nodes.push(node);
            continue;
        }

        let lower = trimmed.to_ascii_lowercase();
        if let Some(value) = parse_assignment(trimmed, &lower, "priority") {
            pending_priority = Some(value);
            continue;
        }
        if let Some(value) = parse_assignment(trimmed, &lower, "weight") {
            pending_weight = Some(value);
            continue;
        }
        if let Some(value) = parse_assignment(trimmed, &lower, "port") {
            pending_port = Some(value);
            continue;
        }
        if let Some(hostname) = parse_hostname_assignment(trimmed, &lower) {
            if let (Some(priority), Some(weight), Some(port)) = (
                pending_priority.take(),
                pending_weight.take(),
                pending_port.take(),
            ) {
                nodes.push(build_srv_node(&priority, &weight, &port, &hostname));
            }
        }
    }

    nodes
}

fn parse_address_list(raw: &str, source: &str) -> Vec<DiscoveredNode> {
    raw.split(',')
        .filter_map(|part| {
            let address = part.trim();
            if address.is_empty() {
                None
            } else {
                Some(DiscoveredNode {
                    address: address.to_string(),
                    source: source.to_string(),
                    meta: BTreeMap::new(),
                })
            }
        })
        .collect()
}

fn normalize_srv_query(service: &str, proto: &str, name: &str) -> String {
    let service = service.trim().trim_start_matches('_');
    let proto = proto.trim().trim_start_matches('_');
    let name = name.trim().trim_end_matches('.');
    format!("_{service}._{proto}.{name}")
}

fn dns_srv_record_lines(query: &str) -> Result<Vec<String>, String> {
    let command_candidates = [
        ("nslookup", vec!["-type=SRV".to_string(), query.to_string()]),
        (
            "dig",
            vec!["+short".to_string(), "SRV".to_string(), query.to_string()],
        ),
    ];
    for (program, args) in command_candidates {
        match Command::new(program).args(&args).output() {
            Ok(output) if output.status.success() => {
                let stdout = String::from_utf8_lossy(&output.stdout);
                let lines: Vec<String> = stdout
                    .lines()
                    .map(str::trim)
                    .filter(|line| !line.is_empty())
                    .map(ToOwned::to_owned)
                    .collect();
                if !lines.is_empty() {
                    return Ok(lines);
                }
            }
            Ok(_) | Err(_) => {}
        }
    }
    Err(format!(
        "dns-srv lookup failed for {query}; neither nslookup nor dig produced records"
    ))
}

fn parse_inline_srv_record(line: &str) -> Option<DiscoveredNode> {
    let candidate = line
        .split_once('=')
        .map(|(_, rhs)| rhs.trim())
        .unwrap_or(line)
        .trim();
    let parts: Vec<&str> = candidate.split_whitespace().collect();
    if parts.len() < 4 || !parts[0].chars().all(|ch| ch.is_ascii_digit()) {
        return None;
    }
    if !parts[1].chars().all(|ch| ch.is_ascii_digit())
        || !parts[2].chars().all(|ch| ch.is_ascii_digit())
    {
        return None;
    }
    Some(build_srv_node(parts[0], parts[1], parts[2], parts[3]))
}

fn parse_assignment(line: &str, lower: &str, key: &str) -> Option<String> {
    if !lower.starts_with(key) {
        return None;
    }
    line.split_once('=').map(|(_, rhs)| rhs.trim().to_string())
}

fn parse_hostname_assignment(line: &str, lower: &str) -> Option<String> {
    if !lower.contains("hostname") {
        return None;
    }
    line.split_once('=').map(|(_, rhs)| rhs.trim().to_string())
}

fn build_srv_node(priority: &str, weight: &str, port: &str, hostname: &str) -> DiscoveredNode {
    let target = hostname.trim_end_matches('.').to_string();
    let mut meta = BTreeMap::new();
    meta.insert("priority".to_string(), priority.to_string());
    meta.insert("weight".to_string(), weight.to_string());
    DiscoveredNode {
        address: format!("{target}:{port}"),
        source: "dns-srv".to_string(),
        meta,
    }
}
