use rustspider::{ContentSummarizer, EntityExtractor, SentimentAnalyzer};

#[test]
fn sentiment_analyzer_detects_positive_html() {
    let result = SentimentAnalyzer::default()
        .analyze_html("<html><body>Excellent product, amazing quality, but one bug.</body></html>");
    assert_eq!(result.sentiment, "positive");
    assert!(result.positive_count > 0);
}

#[test]
fn content_summarizer_uses_meta_description() {
    let result = ContentSummarizer::new(2)
        .summarize("<html><head><title>Demo</title><meta name=\"description\" content=\"Short summary\"></head><body></body></html>");
    assert_eq!(result.method, "meta_description");
    assert_eq!(result.summary, "Short summary");
}

#[test]
fn entity_extractor_finds_structured_and_regex_entities() {
    let result = EntityExtractor::default().extract(
        r#"<html>
            <head><meta name="author" content="Lan"></head>
            <body>
                <div class="organization">OpenAI</div>
                <div class="address">Shanghai</div>
                <div class="product-title">Spider Pro</div>
                联系 support@example.com 价格 $19.99 发布于 2026-04-13
            </body>
        </html>"#,
    );
    assert_eq!(result["persons"][0], "Lan");
    assert_eq!(result["products"][0], "Spider Pro");
    assert_eq!(result["email"][0], "support@example.com");
}
