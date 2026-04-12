package parser

import (
	"fmt"
	"regexp"
	"strings"

	"github.com/antchfx/htmlquery"
	"github.com/PuerkitoBio/goquery"
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
	p.doc.Find(selector).Each(func(i int, s *goquery.Selection) {
		results = append(results, strings.TrimSpace(s.Text()))
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
	p.doc.Find(selector).Each(func(i int, s *goquery.Selection) {
		if val, exists := s.Attr(attr); exists {
			results = append(results, val)
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

// XPathFirstStrict runs a full XPath query against the parsed HTML document.
func (p *HTMLParser) XPathFirstStrict(xpath string) (string, error) {
	if p == nil || p.node == nil {
		return "", fmt.Errorf("html parser is not initialized")
	}
	if strings.TrimSpace(xpath) == "" {
		return "", fmt.Errorf("xpath expression is empty")
	}
	node, err := htmlquery.Query(p.node, xpath)
	if err != nil {
		return "", fmt.Errorf("xpath evaluation error: %w", err)
	}
	if node == nil {
		return "", nil
	}
	if value := strings.TrimSpace(htmlquery.InnerText(node)); value != "" {
		return value, nil
	}
	return strings.TrimSpace(htmlquery.SelectAttr(node, "href")), nil
}

// MustCompileRegex compiles a regex pattern and returns nil on failure.
func MustCompileRegex(expr string) *regexp.Regexp {
	compiled, err := regexp.Compile(expr)
	if err != nil {
		return nil
	}
	return compiled
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
