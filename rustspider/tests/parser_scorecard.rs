use rustspider::{
    DevToolsAnalyzer, DevToolsNetworkArtifact, ExtractRule, HTMLParser, JSONParser,
    LocatorAnalyzer, LocatorTarget, SelectorExtractor,
};

#[test]
fn html_parser_extracts_title_and_links() {
    let parser = HTMLParser::new(
        r#"<html><head><title>RustSpider Parser</title></head><body><a href="https://example.com">example</a></body></html>"#,
    );

    assert_eq!(parser.title(), Some("RustSpider Parser".to_string()));
    assert_eq!(parser.links(), vec!["https://example.com".to_string()]);
}

#[test]
fn json_parser_reads_nested_paths() {
    let parser =
        JSONParser::new(r#"{"job":{"runtime":"media","retries":[1,2,3]}}"#).expect("json parser");

    assert_eq!(parser.get_string("job.runtime"), Some("media".to_string()));
    assert_eq!(parser.get_i64("job.retries.1"), Some(2));
}

#[test]
fn selector_extractor_supports_complex_css_and_xpath_rules() {
    let html = r#"<html><body>
        <article class="product" data-sku="A1"><h2><span>Alpha</span></h2><a class="buy" href="/alpha">Buy</a></article>
        <article class="product featured" data-sku="B2"><h2><span>Beta</span></h2><a class="buy" href="/beta">Buy</a></article>
    </body></html>"#;

    let result = SelectorExtractor
        .extract(
            html,
            &[
                ExtractRule::css("names", "article.product > h2 span::text").all(),
                ExtractRule::xpath(
                    "featured_sku",
                    "//article[contains(@class, 'featured')]/@data-sku",
                ),
                ExtractRule::css("links", "article.product a.buy::attr(href)").all(),
            ],
        )
        .expect("extract");

    assert_eq!(result["names"], serde_json::json!(["Alpha", "Beta"]));
    assert_eq!(result["featured_sku"], serde_json::json!("B2"));
    assert_eq!(result["links"], serde_json::json!(["/alpha", "/beta"]));
}

#[test]
fn locator_analyzer_builds_css_and_xpath_candidates() {
    let html = r#"<html><body><form>
        <input id="search-box" name="q" placeholder="Search products">
        <button data-testid="submit-search">Search</button>
    </form></body></html>"#;

    let plan = LocatorAnalyzer.analyze(html, &LocatorTarget::for_field("q"));
    let expressions = plan
        .candidates
        .iter()
        .map(|candidate| format!("{} {}", candidate.kind, candidate.expr))
        .collect::<std::collections::BTreeSet<_>>();

    assert!(expressions.contains("css #search-box"));
    assert!(expressions.contains("xpath //input[@name='q']"));
}

#[test]
fn devtools_analyzer_snapshots_elements_and_selects_node_reverse_route() {
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
