use rustspider::{run_preflight, PreflightOptions};
use std::env;
use std::path::PathBuf;

fn main() {
    let mut args = env::args().skip(1);
    let mut json_output = false;
    let mut options = PreflightOptions::new();

    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--json" => json_output = true,
            "--writable-path" => {
                if let Some(path) = args.next() {
                    options = options.with_writable_path(PathBuf::from(path));
                } else {
                    eprintln!("missing value for --writable-path");
                    std::process::exit(2);
                }
            }
            "--network-target" => {
                if let Some(target) = args.next() {
                    options = options.with_network_target(target);
                } else {
                    eprintln!("missing value for --network-target");
                    std::process::exit(2);
                }
            }
            "--redis-url" => {
                if let Some(redis_url) = args.next() {
                    options = options.with_redis_url(redis_url);
                } else {
                    eprintln!("missing value for --redis-url");
                    std::process::exit(2);
                }
            }
            "--require-ffmpeg" => options = options.require_ffmpeg(),
            "--require-browser" => options = options.require_browser(),
            "--require-yt-dlp" => options = options.require_yt_dlp(),
            "--help" | "-h" => {
                print_help();
                return;
            }
            unknown => {
                eprintln!("unknown argument: {unknown}");
                print_help();
                std::process::exit(2);
            }
        }
    }

    let report = run_preflight(&options);
    if json_output {
        match report.to_json() {
            Ok(json) => println!("{json}"),
            Err(err) => {
                eprintln!("failed to render preflight JSON: {err}");
                std::process::exit(1);
            }
        }
    } else {
        print_text_report(&report);
    }

    if !report.is_success() {
        std::process::exit(1);
    }
}

fn print_help() {
    println!("rustspider preflight [--json] [--writable-path <path>] [--network-target <host:port>] [--redis-url <url>] [--require-ffmpeg] [--require-browser] [--require-yt-dlp]");
}

fn print_text_report(report: &rustspider::PreflightReport) {
    println!("rustspider preflight");
    println!("===================");
    for check in &report.checks {
        println!("[{:?}] {}: {}", check.status, check.name, check.details);
    }
    println!("summary: {}", report.summary());
}
