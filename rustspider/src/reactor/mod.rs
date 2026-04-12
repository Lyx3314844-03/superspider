use std::collections::HashMap;
use std::time::{Duration, Instant};

use anyhow::Result;
use regex::Regex;

#[derive(Debug, Clone, Default)]
pub struct TargetSpec {
    pub url: String,
    pub method: String,
    pub headers: HashMap<String, String>,
    pub inline_body: Option<String>,
    pub cookies: HashMap<String, String>,
    pub proxy: Option<String>,
    pub allowed_domains: Vec<String>,
}

#[derive(Debug, Clone)]
pub struct TransportPolicy {
    pub timeout: Duration,
    pub retries: u32,
    pub user_agent: String,
    pub request_delay: Option<Duration>,
    pub respect_robots_txt: bool,
}

impl Default for TransportPolicy {
    fn default() -> Self {
        Self {
            timeout: Duration::from_secs(30),
            retries: 2,
            user_agent: "rustspider-x1".to_string(),
            request_delay: None,
            respect_robots_txt: false,
        }
    }
}

#[derive(Debug, Clone, Default)]
pub struct ParsePlan {
    pub capture_body: bool,
}

#[derive(Debug, Clone, Default)]
pub struct MediaPlan {
    pub detect_media: bool,
}

#[derive(Debug, Clone, Default)]
pub struct BudgetSpec {
    pub max_bytes: usize,
    pub max_wall_time_ms: u64,
}

#[derive(Debug, Clone, Default)]
pub struct NativeCrawlPlan {
    pub target: TargetSpec,
    pub transport: TransportPolicy,
    pub parse: ParsePlan,
    pub media: MediaPlan,
    pub budget: BudgetSpec,
}

#[derive(Debug, Clone, Default)]
pub struct KernelResult {
    pub url: String,
    pub status_code: u16,
    pub body: String,
    pub detected_media: Vec<String>,
}

pub trait KernelExecutor {
    fn execute(&self, plan: NativeCrawlPlan) -> Result<KernelResult>;
}

#[derive(Debug, Default)]
pub struct NativeReactor;

impl NativeReactor {
    pub fn new() -> Self {
        Self
    }
}

impl KernelExecutor for NativeReactor {
    fn execute(&self, plan: NativeCrawlPlan) -> Result<KernelResult> {
        let started_at = Instant::now();
        if let Some(body) = plan.target.inline_body.clone() {
            if let Some(delay) = plan.transport.request_delay {
                std::thread::sleep(delay);
            }
            if plan.budget.max_bytes > 0 && body.len() > plan.budget.max_bytes {
                anyhow::bail!(
                    "response body exceeded budget: {} bytes > {} bytes",
                    body.len(),
                    plan.budget.max_bytes
                );
            }
            enforce_wall_time_budget(started_at.elapsed(), &plan.budget)?;
            let detected_media = if plan.media.detect_media && body.contains(".m3u8") {
                vec!["hls".to_string()]
            } else {
                Vec::new()
            };

            return Ok(KernelResult {
                url: plan.target.url,
                status_code: 200,
                body,
                detected_media,
            });
        }

        validate_allowed_domain(&plan.target)?;
        if let Some(delay) = validate_robots_policy(&plan)? {
            std::thread::sleep(delay);
        }

        let mut last_error: Option<anyhow::Error> = None;
        let attempts = plan.transport.retries.saturating_add(1).max(1);
        for attempt in 0..attempts {
            if let Some(delay) = plan.transport.request_delay {
                std::thread::sleep(delay);
            }
            match execute_network_request(&plan) {
                Ok((status, body)) => {
                    let detected_media = if plan.media.detect_media && body.contains(".m3u8") {
                        vec!["hls".to_string()]
                    } else {
                        Vec::new()
                    };
                    enforce_wall_time_budget(started_at.elapsed(), &plan.budget)?;

                    return Ok(KernelResult {
                        url: plan.target.url,
                        status_code: status,
                        body,
                        detected_media,
                    });
                }
                Err(err) => {
                    enforce_wall_time_budget(started_at.elapsed(), &plan.budget)?;
                    last_error = Some(err);
                    if attempt + 1 < attempts {
                        let backoff_ms = 300_u64 * (1_u64 << (attempt.min(5)));
                        std::thread::sleep(Duration::from_millis(backoff_ms));
                    }
                }
            }
        }

        Err(last_error.unwrap_or_else(|| anyhow::anyhow!("request failed")))
    }
}

fn validate_allowed_domain(target: &TargetSpec) -> Result<()> {
    if target.allowed_domains.is_empty() {
        return Ok(());
    }
    let parsed = url::Url::parse(&target.url)?;
    let host = parsed
        .host_str()
        .ok_or_else(|| anyhow::anyhow!("target url is missing host"))?;
    let host_matches = target
        .allowed_domains
        .iter()
        .any(|allowed| !allowed.trim().is_empty() && host.ends_with(allowed.trim()));
    if host_matches {
        Ok(())
    } else {
        anyhow::bail!("target host {host} is outside allowed_domains")
    }
}

fn execute_network_request(plan: &NativeCrawlPlan) -> Result<(u16, String)> {
    let mut builder = reqwest::blocking::Client::builder()
        .timeout(plan.transport.timeout)
        .user_agent(plan.transport.user_agent.clone());
    if let Some(proxy) = plan
        .target
        .proxy
        .as_ref()
        .filter(|value| !value.trim().is_empty())
    {
        builder = builder.proxy(reqwest::Proxy::all(proxy)?);
    }
    let client = builder.build()?;

    let method =
        reqwest::Method::from_bytes(plan.target.method.as_bytes()).unwrap_or(reqwest::Method::GET);
    let mut request = client.request(method, &plan.target.url);
    for (name, value) in &plan.target.headers {
        request = request.header(name, value);
    }
    if !plan.target.cookies.is_empty() {
        let cookie_header = plan
            .target
            .cookies
            .iter()
            .map(|(name, value)| format!("{name}={value}"))
            .collect::<Vec<_>>()
            .join("; ");
        request = request.header(reqwest::header::COOKIE, cookie_header);
    }
    let response = request.send()?;
    let status = response.status().as_u16();
    let bytes = response.bytes()?;
    if plan.budget.max_bytes > 0 && bytes.len() > plan.budget.max_bytes {
        anyhow::bail!(
            "response body exceeded budget: {} bytes > {} bytes",
            bytes.len(),
            plan.budget.max_bytes
        );
    }
    Ok((status, String::from_utf8_lossy(&bytes).to_string()))
}

fn validate_robots_policy(plan: &NativeCrawlPlan) -> Result<Option<Duration>> {
    if !plan.transport.respect_robots_txt {
        return Ok(None);
    }
    let parsed = url::Url::parse(&plan.target.url)?;
    let host = parsed
        .host_str()
        .ok_or_else(|| anyhow::anyhow!("target url is missing host"))?;
    let robots_url = format!("{}://{host}/robots.txt", parsed.scheme());
    let client = reqwest::blocking::Client::builder()
        .timeout(plan.transport.timeout)
        .user_agent(plan.transport.user_agent.clone())
        .build()?;
    let response = match client.get(robots_url).send() {
        Ok(resp) => resp,
        Err(_) => return Ok(None),
    };
    if !response.status().is_success() {
        return Ok(None);
    }
    let content = response.text().unwrap_or_default();
    let parser = RobotsParser::parse(&content);
    let path = if parsed.path().is_empty() {
        "/"
    } else {
        parsed.path()
    };
    if !parser.is_allowed(path, &plan.transport.user_agent) {
        anyhow::bail!("robots.txt forbids {}", plan.target.url);
    }
    Ok(parser
        .crawl_delay(&plan.transport.user_agent)
        .map(Duration::from_secs_f64))
}

#[derive(Debug, Default)]
struct RobotsParser {
    rules: HashMap<String, RobotsRuleSet>,
}

#[derive(Debug, Default)]
struct RobotsRuleSet {
    allow: Vec<String>,
    disallow: Vec<String>,
    crawl_delay: Option<f64>,
}

impl RobotsParser {
    fn parse(content: &str) -> Self {
        let mut parser = Self::default();
        let mut current_agents: Vec<String> = Vec::new();
        let mut group_has_directive = false;
        for line in content.lines() {
            let raw = strip_robots_comment(line).trim();
            if raw.is_empty() {
                continue;
            }
            let lower = raw.to_lowercase();
            if let Some(value) = lower.strip_prefix("user-agent:") {
                if group_has_directive {
                    current_agents.clear();
                    group_has_directive = false;
                }
                let ua = value.trim().to_string();
                if ua.is_empty() {
                    continue;
                }
                parser.rules.entry(ua.clone()).or_default();
                current_agents.push(ua);
                continue;
            }
            if let Some(value) = lower.strip_prefix("allow:") {
                let path = value.trim().to_string();
                for ua in &current_agents {
                    parser
                        .rules
                        .entry(ua.clone())
                        .or_default()
                        .allow
                        .push(path.clone());
                }
                group_has_directive = true;
                continue;
            }
            if let Some(value) = lower.strip_prefix("disallow:") {
                let path = value.trim().to_string();
                for ua in &current_agents {
                    parser
                        .rules
                        .entry(ua.clone())
                        .or_default()
                        .disallow
                        .push(path.clone());
                }
                group_has_directive = true;
                continue;
            }
            if let Some(value) = lower.strip_prefix("crawl-delay:") {
                if let Ok(delay) = value.trim().parse::<f64>() {
                    if delay >= 0.0 {
                        for ua in &current_agents {
                            parser.rules.entry(ua.clone()).or_default().crawl_delay = Some(delay);
                        }
                        group_has_directive = true;
                    }
                }
            }
        }
        parser
    }

    fn rules_for(&self, user_agent: &str) -> Option<&RobotsRuleSet> {
        let ua = user_agent.trim().to_lowercase();
        if let Some(exact) = self.rules.get(&ua) {
            return Some(exact);
        }
        self.rules.get("*")
    }

    fn is_allowed(&self, path: &str, user_agent: &str) -> bool {
        let Some(rules) = self.rules_for(user_agent) else {
            return true;
        };
        let mut best_allow = -1_i32;
        let mut best_disallow = -1_i32;
        for rule in &rules.allow {
            if matches_robots_rule(path, rule) {
                best_allow = best_allow.max(rule.len() as i32);
            }
        }
        for rule in &rules.disallow {
            if matches_robots_rule(path, rule) {
                best_disallow = best_disallow.max(rule.len() as i32);
            }
        }
        if best_allow < 0 && best_disallow < 0 {
            return true;
        }
        best_allow >= best_disallow
    }

    fn crawl_delay(&self, user_agent: &str) -> Option<f64> {
        self.rules_for(user_agent)
            .and_then(|rules| rules.crawl_delay)
    }
}

fn strip_robots_comment(line: &str) -> &str {
    match line.find('#') {
        Some(idx) => &line[..idx],
        None => line,
    }
}

fn matches_robots_rule(path: &str, rule: &str) -> bool {
    if rule.is_empty() {
        return false;
    }
    if !rule.contains('*') && !rule.contains('$') {
        return path.starts_with(rule);
    }
    let mut pattern = regex::escape(rule);
    pattern = pattern.replace("\\*", ".*");
    if pattern.ends_with("\\$") {
        pattern = format!("{}$", pattern.trim_end_matches("\\$"));
    }
    match Regex::new(&format!("^{pattern}")) {
        Ok(re) => re.is_match(path),
        Err(_) => path.starts_with(rule),
    }
}

fn enforce_wall_time_budget(elapsed: Duration, budget: &BudgetSpec) -> Result<()> {
    if budget.max_wall_time_ms > 0 && elapsed.as_millis() > u128::from(budget.max_wall_time_ms) {
        anyhow::bail!(
            "job exceeded budget.wall_time_ms: used={} limit={}",
            elapsed.as_millis(),
            budget.max_wall_time_ms
        );
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn native_reactor_executes_inline_plan() {
        let reactor = NativeReactor::new();
        let plan = NativeCrawlPlan {
            target: TargetSpec {
                url: "inline://page".to_string(),
                method: "GET".to_string(),
                headers: HashMap::new(),
                inline_body: Some("<html>playlist.m3u8</html>".to_string()),
                cookies: HashMap::new(),
                proxy: None,
                allowed_domains: Vec::new(),
            },
            media: MediaPlan { detect_media: true },
            ..Default::default()
        };

        let result = reactor.execute(plan).expect("inline execute");
        assert_eq!(result.status_code, 200);
        assert_eq!(result.detected_media, vec!["hls".to_string()]);
    }

    #[test]
    fn robots_parser_blocks_disallowed_path() {
        let parser = RobotsParser::parse("User-agent: *\nDisallow: /private\n");
        assert!(!parser.is_allowed("/private/report", "rustspider-x1"));
        assert!(parser.is_allowed("/public/report", "rustspider-x1"));
    }
}
