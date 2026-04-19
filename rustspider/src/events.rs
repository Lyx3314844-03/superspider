use crossbeam_channel::{unbounded, Receiver, Sender};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::BTreeMap;
use std::sync::Mutex;

pub const TOPIC_TASK_CREATED: &str = "task:created";
pub const TOPIC_TASK_QUEUED: &str = "task:queued";
pub const TOPIC_TASK_RUNNING: &str = "task:running";
pub const TOPIC_TASK_SUCCEEDED: &str = "task:succeeded";
pub const TOPIC_TASK_FAILED: &str = "task:failed";
pub const TOPIC_TASK_CANCELLED: &str = "task:cancelled";
pub const TOPIC_TASK_DELETED: &str = "task:deleted";
pub const TOPIC_TASK_RESULT: &str = "task:result";

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Event {
    pub topic: String,
    pub timestamp_unix: u64,
    pub payload: Value,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct TaskLifecyclePayload {
    pub task_id: String,
    pub state: String,
    pub runtime: String,
    pub url: String,
    pub worker_id: String,
    pub updated_at: String,
    pub has_result: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ArtifactRef {
    pub kind: String,
    pub uri: String,
    pub path: String,
    pub size: i64,
    #[serde(default)]
    pub metadata: BTreeMap<String, Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct TaskResultPayload {
    pub task_id: String,
    pub state: String,
    pub runtime: String,
    pub url: String,
    pub status_code: u16,
    #[serde(default)]
    pub artifacts: Vec<String>,
    #[serde(default)]
    pub artifact_refs: BTreeMap<String, ArtifactRef>,
    pub updated_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct TaskDeletedPayload {
    pub task_id: String,
    pub deleted_at: String,
}

#[derive(Default)]
pub struct EventBus {
    subscribers: Mutex<BTreeMap<String, Vec<Sender<Event>>>>,
    history: Mutex<Vec<Event>>,
}

impl EventBus {
    pub fn subscribe(&self, topic: &str) -> Receiver<Event> {
        let (tx, rx) = unbounded();
        self.subscribers
            .lock()
            .expect("event subscribers lock")
            .entry(topic.to_string())
            .or_default()
            .push(tx);
        rx
    }

    pub fn publish(&self, topic: &str, payload: Value) -> Event {
        let event = Event {
            topic: topic.to_string(),
            timestamp_unix: chrono::Utc::now().timestamp() as u64,
            payload,
        };
        self.history
            .lock()
            .expect("event history lock")
            .push(event.clone());
        let subscribers = self.subscribers.lock().expect("event subscribers lock");
        for key in [topic, "*"] {
            if let Some(targets) = subscribers.get(key) {
                for sender in targets {
                    let _ = sender.send(event.clone());
                }
            }
        }
        event
    }

    pub fn recent(&self, topic: Option<&str>) -> Vec<Event> {
        self.history
            .lock()
            .expect("event history lock")
            .iter()
            .filter(|event| topic.map(|value| value == event.topic).unwrap_or(true))
            .cloned()
            .collect()
    }
}
