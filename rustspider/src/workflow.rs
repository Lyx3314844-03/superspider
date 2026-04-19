use crate::connector::{Connector, OutputEnvelope};
use crate::event_bus::EventBus;
use serde::{Deserialize, Serialize};
use serde_json::{json, Map, Value};
use std::fs;
use std::path::Path;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Default)]
pub struct ExecutionPolicy {
    #[serde(default)]
    pub step_timeout_millis: u64,
    #[serde(default)]
    pub max_retries: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct FlowStep {
    pub id: String,
    #[serde(rename = "type")]
    pub step_type: String,
    #[serde(default)]
    pub selector: String,
    #[serde(default)]
    pub value: String,
    #[serde(default)]
    pub metadata: Map<String, Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct FlowJob {
    pub id: String,
    pub name: String,
    pub steps: Vec<FlowStep>,
    #[serde(default)]
    pub output_contract: Map<String, Value>,
    #[serde(default)]
    pub policy: ExecutionPolicy,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct FlowResult {
    pub job_id: String,
    pub run_id: String,
    pub extracted: Value,
    pub artifacts: Vec<String>,
}

pub trait WorkflowContext {
    fn goto_url(&mut self, url: &str);
    fn wait_for(&mut self, timeout_ms: u64);
    fn click(&mut self, selector: &str);
    fn type_text(&mut self, selector: &str, value: &str);
    fn select(&mut self, selector: &str, value: &str, options: &Map<String, Value>);
    fn hover(&mut self, selector: &str);
    fn scroll(&mut self, selector: &str, options: &Map<String, Value>);
    fn evaluate(&mut self, script: &str) -> Value;
    fn listen_network(&mut self, options: &Map<String, Value>) -> Value;
    fn capture_html(&self) -> String;
    fn capture_screenshot(&mut self, artifact_path: &str) -> Result<(), String>;
    fn current_url(&self) -> String;
    fn title(&self) -> String;
}

#[derive(Debug, Clone)]
pub struct MemoryWorkflowContext {
    current_url: String,
    title: String,
    html: String,
    network_events: Value,
}

impl Default for MemoryWorkflowContext {
    fn default() -> Self {
        Self {
            current_url: String::new(),
            title: "workflow".to_string(),
            html: "<html><title>workflow</title></html>".to_string(),
            network_events: json!([{ "url": "https://example.com/api", "method": "GET", "status": 200 }]),
        }
    }
}

impl MemoryWorkflowContext {
    pub fn set_title(&mut self, title: impl Into<String>) {
        self.title = title.into();
    }
}

impl WorkflowContext for MemoryWorkflowContext {
    fn goto_url(&mut self, url: &str) {
        self.current_url = url.to_string();
    }

    fn wait_for(&mut self, timeout_ms: u64) {
        if timeout_ms > 0 {
            std::thread::sleep(std::time::Duration::from_millis(timeout_ms));
        }
    }

    fn click(&mut self, _selector: &str) {}

    fn type_text(&mut self, _selector: &str, _value: &str) {}

    fn select(&mut self, _selector: &str, _value: &str, _options: &Map<String, Value>) {}

    fn hover(&mut self, _selector: &str) {}

    fn scroll(&mut self, _selector: &str, _options: &Map<String, Value>) {}

    fn evaluate(&mut self, script: &str) -> Value {
        Value::String(script.to_string())
    }

    fn listen_network(&mut self, _options: &Map<String, Value>) -> Value {
        self.network_events.clone()
    }

    fn capture_html(&self) -> String {
        self.html.clone()
    }

    fn capture_screenshot(&mut self, artifact_path: &str) -> Result<(), String> {
        let path = Path::new(artifact_path);
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent).map_err(|err| err.to_string())?;
        }
        fs::write(path, b"workflow-screenshot").map_err(|err| err.to_string())
    }

    fn current_url(&self) -> String {
        self.current_url.clone()
    }

    fn title(&self) -> String {
        self.title.clone()
    }
}

pub struct WorkflowRunner {
    connectors: Vec<Box<dyn Connector>>,
    event_bus: Option<Box<dyn EventBus>>,
}

impl WorkflowRunner {
    pub fn new() -> Self {
        Self {
            connectors: Vec::new(),
            event_bus: None,
        }
    }

    pub fn with_event_bus<E: EventBus + 'static>(mut self, event_bus: E) -> Self {
        self.event_bus = Some(Box::new(event_bus));
        self
    }

    pub fn add_connector<C: Connector + 'static>(mut self, connector: C) -> Self {
        self.connectors.push(Box::new(connector));
        self
    }

    pub fn execute(&self, job: &FlowJob) -> Result<FlowResult, String> {
        let mut context = MemoryWorkflowContext::default();
        self.execute_with_context(job, &mut context)
    }

    pub fn execute_with_context(
        &self,
        job: &FlowJob,
        context: &mut dyn WorkflowContext,
    ) -> Result<FlowResult, String> {
        let run_id = format!("{}-{}", job.id, uuid_like_suffix());
        let mut extracted = Map::new();
        let mut artifacts = Vec::new();

        if let Some(bus) = &self.event_bus {
            let _ = bus.publish(
                "workflow.job.started",
                json!({"job_id": job.id, "run_id": run_id, "step_count": job.steps.len()}),
            );
        }

        for step in &job.steps {
            if let Some(bus) = &self.event_bus {
                let _ = bus.publish(
                    "workflow.step.started",
                    json!({"job_id": job.id, "run_id": run_id, "step_id": step.id, "type": step.step_type}),
                );
            }
            execute_step(context, step, &mut extracted, &mut artifacts)?;
            if let Some(bus) = &self.event_bus {
                let _ = bus.publish(
                    "workflow.step.succeeded",
                    json!({"job_id": job.id, "run_id": run_id, "step_id": step.id, "type": step.step_type}),
                );
            }
        }

        let result = FlowResult {
            job_id: job.id.clone(),
            run_id: run_id.clone(),
            extracted: Value::Object(extracted.clone()),
            artifacts: artifacts.clone(),
        };
        let envelope = OutputEnvelope {
            job_id: result.job_id.clone(),
            run_id: result.run_id.clone(),
            extracted: result.extracted.clone(),
            artifacts: result.artifacts.clone(),
        };
        for connector in &self.connectors {
            connector.write(&envelope)?;
        }
        if let Some(bus) = &self.event_bus {
            let _ = bus.publish(
                "workflow.job.completed",
                json!({"job_id": job.id, "run_id": run_id, "artifacts": artifacts.len(), "fields": extracted.keys().cloned().collect::<Vec<_>>()}),
            );
        }
        Ok(result)
    }
}

impl Default for WorkflowRunner {
    fn default() -> Self {
        Self::new()
    }
}

fn execute_step(
    context: &mut dyn WorkflowContext,
    step: &FlowStep,
    extracted: &mut Map<String, Value>,
    artifacts: &mut Vec<String>,
) -> Result<(), String> {
    match step.step_type.to_ascii_lowercase().as_str() {
        "goto" => {
            let url = metadata_string(&step.metadata, "url", &step.selector);
            if !url.is_empty() {
                context.goto_url(&url);
            }
        }
        "wait" => {
            context.wait_for(metadata_u64(&step.metadata, "timeout_ms", 0));
        }
        "click" => context.click(&step.selector),
        "type" => context.type_text(&step.selector, &step.value),
        "select" => context.select(&step.selector, &step.value, &step.metadata),
        "hover" => context.hover(&step.selector),
        "scroll" => context.scroll(&step.selector, &step.metadata),
        "eval" => {
            let field = metadata_string(
                &step.metadata,
                "field",
                &metadata_string(&step.metadata, "save_as", "eval"),
            );
            extracted.insert(field, context.evaluate(&step.value));
        }
        "listen_network" => {
            let field = metadata_string(
                &step.metadata,
                "field",
                &metadata_string(&step.metadata, "save_as", "network_requests"),
            );
            extracted.insert(field, context.listen_network(&step.metadata));
        }
        "extract" => {
            let field = metadata_string(
                &step.metadata,
                "field",
                if step.selector.is_empty() {
                    "value"
                } else {
                    step.selector.as_str()
                },
            );
            if let Some(value) = step.metadata.get("value") {
                extracted.insert(field, value.clone());
            } else {
                let value = match field.as_str() {
                    "title" => Value::String(context.title()),
                    "url" => Value::String(context.current_url()),
                    "html" | "dom" => Value::String(context.capture_html()),
                    _ => Value::String(step.value.clone()),
                };
                extracted.insert(field, value);
            }
        }
        "screenshot" => {
            let artifact = metadata_string(
                &step.metadata,
                "artifact",
                if step.value.is_empty() {
                    "workflow.png"
                } else {
                    step.value.as_str()
                },
            );
            context.capture_screenshot(&artifact)?;
            artifacts.push(artifact);
        }
        "download" => {
            let artifact = metadata_string(
                &step.metadata,
                "artifact",
                if step.value.is_empty() {
                    "workflow.bin"
                } else {
                    step.value.as_str()
                },
            );
            let path = Path::new(&artifact);
            if let Some(parent) = path.parent() {
                fs::create_dir_all(parent).map_err(|err| err.to_string())?;
            }
            fs::write(path, b"workflow-artifact").map_err(|err| err.to_string())?;
            artifacts.push(artifact);
        }
        other => return Err(format!("unsupported workflow step: {other}")),
    }
    Ok(())
}

fn metadata_string(metadata: &Map<String, Value>, key: &str, fallback: &str) -> String {
    metadata
        .get(key)
        .and_then(Value::as_str)
        .unwrap_or(fallback)
        .to_string()
}

fn metadata_u64(metadata: &Map<String, Value>, key: &str, fallback: u64) -> u64 {
    metadata
        .get(key)
        .and_then(Value::as_u64)
        .unwrap_or(fallback)
}

fn uuid_like_suffix() -> String {
    format!(
        "{}",
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|duration| duration.as_nanos())
            .unwrap_or_default()
    )
}
