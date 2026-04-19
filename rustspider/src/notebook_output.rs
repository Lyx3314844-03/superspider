use serde::{Deserialize, Serialize};
use serde_json::Value;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExperimentRecord {
    pub id: String,
    pub name: String,
    pub timestamp: f64,
    pub urls: Vec<String>,
    pub schema: Value,
    pub results: Vec<Value>,
    pub metadata: Value,
}

#[derive(Debug, Default)]
pub struct ExperimentTracker {
    pub experiments: Vec<ExperimentRecord>,
}

impl ExperimentTracker {
    pub fn record(
        &mut self,
        name: &str,
        urls: Vec<String>,
        results: Vec<Value>,
        schema: Option<Value>,
        metadata: Option<Value>,
    ) -> ExperimentRecord {
        let record = ExperimentRecord {
            id: format!("exp-{:03}", self.experiments.len() + 1),
            name: name.to_string(),
            timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .map(|value| value.as_secs_f64())
                .unwrap_or_default(),
            urls,
            schema: schema.unwrap_or_else(|| serde_json::json!({})),
            results,
            metadata: metadata.unwrap_or_else(|| serde_json::json!({})),
        };
        self.experiments.push(record.clone());
        record
    }

    pub fn get_experiment(&self, name: &str) -> Option<&ExperimentRecord> {
        self.experiments.iter().find(|item| item.name == name)
    }

    pub fn compare(&self) -> Value {
        let experiments = self
            .experiments
            .iter()
            .map(|experiment| {
                let success_count = experiment
                    .results
                    .iter()
                    .filter(|result| result.get("error").is_none() || result["error"].as_str() == Some(""))
                    .count();
                let average_duration = experiment
                    .results
                    .iter()
                    .filter_map(|result| result.get("duration_ms").and_then(|value| value.as_f64()))
                    .collect::<Vec<_>>();
                serde_json::json!({
                    "id": experiment.id,
                    "name": experiment.name,
                    "urls_count": experiment.urls.len(),
                    "results_count": experiment.results.len(),
                    "success_rate": if experiment.results.is_empty() { 0.0 } else { success_count as f64 * 100.0 / experiment.results.len() as f64 },
                    "avg_extract_time": if average_duration.is_empty() { 0.0 } else { average_duration.iter().sum::<f64>() / average_duration.len() as f64 },
                })
            })
            .collect::<Vec<_>>();
        serde_json::json!({
            "experiments": experiments,
            "summary": {
                "total_experiments": self.experiments.len(),
                "total_urls": self.experiments.iter().map(|item| item.urls.len()).sum::<usize>(),
                "total_results": self.experiments.iter().map(|item| item.results.len()).sum::<usize>(),
            }
        })
    }

    pub fn to_rows(&self) -> Vec<Value> {
        let mut rows = Vec::new();
        for experiment in &self.experiments {
            for result in &experiment.results {
                rows.push(serde_json::json!({
                    "experiment_id": experiment.id,
                    "experiment_name": experiment.name,
                    "seed": result.get("seed").cloned().unwrap_or(Value::Null),
                    "extract": result.get("extract").cloned().unwrap_or_else(|| serde_json::json!({})),
                    "duration_ms": result.get("duration_ms").cloned().unwrap_or(Value::Null),
                    "error": result.get("error").cloned().unwrap_or_else(|| Value::String(String::new())),
                }));
            }
        }
        rows
    }
}
