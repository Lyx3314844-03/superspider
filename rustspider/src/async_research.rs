use crate::research::{ResearchJob, ResearchRuntime, SiteProfile};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::sync::{Arc, Mutex};
use std::time::Instant;
use tokio::sync::Semaphore;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AsyncResearchResult {
    pub seed: String,
    pub profile: Option<SiteProfile>,
    pub extract: Value,
    pub duration_ms: f64,
    pub dataset: Option<Value>,
    pub error: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AsyncResearchConfig {
    pub max_concurrent: usize,
    pub timeout_seconds: f64,
    pub enable_streaming: bool,
}

impl Default for AsyncResearchConfig {
    fn default() -> Self {
        Self {
            max_concurrent: 5,
            timeout_seconds: 30.0,
            enable_streaming: false,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AsyncRuntimeMetrics {
    pub max_concurrent: usize,
    pub tasks_started: usize,
    pub tasks_completed: usize,
    pub tasks_failed: usize,
    pub current_inflight: usize,
    pub peak_inflight: usize,
    pub average_duration_ms: f64,
    pub max_duration_ms: f64,
    pub last_error: String,
    total_duration_ms: f64,
}

impl AsyncRuntimeMetrics {
    fn new(max_concurrent: usize) -> Self {
        Self {
            max_concurrent,
            tasks_started: 0,
            tasks_completed: 0,
            tasks_failed: 0,
            current_inflight: 0,
            peak_inflight: 0,
            average_duration_ms: 0.0,
            max_duration_ms: 0.0,
            last_error: String::new(),
            total_duration_ms: 0.0,
        }
    }
}

pub struct AsyncResearchRuntime {
    pub config: AsyncResearchConfig,
    semaphore: Arc<Semaphore>,
    metrics: Arc<Mutex<AsyncRuntimeMetrics>>,
}

impl AsyncResearchRuntime {
    pub fn new(config: Option<AsyncResearchConfig>) -> Self {
        let config = config.unwrap_or_default();
        Self {
            semaphore: Arc::new(Semaphore::new(config.max_concurrent.max(1))),
            metrics: Arc::new(Mutex::new(AsyncRuntimeMetrics::new(
                config.max_concurrent.max(1),
            ))),
            config,
        }
    }

    pub async fn run_single(
        &self,
        job: ResearchJob,
        content: Option<String>,
    ) -> AsyncResearchResult {
        let permit = self
            .semaphore
            .acquire()
            .await
            .expect("semaphore should be available");
        self.record_start();
        let started = Instant::now();
        let seed = job.seed_urls.first().cloned().unwrap_or_default();
        let job_for_runtime = job.clone();
        let runtime = ResearchRuntime::new();
        let result = tokio::task::spawn_blocking(move || {
            let delay = job_for_runtime
                .policy
                .get("simulate_delay_ms")
                .and_then(|value| value.as_u64())
                .unwrap_or(0);
            if delay > 0 {
                std::thread::sleep(std::time::Duration::from_millis(delay));
            }
            runtime
                .run(&job_for_runtime, content.as_deref())
                .map_err(|err| err.to_string())
        })
        .await
        .ok()
        .and_then(Result::ok);

        let duration_ms = started.elapsed().as_secs_f64() * 1000.0;
        let output = match result {
            Some(payload) => AsyncResearchResult {
                seed: payload["seed"].as_str().unwrap_or_default().to_string(),
                profile: serde_json::from_value(payload["profile"].clone()).ok(),
                extract: payload["extract"].clone(),
                duration_ms,
                dataset: payload.get("dataset").cloned(),
                error: None,
            },
            None => AsyncResearchResult {
                seed,
                profile: None,
                extract: Value::Object(serde_json::Map::new()),
                duration_ms,
                dataset: None,
                error: Some("research runtime failed".to_string()),
            },
        };
        self.record_finish(duration_ms, output.error.clone());
        drop(permit);
        output
    }

    pub async fn run_multiple(
        &self,
        jobs: Vec<ResearchJob>,
        contents: Option<Vec<String>>,
    ) -> Vec<AsyncResearchResult> {
        let contents = contents.unwrap_or_else(|| vec![String::new(); jobs.len()]);
        let mut handles = Vec::with_capacity(jobs.len());
        for (index, job) in jobs.into_iter().enumerate() {
            let runtime = self.clone();
            let content = contents.get(index).cloned();
            handles.push(tokio::spawn(async move {
                runtime.run_single(job, content).await
            }));
        }
        let mut results = Vec::new();
        for handle in handles {
            if let Ok(result) = handle.await {
                results.push(result);
            }
        }
        results
    }

    pub async fn run_stream(
        &self,
        jobs: Vec<ResearchJob>,
        contents: Option<Vec<String>>,
    ) -> Vec<AsyncResearchResult> {
        self.run_multiple(jobs, contents).await
    }

    pub fn reset_metrics(&self) {
        let mut metrics = self
            .metrics
            .lock()
            .expect("metrics lock should be available");
        *metrics = AsyncRuntimeMetrics::new(self.config.max_concurrent.max(1));
    }

    pub async fn run_soak(
        &self,
        jobs: Vec<ResearchJob>,
        contents: Option<Vec<String>>,
        rounds: usize,
    ) -> Value {
        let safe_rounds = rounds.max(1);
        let started = Instant::now();
        self.reset_metrics();
        let mut all_results = Vec::new();
        for _ in 0..safe_rounds {
            all_results.extend(self.run_multiple(jobs.clone(), contents.clone()).await);
        }
        let failures = all_results
            .iter()
            .filter(|result| result.error.is_some())
            .count();
        let metrics = self.snapshot_metrics();
        let total = all_results.len();
        let successes = total.saturating_sub(failures);
        serde_json::json!({
            "jobs": jobs.len(),
            "rounds": safe_rounds,
            "results": total,
            "successes": successes,
            "failures": failures,
            "success_rate": if total == 0 { 0.0 } else { successes as f64 / total as f64 },
            "duration_ms": started.elapsed().as_secs_f64() * 1000.0,
            "peak_inflight": metrics["peak_inflight"].clone(),
            "max_concurrent": self.config.max_concurrent,
            "stable": metrics["current_inflight"].as_u64() == Some(0) && failures == 0 && metrics["tasks_completed"].as_u64() == Some(total as u64),
        })
    }

    pub fn snapshot_metrics(&self) -> Value {
        let metrics = self
            .metrics
            .lock()
            .expect("metrics lock should be available");
        serde_json::json!({
            "max_concurrent": metrics.max_concurrent,
            "tasks_started": metrics.tasks_started,
            "tasks_completed": metrics.tasks_completed,
            "tasks_failed": metrics.tasks_failed,
            "current_inflight": metrics.current_inflight,
            "peak_inflight": metrics.peak_inflight,
            "average_duration_ms": metrics.average_duration_ms,
            "max_duration_ms": metrics.max_duration_ms,
            "last_error": metrics.last_error,
        })
    }

    fn record_start(&self) {
        let mut metrics = self
            .metrics
            .lock()
            .expect("metrics lock should be available");
        metrics.tasks_started += 1;
        metrics.current_inflight += 1;
        metrics.peak_inflight = metrics.peak_inflight.max(metrics.current_inflight);
    }

    fn record_finish(&self, duration_ms: f64, error: Option<String>) {
        let mut metrics = self
            .metrics
            .lock()
            .expect("metrics lock should be available");
        metrics.tasks_completed += 1;
        metrics.current_inflight = metrics.current_inflight.saturating_sub(1);
        if let Some(error) = error.filter(|value| !value.trim().is_empty()) {
            metrics.tasks_failed += 1;
            metrics.last_error = error;
        }
        metrics.total_duration_ms += duration_ms;
        metrics.average_duration_ms = metrics.total_duration_ms / metrics.tasks_completed as f64;
        metrics.max_duration_ms = metrics.max_duration_ms.max(duration_ms);
    }
}

impl Clone for AsyncResearchRuntime {
    fn clone(&self) -> Self {
        Self {
            config: self.config.clone(),
            semaphore: Arc::clone(&self.semaphore),
            metrics: Arc::clone(&self.metrics),
        }
    }
}
