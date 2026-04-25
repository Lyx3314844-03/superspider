#[path = "ecommerce/detector.rs"]
mod detector;
#[path = "ecommerce/profile.rs"]
mod profile;

#[cfg(feature = "browser")]
use rustspider::browser::{BrowserConfig, BrowserManager};
#[cfg(feature = "browser")]
use serde_json::{json, Value};
#[cfg(feature = "browser")]
use std::{env, path::PathBuf, time::Duration};

#[cfg(feature = "browser")]
const USER_AGENT: &str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36";

#[cfg(feature = "browser")]
#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = env::args().collect();
    let site_family = args
        .get(1)
        .map(String::as_str)
        .unwrap_or(profile::DEFAULT_SITE_FAMILY);
    let mode = args.get(2).map(String::as_str).unwrap_or("catalog");
    let crawler = EcommerceBrowserCrawler::new(site_family);
    let payload = crawler.crawl(mode).await?;
    println!(
        "{}",
        serde_json::to_string_pretty(&json!({"artifacts": payload["artifacts"]}))?
    );
    Ok(())
}

#[cfg(feature = "browser")]
pub struct EcommerceBrowserCrawler {
    site_family: String,
    output_dir: PathBuf,
}

#[cfg(feature = "browser")]
impl EcommerceBrowserCrawler {
    pub fn new(site_family: &str) -> Self {
        Self {
            site_family: site_family.to_string(),
            output_dir: PathBuf::from("artifacts").join("browser"),
        }
    }

    pub async fn crawl(&self, mode: &str) -> Result<Value, Box<dyn std::error::Error>> {
        capture_ecommerce_page(&self.site_family, mode, &self.output_dir).await
    }
}

#[cfg(feature = "browser")]
async fn capture_ecommerce_page(
    site_family: &str,
    mode: &str,
    artifact_dir: &PathBuf,
) -> Result<Value, Box<dyn std::error::Error>> {
    let profile_data = profile::profile_for_family(site_family);
    let normalized_mode = match mode {
        "detail" => "detail",
        "review" => "review",
        _ => "catalog",
    };
    let target_url = match normalized_mode {
        "detail" => profile_data.detail_url,
        "review" => profile_data.review_url,
        _ => profile_data.catalog_url,
    };
    let high_friction = is_high_friction_site(site_family);
    let headless = env_bool("ECOM_BROWSER_HEADLESS", !high_friction);
    let manual_seconds = env_usize(
        "ECOM_BROWSER_MANUAL_SECONDS",
        if high_friction { 180 } else { 0 },
    );
    let attempts = env_usize("ECOM_BROWSER_ATTEMPTS", if high_friction { 2 } else { 1 });
    let profile_dir = env::var("ECOM_BROWSER_PROFILE").unwrap_or_else(|_| {
        artifact_dir
            .join("profiles")
            .join(format!("rustspider-{site_family}"))
            .to_string_lossy()
            .to_string()
    });

    let config = BrowserConfig {
        headless,
        timeout: Duration::from_secs(60),
        user_agent: Some(USER_AGENT.to_string()),
        args: vec![
            format!("--user-data-dir={profile_dir}"),
            "--disable-blink-features=AutomationControlled".to_string(),
            "--disable-dev-shm-usage".to_string(),
            "--no-first-run".to_string(),
            "--no-default-browser-check".to_string(),
            "--window-size=1920,1080".to_string(),
        ],
        ..BrowserConfig::default()
    };
    let browser = BrowserManager::new(config).await?;
    browser.bypass_detection().await.ok();
    let mut html = String::new();
    let mut title = String::new();
    let mut current_url = target_url.to_string();
    let mut access_challenge = json!({"blocked": false, "signals": []});
    for attempt in 1..=attempts.max(1) {
        warmup_site(&browser, &origin_url(target_url)).await;
        browser.navigate(target_url).await?;
        wait_for_ecommerce_ready(&browser, if normalized_mode == "catalog" { 8 } else { 4 }).await;
        html = browser.get_html().await?;
        title = browser.get_title().await.unwrap_or_default();
        current_url = browser
            .get_url()
            .await
            .unwrap_or_else(|_| target_url.to_string());
        access_challenge = detect_access_challenge(&current_url, &title, &html);
        if !access_challenge["blocked"].as_bool().unwrap_or(false) {
            break;
        }
        if !headless && manual_seconds > 0 {
            eprintln!("access challenge detected, keep the browser open for {manual_seconds}s to complete login/verification manually");
            wait_for_manual_access(&browser, manual_seconds).await;
            wait_for_ecommerce_ready(&browser, if normalized_mode == "catalog" { 4 } else { 2 })
                .await;
            html = browser.get_html().await?;
            title = browser.get_title().await.unwrap_or_default();
            current_url = browser
                .get_url()
                .await
                .unwrap_or_else(|_| target_url.to_string());
            access_challenge = detect_access_challenge(&current_url, &title, &html);
            if !access_challenge["blocked"].as_bool().unwrap_or(false) {
                break;
            }
        }
        if attempt < attempts.max(1) {
            tokio::time::sleep(Duration::from_secs((attempt * 4) as u64)).await;
        }
    }
    let image_sources = extract_attr_values(
        &html,
        r#"<img[^>]+(?:src|data-src|data-lazy-img)=["']([^"']+)["']"#,
    );
    let links = extract_attr_values(&html, r#"<a[^>]+href=["']([^"']+)["']"#);
    let api_candidates = profile::extract_api_candidates(&html, 30);
    let sku_candidates = profile::collect_matches(&html, profile_data.item_id_patterns, 20);

    std::fs::create_dir_all(artifact_dir)?;
    let prefix = format!("rustspider-{site_family}-{normalized_mode}");
    let html_path = artifact_dir.join(format!("{prefix}.html"));
    let json_path = artifact_dir.join(format!("{prefix}.json"));
    let screenshot_path = artifact_dir.join(format!("{prefix}.png"));
    std::fs::write(&html_path, &html)?;
    browser
        .screenshot_to_file(&screenshot_path.to_string_lossy())
        .await
        .ok();

    let payload = json!({
        "kind": "ecommerce_browser_capture",
        "site_family": site_family,
        "mode": normalized_mode,
        "url": current_url,
        "title": title,
        "detector": detector::detect_ecommerce_site(&current_url, &html),
        "product_link_candidates": profile::collect_product_links(&current_url, links, &profile_data, 30),
        "sku_candidates": sku_candidates,
        "image_candidates": profile::collect_image_links(&current_url, image_sources.clone(), 30),
        "image_gallery": profile::extract_image_gallery(&current_url, &image_sources),
        "json_ld_products": profile::extract_json_ld_products(&html, 10),
        "bootstrap_products": profile::extract_bootstrap_products(&html, 10),
        "embedded_json_blocks": profile::extract_embedded_json_blocks(&html, 5, 2000),
        "api_candidates": api_candidates,
        "api_job_templates": profile::build_api_job_templates(&current_url, site_family, &api_candidates, &sku_candidates, 20),
        "access_challenge": access_challenge,
        "runtime": {
            "headless": headless,
            "user_data_dir": profile_dir,
            "attempts": attempts,
        },
        "parameter_table": profile::extract_parameter_table(&html),
        "coupons_promotions": profile::detect_coupons_promotions(&html),
        "stock_status": profile::extract_stock_status(&html),
        "artifacts": {
            "html": html_path,
            "json": json_path,
            "screenshot": screenshot_path,
        }
    });
    std::fs::write(&json_path, serde_json::to_vec_pretty(&payload)?)?;
    browser.close().await.ok();
    Ok(payload)
}

#[cfg(feature = "browser")]
async fn warmup_site(browser: &BrowserManager, url: &str) {
    if url.is_empty() {
        return;
    }
    if browser.navigate(url).await.is_ok() {
        tokio::time::sleep(Duration::from_millis(700)).await;
        let _ = browser
            .execute_script("window.scrollBy(0, Math.floor((window.innerHeight || 800) * 0.5));")
            .await;
        tokio::time::sleep(Duration::from_millis(500)).await;
    }
}

#[cfg(feature = "browser")]
async fn wait_for_manual_access(browser: &BrowserManager, timeout_seconds: usize) {
    let deadline = std::time::Instant::now() + Duration::from_secs(timeout_seconds as u64);
    while std::time::Instant::now() < deadline {
        let html = browser.get_html().await.unwrap_or_default();
        let title = browser.get_title().await.unwrap_or_default();
        let url = browser.get_url().await.unwrap_or_default();
        if !detect_access_challenge(&url, &title, &html)["blocked"]
            .as_bool()
            .unwrap_or(false)
        {
            return;
        }
        tokio::time::sleep(Duration::from_secs(3)).await;
    }
}

#[cfg(feature = "browser")]
fn detect_access_challenge(url: &str, title: &str, html: &str) -> Value {
    let haystack = format!("{url}\n{title}\n{html}").to_lowercase();
    let signals = [
        "captcha",
        "verify",
        "verification",
        "access denied",
        "robot",
        "安全验证",
        "验证",
        "滑块",
        "登录",
        "扫码",
        "风险",
        "异常",
    ];
    let matched: Vec<&str> = signals
        .iter()
        .copied()
        .filter(|signal| haystack.contains(&signal.to_lowercase()))
        .collect();
    json!({
        "blocked": !matched.is_empty(),
        "signals": matched,
        "url": url,
        "title": title,
    })
}

#[cfg(feature = "browser")]
async fn wait_for_ecommerce_ready(browser: &BrowserManager, scroll_rounds: usize) {
    for selector in [
        "[data-sku]",
        "[data-product-id]",
        ".gl-item",
        ".product",
        ".product-item",
        "[itemtype*='Product']",
    ] {
        if browser
            .wait_for_element(selector, Some(Duration::from_secs(5)))
            .await
            .is_ok()
        {
            break;
        }
    }
    for _ in 0..scroll_rounds.max(1) {
        let _ = browser
            .execute_script("window.scrollBy(0, Math.max(600, window.innerHeight || 800));")
            .await;
        tokio::time::sleep(Duration::from_millis(800)).await;
    }
}

#[cfg(feature = "browser")]
fn extract_attr_values(html: &str, pattern: &str) -> Vec<String> {
    regex::Regex::new(pattern)
        .map(|regex| {
            regex
                .captures_iter(html)
                .filter_map(|capture| capture.get(1).map(|m| m.as_str().to_string()))
                .collect()
        })
        .unwrap_or_default()
}

#[cfg(feature = "browser")]
fn is_high_friction_site(site_family: &str) -> bool {
    matches!(
        site_family.to_lowercase().as_str(),
        "jd" | "taobao" | "tmall" | "pdd" | "amazon"
    )
}

#[cfg(feature = "browser")]
fn env_bool(name: &str, fallback: bool) -> bool {
    env::var(name)
        .map(|value| {
            matches!(
                value.trim().to_lowercase().as_str(),
                "1" | "true" | "yes" | "on"
            )
        })
        .unwrap_or(fallback)
}

#[cfg(feature = "browser")]
fn env_usize(name: &str, fallback: usize) -> usize {
    env::var(name)
        .ok()
        .and_then(|value| value.trim().parse::<usize>().ok())
        .unwrap_or(fallback)
}

#[cfg(feature = "browser")]
fn origin_url(raw_url: &str) -> String {
    let Some((scheme, rest)) = raw_url.split_once("://") else {
        return String::new();
    };
    let host = rest.split('/').next().unwrap_or_default();
    if scheme.is_empty() || host.is_empty() {
        return String::new();
    }
    format!("{scheme}://{host}/")
}

#[cfg(not(feature = "browser"))]
fn main() {
    eprintln!("Run with `cargo run --example ecommerce_browser_capture --features browser -- <site-family> <catalog|detail|review>`.");
}
