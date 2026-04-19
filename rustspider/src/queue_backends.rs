use reqwest::blocking::Client;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::BTreeMap;
use std::error::Error;
use std::io::{Error as IoError, ErrorKind, Write};
use std::process::{Command, Stdio};
use std::time::Duration;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum QueueBackendKind {
    Memory,
    FileJson,
    Redis,
    RabbitMq,
    Kafka,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QueueBackendConfig {
    pub kind: QueueBackendKind,
    pub endpoint: String,
    pub routing_key: Option<String>,
    pub topic: Option<String>,
    pub headers: BTreeMap<String, String>,
    pub username: Option<String>,
    pub password: Option<String>,
}

impl QueueBackendConfig {
    pub fn detect(endpoint: &str) -> Option<QueueBackendKind> {
        let lower = endpoint.trim().to_ascii_lowercase();
        if lower.starts_with("memory://") {
            Some(QueueBackendKind::Memory)
        } else if lower.starts_with("file://") {
            Some(QueueBackendKind::FileJson)
        } else if lower.starts_with("redis://") {
            Some(QueueBackendKind::Redis)
        } else if lower.starts_with("rabbitmq://") {
            Some(QueueBackendKind::RabbitMq)
        } else if lower.starts_with("kafka://") {
            Some(QueueBackendKind::Kafka)
        } else if lower.starts_with("rabbitmq+http://")
            || lower.starts_with("rabbitmq+https://")
            || (lower.starts_with("http://") || lower.starts_with("https://"))
                && lower.contains("/api/exchanges/")
        {
            Some(QueueBackendKind::RabbitMq)
        } else if lower.starts_with("kafka+http://")
            || lower.starts_with("kafka+https://")
            || (lower.starts_with("http://") || lower.starts_with("https://"))
                && lower.contains("/topics/")
        {
            Some(QueueBackendKind::Kafka)
        } else {
            None
        }
    }

    pub fn new(kind: QueueBackendKind, endpoint: impl Into<String>) -> Self {
        Self {
            kind,
            endpoint: endpoint.into(),
            routing_key: None,
            topic: None,
            headers: BTreeMap::new(),
            username: None,
            password: None,
        }
    }
}

pub struct QueueBridgeClient {
    client: Client,
    config: QueueBackendConfig,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct QueueCommandSpec {
    pub program: String,
    pub args: Vec<String>,
    pub stdin: Option<String>,
}

pub struct NativeQueueClient {
    config: QueueBackendConfig,
}

impl NativeQueueClient {
    pub fn new(config: QueueBackendConfig) -> Self {
        Self { config }
    }

    pub fn build_publish_commands(
        &self,
        payload: &Value,
    ) -> Result<Vec<QueueCommandSpec>, Box<dyn Error>> {
        match self.config.kind {
            QueueBackendKind::RabbitMq => self.build_rabbitmq_commands(payload),
            QueueBackendKind::Kafka => self.build_kafka_commands(payload),
            QueueBackendKind::Memory | QueueBackendKind::FileJson | QueueBackendKind::Redis => {
                Err("native queue client only handles RabbitMQ/Kafka endpoints".into())
            }
        }
    }

    pub fn publish_json(&self, payload: &Value) -> Result<(), Box<dyn Error>> {
        let mut last_error: Option<Box<dyn Error>> = None;
        for spec in self.build_publish_commands(payload)? {
            let mut command = Command::new(&spec.program);
            command.args(&spec.args);
            if spec.stdin.is_some() {
                command.stdin(Stdio::piped());
            }
            match command.spawn() {
                Ok(mut child) => {
                    if let Some(stdin_payload) = &spec.stdin {
                        if let Some(mut stdin) = child.stdin.take() {
                            stdin.write_all(stdin_payload.as_bytes())?;
                        }
                    }
                    let status = child.wait()?;
                    if status.success() {
                        return Ok(());
                    }
                    last_error =
                        Some(format!("{} exited with status {}", spec.program, status).into());
                }
                Err(err) if err.kind() == ErrorKind::NotFound => {
                    last_error = Some(Box::new(err));
                }
                Err(err) => return Err(Box::new(err)),
            }
        }
        Err(last_error.unwrap_or_else(|| {
            Box::new(IoError::new(
                ErrorKind::NotFound,
                "no native queue command available",
            ))
        }))
    }

    fn build_rabbitmq_commands(
        &self,
        payload: &Value,
    ) -> Result<Vec<QueueCommandSpec>, Box<dyn Error>> {
        let uri = url::Url::parse(&self.config.endpoint)?;
        let host = uri.host_str().unwrap_or("localhost").to_string();
        let port = uri.port().unwrap_or(5672).to_string();
        let segments: Vec<String> = uri
            .path_segments()
            .map(|parts| {
                parts
                    .filter(|part| !part.is_empty())
                    .map(ToOwned::to_owned)
                    .collect()
            })
            .unwrap_or_default();
        let exchange = uri
            .query_pairs()
            .find(|(key, _)| key == "exchange")
            .map(|(_, value)| value.into_owned())
            .or_else(|| segments.last().cloned())
            .unwrap_or_else(|| "amq.default".to_string());
        let vhost = uri
            .query_pairs()
            .find(|(key, _)| key == "vhost")
            .map(|(_, value)| value.into_owned())
            .unwrap_or_else(|| "/".to_string());
        let routing_key = self
            .config
            .routing_key
            .clone()
            .or_else(|| {
                uri.query_pairs()
                    .find(|(key, _)| key == "routing_key")
                    .map(|(_, value)| value.into_owned())
            })
            .unwrap_or_default();
        let body = payload.to_string();
        Ok(vec![
            QueueCommandSpec {
                program: "amqp-publish".to_string(),
                args: vec![
                    "--url".to_string(),
                    format!(
                        "amqp://{}:{}/{}",
                        host,
                        port,
                        if vhost == "/" { "%2F" } else { vhost.as_str() }
                    ),
                    "--exchange".to_string(),
                    exchange.clone(),
                    "--routing-key".to_string(),
                    routing_key.clone(),
                    "--body".to_string(),
                    body.clone(),
                ],
                stdin: None,
            },
            QueueCommandSpec {
                program: "rabbitmqadmin".to_string(),
                args: vec![
                    "--host".to_string(),
                    host,
                    "--port".to_string(),
                    port,
                    "--username".to_string(),
                    self.config
                        .username
                        .clone()
                        .unwrap_or_else(|| "guest".to_string()),
                    "--password".to_string(),
                    self.config
                        .password
                        .clone()
                        .unwrap_or_else(|| "guest".to_string()),
                    "--vhost".to_string(),
                    vhost,
                    "publish".to_string(),
                    format!("exchange={exchange}"),
                    format!("routing_key={routing_key}"),
                    format!("payload={body}"),
                ],
                stdin: None,
            },
        ])
    }

    fn build_kafka_commands(
        &self,
        payload: &Value,
    ) -> Result<Vec<QueueCommandSpec>, Box<dyn Error>> {
        let uri = url::Url::parse(&self.config.endpoint)?;
        let host_port = format!(
            "{}:{}",
            uri.host_str().unwrap_or("localhost"),
            uri.port().unwrap_or(9092)
        );
        let topic = self
            .config
            .topic
            .clone()
            .or_else(|| {
                uri.path_segments().and_then(|mut segments| {
                    segments
                        .find(|part| !part.is_empty())
                        .map(ToOwned::to_owned)
                })
            })
            .unwrap_or_else(|| "spider-tasks".to_string());
        let body = payload.to_string();
        Ok(vec![
            QueueCommandSpec {
                program: "kcat".to_string(),
                args: vec![
                    "-b".to_string(),
                    host_port.clone(),
                    "-t".to_string(),
                    topic.clone(),
                    "-P".to_string(),
                ],
                stdin: Some(body.clone()),
            },
            QueueCommandSpec {
                program: "kafka-console-producer".to_string(),
                args: vec![
                    "--bootstrap-server".to_string(),
                    host_port,
                    "--topic".to_string(),
                    topic,
                ],
                stdin: Some(body),
            },
        ])
    }
}

impl QueueBridgeClient {
    pub fn new(config: QueueBackendConfig) -> Result<Self, Box<dyn Error>> {
        let client = Client::builder().timeout(Duration::from_secs(30)).build()?;
        Ok(Self { client, config })
    }

    pub fn publish_json(&self, payload: &Value) -> Result<(), Box<dyn Error>> {
        match self.config.kind {
            QueueBackendKind::RabbitMq => self.publish_rabbitmq(payload),
            QueueBackendKind::Kafka => self.publish_kafka(payload),
            QueueBackendKind::Memory | QueueBackendKind::FileJson | QueueBackendKind::Redis => {
                Err("queue bridge client only handles RabbitMQ/Kafka bridge endpoints".into())
            }
        }
    }

    fn publish_rabbitmq(&self, payload: &Value) -> Result<(), Box<dyn Error>> {
        let endpoint = normalize_bridge_endpoint(
            &self.config.endpoint,
            "rabbitmq+http://",
            "rabbitmq+https://",
        );
        let body = serde_json::json!({
            "properties": {},
            "routing_key": self.config.routing_key.clone().unwrap_or_default(),
            "payload": payload.to_string(),
            "payload_encoding": "string"
        });

        let mut request = self.client.post(endpoint).json(&body);
        for (key, value) in &self.config.headers {
            request = request.header(key, value);
        }
        if let (Some(username), Some(password)) = (&self.config.username, &self.config.password) {
            request = request.basic_auth(username, Some(password));
        }
        let response = request.send()?;
        if !response.status().is_success() {
            return Err(format!("rabbitmq publish failed: {}", response.status()).into());
        }
        Ok(())
    }

    fn publish_kafka(&self, payload: &Value) -> Result<(), Box<dyn Error>> {
        let endpoint =
            normalize_bridge_endpoint(&self.config.endpoint, "kafka+http://", "kafka+https://");
        let body = serde_json::json!({
            "records": [
                {
                    "value": payload
                }
            ]
        });

        let mut request = self.client.post(endpoint).json(&body);
        for (key, value) in &self.config.headers {
            request = request.header(key, value);
        }
        if let (Some(username), Some(password)) = (&self.config.username, &self.config.password) {
            request = request.basic_auth(username, Some(password));
        }
        let response = request.send()?;
        if !response.status().is_success() {
            return Err(format!("kafka publish failed: {}", response.status()).into());
        }
        Ok(())
    }
}

fn normalize_bridge_endpoint(endpoint: &str, http_prefix: &str, https_prefix: &str) -> String {
    endpoint
        .strip_prefix(http_prefix)
        .map(|value| format!("http://{value}"))
        .or_else(|| {
            endpoint
                .strip_prefix(https_prefix)
                .map(|value| format!("https://{value}"))
        })
        .unwrap_or_else(|| endpoint.to_string())
}

pub fn queue_backend_support() -> Value {
    serde_json::json!({
        "native": ["memory", "file-json", "redis", "rabbitmq", "kafka"],
        "native_process": {
            "rabbitmq": {
                "mode": "cli-adapter",
                "commands": ["amqp-publish", "rabbitmqadmin"]
            },
            "kafka": {
                "mode": "cli-adapter",
                "commands": ["kcat", "kafka-console-producer"]
            }
        },
        "bridged": {
            "rabbitmq": {
                "mode": "http-management-bridge",
                "adapter_engine": "rabbitmq-management-api"
            },
            "kafka": {
                "mode": "rest-proxy-bridge",
                "adapter_engine": "kafka-rest-proxy"
            }
        }
    })
}
