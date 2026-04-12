package scrapy

import (
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestSelectorSupportsCSSXPathAndRegex(t *testing.T) {
	selector := NewSelector(`<html><body><h1>Demo</h1><a href="/next">Next</a></body></html>`)

	if got := selector.CSS("h1").Get(); got != "Demo" {
		t.Fatalf("expected css title Demo, got %q", got)
	}
	if got := selector.XPath("//a/@href").Get(); got != "/next" {
		t.Fatalf("expected xpath href /next, got %q", got)
	}
	if got := selector.ReFirst(`<h1>([^<]+)</h1>`); got != "Demo" {
		t.Fatalf("expected regex title Demo, got %q", got)
	}
}

func TestCrawlerProcessCollectsItemsAndFollowRequests(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/":
			_, _ = w.Write([]byte(`<html><title>Home</title><a href="/next">Next</a></html>`))
		case "/next":
			_, _ = w.Write([]byte(`<html><title>Next</title></html>`))
		default:
			http.NotFound(w, r)
		}
	}))
	defer server.Close()

	spider := NewSpider("demo", func(response *Response) ([]any, error) {
		results := []any{
			NewItem().Set("title", response.CSS("title").Get()),
		}
		if strings.HasSuffix(response.URL, "/") {
			results = append(results, response.Follow("/next", func(response *Response) ([]any, error) {
				return []any{NewItem().Set("title", response.CSS("title").Get()).Set("url", response.URL)}, nil
			}))
		}
		return results, nil
	}).AddStartURL(server.URL + "/")

	process := NewCrawlerProcess(spider)
	items, err := process.Run()
	if err != nil {
		t.Fatalf("crawler process failed: %v", err)
	}
	if len(items) != 2 {
		t.Fatalf("expected 2 items, got %d", len(items))
	}
	if items[1]["url"] != server.URL+"/next" {
		t.Fatalf("expected follow url %s/next, got %#v", server.URL, items[1]["url"])
	}
}

func TestFeedExporterWritesJSON(t *testing.T) {
	path := filepath.Join(t.TempDir(), "items.json")
	exporter := NewFeedExporter("json", path)
	exporter.ExportItem(NewItem().Set("title", "Demo"))
	if err := exporter.Close(); err != nil {
		t.Fatalf("exporter failed: %v", err)
	}
	content, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("failed to read export: %v", err)
	}
	if !strings.Contains(string(content), "Demo") {
		t.Fatalf("expected exported content to contain Demo, got %s", string(content))
	}
}

type suffixPipeline struct{}

func (suffixPipeline) ProcessItem(item Item) (Item, error) {
	item["pipeline"] = "active"
	return item, nil
}

type testPlugin struct {
	openCalled  bool
	closeCalled bool
}

func (p *testPlugin) PrepareSpider(spider *Spider) error {
	spider.Name = "prepared-" + spider.Name
	return nil
}

func (p *testPlugin) ProvidePipelines() []ItemPipeline {
	return []ItemPipeline{suffixPipeline{}}
}

func (p *testPlugin) OnSpiderOpened(spider *Spider) error {
	p.openCalled = true
	return nil
}

func (p *testPlugin) OnSpiderClosed(spider *Spider) error {
	p.closeCalled = true
	return nil
}

func (p *testPlugin) ProcessItem(item Item, spider *Spider) (Item, error) {
	item["plugin"] = spider.Name
	return item, nil
}

func TestCrawlerProcessRunsPluginHooksAndInjectedPipelines(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write([]byte(`<html><title>Demo</title></html>`))
	}))
	defer server.Close()

	plugin := &testPlugin{}
	spider := NewSpider("demo", func(response *Response) ([]any, error) {
		return []any{NewItem().Set("title", response.CSS("title").Get())}, nil
	}).AddStartURL(server.URL)

	items, err := NewCrawlerProcess(spider).AddPlugin(plugin).Run()
	if err != nil {
		t.Fatalf("crawler process failed: %v", err)
	}
	if !plugin.openCalled || !plugin.closeCalled {
		t.Fatalf("expected plugin lifecycle to run, got open=%v close=%v", plugin.openCalled, plugin.closeCalled)
	}
	if len(items) != 1 {
		t.Fatalf("expected one item, got %d", len(items))
	}
	if fmt.Sprint(items[0]["pipeline"]) != "active" {
		t.Fatalf("expected injected pipeline value, got %#v", items[0]["pipeline"])
	}
	if fmt.Sprint(items[0]["plugin"]) != "prepared-demo" {
		t.Fatalf("expected plugin item mutation, got %#v", items[0]["plugin"])
	}
}

func TestPluginRegistryResolvesNamedPlugin(t *testing.T) {
	RegisterPlugin("test-plugin", func() Plugin { return &testPlugin{} })

	process := NewCrawlerProcess(NewSpider("demo", func(response *Response) ([]any, error) {
		return []any{NewItem().Set("title", "Demo")}, nil
	}))
	if err := process.AddNamedPlugin("test-plugin"); err != nil {
		t.Fatalf("expected named plugin registration to work: %v", err)
	}
	if len(process.Plugins) != 1 {
		t.Fatalf("expected one plugin, got %d", len(process.Plugins))
	}
	if _, ok := process.Plugins[0].(*testPlugin); !ok {
		t.Fatalf("expected *testPlugin, got %T", process.Plugins[0])
	}
}

type configAwarePlugin struct {
	configured bool
}

func (p *configAwarePlugin) Configure(config map[string]any) error {
	p.configured = config["runner"] == "browser"
	return nil
}

func (p *configAwarePlugin) PrepareSpider(spider *Spider) error { return nil }

func (p *configAwarePlugin) ProvidePipelines() []ItemPipeline { return nil }

func (p *configAwarePlugin) ProvideSpiderMiddlewares() []SpiderMiddleware {
	return []SpiderMiddleware{spiderMiddlewareFunc(func(response *Response, result []any, spider *Spider) ([]any, error) {
		return append(result, NewItem().Set("middleware", "spider")), nil
	})}
}

func (p *configAwarePlugin) ProvideDownloaderMiddlewares() []DownloaderMiddleware {
	return []DownloaderMiddleware{downloaderMiddlewareFunc{
		processRequest: func(request *Request, spider *Spider) (*Request, error) {
			return request.SetHeader("X-Test", "active"), nil
		},
		processResponse: func(response *Response, spider *Spider) (*Response, error) {
			response.Headers.Set("X-Test", "active")
			return response, nil
		},
	}}
}

func (p *configAwarePlugin) OnSpiderOpened(spider *Spider) error { return nil }

func (p *configAwarePlugin) OnSpiderClosed(spider *Spider) error { return nil }

func (p *configAwarePlugin) ProcessItem(item Item, spider *Spider) (Item, error) {
	item["configured"] = p.configured
	return item, nil
}

type spiderMiddlewareFunc func(*Response, []any, *Spider) ([]any, error)

func (f spiderMiddlewareFunc) ProcessSpiderOutput(response *Response, result []any, spider *Spider) ([]any, error) {
	return f(response, result, spider)
}

type downloaderMiddlewareFunc struct {
	processRequest  func(*Request, *Spider) (*Request, error)
	processResponse func(*Response, *Spider) (*Response, error)
}

func (m downloaderMiddlewareFunc) ProcessRequest(request *Request, spider *Spider) (*Request, error) {
	return m.processRequest(request, spider)
}

func (m downloaderMiddlewareFunc) ProcessResponse(response *Response, spider *Spider) (*Response, error) {
	return m.processResponse(response, spider)
}

func TestCrawlerProcessSupportsConfigMiddlewareAndBrowserRunner(t *testing.T) {
	plugin := &configAwarePlugin{}
	spider := NewSpider("demo", func(response *Response) ([]any, error) {
		return []any{NewItem().Set("title", response.CSS("title").Get())}, nil
	}).AddStartURL("https://example.com")
	items, err := NewCrawlerProcess(spider).
		WithConfig(map[string]any{"runner": "browser"}).
		WithBrowserFetch(func(request *Request, spider *Spider) (*Response, error) {
			return &Response{
				URL:        request.URL,
				StatusCode: 200,
				Headers:    http.Header{},
				Body:       []byte(`<html><title>Browser Demo</title></html>`),
				Text:       `<html><title>Browser Demo</title></html>`,
				Request:    request,
			}, nil
		}).
		AddPlugin(plugin).
		Run()
	if err != nil {
		t.Fatalf("crawler process failed: %v", err)
	}
	if len(items) != 2 {
		t.Fatalf("expected 2 items after spider middleware injection, got %d", len(items))
	}
	if fmt.Sprint(items[0]["configured"]) != "true" {
		t.Fatalf("expected configurable plugin flag, got %#v", items[0]["configured"])
	}
	if fmt.Sprint(items[0]["title"]) != "Browser Demo" {
		t.Fatalf("expected browser fetch title, got %#v", items[0]["title"])
	}
	if fmt.Sprint(items[1]["middleware"]) != "spider" {
		t.Fatalf("expected spider middleware item, got %#v", items[1]["middleware"])
	}
}
