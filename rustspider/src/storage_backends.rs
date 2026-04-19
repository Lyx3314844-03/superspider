use mongodb::bson::{doc, Document};
use mongodb::options::ReplaceOptions;
use mongodb::sync::Client as MongoClient;
use mysql::params;
use mysql::prelude::Queryable;
use postgres::{Client as PostgresClient, NoTls};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::BTreeMap;
use std::error::Error;
use std::io::{Error as IoError, ErrorKind, Write};
use std::process::{Command, Stdio};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum StorageBackendKind {
    Postgres,
    MySql,
    MongoDb,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StorageBackendConfig {
    pub kind: StorageBackendKind,
    pub endpoint: String,
    pub table: Option<String>,
    pub collection: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StorageCommandSpec {
    pub program: String,
    pub args: Vec<String>,
    pub env: BTreeMap<String, String>,
    pub stdin: Option<String>,
}

#[derive(Default)]
pub struct ProcessResultStore {
    config: Option<StorageBackendConfig>,
    memory: parking_lot::Mutex<BTreeMap<String, Value>>,
}

#[derive(Default)]
pub struct ProcessDatasetStore {
    config: Option<StorageBackendConfig>,
    rows: parking_lot::Mutex<Vec<Value>>,
}

impl ProcessResultStore {
    pub fn new(config: StorageBackendConfig) -> Self {
        Self {
            config: Some(config),
            memory: parking_lot::Mutex::new(BTreeMap::new()),
        }
    }

    pub fn put_json(&self, id: &str, payload: &Value) -> Result<(), Box<dyn Error>> {
        self.memory.lock().insert(id.to_string(), payload.clone());
        let mut last_error: Option<Box<dyn Error>> = None;
        for spec in self.build_upsert_commands(id, payload)? {
            let mut command = Command::new(&spec.program);
            command.args(&spec.args);
            if !spec.env.is_empty() {
                command.envs(&spec.env);
            }
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
                "no storage backend command available",
            ))
        }))
    }

    pub fn get_json(&self, id: &str) -> Option<Value> {
        self.memory.lock().get(id).cloned()
    }

    pub fn list_json(&self) -> Vec<Value> {
        self.memory.lock().values().cloned().collect()
    }

    pub fn build_upsert_commands(
        &self,
        id: &str,
        payload: &Value,
    ) -> Result<Vec<StorageCommandSpec>, Box<dyn Error>> {
        let config = self
            .config
            .clone()
            .ok_or("missing storage backend config")?;
        match config.kind {
            StorageBackendKind::Postgres => build_postgres_commands(&config, id, payload),
            StorageBackendKind::MySql => build_mysql_commands(&config, id, payload),
            StorageBackendKind::MongoDb => build_mongo_commands(&config, id, payload),
        }
    }
}

impl ProcessDatasetStore {
    pub fn new(config: StorageBackendConfig) -> Self {
        Self {
            config: Some(config),
            rows: parking_lot::Mutex::new(Vec::new()),
        }
    }

    pub fn push_json(&self, payload: &Value) -> Result<(), Box<dyn Error>> {
        self.rows.lock().push(payload.clone());
        let mut last_error: Option<Box<dyn Error>> = None;
        for spec in self.build_insert_commands(payload)? {
            let mut command = Command::new(&spec.program);
            command.args(&spec.args);
            if !spec.env.is_empty() {
                command.envs(&spec.env);
            }
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
                "no dataset backend command available",
            ))
        }))
    }

    pub fn build_insert_commands(
        &self,
        payload: &Value,
    ) -> Result<Vec<StorageCommandSpec>, Box<dyn Error>> {
        let config = self
            .config
            .clone()
            .ok_or("missing storage backend config")?;
        match config.kind {
            StorageBackendKind::Postgres => {
                let record_id = payload
                    .get("id")
                    .and_then(Value::as_str)
                    .unwrap_or("dataset-row");
                build_postgres_commands(&config, record_id, payload)
            }
            StorageBackendKind::MySql => {
                let record_id = payload
                    .get("id")
                    .and_then(Value::as_str)
                    .unwrap_or("dataset-row");
                build_mysql_commands(&config, record_id, payload)
            }
            StorageBackendKind::MongoDb => build_mongo_insert_commands(&config, payload),
        }
    }
}

pub fn storage_backend_support() -> Value {
    serde_json::json!({
        "native_driver": {
            "postgres": { "mode": "driver", "adapter_engine": "postgres" },
            "mysql": { "mode": "driver", "adapter_engine": "mysql" },
            "mongodb": { "mode": "driver", "adapter_engine": "mongodb-sync" }
        },
        "native_process": {
            "postgres": { "mode": "cli-adapter", "commands": ["psql"] },
            "mysql": { "mode": "cli-adapter", "commands": ["mysql"] },
            "mongodb": { "mode": "cli-adapter", "commands": ["mongosh"] }
        }
    })
}

pub fn configured_process_dataset_store_from_env() -> Option<ProcessDatasetStore> {
    let mode = std::env::var("RUSTSPIDER_STORAGE_MODE")
        .ok()
        .unwrap_or_default()
        .trim()
        .to_lowercase();
    if mode == "driver" {
        return None;
    }
    let backend = std::env::var("RUSTSPIDER_DATASET_BACKEND")
        .ok()
        .filter(|v| !v.trim().is_empty())
        .unwrap_or_else(|| std::env::var("RUSTSPIDER_STORAGE_BACKEND").unwrap_or_default())
        .trim()
        .to_lowercase();
    let endpoint = std::env::var("RUSTSPIDER_DATASET_ENDPOINT")
        .ok()
        .filter(|v| !v.trim().is_empty())
        .unwrap_or_else(|| std::env::var("RUSTSPIDER_STORAGE_ENDPOINT").unwrap_or_default())
        .trim()
        .to_string();
    if endpoint.is_empty() {
        return None;
    }
    let kind = match backend.as_str() {
        "postgres" | "postgresql" => StorageBackendKind::Postgres,
        "mysql" => StorageBackendKind::MySql,
        "mongo" | "mongodb" => StorageBackendKind::MongoDb,
        _ => return None,
    };
    Some(ProcessDatasetStore::new(StorageBackendConfig {
        kind,
        endpoint,
        table: std::env::var("RUSTSPIDER_DATASET_TABLE")
            .ok()
            .filter(|v| !v.trim().is_empty())
            .or_else(|| {
                std::env::var("RUSTSPIDER_STORAGE_TABLE")
                    .ok()
                    .filter(|v| !v.trim().is_empty())
            }),
        collection: std::env::var("RUSTSPIDER_DATASET_COLLECTION")
            .ok()
            .filter(|v| !v.trim().is_empty())
            .or_else(|| {
                std::env::var("RUSTSPIDER_STORAGE_COLLECTION")
                    .ok()
                    .filter(|v| !v.trim().is_empty())
            }),
    }))
}

pub fn configured_driver_dataset_store_from_env() -> Option<DriverDatasetStore> {
    let mode = std::env::var("RUSTSPIDER_STORAGE_MODE")
        .ok()?
        .trim()
        .to_lowercase();
    if mode != "driver" {
        return None;
    }
    let backend = std::env::var("RUSTSPIDER_DATASET_BACKEND")
        .ok()
        .filter(|v| !v.trim().is_empty())
        .unwrap_or_else(|| std::env::var("RUSTSPIDER_STORAGE_BACKEND").unwrap_or_default())
        .trim()
        .to_lowercase();
    let endpoint = std::env::var("RUSTSPIDER_DATASET_ENDPOINT")
        .ok()
        .filter(|v| !v.trim().is_empty())
        .unwrap_or_else(|| std::env::var("RUSTSPIDER_STORAGE_ENDPOINT").unwrap_or_default())
        .trim()
        .to_string();
    if endpoint.is_empty() {
        return None;
    }
    let kind = match backend.as_str() {
        "postgres" | "postgresql" => StorageBackendKind::Postgres,
        "mysql" => StorageBackendKind::MySql,
        "mongo" | "mongodb" => StorageBackendKind::MongoDb,
        _ => return None,
    };
    Some(DriverDatasetStore::new(StorageBackendConfig {
        kind,
        endpoint,
        table: std::env::var("RUSTSPIDER_DATASET_TABLE")
            .ok()
            .filter(|v| !v.trim().is_empty())
            .or_else(|| {
                std::env::var("RUSTSPIDER_STORAGE_TABLE")
                    .ok()
                    .filter(|v| !v.trim().is_empty())
            }),
        collection: std::env::var("RUSTSPIDER_DATASET_COLLECTION")
            .ok()
            .filter(|v| !v.trim().is_empty())
            .or_else(|| {
                std::env::var("RUSTSPIDER_STORAGE_COLLECTION")
                    .ok()
                    .filter(|v| !v.trim().is_empty())
            }),
    }))
}

#[derive(Default)]
pub struct DriverResultStore {
    config: Option<StorageBackendConfig>,
}

#[derive(Default)]
pub struct DriverDatasetStore {
    config: Option<StorageBackendConfig>,
}

impl DriverResultStore {
    pub fn new(config: StorageBackendConfig) -> Self {
        Self {
            config: Some(config),
        }
    }

    pub fn put_json(&self, id: &str, payload: &Value) -> Result<(), Box<dyn Error>> {
        let config = self
            .config
            .clone()
            .ok_or("missing storage backend config")?;
        match config.kind {
            StorageBackendKind::Postgres => self.put_postgres(&config, id, payload),
            StorageBackendKind::MySql => self.put_mysql(&config, id, payload),
            StorageBackendKind::MongoDb => self.put_mongo(&config, id, payload),
        }
    }

    fn put_postgres(
        &self,
        config: &StorageBackendConfig,
        id: &str,
        payload: &Value,
    ) -> Result<(), Box<dyn Error>> {
        let mut client = PostgresClient::connect(&config.endpoint, NoTls)?;
        let table = config
            .table
            .clone()
            .unwrap_or_else(|| "spider_results".to_string());
        client.batch_execute(&format!(
            "CREATE TABLE IF NOT EXISTS {table} (id TEXT PRIMARY KEY, payload JSONB NOT NULL, updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW())",
            table = table
        ))?;
        client.execute(
            &format!(
                "INSERT INTO {table} (id, payload, updated_at) VALUES ($1, $2::jsonb, NOW()) ON CONFLICT (id) DO UPDATE SET payload = EXCLUDED.payload, updated_at = EXCLUDED.updated_at",
                table = table
            ),
            &[&id, &payload.to_string()],
        )?;
        Ok(())
    }

    fn put_mysql(
        &self,
        config: &StorageBackendConfig,
        id: &str,
        payload: &Value,
    ) -> Result<(), Box<dyn Error>> {
        let opts = mysql::Opts::from_url(&config.endpoint)?;
        let pool = mysql::Pool::new(opts)?;
        let mut conn = pool.get_conn()?;
        let table = config
            .table
            .clone()
            .unwrap_or_else(|| "spider_results".to_string());
        conn.query_drop(format!(
            "CREATE TABLE IF NOT EXISTS {table} (id VARCHAR(255) PRIMARY KEY, payload JSON NOT NULL, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP)",
            table = table
        ))?;
        conn.exec_drop(
            format!(
                "INSERT INTO {table} (id, payload, updated_at) VALUES (:id, :payload, NOW()) ON DUPLICATE KEY UPDATE payload=VALUES(payload), updated_at=VALUES(updated_at)",
                table = table
            ),
            mysql::params! {
                "id" => id,
                "payload" => payload.to_string(),
            },
        )?;
        Ok(())
    }

    fn put_mongo(
        &self,
        config: &StorageBackendConfig,
        id: &str,
        payload: &Value,
    ) -> Result<(), Box<dyn Error>> {
        let client = MongoClient::with_uri_str(&config.endpoint)?;
        let database = mongo_database_name(&config.endpoint);
        let collection = config
            .collection
            .clone()
            .unwrap_or_else(|| "spider_results".to_string());
        let coll = client
            .database(&database)
            .collection::<Document>(&collection);
        let replacement = mongodb::bson::to_document(payload)?;
        coll.replace_one(
            doc! { "id": id },
            replacement,
            ReplaceOptions::builder().upsert(true).build(),
        )?;
        Ok(())
    }
}

impl DriverDatasetStore {
    pub fn new(config: StorageBackendConfig) -> Self {
        Self {
            config: Some(config),
        }
    }

    pub fn push_json(&self, payload: &Value) -> Result<(), Box<dyn Error>> {
        let config = self
            .config
            .clone()
            .ok_or("missing storage backend config")?;
        match config.kind {
            StorageBackendKind::Postgres => {
                let id = payload
                    .get("id")
                    .and_then(Value::as_str)
                    .unwrap_or("dataset-row");
                DriverResultStore::new(config.clone()).put_postgres(&config, id, payload)
            }
            StorageBackendKind::MySql => {
                let id = payload
                    .get("id")
                    .and_then(Value::as_str)
                    .unwrap_or("dataset-row");
                DriverResultStore::new(config.clone()).put_mysql(&config, id, payload)
            }
            StorageBackendKind::MongoDb => {
                let client = MongoClient::with_uri_str(&config.endpoint)?;
                let database = mongo_database_name(&config.endpoint);
                let collection = config
                    .collection
                    .clone()
                    .unwrap_or_else(|| "spider_dataset".to_string());
                let coll = client
                    .database(&database)
                    .collection::<Document>(&collection);
                coll.insert_one(mongodb::bson::to_document(payload)?, None)?;
                Ok(())
            }
        }
    }
}

fn build_postgres_commands(
    config: &StorageBackendConfig,
    id: &str,
    payload: &Value,
) -> Result<Vec<StorageCommandSpec>, Box<dyn Error>> {
    let uri = url::Url::parse(&config.endpoint)?;
    let table = config
        .table
        .clone()
        .unwrap_or_else(|| "spider_results".to_string());
    let sql = format!(
        "CREATE TABLE IF NOT EXISTS {table} (id TEXT PRIMARY KEY, payload JSONB NOT NULL, updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()); INSERT INTO {table} (id, payload, updated_at) VALUES ('{id}', $${payload}$$::jsonb, NOW()) ON CONFLICT (id) DO UPDATE SET payload = EXCLUDED.payload, updated_at = EXCLUDED.updated_at;",
        table = table,
        id = escape_sql(id),
        payload = payload
    );
    let mut env = BTreeMap::new();
    if let Some(password) = uri.password() {
        env.insert("PGPASSWORD".to_string(), password.to_string());
    }
    Ok(vec![StorageCommandSpec {
        program: "psql".to_string(),
        args: vec![
            config.endpoint.clone(),
            "-v".to_string(),
            "ON_ERROR_STOP=1".to_string(),
            "-c".to_string(),
            sql,
        ],
        env,
        stdin: None,
    }])
}

fn build_mysql_commands(
    config: &StorageBackendConfig,
    id: &str,
    payload: &Value,
) -> Result<Vec<StorageCommandSpec>, Box<dyn Error>> {
    let uri = url::Url::parse(&config.endpoint)?;
    let table = config
        .table
        .clone()
        .unwrap_or_else(|| "spider_results".to_string());
    let database = uri.path().trim_start_matches('/').to_string();
    let sql = format!(
        "CREATE TABLE IF NOT EXISTS {table} (id VARCHAR(255) PRIMARY KEY, payload JSON NOT NULL, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP); INSERT INTO {table} (id, payload, updated_at) VALUES ('{id}', '{payload}', NOW()) ON DUPLICATE KEY UPDATE payload=VALUES(payload), updated_at=VALUES(updated_at);",
        table = table,
        id = escape_sql(id),
        payload = escape_sql(&payload.to_string()),
    );
    let mut args = vec![
        "-h".to_string(),
        uri.host_str().unwrap_or("localhost").to_string(),
        "-P".to_string(),
        uri.port().unwrap_or(3306).to_string(),
        "-D".to_string(),
        database,
        "-e".to_string(),
        sql,
    ];
    if !uri.username().is_empty() {
        args.push("-u".to_string());
        args.push(uri.username().to_string());
    }
    if let Some(password) = uri.password() {
        args.push(format!("-p{password}"));
    }
    Ok(vec![StorageCommandSpec {
        program: "mysql".to_string(),
        args,
        env: BTreeMap::new(),
        stdin: None,
    }])
}

fn build_mongo_commands(
    config: &StorageBackendConfig,
    id: &str,
    payload: &Value,
) -> Result<Vec<StorageCommandSpec>, Box<dyn Error>> {
    let collection = config
        .collection
        .clone()
        .unwrap_or_else(|| "spider_results".to_string());
    let script = format!(
        r#"db.getCollection("{collection}").updateOne({{id: "{id}"}}, {{$set: {payload}}}, {{upsert: true}})"#,
        collection = collection,
        id = id,
        payload = payload
    );
    Ok(vec![StorageCommandSpec {
        program: "mongosh".to_string(),
        args: vec![
            config.endpoint.clone(),
            "--quiet".to_string(),
            "--eval".to_string(),
            script,
        ],
        env: BTreeMap::new(),
        stdin: None,
    }])
}

fn build_mongo_insert_commands(
    config: &StorageBackendConfig,
    payload: &Value,
) -> Result<Vec<StorageCommandSpec>, Box<dyn Error>> {
    let collection = config
        .collection
        .clone()
        .unwrap_or_else(|| "spider_dataset".to_string());
    let script = format!(
        r#"db.getCollection("{collection}").insertOne({payload})"#,
        collection = collection,
        payload = payload
    );
    Ok(vec![StorageCommandSpec {
        program: "mongosh".to_string(),
        args: vec![
            config.endpoint.clone(),
            "--quiet".to_string(),
            "--eval".to_string(),
            script,
        ],
        env: BTreeMap::new(),
        stdin: None,
    }])
}

fn escape_sql(value: &str) -> String {
    value.replace('\'', "''")
}

fn mongo_database_name(endpoint: &str) -> String {
    url::Url::parse(endpoint)
        .ok()
        .map(|uri| uri.path().trim_start_matches('/').to_string())
        .filter(|value| !value.is_empty())
        .unwrap_or_else(|| "spider".to_string())
}
