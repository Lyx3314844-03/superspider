package ai

import "testing"

func TestSentimentAnalyzerClassifiesPositiveAndNegativeTerms(t *testing.T) {
	result := NewSentimentAnalyzer().AnalyzeHTML("<html><body>Excellent product, great quality, but one bug.</body></html>")
	if result.Sentiment != "positive" {
		t.Fatalf("expected positive sentiment, got %+v", result)
	}
	if result.PositiveCount == 0 {
		t.Fatalf("expected positive words to be detected: %+v", result)
	}
}

func TestContentSummarizerUsesMetaDescriptionWhenPresent(t *testing.T) {
	result := NewContentSummarizer(2).Summarize(`<html><head><title>Demo</title><meta name="description" content="Short summary"></head><body></body></html>`)
	if result.Method != "meta_description" || result.Summary != "Short summary" {
		t.Fatalf("unexpected summary result: %+v", result)
	}
}

func TestEntityExtractorFindsStructuredAndRegexEntities(t *testing.T) {
	result := NewEntityExtractor().Extract(`
		<html>
			<head><meta name="author" content="Lan"></head>
			<body>
				<div class="organization">OpenAI</div>
				<div class="address">Shanghai</div>
				<div class="product-title">Spider Pro</div>
				联系 support@example.com 价格 $19.99 发布于 2026-04-13
			</body>
		</html>
	`)
	if len(result["persons"]) == 0 || result["persons"][0] != "Lan" {
		t.Fatalf("expected author entity, got %+v", result)
	}
	if len(result["email"]) == 0 || result["email"][0] != "support@example.com" {
		t.Fatalf("expected email entity, got %+v", result)
	}
	if len(result["products"]) == 0 || result["products"][0] != "Spider Pro" {
		t.Fatalf("expected product entity, got %+v", result)
	}
}
