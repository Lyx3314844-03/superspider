package project

import (
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"gopkg.in/yaml.v3"
	nodereverse "gospider/node_reverse"
	"gospider/parser"
	scrapyapi "gospider/scrapy"
)

type SpiderFactory func() *scrapyapi.Spider
type PluginFactory func() scrapyapi.Plugin
type PluginSpec struct {
	Name     string
	Enabled  bool
	Priority int
	Config   map[string]any
}

type artifactProjectConfig struct {
	Scrapy struct {
		Plugins               []string                  `yaml:"plugins"`
		Pipelines             []string                  `yaml:"pipelines"`
		SpiderMiddlewares     []string                  `yaml:"spider_middlewares"`
		DownloaderMiddlewares []string                  `yaml:"downloader_middlewares"`
		ComponentConfig       map[string]map[string]any `yaml:"component_config"`
	} `yaml:"scrapy"`
	NodeReverse struct {
		BaseURL string `yaml:"base_url"`
	} `yaml:"node_reverse"`
}

type AIProjectAssets struct {
	Schema              map[string]any
	Blueprint           map[string]any
	ExtractionPrompt    string
	PaginationEnabled   bool
	PaginationSelectors []string
	RecommendedRunner   string
	RequestHeaders      map[string]string
	AuthRequired        bool
	StorageStateFile    string
	CookiesFile         string
}

var registry = map[string]SpiderFactory{}
var pluginRegistry = map[string]PluginFactory{}

func LoadAIProjectAssets(projectRoot string) AIProjectAssets {
	root := strings.TrimSpace(projectRoot)
	if root == "" {
		if cwd, err := os.Getwd(); err == nil {
			root = cwd
		}
	}
	assets := AIProjectAssets{
		Schema: map[string]any{
			"type": "object",
			"properties": map[string]any{
				"title":   map[string]any{"type": "string"},
				"summary": map[string]any{"type": "string"},
				"url":     map[string]any{"type": "string"},
			},
		},
		Blueprint:           map[string]any{},
		ExtractionPrompt:    "提取标题、摘要和 URL",
		PaginationEnabled:   false,
		PaginationSelectors: []string{},
		RecommendedRunner:   "http",
		RequestHeaders:      map[string]string{},
		AuthRequired:        false,
		StorageStateFile:    "",
		CookiesFile:         "",
	}
	if root == "" {
		return assets
	}
	if data, err := os.ReadFile(filepath.Join(root, "ai-schema.json")); err == nil {
		var schema map[string]any
		if json.Unmarshal(data, &schema) == nil && len(schema) > 0 {
			assets.Schema = schema
		}
	}
	if data, err := os.ReadFile(filepath.Join(root, "ai-blueprint.json")); err == nil {
		var blueprint map[string]any
		if json.Unmarshal(data, &blueprint) == nil && len(blueprint) > 0 {
			assets.Blueprint = blueprint
			if prompt := strings.TrimSpace(fmt.Sprint(blueprint["extraction_prompt"])); prompt != "" && prompt != "<nil>" {
				assets.ExtractionPrompt = prompt
			}
			if pagination, ok := blueprint["pagination"].(map[string]any); ok {
				if enabled, ok := pagination["enabled"].(bool); ok {
					assets.PaginationEnabled = enabled
				}
				if selectors, ok := pagination["selectors"].([]any); ok {
					for _, item := range selectors {
						trimmed := strings.TrimSpace(fmt.Sprint(item))
						if trimmed != "" {
							assets.PaginationSelectors = append(assets.PaginationSelectors, trimmed)
						}
					}
				}
			}
			if auth, ok := blueprint["authentication"].(map[string]any); ok {
				if required, ok := auth["required"].(bool); ok {
					assets.AuthRequired = required
				}
			}
			if runtime, ok := blueprint["javascript_runtime"].(map[string]any); ok {
				if runner := strings.TrimSpace(fmt.Sprint(runtime["recommended_runner"])); runner != "" && runner != "<nil>" {
					assets.RecommendedRunner = runner
				}
			}
			if assets.RecommendedRunner == "http" {
				if antiBot, ok := blueprint["anti_bot_strategy"].(map[string]any); ok {
					if runner := strings.TrimSpace(fmt.Sprint(antiBot["recommended_runner"])); runner != "" && runner != "<nil>" {
						assets.RecommendedRunner = runner
					}
				}
			}
		}
	}
	if assets.ExtractionPrompt == "提取标题、摘要和 URL" {
		if data, err := os.ReadFile(filepath.Join(root, "ai-extract-prompt.txt")); err == nil {
			if prompt := strings.TrimSpace(string(data)); prompt != "" {
				assets.ExtractionPrompt = prompt
			}
		}
	}
	if data, err := os.ReadFile(filepath.Join(root, "ai-auth.json")); err == nil {
		var auth struct {
			Headers          map[string]string `json:"headers"`
			StorageStateFile string            `json:"storage_state_file"`
			CookiesFile      string            `json:"cookies_file"`
		}
		if json.Unmarshal(data, &auth) == nil {
			for key, value := range auth.Headers {
				if strings.TrimSpace(key) != "" && strings.TrimSpace(value) != "" {
					assets.RequestHeaders[key] = value
				}
			}
			if strings.TrimSpace(auth.StorageStateFile) != "" {
				assets.StorageStateFile = auth.StorageStateFile
			}
			if strings.TrimSpace(auth.CookiesFile) != "" {
				assets.CookiesFile = auth.CookiesFile
			}
		}
	}
	if cookie := strings.TrimSpace(os.Getenv("SPIDER_AUTH_COOKIE")); cookie != "" {
		assets.RequestHeaders["Cookie"] = cookie
	}
	if raw := strings.TrimSpace(os.Getenv("SPIDER_AUTH_HEADERS_JSON")); raw != "" {
		headers := map[string]string{}
		if json.Unmarshal([]byte(raw), &headers) == nil {
			for key, value := range headers {
				if strings.TrimSpace(key) != "" && strings.TrimSpace(value) != "" {
					assets.RequestHeaders[key] = value
				}
			}
		}
	}
	if assets.AuthRequired && assets.RecommendedRunner == "http" {
		assets.RecommendedRunner = "browser"
	}
	return assets
}

func ApplyAIStartMeta(spider *scrapyapi.Spider, assets AIProjectAssets) *scrapyapi.Spider {
	if spider == nil {
		return nil
	}
	if strings.TrimSpace(assets.RecommendedRunner) != "" && assets.RecommendedRunner != "http" {
		spider.WithStartMeta("runner", assets.RecommendedRunner)
	}
	if strings.TrimSpace(assets.StorageStateFile) != "" || strings.TrimSpace(assets.CookiesFile) != "" {
		browserMeta := map[string]any{}
		if strings.TrimSpace(assets.StorageStateFile) != "" {
			browserMeta["storage_state_file"] = assets.StorageStateFile
		}
		if strings.TrimSpace(assets.CookiesFile) != "" {
			browserMeta["cookies_file"] = assets.CookiesFile
		}
		spider.WithStartMeta("browser", browserMeta)
	}
	for key, value := range assets.RequestHeaders {
		spider.WithStartHeader(key, value)
	}
	return spider
}

func ApplyAIRequestStrategy(req *scrapyapi.Request, assets AIProjectAssets) *scrapyapi.Request {
	if req == nil {
		return nil
	}
	if strings.TrimSpace(assets.RecommendedRunner) != "" && assets.RecommendedRunner != "http" {
		req.SetMeta("runner", assets.RecommendedRunner)
	}
	if strings.TrimSpace(assets.StorageStateFile) != "" || strings.TrimSpace(assets.CookiesFile) != "" {
		browserMeta := map[string]any{}
		if existing, ok := req.Meta["browser"].(map[string]any); ok {
			for key, value := range existing {
				browserMeta[key] = value
			}
		}
		if strings.TrimSpace(assets.StorageStateFile) != "" {
			browserMeta["storage_state_file"] = assets.StorageStateFile
		}
		if strings.TrimSpace(assets.CookiesFile) != "" {
			browserMeta["cookies_file"] = assets.CookiesFile
		}
		req.SetMeta("browser", browserMeta)
	}
	for key, value := range assets.RequestHeaders {
		req.SetHeader(key, value)
	}
	return req
}

func CollectAIPaginationRequests(response *scrapyapi.Response, callback scrapyapi.Callback, assets AIProjectAssets) []*scrapyapi.Request {
	if response == nil || !assets.PaginationEnabled || len(assets.PaginationSelectors) == 0 {
		return nil
	}
	htmlParser := parser.NewHTMLParser(response.Text)
	seen := map[string]bool{}
	requests := []*scrapyapi.Request{}
	for _, selector := range assets.PaginationSelectors {
		for _, link := range htmlParser.CSSAttr(selector, "href") {
			if strings.TrimSpace(link) == "" || seen[link] {
				continue
			}
			seen[link] = true
			req := response.Follow(link, callback)
			requests = append(requests, ApplyAIRequestStrategy(req, assets))
		}
	}
	return requests
}

func RegisterSpider(name string, factory SpiderFactory) {
	if factory == nil {
		return
	}
	name = strings.TrimSpace(name)
	if name == "" {
		return
	}
	registry[name] = factory
}

func SpiderNames() []string {
	names := make([]string, 0, len(registry))
	for name := range registry {
		names = append(names, name)
	}
	sort.Strings(names)
	return names
}

func RegisterPlugin(name string, factory PluginFactory) {
	if factory == nil {
		return
	}
	name = strings.TrimSpace(name)
	if name == "" {
		return
	}
	pluginRegistry[name] = factory
}

func PluginNames() []string {
	names := make([]string, 0, len(pluginRegistry))
	for name := range pluginRegistry {
		names = append(names, name)
	}
	sort.Strings(names)
	return names
}

func ResolvePlugins(selected []string) ([]scrapyapi.Plugin, error) {
	if len(selected) == 0 {
		return ResolvePluginSpecs(nil)
	}
	specs := make([]PluginSpec, 0, len(selected))
	for _, name := range selected {
		specs = append(specs, PluginSpec{Name: name, Enabled: true})
	}
	return ResolvePluginSpecs(specs)
}

func ResolvePluginSpecs(selected []PluginSpec) ([]scrapyapi.Plugin, error) {
	specs := normalizePluginSpecs(selected)
	if len(specs) == 0 {
		names := PluginNames()
		specs = make([]PluginSpec, 0, len(names))
		for _, name := range names {
			specs = append(specs, PluginSpec{Name: name, Enabled: true})
		}
	}
	plugins := make([]scrapyapi.Plugin, 0, len(specs))
	for _, spec := range specs {
		if !spec.Enabled {
			continue
		}
		if factory, ok := pluginRegistry[spec.Name]; ok {
			plugins = append(plugins, factory())
			continue
		}
		plugin, ok := newBuiltinPlugin(spec)
		if !ok {
			return nil, fmt.Errorf("unknown registered plugin: %s", spec.Name)
		}
		plugins = append(plugins, plugin)
	}
	return plugins, nil
}

func ResolveSpider(name string) (*scrapyapi.Spider, error) {
	if len(registry) == 0 {
		return nil, errors.New("no registered scrapy spiders")
	}
	if strings.TrimSpace(name) == "" {
		names := SpiderNames()
		return registry[names[0]](), nil
	}
	factory, ok := registry[name]
	if !ok {
		return nil, fmt.Errorf("unknown registered spider: %s", name)
	}
	return factory(), nil
}

func RunFromEnv() (bool, error) {
	if os.Getenv("GOSPIDER_SCRAPY_RUNNER") != "1" {
		return false, nil
	}

	selectedSpider := os.Getenv("GOSPIDER_SCRAPY_SPIDER")
	targetURL := firstNonBlank(os.Getenv("GOSPIDER_SCRAPY_URL"), "https://example.com")
	htmlFile := os.Getenv("GOSPIDER_SCRAPY_HTML_FILE")
	outputPath := firstNonBlank(os.Getenv("GOSPIDER_SCRAPY_OUTPUT"), "artifacts/exports/items.json")
	selectedPlugins := splitCSV(os.Getenv("GOSPIDER_SCRAPY_PLUGINS"))
	projectRoot := os.Getenv("GOSPIDER_SCRAPY_PROJECT")
	reverseURL := firstNonBlank(os.Getenv("GOSPIDER_SCRAPY_REVERSE_URL"), "")
	projectCfg, settingsSource := loadArtifactProjectConfig(projectRoot)
	if strings.TrimSpace(reverseURL) == "" {
		reverseURL = firstNonBlank(projectCfg.NodeReverse.BaseURL)
	}
	selectedPluginSpecs := []PluginSpec{}
	if len(selectedPlugins) > 0 {
		for _, name := range selectedPlugins {
			selectedPluginSpecs = append(selectedPluginSpecs, PluginSpec{Name: name, Enabled: true})
		}
	} else if strings.TrimSpace(projectRoot) != "" {
		selectedPluginSpecs = LoadPluginSpecsFromManifest(projectRoot)
		if len(selectedPluginSpecs) == 0 {
			selectedPluginSpecs = artifactConfiguredPluginSpecs(projectCfg)
		}
	}

	spider, err := ResolveSpider(selectedSpider)
	if err != nil {
		return true, err
	}
	plugins, err := ResolvePluginSpecs(selectedPluginSpecs)
	if err != nil {
		return true, err
	}
	appliedPlugins := pluginSpecNames(selectedPluginSpecs)
	if len(appliedPlugins) == 0 {
		appliedPlugins = PluginNames()
	}

	if len(spider.StartURLs) == 0 && strings.TrimSpace(targetURL) != "" {
		spider.AddStartURL(targetURL)
	}

	declarativePipelines := buildArtifactDeclarativePipelines(projectCfg)
	declarativeSpiderMiddlewares := buildArtifactDeclarativeSpiderMiddlewares(projectCfg)
	declarativeDownloaderMiddlewares := buildArtifactDeclarativeDownloaderMiddlewares(projectCfg)
	items, err := RunSpiderWithPlugins(
		spider,
		plugins,
		targetURL,
		htmlFile,
		declarativePipelines,
		declarativeSpiderMiddlewares,
		declarativeDownloaderMiddlewares,
	)
	if err != nil {
		return true, err
	}

	exporter := scrapyapi.NewFeedExporter("json", outputPath)
	for _, item := range items {
		exporter.ExportItem(item)
	}
	if err := exporter.Close(); err != nil {
		return true, err
	}
	pipelineCount := len(declarativePipelines)
	spiderMiddlewareCount := len(declarativeSpiderMiddlewares)
	downloaderMiddlewareCount := len(declarativeDownloaderMiddlewares)
	for _, plugin := range plugins {
		pipelineCount += len(plugin.ProvidePipelines())
		if provider, ok := plugin.(scrapyapi.SpiderMiddlewareProvider); ok {
			spiderMiddlewareCount += len(provider.ProvideSpiderMiddlewares())
		}
		if provider, ok := plugin.(scrapyapi.DownloaderMiddlewareProvider); ok {
			downloaderMiddlewareCount += len(provider.ProvideDownloaderMiddlewares())
		}
	}

	payload := map[string]any{
		"command":                     "scrapy run",
		"runtime":                     "go",
		"runner":                      "artifact-project",
		"spider":                      spider.Name,
		"plugins":                     appliedPlugins,
		"settings_source":             settingsSource,
		"pipelines":                   append([]string{}, projectCfg.Scrapy.Pipelines...),
		"spider_middlewares":          append([]string{}, projectCfg.Scrapy.SpiderMiddlewares...),
		"downloader_middlewares":      append([]string{}, projectCfg.Scrapy.DownloaderMiddlewares...),
		"pipeline_count":              pipelineCount,
		"spider_middleware_count":     spiderMiddlewareCount,
		"downloader_middleware_count": downloaderMiddlewareCount,
		"item_count":                  len(items),
		"output":                      outputPath,
	}
	if strings.TrimSpace(reverseURL) != "" {
		if summary := CollectReverseSummary(reverseURL, targetURL, htmlFile); summary != nil {
			payload["reverse"] = summary
		}
	}
	encoded, _ := json.MarshalIndent(payload, "", "  ")
	fmt.Println(string(encoded))
	return true, nil
}

func CollectReverseSummary(baseURL, targetURL, htmlFile string) map[string]any {
	var (
		html       string
		statusCode int
	)
	if strings.TrimSpace(htmlFile) != "" {
		data, err := os.ReadFile(htmlFile)
		if err != nil {
			return nil
		}
		html = string(data)
		statusCode = http.StatusOK
	} else {
		resp, err := http.Get(targetURL)
		if err != nil {
			return nil
		}
		defer resp.Body.Close()
		body, err := io.ReadAll(io.LimitReader(resp.Body, 1<<20))
		if err != nil {
			return nil
		}
		html = string(body)
		statusCode = resp.StatusCode
	}

	client := nodereverse.NewNodeReverseClient(baseURL)
	detect, _ := client.DetectAntiBot(nodereverse.AntiBotProfileRequest{
		HTML:       html,
		URL:        targetURL,
		StatusCode: statusCode,
	})
	profile, _ := client.ProfileAntiBot(nodereverse.AntiBotProfileRequest{
		HTML:       html,
		URL:        targetURL,
		StatusCode: statusCode,
	})
	spoof, _ := client.SpoofFingerprint(nodereverse.FingerprintSpoofRequest{
		Browser:  "chrome",
		Platform: "windows",
	})
	tlsFP, _ := client.GenerateTLSFingerprint(nodereverse.TLSFingerprintRequest{
		Browser: "chrome",
		Version: "120",
	})
	payload := map[string]any{
		"detect":            detect,
		"profile":           profile,
		"fingerprint_spoof": spoof,
		"tls_fingerprint":   tlsFP,
	}
	if scriptSample := extractScriptSample(html); strings.TrimSpace(scriptSample) != "" {
		if crypto, err := client.AnalyzeCrypto(scriptSample); err == nil {
			payload["crypto_analysis"] = crypto
		}
	}
	return payload
}

func extractScriptSample(html string) string {
	lowered := strings.ToLower(html)
	start := 0
	parts := make([]string, 0, 4)
	for {
		open := strings.Index(lowered[start:], "<script")
		if open < 0 {
			break
		}
		open += start
		tagEnd := strings.Index(lowered[open:], ">")
		if tagEnd < 0 {
			break
		}
		tagEnd += open
		closeIdx := strings.Index(lowered[tagEnd:], "</script>")
		if closeIdx < 0 {
			break
		}
		closeIdx += tagEnd
		snippet := strings.TrimSpace(html[tagEnd+1 : closeIdx])
		if snippet != "" {
			parts = append(parts, snippet)
		}
		start = closeIdx + len("</script>")
	}
	joined := strings.Join(parts, "\n")
	if joined != "" {
		if len(joined) > 32000 {
			return joined[:32000]
		}
		return joined
	}
	if len(html) > 32000 {
		return html[:32000]
	}
	return html
}

func RunSpiderWithPlugins(
	spider *scrapyapi.Spider,
	plugins []scrapyapi.Plugin,
	targetURL, htmlFile string,
	declarativePipelines []scrapyapi.ItemPipeline,
	declarativeSpiderMiddlewares []scrapyapi.SpiderMiddleware,
	declarativeDownloaderMiddlewares []scrapyapi.DownloaderMiddleware,
) ([]scrapyapi.Item, error) {
	if spider == nil {
		return nil, errors.New("spider is nil")
	}

	if strings.TrimSpace(htmlFile) != "" {
		htmlBytes, readErr := os.ReadFile(htmlFile)
		if readErr != nil {
			return nil, readErr
		}
		activePipelines := append([]scrapyapi.ItemPipeline{}, declarativePipelines...)
		activeSpiderMiddlewares := append([]scrapyapi.SpiderMiddleware{}, declarativeSpiderMiddlewares...)
		activeDownloaderMiddlewares := append([]scrapyapi.DownloaderMiddleware{}, declarativeDownloaderMiddlewares...)
		for _, plugin := range plugins {
			if err := plugin.PrepareSpider(spider); err != nil {
				return nil, err
			}
			if err := plugin.OnSpiderOpened(spider); err != nil {
				return nil, err
			}
			activePipelines = append(activePipelines, plugin.ProvidePipelines()...)
			if provider, ok := plugin.(scrapyapi.SpiderMiddlewareProvider); ok {
				activeSpiderMiddlewares = append(activeSpiderMiddlewares, provider.ProvideSpiderMiddlewares()...)
			}
			if provider, ok := plugin.(scrapyapi.DownloaderMiddlewareProvider); ok {
				activeDownloaderMiddlewares = append(activeDownloaderMiddlewares, provider.ProvideDownloaderMiddlewares()...)
			}
		}
		request := scrapyapi.NewRequest(targetURL, nil)
		var err error
		for _, middleware := range activeDownloaderMiddlewares {
			request, err = middleware.ProcessRequest(request, spider)
			if err != nil {
				return nil, err
			}
		}
		response := &scrapyapi.Response{
			URL:        targetURL,
			StatusCode: http.StatusOK,
			Headers:    http.Header{},
			Body:       htmlBytes,
			Text:       string(htmlBytes),
			Request:    request,
		}
		for _, middleware := range activeDownloaderMiddlewares {
			response, err = middleware.ProcessResponse(response, spider)
			if err != nil {
				return nil, err
			}
		}
		results, err := spider.Parse(response)
		if err != nil {
			return nil, err
		}
		for _, middleware := range activeSpiderMiddlewares {
			results, err = middleware.ProcessSpiderOutput(response, results, spider)
			if err != nil {
				return nil, err
			}
		}
		items := make([]scrapyapi.Item, 0, len(results))
		for _, result := range results {
			switch value := result.(type) {
			case scrapyapi.Item:
				item := value
				for _, pipeline := range activePipelines {
					item, err = pipeline.ProcessItem(item)
					if err != nil {
						return nil, err
					}
				}
				for _, plugin := range plugins {
					item, err = plugin.ProcessItem(item, spider)
					if err != nil {
						return nil, err
					}
				}
				items = append(items, item)
			case map[string]any:
				item := scrapyapi.Item(value)
				for _, pipeline := range activePipelines {
					item, err = pipeline.ProcessItem(item)
					if err != nil {
						return nil, err
					}
				}
				for _, plugin := range plugins {
					item, err = plugin.ProcessItem(item, spider)
					if err != nil {
						return nil, err
					}
				}
				items = append(items, item)
			}
		}
		for _, plugin := range plugins {
			_ = plugin.OnSpiderClosed(spider)
		}
		return items, nil
	}

	process := scrapyapi.NewCrawlerProcess(spider)
	for _, pipeline := range declarativePipelines {
		process.AddPipeline(pipeline)
	}
	for _, middleware := range declarativeSpiderMiddlewares {
		process.AddSpiderMiddleware(middleware)
	}
	for _, middleware := range declarativeDownloaderMiddlewares {
		process.AddDownloaderMiddleware(middleware)
	}
	for _, plugin := range plugins {
		process.AddPlugin(plugin)
	}
	return process.Run()
}

func firstNonBlank(values ...string) string {
	for _, value := range values {
		if strings.TrimSpace(value) != "" {
			return value
		}
	}
	return ""
}

func splitCSV(value string) []string {
	items := []string{}
	for _, item := range strings.Split(value, ",") {
		trimmed := strings.TrimSpace(item)
		if trimmed != "" {
			items = append(items, trimmed)
		}
	}
	return items
}

func loadArtifactProjectConfig(projectRoot string) (artifactProjectConfig, string) {
	cfg := artifactProjectConfig{}
	if strings.TrimSpace(projectRoot) == "" {
		return cfg, ""
	}
	path := filepath.Join(projectRoot, "spider-framework.yaml")
	data, err := os.ReadFile(path)
	if err != nil {
		return cfg, ""
	}
	_ = yaml.Unmarshal(data, &cfg)
	return cfg, path
}

func artifactConfiguredPluginSpecs(cfg artifactProjectConfig) []PluginSpec {
	specs := make([]PluginSpec, 0, len(cfg.Scrapy.Plugins))
	for _, name := range cfg.Scrapy.Plugins {
		trimmed := strings.TrimSpace(name)
		if trimmed == "" {
			continue
		}
		specs = append(specs, PluginSpec{Name: trimmed, Enabled: true})
	}
	return specs
}

func buildArtifactDeclarativePipelines(cfg artifactProjectConfig) []scrapyapi.ItemPipeline {
	pipelines := []scrapyapi.ItemPipeline{}
	for _, name := range cfg.Scrapy.Pipelines {
		switch strings.TrimSpace(name) {
		case "field-injector":
			pipelines = append(pipelines, artifactFieldInjectorPipeline{
				fields: readArtifactAnyMap(cfg.Scrapy.ComponentConfig["field_injector"], "fields"),
			})
		}
	}
	return pipelines
}

func buildArtifactDeclarativeSpiderMiddlewares(cfg artifactProjectConfig) []scrapyapi.SpiderMiddleware {
	middlewares := []scrapyapi.SpiderMiddleware{}
	for _, name := range cfg.Scrapy.SpiderMiddlewares {
		if strings.TrimSpace(name) == "response-context" {
			middlewares = append(middlewares, artifactResponseContextSpiderMiddleware{})
		}
	}
	return middlewares
}

func buildArtifactDeclarativeDownloaderMiddlewares(cfg artifactProjectConfig) []scrapyapi.DownloaderMiddleware {
	middlewares := []scrapyapi.DownloaderMiddleware{}
	for _, name := range cfg.Scrapy.DownloaderMiddlewares {
		if strings.TrimSpace(name) == "request-headers" {
			middlewares = append(middlewares, artifactRequestHeadersMiddleware{
				headers: readArtifactStringMap(cfg.Scrapy.ComponentConfig["request_headers"], "headers"),
			})
		}
	}
	return middlewares
}

func LoadPluginSpecsFromManifest(projectRoot string) []PluginSpec {
	data, err := os.ReadFile(filepath.Join(projectRoot, "scrapy-plugins.json"))
	if err != nil {
		return nil
	}
	var payload any
	if err := json.Unmarshal(data, &payload); err != nil {
		return nil
	}
	items, ok := payload.([]any)
	if !ok {
		object, objectOK := payload.(map[string]any)
		if !objectOK {
			return nil
		}
		items, ok = object["plugins"].([]any)
		if !ok {
			return nil
		}
	}
	specs := []PluginSpec{}
	for _, item := range items {
		switch value := item.(type) {
		case string:
			if strings.TrimSpace(value) != "" {
				specs = append(specs, PluginSpec{Name: strings.TrimSpace(value), Enabled: true})
			}
		case map[string]any:
			name, ok := value["name"].(string)
			if !ok || strings.TrimSpace(name) == "" {
				continue
			}
			spec := PluginSpec{
				Name:     strings.TrimSpace(name),
				Enabled:  true,
				Priority: 0,
				Config:   map[string]any{},
			}
			if enabled, ok := value["enabled"].(bool); ok {
				spec.Enabled = enabled
			}
			if priority, ok := value["priority"].(float64); ok {
				spec.Priority = int(priority)
			}
			if config, ok := value["config"].(map[string]any); ok {
				spec.Config = config
			}
			specs = append(specs, spec)
		}
	}
	return normalizePluginSpecs(specs)
}

func pluginSpecNames(specs []PluginSpec) []string {
	names := make([]string, 0, len(specs))
	for _, spec := range normalizePluginSpecs(specs) {
		if spec.Enabled && strings.TrimSpace(spec.Name) != "" {
			names = append(names, spec.Name)
		}
	}
	return names
}

func normalizePluginSpecs(specs []PluginSpec) []PluginSpec {
	if len(specs) == 0 {
		return nil
	}
	normalized := make([]PluginSpec, 0, len(specs))
	for _, spec := range specs {
		name := strings.TrimSpace(spec.Name)
		if name == "" {
			continue
		}
		normalized = append(normalized, PluginSpec{
			Name:     name,
			Enabled:  spec.Enabled,
			Priority: spec.Priority,
			Config:   spec.Config,
		})
	}
	sort.SliceStable(normalized, func(i, j int) bool {
		if normalized[i].Priority == normalized[j].Priority {
			return normalized[i].Name < normalized[j].Name
		}
		return normalized[i].Priority < normalized[j].Priority
	})
	return normalized
}

func newBuiltinPlugin(spec PluginSpec) (scrapyapi.Plugin, bool) {
	switch spec.Name {
	case "field-injector":
		return newFieldInjectorPlugin(spec.Config), true
	default:
		return nil, false
	}
}

type fieldInjectorPlugin struct {
	fields map[string]any
}

func newFieldInjectorPlugin(config map[string]any) scrapyapi.Plugin {
	fields := map[string]any{}
	if rawFields, ok := config["fields"].(map[string]any); ok {
		for key, value := range rawFields {
			fields[key] = value
		}
	}
	return &fieldInjectorPlugin{fields: fields}
}

type artifactFieldInjectorPipeline struct {
	fields map[string]any
}

func (p artifactFieldInjectorPipeline) ProcessItem(item scrapyapi.Item) (scrapyapi.Item, error) {
	for key, value := range p.fields {
		item[key] = value
	}
	return item, nil
}

type artifactResponseContextSpiderMiddleware struct{}

func (artifactResponseContextSpiderMiddleware) ProcessSpiderOutput(response *scrapyapi.Response, result []any, spider *scrapyapi.Spider) ([]any, error) {
	enriched := make([]any, 0, len(result))
	for _, entry := range result {
		switch value := entry.(type) {
		case scrapyapi.Item:
			value["response_url"] = response.URL
			value["response_status"] = response.StatusCode
			enriched = append(enriched, value)
		case map[string]any:
			value["response_url"] = response.URL
			value["response_status"] = response.StatusCode
			enriched = append(enriched, value)
		default:
			enriched = append(enriched, entry)
		}
	}
	return enriched, nil
}

type artifactRequestHeadersMiddleware struct {
	headers map[string]string
}

func (m artifactRequestHeadersMiddleware) ProcessRequest(request *scrapyapi.Request, spider *scrapyapi.Spider) (*scrapyapi.Request, error) {
	for key, value := range m.headers {
		request.Headers[key] = value
	}
	return request, nil
}

func (m artifactRequestHeadersMiddleware) ProcessResponse(response *scrapyapi.Response, spider *scrapyapi.Spider) (*scrapyapi.Response, error) {
	return response, nil
}

func readArtifactAnyMap(config map[string]any, key string) map[string]any {
	raw, ok := config[key].(map[string]any)
	if !ok {
		return map[string]any{}
	}
	fields := map[string]any{}
	for field, value := range raw {
		fields[field] = value
	}
	return fields
}

func readArtifactStringMap(config map[string]any, key string) map[string]string {
	raw, ok := config[key].(map[string]any)
	if !ok {
		return map[string]string{}
	}
	fields := map[string]string{}
	for field, value := range raw {
		fields[field] = fmt.Sprint(value)
	}
	return fields
}

func (p *fieldInjectorPlugin) PrepareSpider(_ *scrapyapi.Spider) error { return nil }

func (p *fieldInjectorPlugin) ProvidePipelines() []scrapyapi.ItemPipeline { return nil }

func (p *fieldInjectorPlugin) OnSpiderOpened(_ *scrapyapi.Spider) error { return nil }

func (p *fieldInjectorPlugin) OnSpiderClosed(_ *scrapyapi.Spider) error { return nil }

func (p *fieldInjectorPlugin) ProcessItem(item scrapyapi.Item, _ *scrapyapi.Spider) (scrapyapi.Item, error) {
	for key, value := range p.fields {
		item[key] = value
	}
	return item, nil
}
