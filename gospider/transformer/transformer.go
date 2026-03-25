package transformer

import (
	"regexp"
	"strings"
	"time"
)

// DataTransformer 数据转换器
type DataTransformer struct {
	rules []TransformRule
}

// TransformRule 转换规则
type TransformRule struct {
	Field  string
	Type   string
	Param  interface{}
	Apply  func(interface{}) interface{}
}

// NewDataTransformer 创建数据转换器
func NewDataTransformer() *DataTransformer {
	return &DataTransformer{
		rules: make([]TransformRule, 0),
	}
}

// AddTrimRule 添加去除空白规则
func (t *DataTransformer) AddTrimRule(fields ...string) *DataTransformer {
	for _, field := range fields {
		t.rules = append(t.rules, TransformRule{
			Field: field,
			Type:  "trim",
			Apply: func(v interface{}) interface{} {
				if s, ok := v.(string); ok {
					return strings.TrimSpace(s)
				}
				return v
			},
		})
	}
	return t
}

// AddReplaceRule 添加替换规则
func (t *DataTransformer) AddReplaceRule(field, from, to string) *DataTransformer {
	t.rules = append(t.rules, TransformRule{
		Field: field,
		Type:  "replace",
		Param: []string{from, to},
		Apply: func(v interface{}) interface{} {
			if s, ok := v.(string); ok {
				return strings.ReplaceAll(s, from, to)
			}
			return v
		},
	})
	return t
}

// AddRegexRule 添加正则提取规则
func (t *DataTransformer) AddRegexRule(field, pattern string) *DataTransformer {
	t.rules = append(t.rules, TransformRule{
		Field: field,
		Type:  "regex",
		Param: pattern,
		Apply: func(v interface{}) interface{} {
			if s, ok := v.(string); ok {
				re := regexp.MustCompile(pattern)
				matches := re.FindStringSubmatch(s)
				if len(matches) > 1 {
					return matches[1]
				}
				return s
			}
			return v
		},
	})
	return t
}

// AddUpperCaseRule 添加大写规则
func (t *DataTransformer) AddUpperCaseRule(field string) *DataTransformer {
	t.rules = append(t.rules, TransformRule{
		Field: field,
		Type:  "upper",
		Apply: func(v interface{}) interface{} {
			if s, ok := v.(string); ok {
				return strings.ToUpper(s)
			}
			return v
		},
	})
	return t
}

// AddLowerCaseRule 添加小写规则
func (t *DataTransformer) AddLowerCaseRule(field string) *DataTransformer {
	t.rules = append(t.rules, TransformRule{
		Field: field,
		Type:  "lower",
		Apply: func(v interface{}) interface{} {
			if s, ok := v.(string); ok {
				return strings.ToLower(s)
			}
			return v
		},
	})
	return t
}

// AddDateFormatRule 添加日期格式化规则
func (t *DataTransformer) AddDateFormatRule(field, format string) *DataTransformer {
	t.rules = append(t.rules, TransformRule{
		Field: field,
		Type:  "date",
		Param: format,
		Apply: func(v interface{}) interface{} {
			if s, ok := v.(string); ok {
				// 尝试解析常见日期格式
				formats := []string{
					"2006-01-02",
					"2006/01/02",
					"01/02/2006",
					"2006-01-02 15:04:05",
					time.RFC3339,
				}
				
				for _, f := range formats {
					if t, err := time.Parse(f, s); err == nil {
						return t.Format(format)
					}
				}
				return s
			}
			return v
		},
	})
	return t
}

// AddNullRule 添加空值处理规则
func (t *DataTransformer) AddNullRule(field string, defaultValue interface{}) *DataTransformer {
	t.rules = append(t.rules, TransformRule{
		Field: field,
		Type:  "null",
		Param: defaultValue,
		Apply: func(v interface{}) interface{} {
			if v == nil || v == "" {
				return defaultValue
			}
			return v
		},
	})
	return t
}

// AddHTMLCleanRule 添加 HTML 清理规则
func (t *DataTransformer) AddHTMLCleanRule(fields ...string) *DataTransformer {
	for _, field := range fields {
		t.rules = append(t.rules, TransformRule{
			Field: field,
			Type:  "html_clean",
			Apply: func(v interface{}) interface{} {
				if s, ok := v.(string); ok {
					// 简单 HTML 标签移除
					re := regexp.MustCompile(`<[^>]*>`)
					return re.ReplaceAllString(s, "")
				}
				return v
			},
		})
	}
	return t
}

// Transform 转换数据
func (t *DataTransformer) Transform(data map[string]interface{}) map[string]interface{} {
	result := make(map[string]interface{})
	
	// 复制原始数据
	for k, v := range data {
		result[k] = v
	}
	
	// 应用规则
	for _, rule := range t.rules {
		if val, ok := result[rule.Field]; ok {
			result[rule.Field] = rule.Apply(val)
		}
	}
	
	return result
}

// ClearRules 清空规则
func (t *DataTransformer) ClearRules() {
	t.rules = make([]TransformRule, 0)
}
