use std::collections::HashMap;

use rustspider::{
    KernelExecutor, MediaPlan, NativeCrawlPlan, NativeReactor, ParsePlan, TargetSpec,
    TransportPolicy,
};

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 2 {
        eprintln!("Usage: native_plan <url> [inline-body]");
        std::process::exit(1);
    }

    let url = args[1].clone();
    let inline_body = args.get(2).cloned();
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
            println!("url={}", result.url);
            println!("status={}", result.status_code);
            println!("body_len={}", result.body.len());
            println!("detected_media={:?}", result.detected_media);
        }
        Err(err) => {
            eprintln!("native_plan failed: {err}");
            std::process::exit(1);
        }
    }
}
