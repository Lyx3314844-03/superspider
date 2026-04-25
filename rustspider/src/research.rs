use scraper::{Html, Selector};
use serde::{Deserialize, Serialize};
use serde_json::{Map, Value};
use std::collections::BTreeMap;
use std::fs;
use std::path::Path;

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct ResearchJob {
    pub seed_urls: Vec<String>,
    #[serde(default)]
    pub site_profile: Map<String, Value>,
    #[serde(default)]
    pub extract_schema: Map<String, Value>,
    #[serde(default)]
    pub extract_specs: Vec<Map<String, Value>>,
    #[serde(default)]
    pub policy: Map<String, Value>,
    #[serde(default)]
    pub output: Map<String, Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SiteProfile {
    pub url: String,
    pub page_type: String,
    pub site_family: String,
    pub signals: BTreeMap<String, bool>,
    pub candidate_fields: Vec<String>,
    pub risk_level: String,
    pub crawler_type: String,
    pub runner_order: Vec<String>,
    pub strategy_hints: Vec<String>,
    pub job_templates: Vec<String>,
}

pub struct ResearchRuntime;

impl ResearchRuntime {
    pub fn new() -> Self {
        Self
    }

    pub fn run(
        &self,
        job: &ResearchJob,
        content: Option<&str>,
    ) -> Result<Value, Box<dyn std::error::Error>> {
        let seed = job
            .seed_urls
            .first()
            .cloned()
            .filter(|value| !value.trim().is_empty())
            .ok_or("seed_urls[0] is required")?;
        let resolved_content = content
            .filter(|value| !value.trim().is_empty())
            .map(|value| value.to_string())
            .unwrap_or_else(|| format!("<title>{seed}</title>"));
        let profile = profile_site(&seed, &resolved_content);
        let extract = extract_content(
            &resolved_content,
            job.extract_schema
                .get("properties")
                .and_then(|value| value.as_object()),
            &job.extract_specs,
        )?;

        let mut result = serde_json::json!({
            "seed": seed,
            "profile": profile,
            "extract": extract,
        });

        if let Some(path) = job.output.get("path").and_then(|value| value.as_str()) {
            let format = job
                .output
                .get("format")
                .and_then(|value| value.as_str())
                .unwrap_or_else(|| detect_format(path));
            let dataset = write_dataset(path, format, &extract)?;
            result["dataset"] = dataset;
        }

        Ok(result)
    }
}

impl Default for ResearchRuntime {
    fn default() -> Self {
        Self::new()
    }
}

pub fn profile_site(url: &str, content: &str) -> SiteProfile {
    let lower = content.to_ascii_lowercase();
    let compact = lower.replace(' ', "");
    let url_lower = url.to_ascii_lowercase();
    let site_family = resolve_site_family(&url_lower);
    let has_search_query = ["/search", "search?", "keyword=", "q=", "query=", "wd="]
        .iter()
        .any(|token| url_lower.contains(token));
    let signals = BTreeMap::from([
        ("has_form".to_string(), lower.contains("<form")),
        (
            "has_pagination".to_string(),
            lower.contains("next")
                || lower.contains("page=")
                || lower.contains("pagination")
                || content.contains("下一页"),
        ),
        (
            "has_list".to_string(),
            lower.contains("<li")
                || lower.contains("<ul")
                || lower.contains("<ol")
                || lower.contains("product-list")
                || lower.contains("goods-list")
                || lower.contains("sku-item"),
        ),
        (
            "has_detail".to_string(),
            lower.contains("<article") || lower.contains("<h1"),
        ),
        (
            "has_captcha".to_string(),
            lower.contains("captcha")
                || lower.contains("verify")
                || lower.contains("human verification")
                || content.contains("滑块")
                || content.contains("验证码"),
        ),
        (
            "has_price".to_string(),
            lower.contains("price")
                || lower.contains("\"price\"")
                || content.contains("￥")
                || content.contains("¥")
                || content.contains("价格"),
        ),
        (
            "has_search".to_string(),
            has_search_query
                || lower.contains("type=\"search\"")
                || content.contains("搜索")
                || lower.contains("search-input"),
        ),
        (
            "has_login".to_string(),
            lower.contains("type=\"password\"")
                || lower.contains("sign in")
                || lower.contains("signin")
                || content.contains("登录"),
        ),
        (
            "has_hydration".to_string(),
            lower.contains("__next_data__")
                || lower.contains("__next_f")
                || lower.contains("__nuxt__")
                || lower.contains("__apollo_state__")
                || lower.contains("__initial_state__")
                || lower.contains("__preloaded_state__")
                || lower.contains("window.__initial_data__"),
        ),
        (
            "has_api_bootstrap".to_string(),
            lower.contains("__initial_state__")
                || lower.contains("__preloaded_state__")
                || lower.contains("__next_data__")
                || lower.contains("__apollo_state__")
                || lower.contains("application/json")
                || lower.contains("window.__initial_data__"),
        ),
        (
            "has_infinite_scroll".to_string(),
            lower.contains("load more")
                || lower.contains("infinite")
                || lower.contains("intersectionobserver")
                || lower.contains("onscroll")
                || lower.contains("virtual-list")
                || content.contains("加载更多"),
        ),
        ("has_graphql".to_string(), lower.contains("graphql")),
        (
            "has_reviews".to_string(),
            lower.contains("review") || content.contains("评价") || lower.contains("comments"),
        ),
        (
            "has_product_schema".to_string(),
            compact.contains("\"@type\":\"product\"") || compact.contains("\"@type\":\"offer\""),
        ),
        (
            "has_cart".to_string(),
            lower.contains("add to cart")
                || content.contains("购物车")
                || lower.contains("buy-now")
                || content.contains("立即购买"),
        ),
        (
            "has_sku".to_string(),
            lower.contains("sku")
                || content.contains("商品编号")
                || url_lower.contains("item.jd.com")
                || url_lower.contains("/item.htm"),
        ),
        (
            "has_image".to_string(),
            lower.contains("<img") || lower.contains("og:image"),
        ),
    ]);
    let crawler_type = resolve_crawler_type(&signals, "");
    let page_type = match crawler_type.as_str() {
        "static_listing" | "search_results" | "ecommerce_search" | "infinite_scroll_listing" => {
            "list"
        }
        "static_detail" | "ecommerce_detail" => "detail",
        _ if *signals.get("has_list").unwrap_or(&false)
            && !*signals.get("has_detail").unwrap_or(&false) =>
        {
            "list"
        }
        _ if *signals.get("has_detail").unwrap_or(&false) => "detail",
        _ => "generic",
    };

    let mut candidate_fields = Vec::new();
    if lower.contains("<title") {
        candidate_fields.push("title".to_string());
    }
    if *signals.get("has_price").unwrap_or(&false) {
        candidate_fields.push("price".to_string());
    }
    if lower.contains("author") || content.contains("作者") {
        candidate_fields.push("author".to_string());
    }
    if *signals.get("has_sku").unwrap_or(&false) {
        candidate_fields.push("sku".to_string());
    }
    if *signals.get("has_reviews").unwrap_or(&false) {
        candidate_fields.push("rating".to_string());
    }
    if *signals.get("has_search").unwrap_or(&false) {
        candidate_fields.push("keyword".to_string());
    }
    if *signals.get("has_image").unwrap_or(&false) {
        candidate_fields.push("image".to_string());
    }
    if lower.contains("shop") || lower.contains("seller") || content.contains("店铺") {
        candidate_fields.push("shop".to_string());
    }
    if lower.contains("description") || content.contains("详情") {
        candidate_fields.push("description".to_string());
    }
    candidate_fields.sort();
    candidate_fields.dedup();

    let risk_level = if *signals.get("has_captcha").unwrap_or(&false) {
        "high"
    } else if url.to_ascii_lowercase().starts_with("https://")
        && (*signals.get("has_form").unwrap_or(&false)
            || *signals.get("has_login").unwrap_or(&false)
            || *signals.get("has_hydration").unwrap_or(&false)
            || *signals.get("has_graphql").unwrap_or(&false))
    {
        "medium"
    } else {
        "low"
    };
    let runner_order = resolve_runner_order(&crawler_type, &signals);

    SiteProfile {
        url: url.to_string(),
        page_type: page_type.to_string(),
        site_family,
        signals,
        candidate_fields,
        risk_level: risk_level.to_string(),
        crawler_type: crawler_type.clone(),
        runner_order: runner_order.clone(),
        strategy_hints: resolve_strategy_hints(&crawler_type, &runner_order),
        job_templates: resolve_job_templates(&crawler_type, &url_lower),
    }
}

fn resolve_site_family(url_lower: &str) -> String {
    let mapping = [
        ("jd.com", "jd"),
        ("3.cn", "jd"),
        ("taobao.com", "taobao"),
        ("tmall.com", "tmall"),
        ("pinduoduo.com", "pinduoduo"),
        ("yangkeduo.com", "pinduoduo"),
        ("xiaohongshu.com", "xiaohongshu"),
        ("xhslink.com", "xiaohongshu"),
        ("douyin.com", "douyin-shop"),
        ("jinritemai.com", "douyin-shop"),
    ];
    for (suffix, family) in mapping {
        if url_lower.contains(suffix) {
            return family.to_string();
        }
    }
    "generic".to_string()
}

fn resolve_crawler_type(signals: &BTreeMap<String, bool>, path: &str) -> String {
    if *signals.get("has_login").unwrap_or(&false) && !*signals.get("has_detail").unwrap_or(&false)
    {
        return "login_session".to_string();
    }
    if *signals.get("has_infinite_scroll").unwrap_or(&false)
        && (*signals.get("has_list").unwrap_or(&false)
            || *signals.get("has_search").unwrap_or(&false))
    {
        return "infinite_scroll_listing".to_string();
    }
    if *signals.get("has_price").unwrap_or(&false)
        && (*signals.get("has_cart").unwrap_or(&false)
            || *signals.get("has_sku").unwrap_or(&false)
            || *signals.get("has_product_schema").unwrap_or(&false))
        && (*signals.get("has_search").unwrap_or(&false)
            || (*signals.get("has_list").unwrap_or(&false) && path.contains("search")))
    {
        return "ecommerce_search".to_string();
    }
    if *signals.get("has_price").unwrap_or(&false)
        && (*signals.get("has_cart").unwrap_or(&false)
            || *signals.get("has_sku").unwrap_or(&false)
            || *signals.get("has_product_schema").unwrap_or(&false))
        && *signals.get("has_list").unwrap_or(&false)
        && !*signals.get("has_detail").unwrap_or(&false)
    {
        return "ecommerce_search".to_string();
    }
    if *signals.get("has_price").unwrap_or(&false)
        && (*signals.get("has_cart").unwrap_or(&false)
            || *signals.get("has_sku").unwrap_or(&false)
            || *signals.get("has_product_schema").unwrap_or(&false))
    {
        return "ecommerce_detail".to_string();
    }
    if *signals.get("has_hydration").unwrap_or(&false)
        && (*signals.get("has_list").unwrap_or(&false)
            || *signals.get("has_detail").unwrap_or(&false)
            || *signals.get("has_search").unwrap_or(&false))
    {
        return "hydrated_spa".to_string();
    }
    if *signals.get("has_api_bootstrap").unwrap_or(&false)
        || *signals.get("has_graphql").unwrap_or(&false)
    {
        return "api_bootstrap".to_string();
    }
    if *signals.get("has_search").unwrap_or(&false)
        && (*signals.get("has_list").unwrap_or(&false)
            || *signals.get("has_pagination").unwrap_or(&false))
    {
        return "search_results".to_string();
    }
    if *signals.get("has_list").unwrap_or(&false) && !*signals.get("has_detail").unwrap_or(&false) {
        return "static_listing".to_string();
    }
    if *signals.get("has_detail").unwrap_or(&false) {
        return "static_detail".to_string();
    }
    "generic_http".to_string()
}

fn resolve_runner_order(crawler_type: &str, signals: &BTreeMap<String, bool>) -> Vec<String> {
    match crawler_type {
        "hydrated_spa" | "infinite_scroll_listing" | "login_session" | "ecommerce_search" => {
            vec!["browser".to_string(), "http".to_string()]
        }
        "ecommerce_detail" if *signals.get("has_hydration").unwrap_or(&false) => {
            vec!["browser".to_string(), "http".to_string()]
        }
        "ecommerce_detail" => vec!["http".to_string(), "browser".to_string()],
        _ => vec!["http".to_string(), "browser".to_string()],
    }
}

fn resolve_strategy_hints(crawler_type: &str, runner_order: &[String]) -> Vec<String> {
    match crawler_type {
        "ecommerce_search" => vec![
            "start with browser rendering, capture HTML and network payloads, then promote stable fields into HTTP follow-up jobs".to_string(),
            "split listing fields from detail fields so sku and price can be validated independently".to_string(),
        ],
        "hydrated_spa" => vec![
            "render the page in browser mode and inspect embedded hydration data before DOM scraping".to_string(),
            "capture network responses and promote repeatable JSON endpoints into secondary HTTP jobs".to_string(),
        ],
        "infinite_scroll_listing" => vec![
            "drive a bounded scroll loop and stop when repeated snapshots stop changing".to_string(),
            "persist network and DOM artifacts so load-more behavior can be replayed without guessing".to_string(),
        ],
        "login_session" => vec![
            "bootstrap an authenticated session once, then reuse cookies or storage state for follow-up jobs".to_string(),
            "validate the post-login page shape before starting extraction".to_string(),
        ],
        "ecommerce_detail" => vec![
            "extract embedded product JSON and schema blocks before relying on brittle selectors".to_string(),
            "keep screenshot and HTML artifacts together for price and title regression checks".to_string(),
        ],
        "api_bootstrap" => vec![
            "inspect script tags and bootstrap JSON before adding browser interactions".to_string(),
            "extract stable JSON blobs into dedicated parsing rules so DOM churn matters less".to_string(),
        ],
        _ => vec![
            format!(
                "start with {} mode and fall back only when the initial surface is empty",
                runner_order.first().map(String::as_str).unwrap_or("http")
            ),
            "prefer stable title, meta, schema, and bootstrap data before brittle DOM selectors".to_string(),
        ],
    }
}

fn resolve_job_templates(crawler_type: &str, url_lower: &str) -> Vec<String> {
    let mut templates = match crawler_type {
        "hydrated_spa" => vec!["examples/crawler-types/hydrated-spa-browser.json".to_string()],
        "infinite_scroll_listing" => {
            vec!["examples/crawler-types/infinite-scroll-browser.json".to_string()]
        }
        "ecommerce_search" => {
            vec!["examples/crawler-types/ecommerce-search-browser.json".to_string()]
        }
        "ecommerce_detail" => vec![
            "examples/crawler-types/ecommerce-search-browser.json".to_string(),
            "examples/crawler-types/api-bootstrap-http.json".to_string(),
        ],
        "login_session" => vec!["examples/crawler-types/login-session-browser.json".to_string()],
        _ => vec!["examples/crawler-types/api-bootstrap-http.json".to_string()],
    };
    match resolve_site_family(url_lower).as_str() {
        "jd" if crawler_type == "ecommerce_detail" => {
            templates.push("examples/site-presets/jd-detail-browser.json".to_string())
        }
        "taobao" if crawler_type == "ecommerce_detail" => {
            templates.push("examples/site-presets/taobao-detail-browser.json".to_string())
        }
        "jd" => templates.push("examples/site-presets/jd-search-browser.json".to_string()),
        "taobao" => templates.push("examples/site-presets/taobao-search-browser.json".to_string()),
        "tmall" => templates.push("examples/site-presets/tmall-search-browser.json".to_string()),
        "pinduoduo" => {
            templates.push("examples/site-presets/pinduoduo-search-browser.json".to_string())
        }
        "xiaohongshu" => {
            templates.push("examples/site-presets/xiaohongshu-feed-browser.json".to_string())
        }
        "douyin-shop" => {
            templates.push("examples/site-presets/douyin-shop-browser.json".to_string())
        }
        _ => {}
    }
    templates.sort();
    templates.dedup();
    templates
}

fn extract_content(
    content: &str,
    properties: Option<&Map<String, Value>>,
    specs: &[Map<String, Value>],
) -> Result<Value, Box<dyn std::error::Error>> {
    let mut extract = Map::new();
    if !specs.is_empty() {
        for spec in specs {
            let field = spec
                .get("field")
                .and_then(|value| value.as_str())
                .unwrap_or("")
                .trim()
                .to_string();
            if field.is_empty() {
                continue;
            }
            let value = extract_with_spec(content, &field, spec);
            if value.is_null() || value.as_str().is_some_and(|text| text.trim().is_empty()) {
                if spec.get("required").and_then(|value| value.as_bool()) == Some(true) {
                    return Err(format!(
                        "required extract field \"{field}\" could not be resolved"
                    )
                    .into());
                }
                continue;
            }
            validate_schema(&field, &value, schema_for_field(spec, properties, &field))?;
            extract.insert(field, value);
        }
        return Ok(Value::Object(extract));
    }

    if let Some(properties) = properties {
        for field in properties.keys() {
            if let Some(value) = heuristic_extract(content, field) {
                extract.insert(field.clone(), Value::String(value));
            }
        }
    }
    Ok(Value::Object(extract))
}

fn extract_with_spec(content: &str, field: &str, spec: &Map<String, Value>) -> Value {
    let extract_type = spec
        .get("type")
        .and_then(|value| value.as_str())
        .unwrap_or("")
        .to_ascii_lowercase();
    let expr = spec
        .get("expr")
        .and_then(|value| value.as_str())
        .unwrap_or("");
    let path = spec
        .get("path")
        .and_then(|value| value.as_str())
        .unwrap_or(expr);

    match extract_type.as_str() {
        "css" => {
            let selector = if expr.is_empty() && field.eq_ignore_ascii_case("title") {
                "title"
            } else {
                expr
            };
            if !selector.is_empty() {
                if let Some(value) = extract_css_text(content, selector) {
                    return Value::String(value);
                }
            }
        }
        "css_attr" => {
            let attr = spec
                .get("attr")
                .and_then(|value| value.as_str())
                .unwrap_or("");
            if !expr.is_empty() && !attr.is_empty() {
                if let Some(value) = extract_css_attr(content, expr, attr) {
                    return Value::String(value);
                }
            }
        }
        "xpath" => {
            if let Some(value) = extract_xpath(content, expr) {
                return Value::String(value);
            }
        }
        "regex" => {
            if !expr.is_empty() {
                if let Ok(re) = regex::Regex::new(&format!("(?is){expr}")) {
                    if let Some(captures) = re.captures(content) {
                        if let Some(value) = captures.get(1).or_else(|| captures.get(0)) {
                            return Value::String(value.as_str().trim().to_string());
                        }
                    }
                }
            }
        }
        "json_path" => {
            if let Some(value) = extract_json_path(content, path) {
                return value;
            }
        }
        "ai" => {
            if field.eq_ignore_ascii_case("title") {
                return heuristic_extract(content, "title")
                    .map(Value::String)
                    .unwrap_or(Value::Null);
            }
            if matches!(field, "html" | "dom") {
                return Value::String(content.to_string());
            }
        }
        _ => {}
    }

    heuristic_extract(content, field)
        .map(Value::String)
        .unwrap_or(Value::Null)
}

fn extract_xpath(content: &str, expr: &str) -> Option<String> {
    let normalized = expr.trim().to_ascii_lowercase();
    if normalized == "//title/text()" {
        return heuristic_extract(content, "title");
    }
    if normalized == "//h1/text()" {
        let re = regex::Regex::new("(?is)<h1[^>]*>(.*?)</h1>").ok()?;
        let captures = re.captures(content)?;
        let strip_re = regex::Regex::new("(?is)<[^>]+>").ok()?;
        return captures
            .get(1)
            .map(|value| strip_re.replace_all(value.as_str(), "").trim().to_string());
    }
    let meta = regex::Regex::new(r#"(?is)^//meta\[@name=['"]([^'"]+)['"]\]/@content$"#).ok()?;
    let captures = meta.captures(&normalized)?;
    let name = captures.get(1)?.as_str();
    let re = regex::Regex::new(&format!(
        r#"(?is)<meta[^>]*name=["']{}["'][^>]*content=["']([^"']+)["']"#,
        regex::escape(name)
    ))
    .ok()?;
    re.captures(content)
        .and_then(|found| found.get(1))
        .map(|value| value.as_str().trim().to_string())
}

fn heuristic_extract(content: &str, field: &str) -> Option<String> {
    if field.eq_ignore_ascii_case("title") {
        let re = regex::Regex::new("(?is)<title>(.*?)</title>").ok()?;
        let captures = re.captures(content)?;
        return captures
            .get(1)
            .map(|value| value.as_str().trim().to_string());
    }
    let re = regex::Regex::new(&format!(
        r"(?im){}\s*[:=]\s*([^\n<]+)",
        regex::escape(field)
    ))
    .ok()?;
    let captures = re.captures(content)?;
    captures
        .get(1)
        .map(|value| value.as_str().trim().to_string())
}

fn extract_css_text(content: &str, selector: &str) -> Option<String> {
    let parsed = Html::parse_document(content);
    let selector = Selector::parse(selector).ok()?;
    parsed
        .select(&selector)
        .next()
        .map(|element| element.text().collect::<String>().trim().to_string())
        .filter(|value| !value.is_empty())
}

fn extract_css_attr(content: &str, selector: &str, attr: &str) -> Option<String> {
    let parsed = Html::parse_document(content);
    let selector = Selector::parse(selector).ok()?;
    parsed
        .select(&selector)
        .next()
        .and_then(|element| element.value().attr(attr))
        .map(|value| value.trim().to_string())
        .filter(|value| !value.is_empty())
}

fn extract_json_path(content: &str, path: &str) -> Option<Value> {
    let payload: Value = serde_json::from_str(content).ok()?;
    let normalized = path.trim().trim_start_matches("$.").trim();
    if normalized.is_empty() {
        return None;
    }
    let mut current = &payload;
    for segment in normalized.split('.') {
        current = current.get(segment)?;
    }
    Some(current.clone())
}

fn validate_schema(
    field: &str,
    value: &Value,
    schema: Option<&Map<String, Value>>,
) -> Result<(), Box<dyn std::error::Error>> {
    let expected_type = schema
        .and_then(|map| map.get("type"))
        .and_then(|value| value.as_str())
        .unwrap_or("")
        .trim();
    if expected_type.is_empty() {
        return Ok(());
    }
    let valid = match expected_type {
        "string" => value.is_string(),
        "number" => value.is_number(),
        "integer" => value.as_i64().is_some() || value.as_u64().is_some(),
        "boolean" => value.is_boolean(),
        "object" => value.is_object(),
        "array" => value.is_array(),
        _ => true,
    };
    if !valid {
        return Err(
            format!("extract field \"{field}\" violates schema.type={expected_type}").into(),
        );
    }
    Ok(())
}

fn schema_for_field<'a>(
    spec: &'a Map<String, Value>,
    properties: Option<&'a Map<String, Value>>,
    field: &str,
) -> Option<&'a Map<String, Value>> {
    spec.get("schema")
        .and_then(|value| value.as_object())
        .or_else(|| {
            properties
                .and_then(|map| map.get(field))
                .and_then(|value| value.as_object())
        })
}

fn write_dataset(
    path: &str,
    format: &str,
    extract: &Value,
) -> Result<Value, Box<dyn std::error::Error>> {
    if let Some(parent) = Path::new(path).parent() {
        fs::create_dir_all(parent)?;
    }
    match format {
        "jsonl" => {
            fs::write(path, format!("{}\n", serde_json::to_string(extract)?))?;
        }
        "csv" => {
            let object = extract.as_object().cloned().unwrap_or_default();
            let headers = object.keys().cloned().collect::<Vec<_>>();
            let row = headers
                .iter()
                .map(|key| object.get(key).map(stringify_value).unwrap_or_default())
                .collect::<Vec<_>>();
            let mut data = String::new();
            data.push_str(&headers.join(","));
            data.push('\n');
            data.push_str(&row.join(","));
            data.push('\n');
            fs::write(path, data)?;
        }
        _ => {
            fs::write(path, serde_json::to_vec_pretty(&vec![extract])?)?;
        }
    }
    if let Some(store) = crate::storage_backends::configured_driver_dataset_store_from_env() {
        let _ = store.push_json(extract);
    } else if let Some(store) = crate::storage_backends::configured_process_dataset_store_from_env()
    {
        let _ = store.push_json(extract);
    }
    Ok(serde_json::json!({
        "path": path,
        "format": format,
    }))
}

fn stringify_value(value: &Value) -> String {
    match value {
        Value::Null => String::new(),
        Value::String(text) => text.clone(),
        other => serde_json::to_string(other).unwrap_or_default(),
    }
}

fn detect_format(path: &str) -> &'static str {
    let lower = path.to_ascii_lowercase();
    if lower.ends_with(".jsonl") {
        "jsonl"
    } else if lower.ends_with(".csv") {
        "csv"
    } else {
        "json"
    }
}
