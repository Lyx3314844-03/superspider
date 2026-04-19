use rustspider::async_research::{AsyncResearchConfig, AsyncResearchRuntime};
use rustspider::notebook_output::ExperimentTracker;
use rustspider::research::{ResearchJob, ResearchRuntime};
use serde_json::{Map, Value};

fn title_schema() -> Map<String, Value> {
    let mut properties = Map::new();
    properties.insert("title".to_string(), serde_json::json!({"type": "string"}));
    let mut schema = Map::new();
    schema.insert("properties".to_string(), Value::Object(properties));
    schema
}

#[test]
fn research_job_is_constructible() {
    let job = ResearchJob {
        seed_urls: vec!["https://example.com".to_string()],
        ..ResearchJob::default()
    };
    assert_eq!(job.seed_urls, vec!["https://example.com".to_string()]);
}

#[test]
fn research_runtime_runs_job() {
    let runtime = ResearchRuntime::new();
    let job = ResearchJob {
        seed_urls: vec!["https://example.com".to_string()],
        extract_schema: title_schema(),
        ..ResearchJob::default()
    };

    let result = runtime
        .run(&job, Some("<title>Rust Research Demo</title>"))
        .expect("research runtime should succeed");

    assert_eq!(result["extract"]["title"], "Rust Research Demo");
}

#[test]
fn research_runtime_writes_jsonl_dataset() {
    let runtime = ResearchRuntime::new();
    let output_path =
        std::env::temp_dir().join(format!("rust-research-{}.jsonl", std::process::id()));
    let mut output = Map::new();
    output.insert("format".to_string(), Value::String("jsonl".to_string()));
    output.insert(
        "path".to_string(),
        Value::String(output_path.to_string_lossy().to_string()),
    );
    let job = ResearchJob {
        seed_urls: vec!["https://example.com".to_string()],
        extract_schema: title_schema(),
        output,
        ..ResearchJob::default()
    };

    let result = runtime
        .run(&job, Some("<title>Rust Dataset Demo</title>"))
        .expect("research runtime should succeed");

    assert_eq!(
        result["dataset"]["path"].as_str().unwrap_or_default(),
        output_path.to_string_lossy()
    );
    assert!(output_path.exists());
    let _ = std::fs::remove_file(output_path);
}

#[test]
fn research_runtime_validates_required_and_schema_for_specs() {
    let runtime = ResearchRuntime::new();
    let mut properties = Map::new();
    properties.insert("price".to_string(), serde_json::json!({"type": "number"}));
    let mut schema = Map::new();
    schema.insert("properties".to_string(), Value::Object(properties));
    let spec = serde_json::Map::from_iter([
        ("field".to_string(), Value::String("price".to_string())),
        ("type".to_string(), Value::String("regex".to_string())),
        (
            "expr".to_string(),
            Value::String(r"price:\s*(\w+)".to_string()),
        ),
        ("required".to_string(), Value::Bool(true)),
    ]);
    let job = ResearchJob {
        seed_urls: vec!["https://example.com".to_string()],
        extract_schema: schema,
        extract_specs: vec![spec],
        ..ResearchJob::default()
    };

    let err = runtime
        .run(&job, Some("<title>Demo</title>\nprice: free"))
        .expect_err("schema validation should fail");
    assert!(err.to_string().contains("schema.type=number"));
}

#[test]
fn research_runtime_supports_xpath_and_json_path_specs() {
    let runtime = ResearchRuntime::new();
    let css_job = ResearchJob {
        seed_urls: vec!["https://example.com".to_string()],
        extract_specs: vec![
            serde_json::Map::from_iter([
                ("field".to_string(), Value::String("title".to_string())),
                ("type".to_string(), Value::String("css".to_string())),
                ("expr".to_string(), Value::String("title".to_string())),
                ("required".to_string(), Value::Bool(true)),
            ]),
            serde_json::Map::from_iter([
                ("field".to_string(), Value::String("cover".to_string())),
                ("type".to_string(), Value::String("css_attr".to_string())),
                (
                    "expr".to_string(),
                    Value::String("meta[name=\"og:image\"]".to_string()),
                ),
                ("attr".to_string(), Value::String("content".to_string())),
                ("required".to_string(), Value::Bool(true)),
            ]),
        ],
        ..ResearchJob::default()
    };
    let css_result = runtime
        .run(
            &css_job,
            Some(
                r#"<html><head><title>CSS Demo</title><meta name="og:image" content="https://img.example.com/cover.jpg" /></head></html>"#,
            ),
        )
        .expect("css extraction should succeed");
    assert_eq!(css_result["extract"]["title"], "CSS Demo");
    assert_eq!(
        css_result["extract"]["cover"],
        "https://img.example.com/cover.jpg"
    );

    let xpath_job = ResearchJob {
        seed_urls: vec!["https://example.com".to_string()],
        extract_specs: vec![serde_json::Map::from_iter([
            ("field".to_string(), Value::String("title".to_string())),
            ("type".to_string(), Value::String("xpath".to_string())),
            (
                "expr".to_string(),
                Value::String("//title/text()".to_string()),
            ),
            ("required".to_string(), Value::Bool(true)),
        ])],
        ..ResearchJob::default()
    };
    let xpath_result = runtime
        .run(&xpath_job, Some("<html><title>XPath Demo</title></html>"))
        .expect("xpath extraction should succeed");
    assert_eq!(xpath_result["extract"]["title"], "XPath Demo");

    let json_job = ResearchJob {
        seed_urls: vec!["https://example.com".to_string()],
        extract_specs: vec![serde_json::Map::from_iter([
            ("field".to_string(), Value::String("name".to_string())),
            ("type".to_string(), Value::String("json_path".to_string())),
            (
                "path".to_string(),
                Value::String("$.product.name".to_string()),
            ),
            ("required".to_string(), Value::Bool(true)),
        ])],
        ..ResearchJob::default()
    };
    let json_result = runtime
        .run(&json_job, Some(r#"{"product":{"name":"Capsule"}}"#))
        .expect("json path extraction should succeed");
    assert_eq!(json_result["extract"]["name"], "Capsule");
}

#[tokio::test]
async fn async_research_runtime_runs_multiple_jobs() {
    let runtime = AsyncResearchRuntime::new(Some(AsyncResearchConfig {
        max_concurrent: 2,
        timeout_seconds: 10.0,
        enable_streaming: false,
    }));
    let jobs = vec![
        ResearchJob {
            seed_urls: vec!["https://example.com/1".to_string()],
            extract_schema: title_schema(),
            ..ResearchJob::default()
        },
        ResearchJob {
            seed_urls: vec!["https://example.com/2".to_string()],
            extract_schema: title_schema(),
            ..ResearchJob::default()
        },
    ];
    let results = runtime
        .run_multiple(
            jobs,
            Some(vec![
                "<title>One</title>".to_string(),
                "<title>Two</title>".to_string(),
            ]),
        )
        .await;

    assert_eq!(results.len(), 2);
    assert!(results.iter().all(|result| result.error.is_none()));
    assert_eq!(runtime.snapshot_metrics()["tasks_completed"], 2);
}

#[tokio::test]
async fn async_research_runtime_supports_stream_and_soak() {
    let runtime = AsyncResearchRuntime::new(Some(AsyncResearchConfig {
        max_concurrent: 2,
        timeout_seconds: 10.0,
        enable_streaming: false,
    }));
    let jobs = vec![
        ResearchJob {
            seed_urls: vec!["https://example.com/1".to_string()],
            extract_schema: title_schema(),
            policy: serde_json::Map::from_iter([(
                "simulate_delay_ms".to_string(),
                Value::Number(10.into()),
            )]),
            ..ResearchJob::default()
        },
        ResearchJob {
            seed_urls: vec!["https://example.com/2".to_string()],
            extract_schema: title_schema(),
            policy: serde_json::Map::from_iter([(
                "simulate_delay_ms".to_string(),
                Value::Number(10.into()),
            )]),
            ..ResearchJob::default()
        },
    ];

    let stream_results = runtime
        .run_stream(
            jobs.clone(),
            Some(vec![
                "<title>One</title>".to_string(),
                "<title>Two</title>".to_string(),
            ]),
        )
        .await;
    assert_eq!(stream_results.len(), 2);
    assert!(stream_results.iter().all(|result| result.error.is_none()));

    let soak = runtime
        .run_soak(
            jobs,
            Some(vec![
                "<title>One</title>".to_string(),
                "<title>Two</title>".to_string(),
            ]),
            2,
        )
        .await;
    assert_eq!(soak["results"], 4);
    assert_eq!(soak["stable"], true);
}

#[test]
fn experiment_tracker_records_and_compares() {
    let mut tracker = ExperimentTracker::default();
    let record = tracker.record(
        "exp-1",
        vec!["https://example.com".to_string()],
        vec![serde_json::json!({
            "seed": "https://example.com",
            "extract": {"title": "Demo"},
            "duration_ms": 100.0
        })],
        Some(serde_json::json!({"type": "object"})),
        None,
    );

    assert_eq!(record.id, "exp-001");
    assert!(tracker.get_experiment("exp-1").is_some());
    assert_eq!(tracker.to_rows().len(), 1);
    assert_eq!(tracker.compare()["summary"]["total_experiments"], 1);
}
