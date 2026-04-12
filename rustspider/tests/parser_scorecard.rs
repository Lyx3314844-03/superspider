use rustspider::{HTMLParser, JSONParser};

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
