package research

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"reflect"
	"sort"
	"strings"

	"github.com/PuerkitoBio/goquery"
	"gospider/storage"
)

type SiteProfile struct {
	URL             string          `json:"url"`
	PageType        string          `json:"page_type"`
	Signals         map[string]bool `json:"signals"`
	CandidateFields []string        `json:"candidate_fields"`
	RiskLevel       string          `json:"risk_level"`
}

type ResearchRuntime struct{}

func NewResearchRuntime() *ResearchRuntime {
	return &ResearchRuntime{}
}

func (r *ResearchRuntime) Run(job ResearchJob, content string) (map[string]interface{}, error) {
	if len(job.SeedURLs) == 0 || strings.TrimSpace(job.SeedURLs[0]) == "" {
		return nil, fmt.Errorf("seed_urls[0] is required")
	}
	seed := job.SeedURLs[0]
	if strings.TrimSpace(content) == "" {
		content = fmt.Sprintf("<title>%s</title>", seed)
	}
	profile := profileSite(seed, content)
	extracted, err := extractContent(content, job.ExtractSchema, job.ExtractSpecs)
	if err != nil {
		return nil, err
	}

	result := map[string]interface{}{
		"seed":    seed,
		"profile": profile,
		"extract": extracted,
	}

	if outputPath := stringMapValue(job.Output, "path"); outputPath != "" {
		datasetResult, err := writeDataset(outputPath, stringMapValue(job.Output, "format"), extracted)
		if err != nil {
			return nil, err
		}
		result["dataset"] = datasetResult
	}
	return result, nil
}

func profileSite(url string, content string) SiteProfile {
	lower := strings.ToLower(content)
	signals := map[string]bool{
		"has_form":       strings.Contains(lower, "<form"),
		"has_pagination": strings.Contains(lower, "next") || strings.Contains(lower, "page="),
		"has_list":       strings.Contains(lower, "<li") || strings.Contains(lower, "<ul"),
		"has_detail":     strings.Contains(lower, "<article") || strings.Contains(lower, "<h1"),
		"has_captcha":    strings.Contains(lower, "captcha") || strings.Contains(lower, "verify"),
	}

	pageType := "generic"
	if signals["has_list"] && !signals["has_detail"] {
		pageType = "list"
	} else if signals["has_detail"] {
		pageType = "detail"
	}

	candidateFields := []string{}
	if strings.Contains(lower, "<title") {
		candidateFields = append(candidateFields, "title")
	}
	if strings.Contains(lower, "price") {
		candidateFields = append(candidateFields, "price")
	}
	if strings.Contains(lower, "author") {
		candidateFields = append(candidateFields, "author")
	}

	riskLevel := "low"
	if signals["has_captcha"] {
		riskLevel = "high"
	} else if strings.HasPrefix(strings.ToLower(url), "https://") && signals["has_form"] {
		riskLevel = "medium"
	}

	return SiteProfile{
		URL:             url,
		PageType:        pageType,
		Signals:         signals,
		CandidateFields: candidateFields,
		RiskLevel:       riskLevel,
	}
}

func extractContent(content string, schema map[string]interface{}, specs []map[string]interface{}) (map[string]interface{}, error) {
	properties := map[string]interface{}{}
	if schema != nil {
		if raw, ok := schema["properties"].(map[string]interface{}); ok {
			properties = raw
		}
	}

	extracted := map[string]interface{}{}
	if len(specs) > 0 {
		for _, spec := range specs {
			field := strings.TrimSpace(stringMapValue(spec, "field"))
			if field == "" {
				continue
			}
			value := extractWithSpec(content, field, spec)
			if isEmptyValue(value) {
				if boolMapValue(spec, "required") {
					return nil, fmt.Errorf("required extract field %q could not be resolved", field)
				}
				continue
			}
			if err := validateSchema(field, value, schemaForField(spec, properties, field)); err != nil {
				return nil, err
			}
			extracted[field] = value
		}
		return extracted, nil
	}

	fieldNames := make([]string, 0, len(properties))
	for field := range properties {
		fieldNames = append(fieldNames, field)
	}
	sort.Strings(fieldNames)
	for _, field := range fieldNames {
		if value, ok := heuristicExtract(field, content); ok {
			extracted[field] = value
		}
	}
	return extracted, nil
}

func extractWithSpec(content string, field string, spec map[string]interface{}) interface{} {
	extractType := strings.ToLower(strings.TrimSpace(stringMapValue(spec, "type")))
	expr := stringMapValue(spec, "expr")
	path := stringMapValue(spec, "path")
	attr := stringMapValue(spec, "attr")

	switch extractType {
	case "css":
		selector := expr
		if selector == "" && field == "title" {
			selector = "title"
		}
		if selector != "" {
			if value := cssSelectText(content, selector); value != "" {
				return value
			}
		}
	case "css_attr":
		if expr != "" && attr != "" {
			if value := cssSelectAttr(content, expr, attr); value != "" {
				return value
			}
		}
	case "xpath":
		return xpathExtract(content, expr)
	case "regex":
		if expr == "" {
			return nil
		}
		re, err := regexp.Compile("(?is)" + expr)
		if err != nil {
			return nil
		}
		match := re.FindStringSubmatch(content)
		if len(match) > 1 {
			return strings.TrimSpace(match[1])
		}
		if len(match) == 1 {
			return strings.TrimSpace(match[0])
		}
	case "json_path":
		if path == "" {
			path = expr
		}
		return jsonPathExtract(content, path)
	case "ai":
		if field == "title" {
			if value, ok := heuristicExtract("title", content); ok {
				return value
			}
		}
		if field == "html" || field == "dom" {
			return content
		}
	}

	if value, ok := heuristicExtract(field, content); ok {
		return value
	}
	return nil
}

func xpathExtract(content string, expr string) interface{} {
	normalized := strings.TrimSpace(strings.ToLower(expr))
	switch normalized {
	case "//title/text()":
		if value, ok := heuristicExtract("title", content); ok {
			return value
		}
	case "//h1/text()":
		re := regexp.MustCompile(`(?is)<h1[^>]*>(.*?)</h1>`)
		if match := re.FindStringSubmatch(content); len(match) > 1 {
			return strings.TrimSpace(stripHTML(match[1]))
		}
	default:
		metaRe := regexp.MustCompile(`(?is)^//meta\[@name=['"]([^'"]+)['"]\]/@content$`)
		if match := metaRe.FindStringSubmatch(normalized); len(match) > 1 {
			pattern := regexp.MustCompile(fmt.Sprintf(`(?is)<meta[^>]*name=["']%s["'][^>]*content=["']([^"']+)["']`, regexp.QuoteMeta(match[1])))
			if found := pattern.FindStringSubmatch(content); len(found) > 1 {
				return strings.TrimSpace(found[1])
			}
		}
	}
	return nil
}

func heuristicExtract(field string, content string) (interface{}, bool) {
	switch strings.ToLower(strings.TrimSpace(field)) {
	case "title":
		re := regexp.MustCompile(`(?is)<title>(.*?)</title>`)
		match := re.FindStringSubmatch(content)
		if len(match) > 1 {
			return strings.TrimSpace(match[1]), true
		}
	default:
		re := regexp.MustCompile(`(?im)` + regexp.QuoteMeta(field) + `\s*[:=]\s*([^\n<]+)`)
		match := re.FindStringSubmatch(content)
		if len(match) > 1 {
			return strings.TrimSpace(match[1]), true
		}
	}
	return nil, false
}

func jsonPathExtract(content string, path string) interface{} {
	if strings.TrimSpace(path) == "" {
		return nil
	}
	var payload interface{}
	if err := json.Unmarshal([]byte(content), &payload); err != nil {
		return nil
	}
	normalized := strings.TrimPrefix(strings.TrimSpace(path), "$.")
	if normalized == "" {
		return nil
	}
	current := payload
	for _, segment := range strings.Split(normalized, ".") {
		object, ok := current.(map[string]interface{})
		if !ok {
			return nil
		}
		value, exists := object[segment]
		if !exists {
			return nil
		}
		current = value
	}
	return current
}

func validateSchema(field string, value interface{}, schema map[string]interface{}) error {
	expectedType := strings.TrimSpace(stringMapValue(schema, "type"))
	if expectedType == "" {
		return nil
	}
	valid := false
	switch expectedType {
	case "string":
		_, valid = value.(string)
	case "number":
		switch value.(type) {
		case int, int32, int64, float32, float64:
			valid = true
		}
	case "integer":
		switch value.(type) {
		case int, int32, int64:
			valid = true
		}
	case "boolean":
		_, valid = value.(bool)
	case "object":
		valid = reflect.TypeOf(value) != nil && reflect.TypeOf(value).Kind() == reflect.Map
	case "array":
		valid = reflect.TypeOf(value) != nil && (reflect.TypeOf(value).Kind() == reflect.Slice || reflect.TypeOf(value).Kind() == reflect.Array)
	}
	if !valid {
		return fmt.Errorf("extract field %q violates schema.type=%s", field, expectedType)
	}
	return nil
}

func schemaForField(spec map[string]interface{}, properties map[string]interface{}, field string) map[string]interface{} {
	if raw, ok := spec["schema"].(map[string]interface{}); ok {
		return raw
	}
	if raw, ok := properties[field].(map[string]interface{}); ok {
		return raw
	}
	return map[string]interface{}{}
}

func stripHTML(value string) string {
	re := regexp.MustCompile(`(?is)<[^>]+>`)
	return re.ReplaceAllString(value, "")
}

func cssSelectText(content string, selector string) string {
	document, err := goquery.NewDocumentFromReader(bytes.NewReader([]byte(content)))
	if err != nil {
		return ""
	}
	selection := document.Find(selector).First()
	if selection.Length() == 0 {
		return ""
	}
	return strings.TrimSpace(selection.Text())
}

func cssSelectAttr(content string, selector string, attr string) string {
	document, err := goquery.NewDocumentFromReader(bytes.NewReader([]byte(content)))
	if err != nil {
		return ""
	}
	selection := document.Find(selector).First()
	if selection.Length() == 0 {
		return ""
	}
	value, ok := selection.Attr(attr)
	if !ok {
		return ""
	}
	return strings.TrimSpace(value)
}

func writeDataset(path string, format string, extracted map[string]interface{}) (map[string]interface{}, error) {
	if format == "" {
		format = detectOutputFormat(path)
	}
	if format == "" {
		format = "json"
	}
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return nil, err
	}

	switch format {
	case "jsonl":
		encoded, err := json.Marshal(extracted)
		if err != nil {
			return nil, err
		}
		if err := os.WriteFile(path, append(encoded, '\n'), 0o644); err != nil {
			return nil, err
		}
	case "json", "csv":
		dataset := storage.NewDataset("research")
		dataset.Push(extracted)
		if err := dataset.Save(path, format); err != nil {
			return nil, err
		}
	default:
		return nil, fmt.Errorf("unsupported dataset format %q", format)
	}
	_ = storage.MirrorDatasetRow(extracted)

	return map[string]interface{}{
		"path":   path,
		"format": format,
	}, nil
}

func detectOutputFormat(path string) string {
	extension := strings.ToLower(filepath.Ext(path))
	switch extension {
	case ".json":
		return "json"
	case ".jsonl":
		return "jsonl"
	case ".csv":
		return "csv"
	default:
		return ""
	}
}

func stringMapValue(values map[string]interface{}, key string) string {
	if values == nil {
		return ""
	}
	if value, ok := values[key].(string); ok {
		return value
	}
	return ""
}

func boolMapValue(values map[string]interface{}, key string) bool {
	if values == nil {
		return false
	}
	if value, ok := values[key].(bool); ok {
		return value
	}
	return false
}

func isEmptyValue(value interface{}) bool {
	if value == nil {
		return true
	}
	if text, ok := value.(string); ok {
		return strings.TrimSpace(text) == ""
	}
	return false
}
