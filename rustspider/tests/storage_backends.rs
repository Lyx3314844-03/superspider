use rustspider::{
    storage_backend_support, DriverDatasetStore, DriverResultStore, ProcessDatasetStore,
    ProcessResultStore, StorageBackendConfig, StorageBackendKind,
};

#[test]
fn process_result_store_builds_postgres_command() {
    let store = ProcessResultStore::new(StorageBackendConfig {
        kind: StorageBackendKind::Postgres,
        endpoint: "postgres://user:secret@localhost:5432/spider?sslmode=disable".to_string(),
        table: Some("results".to_string()),
        collection: None,
    });
    let specs = store
        .build_upsert_commands("job-1", &serde_json::json!({"status":"ok"}))
        .expect("postgres commands");
    assert_eq!(specs[0].program, "psql");
    assert_eq!(
        specs[0].env.get("PGPASSWORD").map(String::as_str),
        Some("secret")
    );
}

#[test]
fn process_result_store_builds_mysql_and_mongo_commands() {
    let mysql = ProcessResultStore::new(StorageBackendConfig {
        kind: StorageBackendKind::MySql,
        endpoint: "mysql://user:secret@localhost:3306/spider".to_string(),
        table: Some("results".to_string()),
        collection: None,
    });
    let mysql_specs = mysql
        .build_upsert_commands("job-1", &serde_json::json!({"status":"ok"}))
        .expect("mysql commands");
    assert_eq!(mysql_specs[0].program, "mysql");

    let mongo = ProcessResultStore::new(StorageBackendConfig {
        kind: StorageBackendKind::MongoDb,
        endpoint: "mongodb://localhost:27017/spider".to_string(),
        table: None,
        collection: Some("results".to_string()),
    });
    let mongo_specs = mongo
        .build_upsert_commands("job-1", &serde_json::json!({"status":"ok"}))
        .expect("mongo commands");
    assert_eq!(mongo_specs[0].program, "mongosh");
    assert_eq!(
        storage_backend_support()["native_process"]["postgres"]["commands"][0],
        "psql"
    );
}

#[test]
fn process_dataset_store_builds_insert_commands() {
    let mongo = ProcessDatasetStore::new(StorageBackendConfig {
        kind: StorageBackendKind::MongoDb,
        endpoint: "mongodb://localhost:27017/spider".to_string(),
        table: None,
        collection: Some("dataset_rows".to_string()),
    });
    let specs = mongo
        .build_insert_commands(&serde_json::json!({"id":"row-1","title":"demo"}))
        .expect("mongo dataset commands");
    assert_eq!(specs[0].program, "mongosh");
}

#[test]
fn driver_backends_are_exposed_in_support_payload() {
    let support = storage_backend_support();
    assert_eq!(
        support["native_driver"]["postgres"]["adapter_engine"],
        "postgres"
    );
    assert_eq!(support["native_driver"]["mysql"]["adapter_engine"], "mysql");
    assert_eq!(
        support["native_driver"]["mongodb"]["adapter_engine"],
        "mongodb-sync"
    );
    let _ = DriverResultStore::new(StorageBackendConfig {
        kind: StorageBackendKind::Postgres,
        endpoint: "postgres://localhost/spider".to_string(),
        table: Some("results".to_string()),
        collection: None,
    });
    let _ = DriverDatasetStore::new(StorageBackendConfig {
        kind: StorageBackendKind::MongoDb,
        endpoint: "mongodb://localhost:27017/spider".to_string(),
        table: None,
        collection: Some("dataset".to_string()),
    });
}

#[test]
fn dataset_store_env_helpers_build_expected_backends() {
    std::env::set_var("RUSTSPIDER_STORAGE_MODE", "driver");
    std::env::set_var("RUSTSPIDER_STORAGE_BACKEND", "postgres");
    std::env::set_var("RUSTSPIDER_STORAGE_ENDPOINT", "postgres://localhost/spider");
    assert!(rustspider::storage_backends::configured_driver_dataset_store_from_env().is_some());

    std::env::set_var("RUSTSPIDER_STORAGE_MODE", "process");
    std::env::set_var("RUSTSPIDER_STORAGE_BACKEND", "mongodb");
    std::env::set_var(
        "RUSTSPIDER_STORAGE_ENDPOINT",
        "mongodb://localhost:27017/spider",
    );
    assert!(rustspider::storage_backends::configured_process_dataset_store_from_env().is_some());
}

#[test]
fn configured_process_result_store_style_env_values_are_supported() {
    let store = ProcessResultStore::new(StorageBackendConfig {
        kind: StorageBackendKind::Postgres,
        endpoint: "postgres://user:secret@localhost:5432/spider?sslmode=disable".to_string(),
        table: Some("results".to_string()),
        collection: None,
    });
    assert!(store
        .build_upsert_commands("job-2", &serde_json::json!({"status":"ok"}))
        .is_ok());
}
