use std::net::{IpAddr, ToSocketAddrs};

pub fn validate_safe_url(raw_url: &str) -> Result<String, String> {
    let parsed = url::Url::parse(raw_url.trim()).map_err(|err| format!("invalid url: {err}"))?;
    match parsed.scheme() {
        "http" | "https" => {}
        other => return Err(format!("unsupported url scheme: {other}")),
    }
    let host = parsed
        .host_str()
        .ok_or_else(|| "missing host".to_string())?;
    let lower = host.to_ascii_lowercase();
    if matches!(lower.as_str(), "localhost" | "metadata.google.internal")
        || host == "169.254.169.254"
        || host == "168.63.129.16"
    {
        return Err(format!("blocked by SSRF protection: {raw_url}"));
    }
    let port = parsed.port_or_known_default().unwrap_or(80);
    let addrs = (host, port)
        .to_socket_addrs()
        .map_err(|err| format!("dns resolution failed: {err}"))?;
    for addr in addrs {
        if is_blocked_ip(addr.ip()) {
            return Err(format!("blocked by SSRF protection: {raw_url}"));
        }
    }
    Ok(parsed.to_string())
}

fn is_blocked_ip(ip: IpAddr) -> bool {
    match ip {
        IpAddr::V4(ipv4) => {
            ipv4.is_loopback()
                || ipv4.is_private()
                || ipv4.is_link_local()
                || ipv4.is_multicast()
                || ipv4.octets()[0] == 0
        }
        IpAddr::V6(ipv6) => ipv6.is_loopback() || ipv6.is_unspecified() || ipv6.is_multicast(),
    }
}
