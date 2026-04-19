package ai

import (
	"regexp"
	"strings"

	"github.com/PuerkitoBio/goquery"
)

type EntityExtractionResult map[string][]string

type EntityExtractor struct{}

func NewEntityExtractor() *EntityExtractor {
	return &EntityExtractor{}
}

func (e *EntityExtractor) Extract(html string) EntityExtractionResult {
	doc, err := goquery.NewDocumentFromReader(strings.NewReader(html))
	if err != nil {
		return EntityExtractionResult{}
	}
	text := doc.Text()
	result := EntityExtractionResult{}
	patterns := map[string]*regexp.Regexp{
		"email":      regexp.MustCompile(`\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b`),
		"phone":      regexp.MustCompile(`(?:\+?\d[\d\s()./\-]{6,}\d)`),
		"url":        regexp.MustCompile("https?://[^\\s<>\"{}|\\\\^`\\[\\]]+"),
		"date":       regexp.MustCompile(`\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b|\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b`),
		"time":       regexp.MustCompile(`\b\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM)?\b`),
		"money":      regexp.MustCompile(`[\$€£￥¥]\s*\d+[,.]?\d*`),
		"percentage": regexp.MustCompile(`\d+\.?\d*\s*%`),
	}
	for entityType, pattern := range patterns {
		result[entityType] = uniqueMatches(pattern.FindAllString(text, -1))
	}
	result["persons"] = uniqueMatches(append(result["persons"], extractMetaOrSelection(doc, "meta[name='author'], .author, .byline, [itemprop='author']")...))
	result["organizations"] = uniqueMatches(append(result["organizations"], extractMetaOrSelection(doc, "meta[name='application-name'], meta[name='copyright'], .organization, .org")...))
	result["locations"] = uniqueMatches(extractSelectionTexts(doc, "[itemprop='location'], .location, .address"))
	result["products"] = uniqueMatches(extractMetaOrSelection(doc, ".product-name, .product-title, [itemprop='name'], meta[property='product:name'], h1.product-title"))

	cleaned := EntityExtractionResult{}
	for key, values := range result {
		if len(values) > 0 {
			cleaned[key] = values
		}
	}
	return cleaned
}

func extractSelectionTexts(doc *goquery.Document, selector string) []string {
	values := make([]string, 0)
	doc.Find(selector).Each(func(_ int, selection *goquery.Selection) {
		text := strings.TrimSpace(selection.Text())
		if text != "" && len(text) < 200 {
			values = append(values, text)
		}
	})
	return values
}

func extractMetaOrSelection(doc *goquery.Document, selector string) []string {
	values := make([]string, 0)
	doc.Find(selector).Each(func(_ int, selection *goquery.Selection) {
		if goquery.NodeName(selection) == "meta" {
			if content := strings.TrimSpace(selection.AttrOr("content", "")); content != "" {
				values = append(values, content)
			}
			return
		}
		text := strings.TrimSpace(selection.Text())
		if text != "" && len(text) < 200 {
			values = append(values, text)
		}
	})
	return values
}

func uniqueMatches(values []string) []string {
	seen := map[string]struct{}{}
	unique := make([]string, 0, len(values))
	for _, value := range values {
		trimmed := strings.TrimSpace(value)
		if trimmed == "" {
			continue
		}
		if _, ok := seen[trimmed]; ok {
			continue
		}
		seen[trimmed] = struct{}{}
		unique = append(unique, trimmed)
	}
	return unique
}
