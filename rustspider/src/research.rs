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
    pub signals: BTreeMap<String, bool>,
    pub candidate_fields: Vec<String>,
    pub risk_level: String,
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
    let signals = BTreeMap::from([
        ("has_form".to_string(), lower.contains("<form")),
        (
            "has_pagination".to_string(),
            lower.contains("next") || lower.contains("page="),
        ),
        (
            "has_list".to_string(),
            lower.contains("<li") || lower.contains("<ul"),
        ),
        (
            "has_detail".to_string(),
            lower.contains("<article") || lower.contains("<h1"),
        ),
        (
            "has_captcha".to_string(),
            lower.contains("captcha") || lower.contains("verify"),
        ),
    ]);
    let page_type = if *signals.get("has_list").unwrap_or(&false)
        && !*signals.get("has_detail").unwrap_or(&false)
    {
        "list"
    } else if *signals.get("has_detail").unwrap_or(&false) {
        "detail"
    } else {
        "generic"
    };

    let mut candidate_fields = Vec::new();
    if lower.contains("<title") {
        candidate_fields.push("title".to_string());
    }
    if lower.contains("price") {
        candidate_fields.push("price".to_string());
    }
    if lower.contains("author") {
        candidate_fields.push("author".to_string());
    }

    let risk_level = if *signals.get("has_captcha").unwrap_or(&false) {
        "high"
    } else if url.to_ascii_lowercase().starts_with("https://")
        && *signals.get("has_form").unwrap_or(&false)
    {
        "medium"
    } else {
        "low"
    };

    SiteProfile {
        url: url.to_string(),
        page_type: page_type.to_string(),
        signals,
        candidate_fields,
        risk_level: risk_level.to_string(),
    }
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
