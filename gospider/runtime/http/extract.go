package httpruntime

import (
	"encoding/json"
	"fmt"
	"net/url"
	"regexp"
	"strings"

	"gospider/core"
	"gospider/parser"
)

func extractPayload(job core.JobSpec, body string) (map[string]interface{}, error) {
	if len(job.Extract) == 0 {
		return map[string]interface{}{}, nil
	}

	htmlParser := parser.NewHTMLParser(body)
	jsonParser := parser.NewJSONParser(body)
	result := make(map[string]interface{}, len(job.Extract))

	for _, spec := range job.Extract {
		value, ok, err := evaluateExtractSpec(spec, htmlParser, jsonParser, body, job.Target.URL)
		if err != nil {
			return nil, err
		}
		if !ok {
			if spec.Required {
				return nil, fmt.Errorf("required extract field %q could not be resolved", spec.Field)
			}
			continue
		}
		if err := validateExtractValue(spec, value); err != nil {
			return nil, err
		}
		result[spec.Field] = value
	}
	return result, nil
}

func evaluateExtractSpec(spec core.ExtractSpec, htmlParser *parser.HTMLParser, jsonParser *parser.JSONParser, body, targetURL string) (interface{}, bool, error) {
	switch strings.ToLower(spec.Type) {
	case "css":
		if htmlParser == nil || spec.Expr == "" {
			return nil, false, nil
		}
		value := htmlParser.CSSFirst(spec.Expr)
		v, ok := nonEmpty(value)
		return v, ok, nil
	case "css_attr":
		if htmlParser == nil || spec.Expr == "" || spec.Attr == "" {
			return nil, false, nil
		}
		value := htmlParser.CSSAttrFirst(spec.Expr, spec.Attr)
		v, ok := nonEmpty(value)
		return v, ok, nil
	case "xpath":
		if htmlParser == nil || spec.Expr == "" {
			return nil, false, nil
		}
		value, err := htmlParser.XPathFirstStrict(spec.Expr)
		if err != nil {
			return nil, false, err
		}
		v, ok := nonEmpty(value)
		return v, ok, nil
	case "regex":
		if spec.Expr == "" {
			return nil, false, nil
		}
		compiled := parser.MustCompileRegex(spec.Expr)
		if compiled == nil {
			return nil, false, fmt.Errorf("invalid regex extract expression for field %q", spec.Field)
		}
		matches := compiled.FindStringSubmatch(body)
		if len(matches) > 1 {
			v, ok := nonEmpty(matches[1])
			return v, ok, nil
		}
		if len(matches) == 1 {
			v, ok := nonEmpty(matches[0])
			return v, ok, nil
		}
		return nil, false, nil
	case "json_path":
		if jsonParser == nil {
			return nil, false, nil
		}
		path := spec.Path
		if path == "" {
			path = spec.Expr
		}
		if path == "" {
			return nil, false, nil
		}
		value := jsonParser.Get(path)
		if !value.Exists() {
			return nil, false, nil
		}
		return jsonValueToInterface(value.Raw), true, nil
	case "ai":
		return aiExtractValue(spec, htmlParser, body, targetURL)
	default:
		if spec.Field == "url" {
			v, ok := nonEmpty(targetURL)
			return v, ok, nil
		}
		if spec.Field == "html" || spec.Field == "dom" {
			v, ok := nonEmpty(body)
			return v, ok, nil
		}
		return nil, false, nil
	}
}

func aiExtractValue(spec core.ExtractSpec, htmlParser *parser.HTMLParser, body, targetURL string) (interface{}, bool, error) {
	field := strings.ToLower(strings.TrimSpace(spec.Field))
	expectedType, _ := spec.Schema["type"].(string)

	title := ""
	description := ""
	links := []string{}
	images := []string{}
	if htmlParser != nil {
		title = strings.TrimSpace(htmlParser.Title())
		description = strings.TrimSpace(htmlParser.CSSAttrFirst(`meta[name="description"]`, "content"))
		if description == "" {
			description = strings.TrimSpace(htmlParser.CSSAttrFirst(`meta[property="og:description"]`, "content"))
		}
		links = absolutizeURLs(targetURL, htmlParser.Links())
		images = absolutizeURLs(targetURL, htmlParser.Images())
	}

	switch {
	case field == "url":
		v, ok := nonEmpty(targetURL)
		return v, ok, nil
	case field == "html" || field == "dom":
		v, ok := nonEmpty(body)
		return v, ok, nil
	case strings.Contains(field, "title") || strings.Contains(field, "headline"):
		v, ok := nonEmpty(title)
		return v, ok, nil
	case strings.Contains(field, "description") || strings.Contains(field, "summary") || strings.Contains(field, "desc"):
		if description == "" && htmlParser != nil {
			description = strings.TrimSpace(htmlParser.CSSFirst("p"))
		}
		v, ok := nonEmpty(description)
		return v, ok, nil
	case strings.Contains(field, "link"):
		return coerceSliceForSchema(expectedType, links)
	case strings.Contains(field, "image") || strings.Contains(field, "cover") || strings.Contains(field, "thumbnail"):
		return coerceSliceForSchema(expectedType, images)
	case strings.Contains(field, "content") || strings.Contains(field, "body") || field == "text":
		if htmlParser == nil {
			return nil, false, nil
		}
		v, ok := nonEmpty(htmlParser.Text())
		return v, ok, nil
	case strings.Contains(field, "author"):
		author := ""
		if htmlParser != nil {
			author = strings.TrimSpace(htmlParser.CSSAttrFirst(`meta[name="author"]`, "content"))
			if author == "" {
				author = strings.TrimSpace(htmlParser.CSSAttrFirst(`meta[property="article:author"]`, "content"))
			}
		}
		v, ok := nonEmpty(author)
		return v, ok, nil
	case strings.Contains(field, "date") || strings.Contains(field, "published") || strings.Contains(field, "time"):
		date := ""
		if htmlParser != nil {
			date = strings.TrimSpace(htmlParser.CSSAttrFirst(`meta[property="article:published_time"]`, "content"))
			if date == "" {
				date = strings.TrimSpace(htmlParser.CSSAttrFirst("time", "datetime"))
			}
		}
		v, ok := nonEmpty(date)
		return v, ok, nil
	case strings.Contains(field, "price"):
		match := regexp.MustCompile(`[$¥€£]\s?\d+(?:[.,]\d+)?`).FindString(body)
		v, ok := nonEmpty(match)
		return v, ok, nil
	default:
		v, ok := nonEmpty(title)
		return v, ok, nil
	}
}

func absolutizeURLs(base string, raw []string) []string {
	result := make([]string, 0, len(raw))
	for _, item := range raw {
		trimmed := strings.TrimSpace(item)
		if trimmed == "" {
			continue
		}
		if parsed, err := url.Parse(trimmed); err == nil && parsed.IsAbs() {
			result = append(result, parsed.String())
			continue
		}
		if parsedBase, err := url.Parse(base); err == nil {
			if joined, err := parsedBase.Parse(trimmed); err == nil {
				result = append(result, joined.String())
				continue
			}
		}
		result = append(result, trimmed)
	}
	return result
}

func coerceSliceForSchema(expectedType string, values []string) (interface{}, bool, error) {
	filtered := make([]interface{}, 0, len(values))
	for _, value := range values {
		if strings.TrimSpace(value) != "" {
			filtered = append(filtered, value)
		}
	}
	if len(filtered) == 0 {
		return nil, false, nil
	}
	if expectedType == "string" {
		return filtered[0], true, nil
	}
	return filtered, true, nil
}

func validateExtractValue(spec core.ExtractSpec, value interface{}) error {
	if len(spec.Schema) == 0 {
		return nil
	}
	expectedType, _ := spec.Schema["type"].(string)
	if expectedType == "" {
		return nil
	}
	switch expectedType {
	case "string":
		if _, ok := value.(string); !ok {
			return fmt.Errorf("extract field %q violates schema.type=string", spec.Field)
		}
	case "number", "integer":
		switch value.(type) {
		case float64, float32, int, int32, int64, uint, uint32, uint64:
		default:
			return fmt.Errorf("extract field %q violates schema.type=%s", spec.Field, expectedType)
		}
	case "boolean":
		if _, ok := value.(bool); !ok {
			return fmt.Errorf("extract field %q violates schema.type=boolean", spec.Field)
		}
	case "object":
		if _, ok := value.(map[string]interface{}); !ok {
			return fmt.Errorf("extract field %q violates schema.type=object", spec.Field)
		}
	case "array":
		if _, ok := value.([]interface{}); !ok {
			return fmt.Errorf("extract field %q violates schema.type=array", spec.Field)
		}
	}
	return nil
}

func jsonValueToInterface(raw string) interface{} {
	if raw == "" {
		return ""
	}
	var decoded interface{}
	if err := json.Unmarshal([]byte(raw), &decoded); err != nil {
		return raw
	}
	return decoded
}

func nonEmpty(value string) (interface{}, bool) {
	value = strings.TrimSpace(value)
	if value == "" {
		return nil, false
	}
	return value, true
}
