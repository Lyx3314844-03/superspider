use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::PathBuf;
use std::sync::Mutex;
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct EventEnvelope {
    pub topic: String,
    pub timestamp: u64,
    pub payload: Value,
}

pub trait EventBus: Send + Sync {
    fn publish(&self, topic: &str, payload: Value) -> Result<(), String>;
    fn list(&self, limit: usize, topic: Option<&str>) -> Vec<EventEnvelope>;
}

pub struct InMemoryEventBus {
    max_size: usize,
    events: Mutex<Vec<EventEnvelope>>,
}

impl InMemoryEventBus {
    pub fn new(max_size: usize) -> Self {
        Self {
            max_size: max_size.max(1),
            events: Mutex::new(Vec::new()),
        }
    }
}

impl Default for InMemoryEventBus {
    fn default() -> Self {
        Self::new(256)
    }
}

impl EventBus for InMemoryEventBus {
    fn publish(&self, topic: &str, payload: Value) -> Result<(), String> {
        let mut events = self
            .events
            .lock()
            .map_err(|_| "event bus mutex poisoned".to_string())?;
        events.push(EventEnvelope {
            topic: topic.to_string(),
            timestamp: SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .map(|duration| duration.as_secs())
                .unwrap_or_default(),
            payload,
        });
        if events.len() > self.max_size {
            let keep_from = events.len().saturating_sub(self.max_size);
            events.drain(0..keep_from);
        }
        Ok(())
    }

    fn list(&self, limit: usize, topic: Option<&str>) -> Vec<EventEnvelope> {
        let Ok(events) = self.events.lock() else {
            return Vec::new();
        };
        let capped = if limit == 0 { events.len() } else { limit };
        events
            .iter()
            .rev()
            .filter(|event| {
                topic
                    .map(|expected| event.topic == expected)
                    .unwrap_or(true)
            })
            .take(capped)
            .cloned()
            .collect()
    }
}

pub struct FileEventBus {
    path: PathBuf,
    lock: Mutex<()>,
    memory: InMemoryEventBus,
}

impl FileEventBus {
    pub fn new(path: impl Into<PathBuf>) -> Self {
        Self {
            path: path.into(),
            lock: Mutex::new(()),
            memory: InMemoryEventBus::new(1024),
        }
    }
}

impl EventBus for FileEventBus {
    fn publish(&self, topic: &str, payload: Value) -> Result<(), String> {
        self.memory.publish(topic, payload.clone())?;
        let _guard = self
            .lock
            .lock()
            .map_err(|_| "event bus mutex poisoned".to_string())?;
        if let Some(parent) = self.path.parent() {
            fs::create_dir_all(parent).map_err(|err| err.to_string())?;
        }
        let mut file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(&self.path)
            .map_err(|err| err.to_string())?;
        let record = EventEnvelope {
            topic: topic.to_string(),
            timestamp: SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .map(|duration| duration.as_secs())
                .unwrap_or_default(),
            payload,
        };
        let line = serde_json::to_string(&record).map_err(|err| err.to_string())?;
        file.write_all(line.as_bytes())
            .map_err(|err| err.to_string())?;
        file.write_all(b"\n").map_err(|err| err.to_string())?;
        Ok(())
    }

    fn list(&self, limit: usize, topic: Option<&str>) -> Vec<EventEnvelope> {
        self.memory.list(limit, topic)
    }
}
