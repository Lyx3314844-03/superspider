package parser

import (
	"fmt"
	"regexp"
	"strings"

	"github.com/PuerkitoBio/goquery"
	"github.com/antchfx/htmlquery"
	"github.com/tidwall/gjson"
	"golang.org/x/net/html"
)

// HTMLParser HTML 解析器
type HTMLParser struct {
	doc  *goquery.Document
	node *html.Node
	html string
}

// NewHTMLParser 创建解析器
func NewHTMLParser(html string) *HTMLParser {
	doc, err := goquery.NewDocumentFromReader(strings.NewReader(html))
	if err != nil {
		return nil
	}
	node, err := htmlquery.Parse(strings.NewReader(html))
	if err != nil {
		return nil
	}
	return &HTMLParser{
		doc:  doc,
		node: node,
		html: html,
	}
}

// CSS 使用 CSS 选择器提取
func (p *HTMLParser) CSS(selector string) []string {
	results := make([]string, 0)
	query, mode, attr := normalizeCSSSelector(selector)
	if p == nil || p.doc == nil || query == "" {
		return results
	}
	p.doc.Find(query).Each(func(i int, s *goquery.Selection) {
		if value := selectionValue(s, mode, attr); value != "" {
			results = append(results, value)
		}
	})
	return results
}

// CSSFirst 获取第一个匹配
func (p *HTMLParser) CSSFirst(selector string) string {
	results := p.CSS(selector)
	if len(results) > 0 {
		return results[0]
	}
	return ""
}

// CSSAttr 获取属性
func (p *HTMLParser) CSSAttr(selector, attr string) []string {
	results := make([]string, 0)
	query, _, pseudoAttr := normalizeCSSSelector(selector)
	if pseudoAttr != "" {
		attr = pseudoAttr
	}
	if p == nil || p.doc == nil || query == "" || strings.TrimSpace(attr) == "" {
		return results
	}
	p.doc.Find(query).Each(func(i int, s *goquery.Selection) {
		if val, exists := s.Attr(attr); exists && strings.TrimSpace(val) != "" {
			results = append(results, strings.TrimSpace(val))
		}
	})
	return results
}

// CSSAttrFirst 获取第一个属性
func (p *HTMLParser) CSSAttrFirst(selector, attr string) string {
	results := p.CSSAttr(selector, attr)
	if len(results) > 0 {
		return results[0]
	}
	return ""
}

// Links 获取所有链接
func (p *HTMLParser) Links() []string {
	return p.CSSAttr("a", "href")
}

// Images 获取所有图片
func (p *HTMLParser) Images() []string {
	return p.CSSAttr("img", "src")
}

// Title 获取标题
func (p *HTMLParser) Title() string {
	return p.doc.Find("title").Text()
}

// Text 获取文本
func (p *HTMLParser) Text() string {
	return p.doc.Text()
}

// XPathFirst XPath 查询（兼容旧接口）
func (p *HTMLParser) XPathFirst(xpath string) string {
	result, _ := p.XPathFirstStrict(xpath)
	return result
}

// XPath returns every value matched by a full XPath expression.
func (p *HTMLParser) XPath(xpath string) []string {
	values, _ := p.XPathStrict(xpath)
	return values
}

// XPathStrict returns every value matched by a full XPath expression.
func (p *HTMLParser) XPathStrict(xpath string) ([]string, error) {
	if p == nil || p.node == nil {
		return nil, fmt.Errorf("html parser is not initialized")
	}
	if strings.TrimSpace(xpath) == "" {
		return nil, fmt.Errorf("xpath expression is empty")
	}
	nodes, err := htmlquery.QueryAll(p.node, xpath)
	if err != nil {
		return nil, fmt.Errorf("xpath evaluation error: %w", err)
	}
	values := make([]string, 0, len(nodes))
	for _, node := range nodes {
		if value := xpathNodeValue(node); value != "" {
			values = append(values, value)
		}
	}
	return values, nil
}

// XPathFirstStrict runs a full XPath query against the parsed HTML document.
func (p *HTMLParser) XPathFirstStrict(xpath string) (string, error) {
	values, err := p.XPathStrict(xpath)
	if err != nil {
		return "", err
	}
	if len(values) == 0 {
		return "", nil
	}
	return values[0], nil
}

// MustCompileRegex compiles a regex pattern and returns nil on failure.
func MustCompileRegex(expr string) *regexp.Regexp {
	compiled, err := regexp.Compile(expr)
	if err != nil {
		return nil
	}
	return compiled
}

func normalizeCSSSelector(selector string) (query string, mode string, attr string) {
	query = strings.TrimSpace(selector)
	mode = "text"
	lower := strings.ToLower(query)
	if strings.HasSuffix(lower, "::text") {
		return strings.TrimSpace(query[:len(query)-len("::text")]), "text", ""
	}
	if strings.HasSuffix(lower, "::html") {
		return strings.TrimSpace(query[:len(query)-len("::html")]), "html", ""
	}
	attrRe := regexp.MustCompile(`(?i)::attr\(([^)]+)\)\s*$`)
	if match := attrRe.FindStringSubmatchIndex(query); match != nil {
		return strings.TrimSpace(query[:match[0]]), "attr", strings.TrimSpace(query[match[2]:match[3]])
	}
	return query, mode, attr
}

func selectionValue(s *goquery.Selection, mode string, attr string) string {
	switch mode {
	case "attr":
		if value, ok := s.Attr(attr); ok {
			return strings.TrimSpace(value)
		}
	case "html":
		if value, err := s.Html(); err == nil {
			return strings.TrimSpace(value)
		}
	default:
		return strings.TrimSpace(s.Text())
	}
	return ""
}

func xpathNodeValue(node *html.Node) string {
	if node == nil {
		return ""
	}
	if value := strings.TrimSpace(htmlquery.InnerText(node)); value != "" {
		return value
	}
	for _, attr := range node.Attr {
		if strings.TrimSpace(attr.Val) != "" {
			return strings.TrimSpace(attr.Val)
		}
	}
	if value := strings.TrimSpace(htmlquery.SelectAttr(node, "href")); value != "" {
		return value
	}
	return strings.TrimSpace(node.Data)
}

// HTML 获取 HTML
func (p *HTMLParser) HTML() string {
	return p.html
}

// JSONParser JSON 解析器
type JSONParser struct {
	json string
}

// NewJSONParser 创建 JSON 解析器
func NewJSONParser(json string) *JSONParser {
	return &JSONParser{json: json}
}

// Get 获取 JSON 路径
func (p *JSONParser) Get(path string) gjson.Result {
	return gjson.Get(p.json, path)
}

// GetString 获取字符串
func (p *JSONParser) GetString(path string) string {
	return gjson.Get(p.json, path).String()
}

// GetInt 获取整数
func (p *JSONParser) GetInt(path string) int64 {
	return gjson.Get(p.json, path).Int()
}

// GetFloat 获取浮点数
func (p *JSONParser) GetFloat(path string) float64 {
	return gjson.Get(p.json, path).Float()
}

// GetBool 获取布尔值
func (p *JSONParser) GetBool(path string) bool {
	return gjson.Get(p.json, path).Bool()
}

// GetArray 获取数组
func (p *JSONParser) GetArray(path string) []gjson.Result {
	result := gjson.Get(p.json, path)
	results := make([]gjson.Result, 0)
	result.ForEach(func(_, value gjson.Result) bool {
		results = append(results, value)
		return true
	})
	return results
}
