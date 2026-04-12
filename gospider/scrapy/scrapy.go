package scrapy

import (
	"encoding/csv"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"regexp"
	"strings"

	"github.com/antchfx/htmlquery"
	"golang.org/x/net/html"

	"gospider/parser"
)

type Callback func(*Response) ([]any, error)

type Request struct {
	URL      string
	Method   string
	Headers  map[string]string
	Body     string
	Meta     map[string]any
	Priority int
	Callback Callback
}

func NewRequest(rawURL string, callback Callback) *Request {
	return &Request{
		URL:      rawURL,
		Method:   http.MethodGet,
		Headers:  map[string]string{},
		Meta:     map[string]any{},
		Callback: callback,
	}
}

func (r *Request) SetHeader(key, value string) *Request {
	r.Headers[key] = value
	return r
}

func (r *Request) SetMeta(key string, value any) *Request {
	r.Meta[key] = value
	return r
}

type Response struct {
	URL        string
	StatusCode int
	Headers    http.Header
	Body       []byte
	Text       string
	Request    *Request
}

func (r *Response) Selector() *Selector {
	return NewSelector(r.Text)
}

func (r *Response) CSS(query string) *SelectorList {
	return r.Selector().CSS(query)
}

func (r *Response) XPath(expr string) *SelectorList {
	return r.Selector().XPath(expr)
}

func (r *Response) Follow(target string, callback Callback) *Request {
	resolved := target
	if base, err := url.Parse(r.URL); err == nil {
		if rel, relErr := url.Parse(target); relErr == nil {
			resolved = base.ResolveReference(rel).String()
		}
	}
	return NewRequest(resolved, callback)
}

type Item map[string]any

func NewItem() Item {
	return Item{}
}

func (i Item) Set(key string, value any) Item {
	i[key] = value
	return i
}

func (i Item) Get(key string) any {
	return i[key]
}

func (i Item) ToMap() map[string]any {
	result := make(map[string]any, len(i))
	for key, value := range i {
		result[key] = value
	}
	return result
}

type Selector struct {
	html   string
	parser *parser.HTMLParser
	root   *html.Node
}

func NewSelector(rawHTML string) *Selector {
	node, _ := htmlquery.Parse(strings.NewReader(rawHTML))
	return &Selector{
		html:   rawHTML,
		parser: parser.NewHTMLParser(rawHTML),
		root:   node,
	}
}

func (s *Selector) CSS(query string) *SelectorList {
	if s == nil || s.parser == nil {
		return &SelectorList{values: []string{}}
	}
	return &SelectorList{values: s.parser.CSS(query)}
}

func (s *Selector) XPath(expr string) *SelectorList {
	if s == nil || s.root == nil || strings.TrimSpace(expr) == "" {
		return &SelectorList{values: []string{}}
	}
	trimmed := strings.TrimSpace(expr)
	attrName := ""
	textOnly := false
	baseExpr := trimmed
	if index := strings.LastIndex(trimmed, "/@"); index > 0 {
		baseExpr = trimmed[:index]
		attrName = trimmed[index+2:]
	}
	if strings.HasSuffix(trimmed, "/text()") {
		baseExpr = strings.TrimSuffix(trimmed, "/text()")
		textOnly = true
	}
	nodes, err := htmlquery.QueryAll(s.root, baseExpr)
	if err != nil {
		return &SelectorList{values: []string{}}
	}
	values := make([]string, 0, len(nodes))
	for _, node := range nodes {
		if attrName != "" {
			if value := strings.TrimSpace(htmlquery.SelectAttr(node, attrName)); value != "" {
				values = append(values, value)
			}
			continue
		}
		if textOnly {
			if value := strings.TrimSpace(htmlquery.InnerText(node)); value != "" {
				values = append(values, value)
			}
			continue
		}
		if value := strings.TrimSpace(htmlquery.InnerText(node)); value != "" {
			values = append(values, value)
			continue
		}
		if value := strings.TrimSpace(htmlquery.SelectAttr(node, "href")); value != "" {
			values = append(values, value)
		}
	}
	return &SelectorList{values: values}
}

func (s *Selector) Re(pattern string) []string {
	compiled, err := regexp.Compile(pattern)
	if err != nil {
		return []string{}
	}
	matches := compiled.FindAllStringSubmatch(s.html, -1)
	values := make([]string, 0, len(matches))
	for _, match := range matches {
		if len(match) > 1 {
			values = append(values, match[1])
		} else if len(match) > 0 {
			values = append(values, match[0])
		}
	}
	return values
}

func (s *Selector) ReFirst(pattern string) string {
	values := s.Re(pattern)
	if len(values) == 0 {
		return ""
	}
	return values[0]
}

type SelectorList struct {
	values []string
}

func (s *SelectorList) Get() string {
	if s == nil || len(s.values) == 0 {
		return ""
	}
	return s.values[0]
}

func (s *SelectorList) GetAll() []string {
	if s == nil {
		return []string{}
	}
	return append([]string{}, s.values...)
}

func (s *SelectorList) Len() int {
	if s == nil {
		return 0
	}
	return len(s.values)
}

type ItemPipeline interface {
	ProcessItem(Item) (Item, error)
}

type SpiderMiddleware interface {
	ProcessSpiderOutput(*Response, []any, *Spider) ([]any, error)
}

type DownloaderMiddleware interface {
	ProcessRequest(*Request, *Spider) (*Request, error)
	ProcessResponse(*Response, *Spider) (*Response, error)
}

type Plugin interface {
	PrepareSpider(*Spider) error
	ProvidePipelines() []ItemPipeline
	OnSpiderOpened(*Spider) error
	OnSpiderClosed(*Spider) error
	ProcessItem(Item, *Spider) (Item, error)
}

type ConfigurablePlugin interface {
	Configure(map[string]any) error
}

type SpiderMiddlewareProvider interface {
	ProvideSpiderMiddlewares() []SpiderMiddleware
}

type DownloaderMiddlewareProvider interface {
	ProvideDownloaderMiddlewares() []DownloaderMiddleware
}

type BrowserFetchFunc func(*Request, *Spider) (*Response, error)

type FeedExporter struct {
	format string
	path   string
	items  []map[string]any
}

func NewFeedExporter(format string, path string) *FeedExporter {
	return &FeedExporter{
		format: strings.ToLower(format),
		path:   path,
		items:  []map[string]any{},
	}
}

func (f *FeedExporter) ExportItem(item Item) {
	f.items = append(f.items, item.ToMap())
}

func (f *FeedExporter) Close() error {
	if err := os.MkdirAll(filepath.Dir(f.path), 0755); err != nil && filepath.Dir(f.path) != "." {
		return err
	}
	switch f.format {
	case "json":
		payload, err := json.MarshalIndent(f.items, "", "  ")
		if err != nil {
			return err
		}
		return os.WriteFile(f.path, payload, 0644)
	case "jsonlines":
		var builder strings.Builder
		for _, item := range f.items {
			row, err := json.Marshal(item)
			if err != nil {
				return err
			}
			builder.Write(row)
			builder.WriteByte('\n')
		}
		return os.WriteFile(f.path, []byte(builder.String()), 0644)
	case "csv":
		file, err := os.Create(f.path)
		if err != nil {
			return err
		}
		defer file.Close()
		writer := csv.NewWriter(file)
		defer writer.Flush()

		headers := orderedHeaders(f.items)
		if err := writer.Write(headers); err != nil {
			return err
		}
		for _, item := range f.items {
			record := make([]string, 0, len(headers))
			for _, header := range headers {
				record = append(record, fmt.Sprint(item[header]))
			}
			if err := writer.Write(record); err != nil {
				return err
			}
		}
		return nil
	default:
		return fmt.Errorf("unsupported feed format: %s", f.format)
	}
}

type Spider struct {
	Name         string
	StartURLs    []string
	StartMeta    map[string]any
	StartHeaders map[string]string
	Parse        Callback
}

func NewSpider(name string, parse Callback) *Spider {
	return &Spider{Name: name, Parse: parse, StartURLs: []string{}, StartMeta: map[string]any{}, StartHeaders: map[string]string{}}
}

func (s *Spider) AddStartURL(rawURL string) *Spider {
	s.StartURLs = append(s.StartURLs, rawURL)
	return s
}

func (s *Spider) WithStartMeta(key string, value any) *Spider {
	if s.StartMeta == nil {
		s.StartMeta = map[string]any{}
	}
	s.StartMeta[key] = value
	return s
}

func (s *Spider) WithStartHeader(key string, value string) *Spider {
	if s.StartHeaders == nil {
		s.StartHeaders = map[string]string{}
	}
	s.StartHeaders[key] = value
	return s
}

func (s *Spider) StartRequests() []*Request {
	requests := make([]*Request, 0, len(s.StartURLs))
	for _, rawURL := range s.StartURLs {
		req := NewRequest(rawURL, s.Parse)
		for key, value := range s.StartHeaders {
			req.SetHeader(key, value)
		}
		for key, value := range s.StartMeta {
			req.SetMeta(key, value)
		}
		requests = append(requests, req)
	}
	return requests
}

type CrawlerProcess struct {
	Spider                *Spider
	Client                *http.Client
	Pipelines             []ItemPipeline
	SpiderMiddlewares     []SpiderMiddleware
	DownloaderMiddlewares []DownloaderMiddleware
	Plugins               []Plugin
	Seen                  map[string]bool
	Config                map[string]any
	BrowserFetch          BrowserFetchFunc
}

func NewCrawlerProcess(spider *Spider) *CrawlerProcess {
	return &CrawlerProcess{
		Spider: spider,
		Client: &http.Client{},
		Seen:   map[string]bool{},
		Config: map[string]any{},
	}
}

func (c *CrawlerProcess) AddPlugin(plugin Plugin) *CrawlerProcess {
	c.Plugins = append(c.Plugins, plugin)
	return c
}

func (c *CrawlerProcess) AddPipeline(pipeline ItemPipeline) *CrawlerProcess {
	c.Pipelines = append(c.Pipelines, pipeline)
	return c
}

func (c *CrawlerProcess) AddSpiderMiddleware(middleware SpiderMiddleware) *CrawlerProcess {
	c.SpiderMiddlewares = append(c.SpiderMiddlewares, middleware)
	return c
}

func (c *CrawlerProcess) AddDownloaderMiddleware(middleware DownloaderMiddleware) *CrawlerProcess {
	c.DownloaderMiddlewares = append(c.DownloaderMiddlewares, middleware)
	return c
}

func (c *CrawlerProcess) WithConfig(config map[string]any) *CrawlerProcess {
	c.Config = map[string]any{}
	for key, value := range config {
		c.Config[key] = value
	}
	return c
}

func (c *CrawlerProcess) WithBrowserFetch(fetcher BrowserFetchFunc) *CrawlerProcess {
	c.BrowserFetch = fetcher
	return c
}

func (c *CrawlerProcess) Run() ([]Item, error) {
	queue := c.Spider.StartRequests()
	items := make([]Item, 0)
	activePipelines := append([]ItemPipeline{}, c.Pipelines...)
	activeSpiderMWs := append([]SpiderMiddleware{}, c.SpiderMiddlewares...)
	activeDownloaderMWs := append([]DownloaderMiddleware{}, c.DownloaderMiddlewares...)

	for _, plugin := range c.Plugins {
		if configurable, ok := plugin.(ConfigurablePlugin); ok {
			if err := configurable.Configure(c.Config); err != nil {
				return nil, err
			}
		}
		if err := plugin.PrepareSpider(c.Spider); err != nil {
			return nil, err
		}
		activePipelines = append(activePipelines, plugin.ProvidePipelines()...)
		if provider, ok := plugin.(SpiderMiddlewareProvider); ok {
			activeSpiderMWs = append(activeSpiderMWs, provider.ProvideSpiderMiddlewares()...)
		}
		if provider, ok := plugin.(DownloaderMiddlewareProvider); ok {
			activeDownloaderMWs = append(activeDownloaderMWs, provider.ProvideDownloaderMiddlewares()...)
		}
		if err := plugin.OnSpiderOpened(c.Spider); err != nil {
			return nil, err
		}
	}
	defer func() {
		for _, plugin := range c.Plugins {
			_ = plugin.OnSpiderClosed(c.Spider)
		}
	}()

	for len(queue) > 0 {
		request := queue[0]
		queue = queue[1:]
		var err error
		for _, middleware := range activeDownloaderMWs {
			request, err = middleware.ProcessRequest(request, c.Spider)
			if err != nil {
				return nil, err
			}
		}
		if c.Seen[request.URL] {
			continue
		}
		c.Seen[request.URL] = true

		response, err := c.fetchResponse(request)
		if err != nil {
			return nil, err
		}
		for _, middleware := range activeDownloaderMWs {
			response, err = middleware.ProcessResponse(response, c.Spider)
			if err != nil {
				return nil, err
			}
		}

		callback := request.Callback
		if callback == nil {
			callback = c.Spider.Parse
		}
		results, err := callback(response)
		if err != nil {
			return nil, err
		}
		for _, middleware := range activeSpiderMWs {
			results, err = middleware.ProcessSpiderOutput(response, results, c.Spider)
			if err != nil {
				return nil, err
			}
		}

		for _, result := range results {
			switch value := result.(type) {
			case *Request:
				if !c.Seen[value.URL] {
					queue = append(queue, value)
				}
			case Request:
				if !c.Seen[value.URL] {
					copyValue := value
					queue = append(queue, &copyValue)
				}
			case Item:
				item := value
				for _, pipeline := range activePipelines {
					item, err = pipeline.ProcessItem(item)
					if err != nil {
						return nil, err
					}
				}
				for _, plugin := range c.Plugins {
					item, err = plugin.ProcessItem(item, c.Spider)
					if err != nil {
						return nil, err
					}
				}
				items = append(items, item)
			case map[string]any:
				item := Item(value)
				for _, pipeline := range activePipelines {
					item, err = pipeline.ProcessItem(item)
					if err != nil {
						return nil, err
					}
				}
				for _, plugin := range c.Plugins {
					item, err = plugin.ProcessItem(item, c.Spider)
					if err != nil {
						return nil, err
					}
				}
				items = append(items, item)
			}
		}
	}

	return items, nil
}

func orderedHeaders(items []map[string]any) []string {
	headers := make([]string, 0)
	seen := map[string]bool{}
	for _, item := range items {
		for key := range item {
			if seen[key] {
				continue
			}
			seen[key] = true
			headers = append(headers, key)
		}
	}
	return headers
}

func ioReadAllAndClose(resp *http.Response) ([]byte, error) {
	defer resp.Body.Close()
	return io.ReadAll(resp.Body)
}

func (c *CrawlerProcess) fetchResponse(request *Request) (*Response, error) {
	runner := resolveRunner(request.Meta, c.Config)
	if runner == "browser" && c.BrowserFetch != nil {
		return c.BrowserFetch(request, c.Spider)
	}
	httpRequest, err := http.NewRequest(request.Method, request.URL, strings.NewReader(request.Body))
	if err != nil {
		return nil, err
	}
	for key, value := range request.Headers {
		httpRequest.Header.Set(key, value)
	}

	httpResponse, err := c.Client.Do(httpRequest)
	if err != nil {
		return nil, err
	}
	body, err := ioReadAllAndClose(httpResponse)
	if err != nil {
		return nil, err
	}

	return &Response{
		URL:        request.URL,
		StatusCode: httpResponse.StatusCode,
		Headers:    httpResponse.Header.Clone(),
		Body:       body,
		Text:       string(body),
		Request:    request,
	}, nil
}

func resolveRunner(meta map[string]any, config map[string]any) string {
	normalize := func(value any) string {
		text, ok := value.(string)
		if !ok {
			return ""
		}
		text = strings.TrimSpace(strings.ToLower(text))
		switch text {
		case "browser", "http", "hybrid":
			return text
		default:
			return ""
		}
	}
	if runner := normalize(meta["runner"]); runner != "" {
		return runner
	}
	if runner := normalize(config["runner"]); runner != "" {
		return runner
	}
	return "http"
}
