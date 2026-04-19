use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::fs::{self, OpenOptions};
use std::io::{BufRead, BufReader, Write};
use std::path::PathBuf;
use std::sync::{Arc, Mutex};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct AuditEvent {
    pub timestamp: String,
    pub job_id: String,
    pub step_id: String,
    pub event_type: String,
    #[serde(default)]
    pub payload: Value,
}

pub trait AuditTrail {
    fn append(&self, event: AuditEvent) -> Result<(), String>;
    fn events(&self) -> Result<Vec<AuditEvent>, String>;
}

#[derive(Default)]
pub struct MemoryAuditTrail {
    events: Mutex<Vec<AuditEvent>>,
}

impl AuditTrail for MemoryAuditTrail {
    fn append(&self, event: AuditEvent) -> Result<(), String> {
        self.events
            .lock()
            .map_err(|err| err.to_string())?
            .push(event);
        Ok(())
    }

    fn events(&self) -> Result<Vec<AuditEvent>, String> {
        Ok(self.events.lock().map_err(|err| err.to_string())?.clone())
    }
}

pub struct FileAuditTrail {
    path: PathBuf,
    lock: Mutex<()>,
}

impl FileAuditTrail {
    pub fn new(path: impl Into<PathBuf>) -> Self {
        Self {
            path: path.into(),
            lock: Mutex::new(()),
        }
    }
}

impl AuditTrail for FileAuditTrail {
    fn append(&self, event: AuditEvent) -> Result<(), String> {
        let _guard = self.lock.lock().map_err(|err| err.to_string())?;
        if let Some(parent) = self.path.parent() {
            fs::create_dir_all(parent).map_err(|err| err.to_string())?;
        }
        let mut file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(&self.path)
            .map_err(|err| err.to_string())?;
        let line = serde_json::to_string(&event).map_err(|err| err.to_string())?;
        writeln!(file, "{line}").map_err(|err| err.to_string())
    }

    fn events(&self) -> Result<Vec<AuditEvent>, String> {
        if !self.path.exists() {
            return Ok(Vec::new());
        }
        let file = OpenOptions::new()
            .read(true)
            .open(&self.path)
            .map_err(|err| err.to_string())?;
        let reader = BufReader::new(file);
        let mut events = Vec::new();
        for line in reader.lines() {
            let line = line.map_err(|err| err.to_string())?;
            if line.trim().is_empty() {
                continue;
            }
            let event = serde_json::from_str::<AuditEvent>(&line).map_err(|err| err.to_string())?;
            events.push(event);
        }
        Ok(events)
    }
}

pub struct CompositeAuditTrail {
    trails: Vec<Arc<dyn AuditTrail + Send + Sync>>,
}

impl CompositeAuditTrail {
    pub fn new(trails: Vec<Arc<dyn AuditTrail + Send + Sync>>) -> Self {
        Self { trails }
    }
}

impl AuditTrail for CompositeAuditTrail {
    fn append(&self, event: AuditEvent) -> Result<(), String> {
        for trail in &self.trails {
            trail.append(event.clone())?;
        }
        Ok(())
    }

    fn events(&self) -> Result<Vec<AuditEvent>, String> {
        let mut events = Vec::new();
        for trail in &self.trails {
            events.extend(trail.events()?);
        }
        Ok(events)
    }
}
