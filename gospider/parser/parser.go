package parser

import (
	"strings"

	"github.com/PuerkitoBio/goquery"
	"github.com/tidwall/gjson"
)

// HTMLParser HTML 解析器
type HTMLParser struct {
	doc *goquery.Document
	html string
}

// NewHTMLParser 创建解析器
func NewHTMLParser(html string) *HTMLParser {
	doc, err := goquery.NewDocumentFromReader(strings.NewReader(html))
	if err != nil {
		return nil
	}
	return &HTMLParser{
		doc:  doc,
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

// XPathFirst XPath 查询（简化实现）
func (p *HTMLParser) XPathFirst(xpath string) string {
	// 简化实现：使用 CSS 选择器代替
	// 实际应该使用 goquery 的 XPath 支持
	return p.CSSFirst(xpath)
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
