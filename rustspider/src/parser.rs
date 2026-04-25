//! HTML 和 JSON 解析器

use regex::Regex;
use scraper::{ElementRef, Html, Selector};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::BTreeMap;
use std::io::Write;
use std::process::{Command, Stdio};

/// HTML 解析器
pub struct HTMLParser {
    document: Html,
}

impl HTMLParser {
    /// 创建新解析器
    pub fn new(html: &str) -> Self {
        HTMLParser {
            document: Html::parse_document(html),
        }
    }

    /// CSS 选择器提取
    pub fn css(&self, selector: &str) -> Vec<String> {
        let query = CssQuery::parse(selector);
        if query.selector.is_empty() {
            return Vec::new();
        }
        let sel = match Selector::parse(&query.selector) {
            Ok(sel) => sel,
            Err(_) => return Vec::new(),
        };
        self.document
            .select(&sel)
            .filter_map(|elem| css_value(elem, &query))
            .collect()
    }

    /// 获取第一个匹配
    pub fn css_first(&self, selector: &str) -> Option<String> {
        let query = CssQuery::parse(selector);
        if query.selector.is_empty() {
            return None;
        }
        let sel = match Selector::parse(&query.selector) {
            Ok(sel) => sel,
            Err(_) => return None,
        };
        self.document
            .select(&sel)
            .next()
            .and_then(|elem| css_value(elem, &query))
    }

    /// 获取属性
    pub fn css_attr(&self, selector: &str, attr: &str) -> Vec<String> {
        let query = CssQuery::parse(selector);
        let attr = query.attr.as_deref().unwrap_or(attr);
        if query.selector.is_empty() || attr.trim().is_empty() {
            return Vec::new();
        }
        let sel = match Selector::parse(&query.selector) {
            Ok(sel) => sel,
            Err(_) => return Vec::new(),
        };
        self.document
            .select(&sel)
            .filter_map(|elem| elem.value().attr(attr).map(|s| s.trim().to_string()))
            .filter(|value| !value.is_empty())
            .collect()
    }

    /// 获取第一个属性
    pub fn css_attr_first(&self, selector: &str, attr: &str) -> Option<String> {
        let query = CssQuery::parse(selector);
        let attr = query.attr.as_deref().unwrap_or(attr);
        if query.selector.is_empty() || attr.trim().is_empty() {
            return None;
        }
        let sel = match Selector::parse(&query.selector) {
            Ok(sel) => sel,
            Err(_) => return None,
        };
        self.document
            .select(&sel)
            .next()
            .and_then(|elem| elem.value().attr(attr).map(|s| s.trim().to_string()))
            .filter(|value| !value.is_empty())
    }

    pub fn xpath_first(&self, xpath: &str) -> Option<String> {
        self.xpath_first_strict(xpath).ok().flatten()
    }

    pub fn xpath(&self, xpath: &str) -> Vec<String> {
        self.xpath_strict(xpath).unwrap_or_default()
    }

    pub fn xpath_strict(&self, xpath: &str) -> Result<Vec<String>, String> {
        run_xpath_all(&self.html(), xpath)
    }

    pub fn xpath_first_strict(&self, xpath: &str) -> Result<Option<String>, String> {
        Ok(self.xpath_strict(xpath)?.into_iter().next())
    }

    /// 获取所有链接
    pub fn links(&self) -> Vec<String> {
        self.css_attr("a", "href")
    }

    /// 获取所有图片
    pub fn images(&self) -> Vec<String> {
        self.css_attr("img", "src")
    }

    /// 获取标题
    pub fn title(&self) -> Option<String> {
        self.css_first("title")
    }

    /// 获取文本
    pub fn text(&self) -> String {
        self.document
            .root_element()
            .text()
            .collect::<Vec<_>>()
            .join(" ")
    }

    pub fn html(&self) -> String {
        self.document.root_element().html()
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
struct CssQuery {
    selector: String,
    mode: CssMode,
    attr: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
enum CssMode {
    Text,
    Html,
    Attr,
}

impl CssQuery {
    fn parse(selector: &str) -> Self {
        let trimmed = selector.trim();
        let lower = trimmed.to_ascii_lowercase();
        if lower.ends_with("::text") {
            return Self {
                selector: trimmed[..trimmed.len() - "::text".len()].trim().to_string(),
                mode: CssMode::Text,
                attr: None,
            };
        }
        if lower.ends_with("::html") {
            return Self {
                selector: trimmed[..trimmed.len() - "::html".len()].trim().to_string(),
                mode: CssMode::Html,
                attr: None,
            };
        }
        if let Ok(re) = Regex::new(r"(?i)::attr\(([^)]+)\)\s*$") {
            if let Some(capture) = re.captures(trimmed) {
                if let Some(full) = capture.get(0) {
                    return Self {
                        selector: trimmed[..full.start()].trim().to_string(),
                        mode: CssMode::Attr,
                        attr: capture
                            .get(1)
                            .map(|value| value.as_str().trim().to_string()),
                    };
                }
            }
        }
        Self {
            selector: trimmed.to_string(),
            mode: CssMode::Text,
            attr: None,
        }
    }
}

fn css_value(elem: ElementRef<'_>, query: &CssQuery) -> Option<String> {
    let value = match query.mode {
        CssMode::Attr => elem
            .value()
            .attr(query.attr.as_deref()?)?
            .trim()
            .to_string(),
        CssMode::Html => elem.inner_html().trim().to_string(),
        CssMode::Text => elem.text().collect::<Vec<_>>().join("").trim().to_string(),
    };
    (!value.is_empty()).then_some(value)
}

fn run_xpath_all(html: &str, xpath: &str) -> Result<Vec<String>, String> {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .ok_or_else(|| "failed to resolve workspace root".to_string())?;
    let script = root.join("tools").join("xpath_extract.py");
    if !script.exists() {
        return Err(format!("missing helper script: {}", script.display()));
    }

    let mut child = Command::new("python")
        .arg(script)
        .arg(xpath)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|err| format!("failed to spawn xpath helper: {err}"))?;

    if let Some(stdin) = child.stdin.as_mut() {
        stdin
            .write_all(html.as_bytes())
            .map_err(|err| format!("failed to write xpath helper stdin: {err}"))?;
    }
    let output = child
        .wait_with_output()
        .map_err(|err| format!("failed to wait for xpath helper: {err}"))?;
    if !output.status.success() {
        let stdout = String::from_utf8_lossy(&output.stdout);
        if let Ok(payload) = serde_json::from_str::<serde_json::Value>(&stdout) {
            if let Some(error) = payload.get("error").and_then(|value| value.as_str()) {
                return Err(format!("xpath helper failed: {error}"));
            }
        }
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Err(format!("xpath helper failed: {}", stderr.trim()));
    }
    let payload: serde_json::Value = serde_json::from_slice(&output.stdout)
        .map_err(|err| format!("invalid xpath helper output: {err}"))?;
    if let Some(error) = payload.get("error").and_then(|value| value.as_str()) {
        return Err(error.to_string());
    }
    let values = payload
        .get("values")
        .and_then(|value| value.as_array())
        .ok_or_else(|| "xpath helper returned malformed payload".to_string())?;
    Ok(values
        .iter()
        .filter_map(|value| value.as_str())
        .map(|value| value.trim().to_string())
        .filter(|value| !value.is_empty())
        .collect())
}

#[derive(Debug, Clone)]
pub struct ExtractRule {
    pub field: String,
    pub kind: String,
    pub expr: String,
    pub attr: Option<String>,
    pub all: bool,
    pub required: bool,
}

impl ExtractRule {
    pub fn css(field: impl Into<String>, expr: impl Into<String>) -> Self {
        Self::new(field, "css", expr)
    }

    pub fn xpath(field: impl Into<String>, expr: impl Into<String>) -> Self {
        Self::new(field, "xpath", expr)
    }

    pub fn new(field: impl Into<String>, kind: impl Into<String>, expr: impl Into<String>) -> Self {
        Self {
            field: field.into(),
            kind: kind.into(),
            expr: expr.into(),
            attr: None,
            all: false,
            required: false,
        }
    }

    pub fn attr(mut self, attr: impl Into<String>) -> Self {
        self.attr = Some(attr.into());
        self
    }

    pub fn all(mut self) -> Self {
        self.all = true;
        self
    }

    pub fn required(mut self) -> Self {
        self.required = true;
        self
    }
}

#[derive(Debug, Default)]
pub struct SelectorExtractor;

impl SelectorExtractor {
    pub fn extract(
        &self,
        html: &str,
        rules: &[ExtractRule],
    ) -> Result<BTreeMap<String, Value>, String> {
        let parser = HTMLParser::new(html);
        let mut result = BTreeMap::new();
        for rule in rules {
            if rule.field.trim().is_empty() {
                continue;
            }
            let values = extract_values(&parser, html, rule)?;
            if values.is_empty() {
                if rule.required {
                    return Err(format!(
                        "required extract field {:?} could not be resolved",
                        rule.field
                    ));
                }
                continue;
            }
            let value = if rule.all {
                Value::Array(values.into_iter().map(Value::String).collect())
            } else {
                Value::String(values.into_iter().next().unwrap_or_default())
            };
            result.insert(rule.field.clone(), value);
        }
        Ok(result)
    }
}

#[derive(Debug, Clone, Default)]
pub struct LocatorTarget {
    pub tag: String,
    pub text: String,
    pub role: String,
    pub name: String,
    pub placeholder: String,
    pub attr: String,
    pub value: String,
}

impl LocatorTarget {
    pub fn for_text(text: impl Into<String>) -> Self {
        Self {
            text: text.into(),
            ..Self::default()
        }
    }

    pub fn for_field(name: impl Into<String>) -> Self {
        Self {
            name: name.into(),
            ..Self::default()
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LocatorCandidate {
    pub kind: String,
    pub expr: String,
    pub score: i32,
    pub reason: String,
}

#[derive(Debug, Clone, Default)]
pub struct LocatorPlan {
    pub candidates: Vec<LocatorCandidate>,
}

impl LocatorPlan {
    pub fn best(&self) -> Option<&LocatorCandidate> {
        self.candidates.first()
    }
}

#[derive(Debug, Default)]
pub struct LocatorAnalyzer;

impl LocatorAnalyzer {
    pub fn analyze(&self, html: &str, target: &LocatorTarget) -> LocatorPlan {
        let document = Html::parse_document(html);
        let selector = match Selector::parse("*") {
            Ok(selector) => selector,
            Err(_) => return LocatorPlan::default(),
        };
        let mut candidates = BTreeMap::<(String, String), LocatorCandidate>::new();
        for element in document.select(&selector) {
            let score = locator_match_score(element, target);
            if score <= 0 {
                continue;
            }
            for candidate in locator_candidates_for(&document, element, score) {
                let key = (candidate.kind.clone(), candidate.expr.clone());
                if candidates
                    .get(&key)
                    .map(|current| candidate.score > current.score)
                    .unwrap_or(true)
                {
                    candidates.insert(key, candidate);
                }
            }
        }
        let mut ordered = candidates.into_values().collect::<Vec<_>>();
        ordered.sort_by(|left, right| {
            right
                .score
                .cmp(&left.score)
                .then_with(|| left.kind.cmp(&right.kind))
                .then_with(|| left.expr.cmp(&right.expr))
        });
        LocatorPlan {
            candidates: ordered,
        }
    }
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct ElementSnapshot {
    pub tag: String,
    pub css: String,
    pub xpath: String,
    pub text: String,
    pub attrs: BTreeMap<String, String>,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct DevToolsNetworkArtifact {
    pub url: String,
    pub method: String,
    pub status: u16,
    pub resource_type: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ReverseRecommendation {
    pub kind: String,
    pub priority: i32,
    pub reason: String,
    pub evidence: Vec<String>,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct DevToolsReport {
    pub elements: Vec<ElementSnapshot>,
    pub script_sources: Vec<String>,
    pub inline_script_samples: Vec<String>,
    pub network_candidates: Vec<DevToolsNetworkArtifact>,
    pub console_events: Vec<BTreeMap<String, String>>,
    pub reverse_recommendations: Vec<ReverseRecommendation>,
    pub summary: BTreeMap<String, Value>,
}

impl DevToolsReport {
    pub fn best_reverse_route(&self) -> Option<&ReverseRecommendation> {
        self.reverse_recommendations.first()
    }
}

#[derive(Debug, Default)]
pub struct DevToolsAnalyzer;

impl DevToolsAnalyzer {
    pub fn analyze(
        &self,
        html: &str,
        network: &[DevToolsNetworkArtifact],
        console_events: &[BTreeMap<String, String>],
    ) -> DevToolsReport {
        let document = Html::parse_document(html);
        let all = match Selector::parse("*") {
            Ok(selector) => selector,
            Err(_) => return DevToolsReport::default(),
        };
        let elements = document
            .select(&all)
            .map(snapshot_element)
            .collect::<Vec<_>>();
        let (script_sources, inline_script_samples) = script_artifacts(&document);
        let network_candidates = devtools_network_candidates(network);
        let reverse_recommendations = recommend_reverse_routes(
            html,
            &script_sources,
            &inline_script_samples,
            &network_candidates,
        );
        let mut summary = BTreeMap::new();
        summary.insert(
            "element_count".to_string(),
            serde_json::json!(elements.len()),
        );
        summary.insert(
            "script_count".to_string(),
            serde_json::json!(script_sources.len() + inline_script_samples.len()),
        );
        summary.insert(
            "network_candidate_count".to_string(),
            serde_json::json!(network_candidates.len()),
        );
        summary.insert(
            "best_reverse_route".to_string(),
            serde_json::json!(reverse_recommendations
                .first()
                .map(|item| item.kind.as_str())
                .unwrap_or_default()),
        );
        DevToolsReport {
            elements,
            script_sources,
            inline_script_samples,
            network_candidates,
            console_events: console_events.to_vec(),
            reverse_recommendations,
            summary,
        }
    }
}

fn snapshot_element(element: ElementRef<'_>) -> ElementSnapshot {
    let mut attrs = BTreeMap::new();
    for attr in [
        "id",
        "class",
        "name",
        "type",
        "href",
        "src",
        "role",
        "aria-label",
        "data-testid",
        "data-test",
        "placeholder",
        "action",
        "method",
    ] {
        if let Some(value) = element.value().attr(attr) {
            if !value.trim().is_empty() {
                attrs.insert(attr.to_string(), value.trim().to_string());
            }
        }
    }
    let text = element
        .text()
        .collect::<Vec<_>>()
        .join(" ")
        .trim()
        .chars()
        .take(120)
        .collect::<String>();
    let tag = element.value().name().to_string();
    ElementSnapshot {
        css: element_css(&tag, &attrs),
        xpath: element_xpath(&tag, &attrs),
        tag,
        text,
        attrs,
    }
}

fn element_css(tag: &str, attrs: &BTreeMap<String, String>) -> String {
    if let Some(id) = attrs.get("id") {
        return format!("#{}", css_ident(id));
    }
    for attr in [
        "data-testid",
        "data-test",
        "name",
        "aria-label",
        "placeholder",
        "role",
    ] {
        if let Some(value) = attrs.get(attr) {
            return format!("{}[{}='{}']", tag, attr, css_quote(value));
        }
    }
    tag.to_string()
}

fn element_xpath(tag: &str, attrs: &BTreeMap<String, String>) -> String {
    for attr in [
        "id",
        "data-testid",
        "data-test",
        "name",
        "aria-label",
        "placeholder",
        "role",
    ] {
        if let Some(value) = attrs.get(attr) {
            return format!("//{}[@{}={}]", tag, attr, xpath_literal(value));
        }
    }
    format!("//{tag}")
}

fn script_artifacts(document: &Html) -> (Vec<String>, Vec<String>) {
    let selector = match Selector::parse("script") {
        Ok(selector) => selector,
        Err(_) => return (Vec::new(), Vec::new()),
    };
    let mut sources = Vec::new();
    let mut inline = Vec::new();
    for script in document.select(&selector) {
        if let Some(src) = script.value().attr("src") {
            if !src.trim().is_empty() {
                sources.push(src.trim().to_string());
                continue;
            }
        }
        let code = script
            .text()
            .collect::<Vec<_>>()
            .join("")
            .trim()
            .chars()
            .take(2000)
            .collect::<String>();
        if !code.is_empty() {
            inline.push(code);
        }
    }
    (sources, inline)
}

fn devtools_network_candidates(
    network: &[DevToolsNetworkArtifact],
) -> Vec<DevToolsNetworkArtifact> {
    let mut seen = BTreeMap::<String, bool>::new();
    let mut result = Vec::new();
    for entry in network {
        if entry.url.trim().is_empty() || seen.contains_key(&entry.url) {
            continue;
        }
        let resource_type = entry.resource_type.to_ascii_lowercase();
        let signal = format!("{} {}", entry.url, resource_type).to_ascii_lowercase();
        if ["script", "xhr", "fetch", "websocket", "document"].contains(&resource_type.as_str())
            || [
                "api", "sign", "token", "encrypt", "decrypt", "jsonp", "webpack",
            ]
            .iter()
            .any(|token| signal.contains(token))
        {
            seen.insert(entry.url.clone(), true);
            result.push(entry.clone());
        }
    }
    result
}

fn recommend_reverse_routes(
    html: &str,
    script_sources: &[String],
    inline_samples: &[String],
    network: &[DevToolsNetworkArtifact],
) -> Vec<ReverseRecommendation> {
    let mut corpus = html.chars().take(8000).collect::<String>();
    for value in script_sources {
        corpus.push('\n');
        corpus.push_str(value);
    }
    for value in inline_samples {
        corpus.push('\n');
        corpus.push_str(value);
    }
    for value in network {
        corpus.push('\n');
        corpus.push_str(&value.url);
    }
    let corpus = corpus.to_ascii_lowercase();
    let mut result = Vec::new();
    for (kind, priority, reason, markers) in [
        (
            "analyze_crypto",
            100,
            "发现加密、签名或摘要相关标记，优先交给 Node.js crypto 逆向分析",
            vec![
                "cryptojs",
                "crypto.subtle",
                "aes",
                "rsa",
                "md5",
                "sha1",
                "sha256",
                "encrypt",
                "decrypt",
                "signature",
                "sign",
            ],
        ),
        (
            "analyze_webpack",
            90,
            "发现 webpack 模块运行时，适合进入模块表和导出函数逆向",
            vec![
                "__webpack_require__",
                "webpackjsonp",
                "webpackchunk",
                "webpack://",
            ],
        ),
        (
            "simulate_browser",
            80,
            "脚本依赖浏览器运行时对象，适合用 Node.js 浏览器环境模拟",
            vec![
                "localstorage",
                "sessionstorage",
                "navigator.",
                "document.",
                "window.",
                "canvas",
                "webdriver",
            ],
        ),
        (
            "analyze_ast",
            60,
            "存在外链或内联脚本，适合进行 AST 结构分析和函数定位",
            vec![".js", "function", "=>", "eval(", "new function"],
        ),
    ] {
        let evidence = markers
            .iter()
            .filter(|marker| corpus.contains(&marker.to_ascii_lowercase()))
            .take(8)
            .map(|marker| marker.to_string())
            .collect::<Vec<_>>();
        if !evidence.is_empty() {
            result.push(ReverseRecommendation {
                kind: kind.to_string(),
                priority,
                reason: reason.to_string(),
                evidence,
            });
        }
    }
    result.sort_by(|left, right| {
        right
            .priority
            .cmp(&left.priority)
            .then_with(|| left.kind.cmp(&right.kind))
    });
    result
}

fn locator_match_score(element: ElementRef<'_>, target: &LocatorTarget) -> i32 {
    let mut score = 0;
    let tag = element.value().name();
    if !target.tag.is_empty() && target.tag.to_ascii_lowercase() != tag {
        return 0;
    }
    if !target.tag.is_empty() {
        score += 2;
    }
    let text = element
        .text()
        .collect::<Vec<_>>()
        .join(" ")
        .trim()
        .to_string();
    if !target.text.is_empty() {
        if text == target.text {
            score += 6;
        } else if text
            .to_ascii_lowercase()
            .contains(&target.text.to_ascii_lowercase())
        {
            score += 3;
        }
    }
    for (attr, expected, weight) in [
        ("role", target.role.as_str(), 4),
        ("name", target.name.as_str(), 4),
        ("placeholder", target.placeholder.as_str(), 4),
    ] {
        if !expected.is_empty()
            && element
                .value()
                .attr(attr)
                .unwrap_or_default()
                .to_ascii_lowercase()
                .contains(&expected.to_ascii_lowercase())
        {
            score += weight;
        }
    }
    if !target.name.is_empty() {
        for attr in ["id", "aria-label", "data-testid", "data-test"] {
            if element
                .value()
                .attr(attr)
                .unwrap_or_default()
                .to_ascii_lowercase()
                .contains(&target.name.to_ascii_lowercase())
            {
                score += 3;
            }
        }
    }
    if !target.attr.is_empty()
        && !target.value.is_empty()
        && element.value().attr(&target.attr) == Some(target.value.as_str())
    {
        score += 6;
    }
    score
}

fn locator_candidates_for(
    document: &Html,
    element: ElementRef<'_>,
    score: i32,
) -> Vec<LocatorCandidate> {
    let tag = element.value().name();
    let mut candidates = Vec::new();
    for attr in [
        "id",
        "data-testid",
        "data-test",
        "name",
        "aria-label",
        "placeholder",
        "role",
    ] {
        let value = element.value().attr(attr).unwrap_or_default().trim();
        if value.is_empty() {
            continue;
        }
        let css = if attr == "id" {
            format!("#{}", css_ident(value))
        } else {
            format!("{}[{}='{}']", tag, attr, css_quote(value))
        };
        let xpath = format!("//{}[@{}={}]", tag, attr, xpath_literal(value));
        let bonus = if css_count(document, &css) == 1 { 8 } else { 3 };
        candidates.push(LocatorCandidate {
            kind: "css".to_string(),
            expr: css,
            score: score + bonus,
            reason: format!("{attr} attribute"),
        });
        candidates.push(LocatorCandidate {
            kind: "xpath".to_string(),
            expr: xpath,
            score: score + bonus - 1,
            reason: format!("{attr} attribute"),
        });
    }
    let text = element
        .text()
        .collect::<Vec<_>>()
        .join(" ")
        .trim()
        .to_string();
    if !text.is_empty() {
        let snippet = text.chars().take(80).collect::<String>();
        candidates.push(LocatorCandidate {
            kind: "xpath".to_string(),
            expr: format!(
                "//{}[contains(normalize-space(.), {})]",
                tag,
                xpath_literal(&snippet)
            ),
            score: score + 2,
            reason: "visible text".to_string(),
        });
    }
    candidates
}

fn css_count(document: &Html, css: &str) -> usize {
    Selector::parse(css)
        .ok()
        .map(|selector| document.select(&selector).count())
        .unwrap_or(0)
}

fn css_ident(value: &str) -> String {
    value
        .chars()
        .map(|ch| {
            if ch.is_ascii_alphanumeric() || ch == '_' || ch == '-' {
                ch.to_string()
            } else {
                format!("\\{:x} ", ch as u32)
            }
        })
        .collect()
}

fn css_quote(value: &str) -> String {
    value.replace('\\', "\\\\").replace('\'', "\\'")
}

fn xpath_literal(value: &str) -> String {
    if !value.contains('\'') {
        return format!("'{value}'");
    }
    if !value.contains('"') {
        return format!("\"{value}\"");
    }
    format!(
        "concat({})",
        value
            .split('\'')
            .map(|part| format!("'{part}'"))
            .collect::<Vec<_>>()
            .join(", \"'\", ")
    )
}

fn extract_values(
    parser: &HTMLParser,
    html: &str,
    rule: &ExtractRule,
) -> Result<Vec<String>, String> {
    match rule.kind.trim().to_ascii_lowercase().as_str() {
        "css" => Ok(parser.css(&rule.expr)),
        "css_attr" => Ok(parser.css_attr(&rule.expr, rule.attr.as_deref().unwrap_or_default())),
        "xpath" => parser.xpath_strict(&rule.expr),
        "regex" => {
            let regex = Regex::new(&rule.expr).map_err(|err| err.to_string())?;
            Ok(regex
                .captures_iter(html)
                .filter_map(|capture| {
                    capture
                        .get(1)
                        .or_else(|| capture.get(0))
                        .map(|value| value.as_str().trim().to_string())
                })
                .filter(|value| !value.is_empty())
                .collect())
        }
        other => Err(format!("unsupported extract rule type {other:?}")),
    }
}

/// JSON 解析器
pub struct JSONParser {
    value: Value,
}

impl JSONParser {
    /// 创建新解析器
    pub fn new(json: &str) -> Option<Self> {
        serde_json::from_str(json)
            .ok()
            .map(|value| JSONParser { value })
    }

    /// 获取 JSON 路径
    pub fn get(&self, path: &str) -> Option<&Value> {
        let mut current = &self.value;
        for key in path.split('.') {
            current = match current {
                Value::Object(map) => map.get(key)?,
                Value::Array(arr) => {
                    let idx = key.parse::<usize>().ok()?;
                    arr.get(idx)?
                }
                _ => return None,
            };
        }
        Some(current)
    }

    /// 获取字符串
    pub fn get_string(&self, path: &str) -> Option<String> {
        self.get(path)
            .and_then(|v| v.as_str().map(|s| s.to_string()))
    }

    /// 获取整数
    pub fn get_i64(&self, path: &str) -> Option<i64> {
        self.get(path).and_then(|v| v.as_i64())
    }

    /// 获取浮点数
    pub fn get_f64(&self, path: &str) -> Option<f64> {
        self.get(path).and_then(|v| v.as_f64())
    }

    /// 获取布尔值
    pub fn get_bool(&self, path: &str) -> Option<bool> {
        self.get(path).and_then(|v| v.as_bool())
    }

    /// 获取数组
    pub fn get_array(&self, path: &str) -> Option<&Vec<Value>> {
        self.get(path).and_then(|v| v.as_array())
    }
}

#[cfg(test)]
mod tests {
    use super::{DevToolsAnalyzer, DevToolsNetworkArtifact, HTMLParser};

    #[test]
    fn xpath_first_strict_supports_full_xpath() {
        let parser = HTMLParser::new(r#"<html><div><span>One</span><span>Two</span></div></html>"#);
        let value = parser
            .xpath_first_strict("//div/span[2]/text()")
            .expect("xpath");
        assert_eq!(value.as_deref(), Some("Two"));
    }

    #[test]
    fn xpath_first_strict_rejects_invalid_expressions() {
        let parser = HTMLParser::new(r#"<html><div><span>Demo</span></div></html>"#);
        let err = parser.xpath_first_strict("//*[");
        assert!(err.is_err());
    }

    #[test]
    fn devtools_analyzer_selects_node_reverse_crypto_route() {
        let html = r#"<html><body>
            <input id="kw" name="q">
            <script src="/static/app.js"></script>
            <script>const token = CryptoJS.MD5(window.navigator.userAgent).toString();</script>
        </body></html>"#;
        let report = DevToolsAnalyzer.analyze(
            html,
            &[DevToolsNetworkArtifact {
                url: "https://example.com/api/search?sign=abc".to_string(),
                method: "GET".to_string(),
                status: 200,
                resource_type: "xhr".to_string(),
            }],
            &[],
        );

        assert!(report.elements.len() >= 3);
        assert_eq!(
            report.best_reverse_route().map(|route| route.kind.as_str()),
            Some("analyze_crypto")
        );
    }
}
