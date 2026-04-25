package parser

import (
	"fmt"
	"regexp"
	"strings"
)

type ExtractRule struct {
	Field    string
	Type     string
	Expr     string
	Attr     string
	All      bool
	Required bool
}

type SelectorExtractor struct{}

func NewSelectorExtractor() *SelectorExtractor {
	return &SelectorExtractor{}
}

func (e *SelectorExtractor) Extract(html string, rules []ExtractRule) (map[string]any, error) {
	parser := NewHTMLParser(html)
	if parser == nil {
		return nil, fmt.Errorf("html parser is not initialized")
	}
	result := make(map[string]any)
	for _, rule := range rules {
		field := strings.TrimSpace(rule.Field)
		if field == "" {
			continue
		}
		values, err := extractRuleValues(parser, html, rule)
		if err != nil {
			return nil, err
		}
		if len(values) == 0 {
			if rule.Required {
				return nil, fmt.Errorf("required extract field %q could not be resolved", field)
			}
			continue
		}
		if rule.All {
			result[field] = values
		} else {
			result[field] = values[0]
		}
	}
	return result, nil
}

func extractRuleValues(parser *HTMLParser, html string, rule ExtractRule) ([]string, error) {
	expr := strings.TrimSpace(rule.Expr)
	switch strings.ToLower(strings.TrimSpace(rule.Type)) {
	case "css":
		return parser.CSS(expr), nil
	case "css_attr":
		return parser.CSSAttr(expr, rule.Attr), nil
	case "xpath":
		return parser.XPathStrict(expr)
	case "regex":
		compiled, err := regexp.Compile(expr)
		if err != nil {
			return nil, err
		}
		matches := compiled.FindAllStringSubmatch(html, -1)
		values := make([]string, 0, len(matches))
		for _, match := range matches {
			if len(match) > 1 {
				values = append(values, strings.TrimSpace(match[1]))
			} else if len(match) > 0 {
				values = append(values, strings.TrimSpace(match[0]))
			}
		}
		return values, nil
	default:
		return nil, fmt.Errorf("unsupported extract rule type %q", rule.Type)
	}
}
