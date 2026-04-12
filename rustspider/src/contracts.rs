use std::collections::{BTreeMap, HashMap, HashSet};
use std::fs;
use std::path::PathBuf;
use std::sync::{Arc, Mutex};
use std::time::{Duration, SystemTime, UNIX_EPOCH};

use anyhow::{anyhow, Result};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};

use crate::artifact::{ArtifactRecord, ArtifactStore};
use crate::checkpoint::CheckpointManager;
use crate::models::Request;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct RequestFingerprint {
    pub algorithm: String,
    pub value: String,
}

impl RequestFingerprint {
    pub fn from_request(request: &Request) -> Self {
        let payload = serde_json::json!({
            "url": request.url,
            "method": request.method.to_uppercase(),
            "headers": request.headers,
            "body": request.body,
            "meta": request.meta,
            "priority": request.priority,
        });
        let digest = Sha256::digest(payload.to_string().as_bytes());
        Self {
            algorithm: "md5".to_string(),
            value: format!("{:x}", digest),
        }
    }
}

#[derive(Debug, Clone, Default)]
pub struct FileArtifactStore {
    root: PathBuf,
    artifacts: Arc<Mutex<Vec<ArtifactRecord>>>,
}

impl FileArtifactStore {
    pub fn new(root: impl Into<PathBuf>) -> Self {
        let root = root.into();
        let _ = fs::create_dir_all(&root);
        Self {
            root,
            artifacts: Arc::new(Mutex::new(Vec::new())),
        }
    }

    pub fn put_bytes(
        &self,
        name: &str,
        kind: &str,
        data: &[u8],
        metadata: HashMap<String, String>,
    ) -> Result<ArtifactRecord> {
        let mut path = self.root.join(name.replace(['/', '\\'], "_"));
        if path.extension().is_none() {
            let suffix = match kind {
                "html" => ".html",
                "json" | "trace" => ".json",
                "text" => ".txt",
                "screenshot" => ".png",
                _ => "",
            };
            path = PathBuf::from(format!("{}{}", path.display(), suffix));
        }
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)?;
        }
        fs::write(&path, data)?;
        let record = ArtifactRecord {
            name: name.to_string(),
            kind: kind.to_string(),
            uri: None,
            path: Some(path.display().to_string()),
            size: data.len() as u64,
            metadata,
        };
        let _ = self.put(record.clone())?;
        Ok(record)
    }
}

impl ArtifactStore for FileArtifactStore {
    fn put(&self, artifact: ArtifactRecord) -> Result<String> {
        let id = format!("artifact-{}", artifact.name);
        self.artifacts.lock().unwrap().push(artifact);
        Ok(id)
    }

    fn list(&self) -> Result<Vec<ArtifactRecord>> {
        Ok(self.artifacts.lock().unwrap().clone())
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RuntimeSession {
    pub session_id: String,
    pub created_at_unix: u64,
    pub last_used_at_unix: u64,
    pub headers: HashMap<String, String>,
    pub cookies: HashMap<String, String>,
    pub fingerprint_profile: String,
    pub proxy_id: Option<String>,
    pub lease_count: u64,
    pub failure_count: u64,
    pub in_use: bool,
}

#[derive(Debug, Default)]
pub struct SessionPool {
    max_sessions: usize,
    sessions: HashMap<String, RuntimeSession>,
}

impl SessionPool {
    pub fn new(max_sessions: usize) -> Self {
        Self {
            max_sessions: max_sessions.max(1),
            sessions: HashMap::new(),
        }
    }

    pub fn acquire(
        &mut self,
        proxy_id: Option<String>,
        fingerprint_profile: &str,
    ) -> RuntimeSession {
        if let Some(session) = self.sessions.values_mut().find(|session| {
            !session.in_use
                && session.proxy_id == proxy_id
                && session.fingerprint_profile == fingerprint_profile
        }) {
            session.in_use = true;
            session.lease_count += 1;
            session.last_used_at_unix = unix_now();
            return session.clone();
        }

        if self.sessions.len() >= self.max_sessions {
            if let Some((_, oldest)) = self
                .sessions
                .iter_mut()
                .min_by_key(|(_, session)| session.last_used_at_unix)
            {
                oldest.in_use = true;
                oldest.lease_count += 1;
                oldest.last_used_at_unix = unix_now();
                return oldest.clone();
            }
        }

        let now = unix_now();
        let session = RuntimeSession {
            session_id: format!("session-{}", &uuid_seed()[..12]),
            created_at_unix: now,
            last_used_at_unix: now,
            headers: HashMap::new(),
            cookies: HashMap::new(),
            fingerprint_profile: fingerprint_profile.to_string(),
            proxy_id,
            lease_count: 1,
            failure_count: 0,
            in_use: true,
        };
        self.sessions
            .insert(session.session_id.clone(), session.clone());
        session
    }

    pub fn release(&mut self, session_id: &str, success: bool) {
        if let Some(session) = self.sessions.get_mut(session_id) {
            session.in_use = false;
            session.last_used_at_unix = unix_now();
            if !success {
                session.failure_count += 1;
            }
        }
    }

    pub fn snapshot(&self) -> Value {
        serde_json::json!({
            "max_sessions": self.max_sessions,
            "sessions": self.sessions.values().cloned().collect::<Vec<_>>(),
        })
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProxyEndpoint {
    pub proxy_id: String,
    pub url: String,
    pub success_count: u64,
    pub failure_count: u64,
    pub available: bool,
    pub last_error: String,
}

impl ProxyEndpoint {
    pub fn score(&self) -> f64 {
        let total = self.success_count + self.failure_count;
        if total == 0 {
            1.0
        } else {
            self.success_count as f64 / total as f64
        }
    }
}

#[derive(Debug, Default)]
pub struct ProxyPolicy {
    proxies: HashMap<String, ProxyEndpoint>,
}

impl ProxyPolicy {
    pub fn add_proxy(&mut self, proxy_id: &str, url: &str) -> ProxyEndpoint {
        let endpoint = ProxyEndpoint {
            proxy_id: proxy_id.to_string(),
            url: url.to_string(),
            success_count: 0,
            failure_count: 0,
            available: true,
            last_error: String::new(),
        };
        self.proxies
            .insert(endpoint.proxy_id.clone(), endpoint.clone());
        endpoint
    }

    pub fn choose(&self) -> Option<ProxyEndpoint> {
        self.proxies
            .values()
            .filter(|proxy| proxy.available)
            .max_by(|a, b| a.score().partial_cmp(&b.score()).unwrap())
            .cloned()
    }

    pub fn record(&mut self, proxy_id: &str, success: bool, error: &str) {
        if let Some(proxy) = self.proxies.get_mut(proxy_id) {
            if success {
                proxy.success_count += 1;
                proxy.available = true;
                proxy.last_error.clear();
            } else {
                proxy.failure_count += 1;
                proxy.last_error = error.to_string();
                if proxy.failure_count >= 3 && proxy.failure_count > proxy.success_count {
                    proxy.available = false;
                }
            }
        }
    }

    pub fn snapshot(&self) -> Value {
        serde_json::json!({ "proxies": self.proxies.values().cloned().collect::<Vec<_>>() })
    }
}

pub trait Middleware: Send + Sync {
    fn process_request(&self, request: Request) -> Result<Request> {
        Ok(request)
    }

    fn process_response(&self, response: Value, _request: &Request) -> Result<Value> {
        Ok(response)
    }
}

#[derive(Default)]
pub struct MiddlewareChain {
    middlewares: Vec<Arc<dyn Middleware>>,
}

impl MiddlewareChain {
    pub fn add(&mut self, middleware: Arc<dyn Middleware>) {
        self.middlewares.push(middleware);
    }

    pub fn process_request(&self, mut request: Request) -> Result<Request> {
        for middleware in &self.middlewares {
            request = middleware.process_request(request)?;
        }
        Ok(request)
    }

    pub fn process_response(&self, mut response: Value, request: &Request) -> Result<Value> {
        for middleware in self.middlewares.iter().rev() {
            response = middleware.process_response(response, request)?;
        }
        Ok(response)
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StructuredEvent {
    pub timestamp_unix: u64,
    pub level: String,
    pub event: String,
    pub trace_id: Option<String>,
    pub fields: BTreeMap<String, Value>,
}

#[derive(Debug, Default)]
pub struct ObservabilityCollector {
    pub events: Vec<StructuredEvent>,
    pub metrics: BTreeMap<String, f64>,
    pub traces: BTreeMap<String, Vec<StructuredEvent>>,
}

impl ObservabilityCollector {
    pub fn start_trace(&mut self, name: &str) -> String {
        let trace_id = format!("trace-{}", &uuid_seed()[..12]);
        self.log(
            "info",
            name,
            Some(trace_id.clone()),
            BTreeMap::from([("phase".to_string(), Value::String("start".to_string()))]),
        );
        trace_id
    }

    pub fn end_trace(&mut self, trace_id: &str, fields: BTreeMap<String, Value>) {
        self.log("info", "trace.complete", Some(trace_id.to_string()), fields);
    }

    pub fn log(
        &mut self,
        level: &str,
        event: &str,
        trace_id: Option<String>,
        fields: BTreeMap<String, Value>,
    ) {
        let structured = StructuredEvent {
            timestamp_unix: unix_now(),
            level: level.to_string(),
            event: event.to_string(),
            trace_id: trace_id.clone(),
            fields,
        };
        *self.metrics.entry(format!("events.{event}")).or_insert(0.0) += 1.0;
        if let Some(trace_id) = trace_id {
            self.traces
                .entry(trace_id)
                .or_default()
                .push(structured.clone());
        }
        self.events.push(structured);
    }

    pub fn record_request(&mut self, request: &Request, trace_id: Option<String>) {
        *self
            .metrics
            .entry("requests.total".to_string())
            .or_insert(0.0) += 1.0;
        self.log(
            "info",
            "request.enqueued",
            trace_id,
            BTreeMap::from([
                ("url".to_string(), Value::String(request.url.clone())),
                (
                    "priority".to_string(),
                    Value::Number(request.priority.into()),
                ),
            ]),
        );
    }

    pub fn record_result(
        &mut self,
        request: Option<&Request>,
        latency_ms: f64,
        status_code: Option<u16>,
        error: Option<&str>,
        trace_id: Option<String>,
    ) -> String {
        let classification = classify_failure(status_code, error, "");
        *self
            .metrics
            .entry("requests.latency_ms.total".to_string())
            .or_insert(0.0) += latency_ms.max(0.0);
        *self
            .metrics
            .entry(format!("results.{classification}"))
            .or_insert(0.0) += 1.0;
        let mut fields = BTreeMap::new();
        fields.insert(
            "url".to_string(),
            Value::String(request.map(|item| item.url.clone()).unwrap_or_default()),
        );
        fields.insert(
            "latency_ms".to_string(),
            Value::Number(
                serde_json::Number::from_f64(latency_ms.max(0.0)).unwrap_or_else(|| 0.into()),
            ),
        );
        fields.insert(
            "classification".to_string(),
            Value::String(classification.clone()),
        );
        if let Some(code) = status_code {
            fields.insert("status_code".to_string(), Value::Number(code.into()));
        }
        if let Some(error) = error {
            fields.insert("error".to_string(), Value::String(error.to_string()));
        }
        let level = if classification == "ok" || classification == "not_modified" {
            "info"
        } else {
            "error"
        };
        self.log(level, "request.completed", trace_id, fields);
        classification
    }

    pub fn summary(&self) -> Value {
        let requests = self
            .metrics
            .get("requests.total")
            .copied()
            .unwrap_or_default();
        let latency = self
            .metrics
            .get("requests.latency_ms.total")
            .copied()
            .unwrap_or_default();
        serde_json::json!({
            "events": self.events.len(),
            "traces": self.traces.len(),
            "metrics": self.metrics,
            "average_latency_ms": if requests > 0.0 { latency / requests } else { 0.0 }
        })
    }

    pub fn prometheus_text(&self, prefix: &str) -> String {
        let prefix = if prefix.trim().is_empty() {
            "spider_runtime"
        } else {
            prefix
        };
        let summary = self.summary();
        let mut lines = vec![
            format!("# HELP {prefix}_events_total Total structured events emitted by the runtime"),
            format!("# TYPE {prefix}_events_total counter"),
            format!("{prefix}_events_total {}", summary["events"]),
            format!("# HELP {prefix}_traces_total Total traces recorded by the runtime"),
            format!("# TYPE {prefix}_traces_total gauge"),
            format!("{prefix}_traces_total {}", summary["traces"]),
        ];
        if let Some(metrics) = summary["metrics"].as_object() {
            for (key, value) in metrics {
                lines.push(format!(
                    "{prefix}_{} {}",
                    key.replace('.', "_"),
                    value.as_f64().unwrap_or_default()
                ));
            }
        }
        lines.push(format!(
            "{prefix}_average_latency_ms {}",
            summary["average_latency_ms"].as_f64().unwrap_or_default()
        ));
        lines.join("\n") + "\n"
    }

    pub fn otel_payload(&self, service_name: &str) -> Value {
        let summary = self.summary();
        let mut points = Vec::new();
        if let Some(metrics) = summary["metrics"].as_object() {
            for (key, value) in metrics {
                points.push(serde_json::json!({
                    "name": key,
                    "value": value.as_f64().unwrap_or_default(),
                    "unit": "1"
                }));
            }
        }
        points.push(serde_json::json!({
            "name": "average_latency_ms",
            "value": summary["average_latency_ms"].as_f64().unwrap_or_default(),
            "unit": "ms"
        }));
        serde_json::json!({
            "resource": {"service.name": if service_name.trim().is_empty() { "spider-runtime" } else { service_name }},
            "scope": "rustspider::contracts",
            "metrics": points,
            "events": summary["events"],
            "traces": summary["traces"]
        })
    }
}

pub fn classify_failure(status_code: Option<u16>, error: Option<&str>, body: &str) -> String {
    let message = format!(
        "{} {}",
        error.unwrap_or_default().to_lowercase(),
        body.to_lowercase()
    );
    match status_code.unwrap_or_default() {
        304 => return "not_modified".to_string(),
        401 | 403 => return "blocked".to_string(),
        404 => return "not_found".to_string(),
        408 => return "timeout".to_string(),
        429 => return "throttled".to_string(),
        code if code >= 500 => return "server".to_string(),
        _ => {}
    }
    if message.contains("timeout") {
        return "timeout".to_string();
    }
    if message.contains("rate limit") || message.contains("too many requests") {
        return "throttled".to_string();
    }
    if message.contains("captcha") || message.contains("challenge") {
        return "anti_bot".to_string();
    }
    if message.contains("proxy") {
        return "proxy".to_string();
    }
    if error.is_some() {
        return "runtime".to_string();
    }
    "ok".to_string()
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FrontierConfig {
    pub checkpoint_dir: String,
    pub checkpoint_id: String,
    pub autoscale: bool,
    pub min_concurrency: usize,
    pub max_concurrency: usize,
    pub target_latency_ms: u64,
    pub lease_ttl_seconds: u64,
    pub max_inflight_per_domain: usize,
}

impl Default for FrontierConfig {
    fn default() -> Self {
        Self {
            checkpoint_dir: "artifacts/checkpoints/frontier".to_string(),
            checkpoint_id: "runtime-frontier".to_string(),
            autoscale: true,
            min_concurrency: 1,
            max_concurrency: 16,
            target_latency_ms: 1200,
            lease_ttl_seconds: 30,
            max_inflight_per_domain: 2,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct FrontierRequestEnvelope {
    url: String,
    method: String,
    headers: HashMap<String, String>,
    body: Option<String>,
    meta: HashMap<String, String>,
    priority: i32,
    fingerprint: String,
}

#[derive(Debug, Clone)]
pub struct FrontierLease {
    pub request: Request,
    pub fingerprint: String,
    pub leased_at_unix: u64,
    pub expires_at_unix: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct FrontierSnapshot {
    pending: Vec<FrontierRequestEnvelope>,
    known: Vec<String>,
    domain_inflight: HashMap<String, usize>,
    recommended_concurrency: usize,
    latencies: Vec<f64>,
    outcomes: Vec<bool>,
    dead_letters: Vec<FrontierRequestEnvelope>,
}

#[derive(Debug)]
pub struct AutoscaledFrontier {
    config: FrontierConfig,
    checkpoint: CheckpointManager,
    pending: Vec<FrontierRequestEnvelope>,
    known: HashSet<String>,
    leases: HashMap<String, FrontierLease>,
    domain_inflight: HashMap<String, usize>,
    latencies: Vec<f64>,
    outcomes: Vec<bool>,
    dead_letters: Vec<FrontierRequestEnvelope>,
    recommended_concurrency: usize,
    observability: ObservabilityCollector,
}

impl AutoscaledFrontier {
    pub fn new(config: FrontierConfig) -> Self {
        let checkpoint = CheckpointManager::new(&config.checkpoint_dir, None);
        Self {
            recommended_concurrency: config.min_concurrency.max(1),
            checkpoint,
            config,
            pending: Vec::new(),
            known: HashSet::new(),
            leases: HashMap::new(),
            domain_inflight: HashMap::new(),
            latencies: Vec::new(),
            outcomes: Vec::new(),
            dead_letters: Vec::new(),
            observability: ObservabilityCollector::default(),
        }
    }

    pub fn recommended_concurrency(&self) -> usize {
        self.recommended_concurrency
    }

    pub fn dead_letter_count(&self) -> usize {
        self.dead_letters.len()
    }

    pub fn push(&mut self, request: Request) -> bool {
        let fingerprint = RequestFingerprint::from_request(&request).value;
        if self.known.contains(&fingerprint) || self.leases.contains_key(&fingerprint) {
            return false;
        }
        self.known.insert(fingerprint.clone());
        self.pending
            .push(Self::serialize_request(&request, fingerprint));
        self.pending.sort_by(|left, right| {
            right
                .priority
                .cmp(&left.priority)
                .then_with(|| left.url.cmp(&right.url))
        });
        self.observability.record_request(&request, None);
        true
    }

    pub fn lease(&mut self) -> Option<Request> {
        self.reap_expired_leases(3);
        let mut blocked = Vec::new();
        while let Some(item) = self.pending.first().cloned() {
            self.pending.remove(0);
            let domain = frontier_domain(&item.url);
            if !domain.is_empty()
                && self
                    .domain_inflight
                    .get(&domain)
                    .copied()
                    .unwrap_or_default()
                    >= self.config.max_inflight_per_domain
            {
                blocked.push(item);
                continue;
            }
            let request = Self::deserialize_request(&item);
            self.leases.insert(
                item.fingerprint.clone(),
                FrontierLease {
                    request: request.clone(),
                    fingerprint: item.fingerprint.clone(),
                    leased_at_unix: unix_now(),
                    expires_at_unix: unix_now() + self.config.lease_ttl_seconds,
                },
            );
            if !domain.is_empty() {
                *self.domain_inflight.entry(domain).or_insert(0) += 1;
            }
            self.pending.extend(blocked);
            self.pending.sort_by(|left, right| {
                right
                    .priority
                    .cmp(&left.priority)
                    .then_with(|| left.url.cmp(&right.url))
            });
            return Some(request);
        }
        self.pending.extend(blocked);
        self.pending.sort_by(|left, right| {
            right
                .priority
                .cmp(&left.priority)
                .then_with(|| left.url.cmp(&right.url))
        });
        None
    }

    pub fn heartbeat(&mut self, request: &Request, ttl_seconds: Option<u64>) -> bool {
        let fingerprint = RequestFingerprint::from_request(request).value;
        if let Some(lease) = self.leases.get_mut(&fingerprint) {
            lease.expires_at_unix =
                unix_now() + ttl_seconds.unwrap_or(self.config.lease_ttl_seconds).max(1);
            return true;
        }
        false
    }

    pub fn ack(
        &mut self,
        request: &Request,
        success: bool,
        latency_ms: f64,
        error: Option<&str>,
        status_code: Option<u16>,
        max_retries: usize,
    ) {
        let fingerprint = RequestFingerprint::from_request(request).value;
        self.leases.remove(&fingerprint);
        let domain = frontier_domain(&request.url);
        if let Some(count) = self.domain_inflight.get_mut(&domain) {
            if *count > 0 {
                *count -= 1;
            }
        }
        if !success {
            let retry_count = request
                .meta
                .get("retry_count")
                .and_then(|value| value.parse::<usize>().ok())
                .unwrap_or_default();
            if retry_count >= max_retries {
                self.dead_letters
                    .push(Self::serialize_request(request, fingerprint.clone()));
            } else {
                let mut retry_request = request.clone();
                retry_request
                    .meta
                    .insert("retry_count".to_string(), (retry_count + 1).to_string());
                self.pending
                    .push(Self::serialize_request(&retry_request, fingerprint.clone()));
                self.pending.sort_by(|left, right| {
                    right
                        .priority
                        .cmp(&left.priority)
                        .then_with(|| left.url.cmp(&right.url))
                });
            }
        }
        push_bounded(&mut self.latencies, latency_ms.max(0.0), 64);
        push_bounded(&mut self.outcomes, success, 64);
        self.adjust_concurrency();
        self.observability
            .record_result(Some(request), latency_ms, status_code, error, None);
    }

    pub fn persist(&self) -> Result<(), String> {
        let snapshot = self.snapshot();
        let stats = HashMap::from([("frontier".to_string(), snapshot)]);
        self.checkpoint.save(
            &self.config.checkpoint_id,
            self.known.iter().cloned().collect(),
            self.pending.iter().map(|item| item.url.clone()).collect(),
            stats,
            HashMap::new(),
            true,
        )
    }

    pub fn load(&mut self) -> bool {
        let Some(state) = self.checkpoint.load(&self.config.checkpoint_id) else {
            return false;
        };
        let Some(snapshot_value) = state.stats.get("frontier") else {
            return false;
        };
        let snapshot = match serde_json::from_value::<FrontierSnapshot>(snapshot_value.clone()) {
            Ok(snapshot) => snapshot,
            Err(_) => return false,
        };
        self.restore(snapshot);
        true
    }

    pub fn snapshot(&self) -> Value {
        serde_json::to_value(FrontierSnapshot {
            pending: self.pending.clone(),
            known: self.known.iter().cloned().collect(),
            domain_inflight: self.domain_inflight.clone(),
            recommended_concurrency: self.recommended_concurrency,
            latencies: self.latencies.clone(),
            outcomes: self.outcomes.clone(),
            dead_letters: self.dead_letters.clone(),
        })
        .unwrap_or(Value::Null)
    }

    pub fn reap_expired_leases(&mut self, max_retries: usize) -> usize {
        let now = unix_now();
        let expired: Vec<String> = self
            .leases
            .iter()
            .filter(|(_, lease)| lease.expires_at_unix <= now)
            .map(|(fingerprint, _)| fingerprint.clone())
            .collect();
        for fingerprint in &expired {
            if let Some(lease) = self.leases.remove(fingerprint) {
                let domain = frontier_domain(&lease.request.url);
                if let Some(count) = self.domain_inflight.get_mut(&domain) {
                    if *count > 0 {
                        *count -= 1;
                    }
                }
                let retry_count = lease
                    .request
                    .meta
                    .get("retry_count")
                    .and_then(|value| value.parse::<usize>().ok())
                    .unwrap_or_default();
                if retry_count >= max_retries {
                    self.dead_letters
                        .push(Self::serialize_request(&lease.request, fingerprint.clone()));
                    continue;
                }
                let mut retry_request = lease.request.clone();
                retry_request
                    .meta
                    .insert("retry_count".to_string(), (retry_count + 1).to_string());
                self.pending
                    .push(Self::serialize_request(&retry_request, fingerprint.clone()));
            }
        }
        self.pending.sort_by(|left, right| {
            right
                .priority
                .cmp(&left.priority)
                .then_with(|| left.url.cmp(&right.url))
        });
        expired.len()
    }

    fn restore(&mut self, snapshot: FrontierSnapshot) {
        self.pending = snapshot.pending;
        self.known = snapshot.known.into_iter().collect();
        self.leases.clear();
        self.domain_inflight = snapshot.domain_inflight;
        self.latencies = snapshot.latencies;
        self.outcomes = snapshot.outcomes;
        self.dead_letters = snapshot.dead_letters;
        self.recommended_concurrency = snapshot
            .recommended_concurrency
            .max(self.config.min_concurrency)
            .min(self.config.max_concurrency);
        self.pending.sort_by(|left, right| {
            right
                .priority
                .cmp(&left.priority)
                .then_with(|| left.url.cmp(&right.url))
        });
    }

    fn adjust_concurrency(&mut self) {
        if !self.config.autoscale {
            return;
        }
        let average_latency = if self.latencies.is_empty() {
            0.0
        } else {
            self.latencies.iter().sum::<f64>() / self.latencies.len() as f64
        };
        let failure_rate = if self.outcomes.is_empty() {
            0.0
        } else {
            self.outcomes.iter().filter(|success| !**success).count() as f64
                / self.outcomes.len() as f64
        };
        if failure_rate > 0.2 || average_latency > self.config.target_latency_ms as f64 * 1.4 {
            self.recommended_concurrency = self
                .recommended_concurrency
                .saturating_sub(1)
                .max(self.config.min_concurrency);
        } else if self.pending.len() > self.recommended_concurrency
            && average_latency < self.config.target_latency_ms as f64
            && self.recommended_concurrency < self.config.max_concurrency
        {
            self.recommended_concurrency += 1;
        }
    }

    fn serialize_request(request: &Request, fingerprint: String) -> FrontierRequestEnvelope {
        FrontierRequestEnvelope {
            url: request.url.clone(),
            method: request.method.clone(),
            headers: request.headers.clone(),
            body: request.body.clone(),
            meta: request.meta.clone(),
            priority: request.priority,
            fingerprint,
        }
    }

    fn deserialize_request(payload: &FrontierRequestEnvelope) -> Request {
        Request {
            url: payload.url.clone(),
            method: payload.method.clone(),
            headers: payload.headers.clone(),
            body: payload.body.clone(),
            meta: payload.meta.clone(),
            priority: payload.priority,
        }
    }
}

fn frontier_domain(url: &str) -> String {
    match reqwest::Url::parse(url) {
        Ok(url) => url.host_str().unwrap_or_default().to_lowercase(),
        Err(_) => String::new(),
    }
}

fn push_bounded<T>(items: &mut Vec<T>, value: T, max: usize) {
    items.push(value);
    if items.len() > max {
        let remove = items.len() - max;
        items.drain(0..remove);
    }
}

fn unix_now() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or(Duration::from_secs(0))
        .as_secs()
}

fn uuid_seed() -> String {
    let digest = Sha256::digest(format!("{:?}", SystemTime::now()).as_bytes());
    format!("{:x}", digest)
}

pub fn ensure_frontier_persisted(frontier: &AutoscaledFrontier) -> Result<()> {
    frontier.persist().map_err(|error| anyhow!(error))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn request_fingerprint_is_stable() {
        let first = Request::new("https://example.com".to_string())
            .header("Accept", "text/html")
            .meta("page", "1");
        let second = Request::new("https://example.com".to_string())
            .header("Accept", "text/html")
            .meta("page", "1");

        assert_eq!(
            RequestFingerprint::from_request(&first),
            RequestFingerprint::from_request(&second)
        );
    }

    #[test]
    fn frontier_respects_backpressure_and_persists() {
        let temp = tempfile::tempdir().expect("tempdir");
        let mut frontier = AutoscaledFrontier::new(FrontierConfig {
            checkpoint_dir: temp.path().join("checkpoints").display().to_string(),
            checkpoint_id: "demo-frontier".to_string(),
            autoscale: true,
            min_concurrency: 1,
            max_concurrency: 4,
            target_latency_ms: 1200,
            lease_ttl_seconds: 30,
            max_inflight_per_domain: 1,
        });
        let first = Request::new("https://example.com/a".to_string()).priority(10);
        let second = Request::new("https://example.com/b".to_string()).priority(5);
        let other = Request::new("https://other.example.com/c".to_string()).priority(1);

        assert!(frontier.push(first));
        assert!(frontier.push(second));
        assert!(frontier.push(other));

        let leased_first = frontier.lease().expect("lease first");
        let leased_other = frontier.lease().expect("lease other");
        assert_eq!(leased_first.url, "https://example.com/a");
        assert_eq!(leased_other.url, "https://other.example.com/c");

        frontier.persist().expect("persist frontier");

        let mut restored = AutoscaledFrontier::new(FrontierConfig {
            checkpoint_dir: temp.path().join("checkpoints").display().to_string(),
            checkpoint_id: "demo-frontier".to_string(),
            autoscale: true,
            min_concurrency: 1,
            max_concurrency: 4,
            target_latency_ms: 1200,
            lease_ttl_seconds: 30,
            max_inflight_per_domain: 1,
        });
        assert!(restored.load());
        let snapshot: FrontierSnapshot =
            serde_json::from_value(restored.snapshot()).expect("snapshot");
        assert_eq!(snapshot.pending.len(), 1);
        assert_eq!(snapshot.pending[0].url, "https://example.com/b");
    }

    #[test]
    fn observability_and_artifacts_capture_evidence() {
        let temp = tempfile::tempdir().expect("tempdir");
        let store = FileArtifactStore::new(temp.path());
        let record = store
            .put_bytes("frontier", "json", b"{}", HashMap::new())
            .expect("artifact");
        let mut collector = ObservabilityCollector::default();
        let trace_id = collector.start_trace("crawl");
        let classification = collector.record_result(
            Some(&Request::new("https://example.com".to_string())),
            42.0,
            Some(403),
            Some("captcha challenge"),
            Some(trace_id.clone()),
        );
        collector.end_trace(
            &trace_id,
            BTreeMap::from([(
                "artifact".to_string(),
                Value::String(record.path.clone().expect("path")),
            )]),
        );

        assert_eq!(classification, "blocked");
        assert_eq!(collector.summary()["traces"], Value::Number(1.into()));
    }

    #[test]
    fn frontier_synthetic_soak_recovers_after_failures() {
        let temp = tempfile::tempdir().expect("tempdir");
        let mut frontier = AutoscaledFrontier::new(FrontierConfig {
            checkpoint_dir: temp.path().join("checkpoints").display().to_string(),
            checkpoint_id: "soak-frontier".to_string(),
            autoscale: true,
            min_concurrency: 1,
            max_concurrency: 8,
            target_latency_ms: 1200,
            lease_ttl_seconds: 30,
            max_inflight_per_domain: 2,
        });

        for idx in 0..24 {
            let mode = if idx % 7 == 0 {
                "dead-letter"
            } else {
                "success"
            };
            let request = Request::new(format!("https://example.com/item/{idx}"))
                .priority(idx % 3)
                .meta("mode", mode);
            assert!(frontier.push(request));
        }

        let mut processed = 0usize;
        let mut failed = 0usize;
        for idx in 0..80 {
            let Some(request) = frontier.lease() else {
                break;
            };
            if request.meta.get("mode").map(|value| value.as_str()) == Some("dead-letter") {
                failed += 1;
                frontier.ack(
                    &request,
                    false,
                    1800.0,
                    Some("synthetic timeout"),
                    Some(408),
                    1,
                );
            } else {
                processed += 1;
                frontier.ack(&request, true, 40.0, None, Some(200), 1);
            }
        }

        frontier.persist().expect("persist frontier");
        let mut restored = AutoscaledFrontier::new(FrontierConfig {
            checkpoint_dir: temp.path().join("checkpoints").display().to_string(),
            checkpoint_id: "soak-frontier".to_string(),
            autoscale: true,
            min_concurrency: 1,
            max_concurrency: 8,
            target_latency_ms: 1200,
            lease_ttl_seconds: 30,
            max_inflight_per_domain: 2,
        });
        assert!(restored.load());
        assert!(processed > 0);
        assert!(failed > 0);
        assert!(frontier.dead_letter_count() >= 1);
        assert!((1..=8).contains(&restored.recommended_concurrency()));
    }
}
