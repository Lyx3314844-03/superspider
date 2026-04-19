use serde::{Deserialize, Serialize};
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::PathBuf;
use std::sync::Mutex;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct OutputEnvelope {
    pub job_id: String,
    pub run_id: String,
    pub extracted: serde_json::Value,
    pub artifacts: Vec<String>,
}

pub trait Connector: Send + Sync {
    fn write(&self, envelope: &OutputEnvelope) -> Result<(), String>;
}

#[derive(Default)]
pub struct InMemoryConnector {
    envelopes: Mutex<Vec<OutputEnvelope>>,
}

impl InMemoryConnector {
    pub fn list(&self) -> Vec<OutputEnvelope> {
        self.envelopes
            .lock()
            .map(|items| items.clone())
            .unwrap_or_default()
    }
}

impl Connector for InMemoryConnector {
    fn write(&self, envelope: &OutputEnvelope) -> Result<(), String> {
        self.envelopes
            .lock()
            .map_err(|_| "connector mutex poisoned".to_string())?
            .push(envelope.clone());
        Ok(())
    }
}

pub struct FileConnector {
    path: PathBuf,
    lock: Mutex<()>,
}

impl FileConnector {
    pub fn new(path: impl Into<PathBuf>) -> Self {
        Self {
            path: path.into(),
            lock: Mutex::new(()),
        }
    }
}

impl Connector for FileConnector {
    fn write(&self, envelope: &OutputEnvelope) -> Result<(), String> {
        let _guard = self
            .lock
            .lock()
            .map_err(|_| "connector mutex poisoned".to_string())?;
        if let Some(parent) = self.path.parent() {
            fs::create_dir_all(parent).map_err(|err| err.to_string())?;
        }
        let mut file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(&self.path)
            .map_err(|err| err.to_string())?;
        let line = serde_json::to_string(envelope).map_err(|err| err.to_string())?;
        file.write_all(line.as_bytes())
            .map_err(|err| err.to_string())?;
        file.write_all(b"\n").map_err(|err| err.to_string())?;
        Ok(())
    }
}
