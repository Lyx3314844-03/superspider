use std::collections::HashMap;
use std::io::{self, Write};

use rustspider::{
    KernelExecutor, MediaPlan, NativeCrawlPlan, NativeReactor, ParsePlan, TargetSpec,
    TransportPolicy,
};
use serde_json::json;

/// Sidecar 模式：通过 stdin 接收 JSON 输入，通过 stdout 输出 JSON 结果
fn run_sidecar_mode() -> Result<(), Box<dyn std::error::Error>> {
    let mut input = String::new();
    io::stdin().read_line(&mut input)?;

    let plan_spec: serde_json::Value = serde_json::from_str(&input)?;

    let url = plan_spec["url"].as_str().unwrap_or("").to_string();
    let method = plan_spec["method"].as_str().unwrap_or("GET").to_string();
    let capture_body = plan_spec["capture_body"].as_bool().unwrap_or(true);
    let detect_media = plan_spec["detect_media"].as_bool().unwrap_or(true);

    let headers: HashMap<String, String> = if let Some(obj) = plan_spec.get("headers") {
        obj.as_object()
            .map(|m| {
                m.iter()
                    .map(|(k, v)| (k.clone(), v.as_str().unwrap_or("").to_string()))
                    .collect()
            })
            .unwrap_or_default()
    } else {
        HashMap::new()
    };

    let inline_body = plan_spec
        .get("inline_body")
        .and_then(|v| v.as_str())
        .map(String::from);

    let reactor = NativeReactor::new();
    let plan = NativeCrawlPlan {
        target: TargetSpec {
            url: url.clone(),
            method,
            headers,
            inline_body,
            cookies: HashMap::new(),
            proxy: None,
            allowed_domains: Vec::new(),
        },
        transport: TransportPolicy::default(),
        parse: ParsePlan { capture_body },
        media: MediaPlan { detect_media },
        ..Default::default()
    };

    match reactor.execute(plan) {
        Ok(result) => {
            let output = json!({
                "success": true,
                "url": result.url,
                "status_code": result.status_code,
                "body_length": result.body.len(),
                "detected_media": result.detected_media,
                "body": if capture_body { result.body } else { String::new() }
            });

            let stdout = io::stdout();
            let mut handle = stdout.lock();
            writeln!(handle, "{}", serde_json::to_string(&output)?)?;
            handle.flush()?;
        }
        Err(err) => {
            let output = json!({
                "success": false,
                "error": err.to_string()
            });

            let stdout = io::stdout();
            let mut handle = stdout.lock();
            writeln!(handle, "{}", serde_json::to_string(&output)?)?;
            handle.flush()?;
        }
    }

    Ok(())
}

fn main() {
    let args: Vec<String> = std::env::args().collect();

    // 检查是否是 sidecar 模式
    let sidecar_mode = args.iter().any(|arg| arg == "--sidecar" || arg == "-s");

    if sidecar_mode {
        if let Err(err) = run_sidecar_mode() {
            eprintln!("sidecar mode failed: {err}");
            std::process::exit(1);
        }
        return;
    }

    // 传统 CLI 模式
    if args.len() < 2 {
        eprintln!("Usage: native_plan_json <url> [inline-body]");
        eprintln!(
            "       native_plan_json --sidecar  (read JSON from stdin, output JSON to stdout)"
        );
        std::process::exit(1);
    }

    let url = args[1].clone();
    let inline_body = args.get(2).cloned();

    // 检查是否需要 JSON 输出
    let json_output = args.iter().any(|arg| arg == "--json" || arg == "-j");

    let reactor = NativeReactor::new();
    let plan = NativeCrawlPlan {
        target: TargetSpec {
            url: url.clone(),
            method: "GET".to_string(),
            headers: HashMap::new(),
            inline_body,
            cookies: HashMap::new(),
            proxy: None,
            allowed_domains: Vec::new(),
        },
        transport: TransportPolicy::default(),
        parse: ParsePlan { capture_body: true },
        media: MediaPlan { detect_media: true },
        ..Default::default()
    };

    match reactor.execute(plan) {
        Ok(result) => {
            if json_output {
                let output = json!({
                    "url": result.url,
                    "status_code": result.status_code,
                    "body_length": result.body.len(),
                    "detected_media": result.detected_media,
                    "body": result.body
                });
                println!("{}", serde_json::to_string_pretty(&output).unwrap());
            } else {
                println!("url={}", result.url);
                println!("status={}", result.status_code);
                println!("body_len={}", result.body.len());
                println!("detected_media={:?}", result.detected_media);
            }
        }
        Err(err) => {
            eprintln!("native_plan failed: {err}");
            std::process::exit(1);
        }
    }
}
