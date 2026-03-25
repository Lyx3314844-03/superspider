package spider

import (
	"gospider/core"
	"gospider/parser"
)

// Spider 基础爬虫类（Scrapy 风格）
type Spider struct {
	Name      string
	StartURLs []string
	AllowedDomains []string
	CustomSettings map[string]interface{}
}

// NewSpider 创建爬虫
func NewSpider(name string) *Spider {
	return &Spider{
		Name: name,
		StartURLs: make([]string, 0),
		AllowedDomains: make([]string, 0),
		CustomSettings: make(map[string]interface{}),
	}
}

// SetStartURLs 设置起始 URL
func (s *Spider) SetStartURLs(urls ...string) {
	s.StartURLs = append(s.StartURLs, urls...)
}

// SetAllowedDomains 设置允许的域名
func (s *Spider) SetAllowedDomains(domains ...string) {
	s.AllowedDomains = append(s.AllowedDomains, domains...)
}

// SetCustomSettings 设置自定义配置
func (s *Spider) SetCustomSettings(key string, value interface{}) {
	s.CustomSettings[key] = value
}

// Parse 默认解析方法
func (s *Spider) Parse(page *core.Page) []interface{} {
	// 子类实现
	return nil
}

// ParseItem 物品解析方法
func (s *Spider) ParseItem(page *core.Page) map[string]interface{} {
	// 子类实现
	return nil
}

// CrawlSpider 自动爬取爬虫（类似 Scrapy CrawlSpider）
type CrawlSpider struct {
	*Spider
	Rules []Rule
}

// Rule 爬取规则
type Rule struct {
	LinkExtractor *LinkExtractor
	Callback func(*core.Page) []interface{}
	Follow bool
}

// LinkExtractor 链接提取器
type LinkExtractor struct {
	Allow []string
	Deny []string
	CSSSelector string
}

// NewCrawlSpider 创建自动爬取爬虫
func NewCrawlSpider(name string) *CrawlSpider {
	return &CrawlSpider{
		Spider: NewSpider(name),
		Rules: make([]Rule, 0),
	}
}

// AddRule 添加规则
func (s *CrawlSpider) AddRule(rule Rule) {
	s.Rules = append(s.Rules, rule)
}

// ExtractLinks 提取链接
func (s *CrawlSpider) ExtractLinks(page *core.Page) []string {
	htmlParser := parser.NewHTMLParser(page.Response.Text)
	links := make([]string, 0)
	
	for _, rule := range s.Rules {
		if rule.LinkExtractor.CSSSelector != "" {
			extracted := htmlParser.CSSAttr(rule.LinkExtractor.CSSSelector, "href")
			links = append(links, extracted...)
		} else {
			extracted := htmlParser.Links()
			links = append(links, extracted...)
		}
	}
	
	return links
}

// Item 数据项
type Item struct {
	Data map[string]interface{}
}

// NewItem 创建 Item
func NewItem() *Item {
	return &Item{
		Data: make(map[string]interface{}),
	}
}

// Set 设置字段
func (i *Item) Set(key string, value interface{}) {
	i.Data[key] = value
}

// Get 获取字段
func (i *Item) Get(key string) interface{} {
	return i.Data[key]
}

// Loader 数据加载器
type Loader struct {
	Item *Item
}

// NewLoader 创建 Loader
func NewLoader() *Loader {
	return &Loader{
		Item: NewItem(),
	}
}

// AddCSS 使用 CSS 选择器添加字段
func (l *Loader) AddCSS(page *core.Page, fieldName string, cssSelector string) {
	htmlParser := parser.NewHTMLParser(page.Response.Text)
	value := htmlParser.CSSFirst(cssSelector)
	l.Item.Set(fieldName, value)
}

// AddXPath 使用 XPath 添加字段
func (l *Loader) AddXPath(page *core.Page, fieldName string, xpathSelector string) {
	htmlParser := parser.NewHTMLParser(page.Response.Text)
	value := htmlParser.XPathFirst(xpathSelector)
	l.Item.Set(fieldName, value)
}

// AddJSON 使用 JSON 路径添加字段
func (l *Loader) AddJSON(page *core.Page, fieldName string, jsonPath string) {
	jsonParser := parser.NewJSONParser(page.Response.Text)
	value := jsonParser.Get(jsonPath)
	l.Item.Set(fieldName, value.String())
}

// AddValue 直接添加值
func (l *Loader) AddValue(fieldName string, value interface{}) {
	l.Item.Set(fieldName, value)
}

// LoadItem 加载 Item
func (l *Loader) LoadItem() *Item {
	return l.Item
}
