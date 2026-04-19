package main

import (
	"bytes"
	"context"
	"encoding/csv"
	"encoding/json"
	"encoding/xml"
	"flag"
	"fmt"
	"go/ast"
	goparser "go/parser"
	"go/token"
	"io"
	"net/http"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"runtime"
	"sort"
	"strings"
	"time"

	"github.com/PuerkitoBio/goquery"
	"gopkg.in/yaml.v3"
	spiderai "gospider/ai"
	"gospider/antibot"
	"gospider/api"
	"gospider/browser"
	"gospider/core"
	"gospider/distributed"
	"gospider/events"
	"gospider/features"
	nodereverse "gospider/node_reverse"
	"gospider/parser"
	"gospider/queue"
	"gospider/research"
	runtimedispatch "gospider/runtime/dispatch"
	scrapyapi "gospider/scrapy"
	projectruntime "gospider/scrapy/project"
	"gospider/storage"
	"gospider/ultimate"
	webui "gospider/web"
)

const version = "2.0.0"

type contractConfig struct {
	Version int `json:"version" yaml:"version"`
	Project struct {
		Name string `json:"name" yaml:"name"`
	} `json:"project" yaml:"project"`
	Runtime string `json:"runtime" yaml:"runtime"`
	Crawl   struct {
		URLs           []string `json:"urls" yaml:"urls"`
		Concurrency    int      `json:"concurrency" yaml:"concurrency"`
		MaxRequests    int      `json:"max_requests" yaml:"max_requests"`
		MaxDepth       int      `json:"max_depth" yaml:"max_depth"`
		TimeoutSeconds int      `json:"timeout_seconds" yaml:"timeout_seconds"`
	} `json:"crawl" yaml:"crawl"`
	Sitemap struct {
		Enabled bool   `json:"enabled" yaml:"enabled"`
		URL     string `json:"url" yaml:"url"`
		MaxURLs int    `json:"max_urls" yaml:"max_urls"`
	} `json:"sitemap" yaml:"sitemap"`
	Browser struct {
		Enabled          bool   `json:"enabled" yaml:"enabled"`
		Headless         bool   `json:"headless" yaml:"headless"`
		TimeoutSeconds   int    `json:"timeout_seconds" yaml:"timeout_seconds"`
		UserAgent        string `json:"user_agent" yaml:"user_agent"`
		ScreenshotPath   string `json:"screenshot_path" yaml:"screenshot_path"`
		HTMLPath         string `json:"html_path" yaml:"html_path"`
		StorageStateFile string `json:"storage_state_file" yaml:"storage_state_file"`
		CookiesFile      string `json:"cookies_file" yaml:"cookies_file"`
		AuthFile         string `json:"auth_file" yaml:"auth_file"`
	} `json:"browser" yaml:"browser"`
	AntiBot struct {
		Enabled         bool   `json:"enabled" yaml:"enabled"`
		Profile         string `json:"profile" yaml:"profile"`
		ProxyPool       string `json:"proxy_pool" yaml:"proxy_pool"`
		SessionMode     string `json:"session_mode" yaml:"session_mode"`
		Stealth         bool   `json:"stealth" yaml:"stealth"`
		ChallengePolicy string `json:"challenge_policy" yaml:"challenge_policy"`
		CaptchaProvider string `json:"captcha_provider" yaml:"captcha_provider"`
		CaptchaAPIKey   string `json:"captcha_api_key" yaml:"captcha_api_key"`
	} `json:"anti_bot" yaml:"anti_bot"`
	NodeReverse struct {
		Enabled bool   `json:"enabled" yaml:"enabled"`
		BaseURL string `json:"base_url" yaml:"base_url"`
	} `json:"node_reverse" yaml:"node_reverse"`
	Middleware struct {
		UserAgentRotation  bool `json:"user_agent_rotation" yaml:"user_agent_rotation"`
		RespectRobotsTxt   bool `json:"respect_robots_txt" yaml:"respect_robots_txt"`
		MinRequestInterval int  `json:"min_request_interval_ms" yaml:"min_request_interval_ms"`
	} `json:"middleware" yaml:"middleware"`
	Pipeline struct {
		Console   bool   `json:"console" yaml:"console"`
		Dataset   bool   `json:"dataset" yaml:"dataset"`
		JSONLPath string `json:"jsonl_path" yaml:"jsonl_path"`
	} `json:"pipeline" yaml:"pipeline"`
	AutoThrottle struct {
		Enabled              bool `json:"enabled" yaml:"enabled"`
		StartDelayMS         int  `json:"start_delay_ms" yaml:"start_delay_ms"`
		MaxDelayMS           int  `json:"max_delay_ms" yaml:"max_delay_ms"`
		TargetResponseTimeMS int  `json:"target_response_time_ms" yaml:"target_response_time_ms"`
	} `json:"auto_throttle" yaml:"auto_throttle"`
	Frontier struct {
		Enabled              bool   `json:"enabled" yaml:"enabled"`
		Autoscale            bool   `json:"autoscale" yaml:"autoscale"`
		MinConcurrency       int    `json:"min_concurrency" yaml:"min_concurrency"`
		MaxConcurrency       int    `json:"max_concurrency" yaml:"max_concurrency"`
		LeaseTTLSeconds      int    `json:"lease_ttl_seconds" yaml:"lease_ttl_seconds"`
		MaxInflightPerDomain int    `json:"max_inflight_per_domain" yaml:"max_inflight_per_domain"`
		CheckpointID         string `json:"checkpoint_id" yaml:"checkpoint_id"`
		CheckpointDir        string `json:"checkpoint_dir" yaml:"checkpoint_dir"`
	} `json:"frontier" yaml:"frontier"`
	Observability struct {
		StructuredLogs        bool   `json:"structured_logs" yaml:"structured_logs"`
		Metrics               bool   `json:"metrics" yaml:"metrics"`
		Trace                 bool   `json:"trace" yaml:"trace"`
		FailureClassification bool   `json:"failure_classification" yaml:"failure_classification"`
		ArtifactDir           string `json:"artifact_dir" yaml:"artifact_dir"`
	} `json:"observability" yaml:"observability"`
	Cache struct {
		Enabled           bool   `json:"enabled" yaml:"enabled"`
		StorePath         string `json:"store_path" yaml:"store_path"`
		DeltaFetch        bool   `json:"delta_fetch" yaml:"delta_fetch"`
		RevalidateSeconds int    `json:"revalidate_seconds" yaml:"revalidate_seconds"`
	} `json:"cache" yaml:"cache"`
	Plugins struct {
		Enabled  bool   `json:"enabled" yaml:"enabled"`
		Manifest string `json:"manifest" yaml:"manifest"`
	} `json:"plugins" yaml:"plugins"`
	Scrapy struct {
		Plugins               []string                              `json:"plugins,omitempty" yaml:"plugins,omitempty"`
		Runner                string                                `json:"runner,omitempty" yaml:"runner,omitempty"`
		Pipelines             []string                              `json:"pipelines,omitempty" yaml:"pipelines,omitempty"`
		SpiderMiddlewares     []string                              `json:"spider_middlewares,omitempty" yaml:"spider_middlewares,omitempty"`
		DownloaderMiddlewares []string                              `json:"downloader_middlewares,omitempty" yaml:"downloader_middlewares,omitempty"`
		ComponentConfig       map[string]map[string]any             `json:"component_config,omitempty" yaml:"component_config,omitempty"`
		Spiders               map[string]scrapySpiderContractConfig `json:"spiders,omitempty" yaml:"spiders,omitempty"`
	} `json:"scrapy,omitempty" yaml:"scrapy,omitempty"`
	Storage struct {
		CheckpointDir string `json:"checkpoint_dir" yaml:"checkpoint_dir"`
		DatasetDir    string `json:"dataset_dir" yaml:"dataset_dir"`
		ExportDir     string `json:"export_dir" yaml:"export_dir"`
	} `json:"storage" yaml:"storage"`
	Export struct {
		Format     string `json:"format" yaml:"format"`
		OutputPath string `json:"output_path" yaml:"output_path"`
	} `json:"export" yaml:"export"`
	Doctor struct {
		NetworkTargets []string `json:"network_targets,omitempty" yaml:"network_targets,omitempty"`
		RedisURL       string   `json:"redis_url,omitempty" yaml:"redis_url,omitempty"`
	} `json:"doctor,omitempty" yaml:"doctor,omitempty"`
}

type scrapySpiderContractConfig struct {
	Runner                string                    `json:"runner,omitempty" yaml:"runner,omitempty"`
	URL                   string                    `json:"url,omitempty" yaml:"url,omitempty"`
	Pipelines             []string                  `json:"pipelines,omitempty" yaml:"pipelines,omitempty"`
	SpiderMiddlewares     []string                  `json:"spider_middlewares,omitempty" yaml:"spider_middlewares,omitempty"`
	DownloaderMiddlewares []string                  `json:"downloader_middlewares,omitempty" yaml:"downloader_middlewares,omitempty"`
	ComponentConfig       map[string]map[string]any `json:"component_config,omitempty" yaml:"component_config,omitempty"`
}

type browserFetchResult struct {
	Title          string `json:"title"`
	URL            string `json:"url"`
	HTMLPath       string `json:"html_path"`
	ScreenshotPath string `json:"screenshot_path"`
}

type browserFetchRunner interface {
	Fetch(url string, screenshot string, htmlPath string, cfg contractConfig) (browserFetchResult, error)
}

type playwrightBrowserFetchRunner struct{}

var browserFetchRunnerFactory = func() browserFetchRunner {
	return playwrightBrowserFetchRunner{}
}

type repeatedStringFlag []string

func (f *repeatedStringFlag) String() string {
	return strings.Join(*f, ",")
}

func (f *repeatedStringFlag) Set(value string) error {
	*f = append(*f, value)
	return nil
}

func main() {
	if len(os.Args) < 2 {
		printUsage()
		os.Exit(1)
	}

	// 版本检查
	if os.Args[1] == "version" || os.Args[1] == "-v" || os.Args[1] == "--version" {
		fmt.Printf("gospider version %s\n", version)
		os.Exit(0)
	}

	// 命令处理
	command := os.Args[1]
	switch command {
	case "crawl":
		crawlCmd := flag.NewFlagSet("crawl", flag.ExitOnError)
		url := crawlCmd.String("url", "", "target URL to crawl")
		depth := crawlCmd.Int("depth", 3, "crawl depth")
		concurrency := crawlCmd.Int("concurrency", 5, "concurrency level")
		configPath := crawlCmd.String("config", "", "shared contract config path")
		_ = crawlCmd.Parse(os.Args[2:])

		cfg, err := loadContractConfig(*configPath)
		if err != nil {
			fmt.Fprintf(os.Stderr, "config error: %v\n", err)
			os.Exit(2)
		}
		if *url == "" && len(cfg.Crawl.URLs) > 0 {
			*url = cfg.Crawl.URLs[0]
		}
		if cfg.Crawl.Concurrency > 0 {
			*concurrency = cfg.Crawl.Concurrency
		}
		if cfg.Crawl.MaxDepth > 0 {
			*depth = cfg.Crawl.MaxDepth
		}

		if *url == "" {
			fmt.Println("Error: --url is required")
			os.Exit(1)
		}

		fmt.Printf("Starting crawl: %s (depth=%d, concurrency=%d)\n", *url, *depth, *concurrency)

		// 创建配置
		config := core.DefaultSpiderConfig()
		config.Concurrency = *concurrency
		config.RespectRobots = cfg.Middleware.RespectRobotsTxt
		if throttleDelay := maxInt(cfg.Middleware.MinRequestInterval, cfg.AutoThrottle.StartDelayMS); throttleDelay > 0 {
			config.Delay = time.Duration(throttleDelay) * time.Millisecond
		}
		if cfg.Browser.UserAgent != "" {
			config.UserAgent = cfg.Browser.UserAgent
		}
		if cfg.AntiBot.Enabled {
			if antiUA := antiBotUserAgent(cfg); antiUA != "" {
				config.UserAgent = antiUA
			}
		}
		if proxy := antiBotProxy(cfg); proxy != "" {
			config.ProxyURL = proxy
		}

		// 创建爬虫实例
		spider := core.NewSpider(config)
		reverseClient := nodereverse.NewNodeReverseClient(cfg.NodeReverse.BaseURL)

		headers := map[string]string{"User-Agent": config.UserAgent}
		if cfg.AntiBot.Enabled {
			for k, v := range antiBotHeaders(cfg) {
				headers[k] = v
			}
		}
		targets := []string{*url}
		if cfg.Sitemap.Enabled {
			targets = mergeTargets(targets, discoverSitemapTargets(*url, cfg))
		}
		for _, target := range targets {
			req := &queue.Request{
				URL:      target,
				Method:   "GET",
				Headers:  headers,
				Priority: 0,
			}
			if err := spider.AddRequest(req); err != nil {
				fmt.Printf("Failed to add request: %v\n", err)
				os.Exit(1)
			}
		}

		spider.SetOnResponse(func(req *queue.Request, resp *http.Response) error {
			defer resp.Body.Close()

			body, err := io.ReadAll(io.LimitReader(resp.Body, 1<<20))
			if err != nil {
				return err
			}

			title := extractTitle(body)
			spider.GetDataset().Push(map[string]interface{}{
				"url":          req.URL,
				"status_code":  resp.StatusCode,
				"title":        title,
				"content_type": resp.Header.Get("Content-Type"),
			})
			if cfg.NodeReverse.Enabled && cfg.NodeReverse.BaseURL != "" {
				reverseProfile, reverseErr := reverseClient.ProfileAntiBot(nodereverse.AntiBotProfileRequest{
					HTML:       string(body),
					Headers:    map[string]interface{}{"content-type": resp.Header.Get("Content-Type")},
					StatusCode: resp.StatusCode,
					URL:        req.URL,
				})
				if reverseErr == nil && reverseProfile != nil && reverseProfile.Success {
					spider.GetDataset().Push(map[string]interface{}{
						"url":              req.URL,
						"anti_bot_level":   reverseProfile.Level,
						"anti_bot_signals": reverseProfile.Signals,
					})
					fmt.Printf("anti-bot: level=%s signals=%s\n", reverseProfile.Level, strings.Join(reverseProfile.Signals, ","))
				}
			}

			fmt.Printf("[%d] %s\n", resp.StatusCode, req.URL)
			if title != "" {
				fmt.Printf("title: %s\n", title)
			}
			return nil
		})
		spider.SetOnError(func(req *queue.Request, err error) {
			fmt.Fprintf(os.Stderr, "crawl failed: %s: %v\n", req.URL, err)
		})

		if err := spider.Run(); err != nil {
			fmt.Printf("Crawl failed: %v\n", err)
			os.Exit(1)
		}

		stats := spider.GetStats()
		if cfg.Pipeline.Dataset && strings.TrimSpace(cfg.Pipeline.JSONLPath) != "" {
			if err := writeDatasetJSONL(cfg.Pipeline.JSONLPath, spider.GetDataset().ToList()); err != nil {
				fmt.Fprintf(os.Stderr, "failed to persist dataset jsonl: %v\n", err)
			}
		}
		fmt.Printf(
			"Crawl finished: handled=%v failed=%v items=%d\n",
			stats["handled"],
			stats["failed"],
			spider.GetDataset().Size(),
		)
	case "ai":
		os.Exit(aiCommand(os.Args[2:]))
	case "doctor":
		doctorCommand(os.Args[2:])
	case "preflight":
		doctorCommandNamed(os.Args[2:], "preflight")
	case "browser":
		browserCommand(os.Args[2:])
	case "export":
		exportCommand(os.Args[2:])
	case "curl":
		os.Exit(curlCommand(os.Args[2:]))
	case "run":
		os.Exit(runCommand(os.Args[2:]))
	case "job":
		os.Exit(jobCommand(os.Args[2:]))
	case "async-job":
		os.Exit(asyncJobCommand(os.Args[2:]))
	case "jobdir":
		os.Exit(jobdirCommand(os.Args[2:]))
	case "http-cache":
		os.Exit(httpCacheCommand(os.Args[2:]))
	case "console":
		os.Exit(runtimeConsoleCommand(os.Args[2:]))
	case "audit":
		os.Exit(auditCommand(os.Args[2:]))
	case "capabilities":
		capabilitiesCommand()
	case "config":
		configCommand(os.Args[2:])
	case "web":
		os.Exit(webCommand(os.Args[2:]))
	case "media":
		mediaCommand(os.Args[2:])
	case "ultimate":
		ultimateCommand(os.Args[2:])
	case "selector-studio":
		os.Exit(selectorStudioCommand(os.Args[2:]))
	case "scrapy":
		os.Exit(scrapyCommand(os.Args[2:]))
	case "sitemap-discover":
		os.Exit(sitemapDiscoverCommand(os.Args[2:]))
	case "plugins":
		os.Exit(pluginsCommand(os.Args[2:]))
	case "profile-site":
		os.Exit(profileSiteCommand(os.Args[2:]))
	case "research":
		os.Exit(researchCommand(os.Args[2:]))
	case "workflow":
		os.Exit(workflowCommand(os.Args[2:]))
	case "node-reverse":
		os.Exit(nodeReverseCommand(os.Args[2:]))
	case "anti-bot", "antibot":
		os.Exit(antiBotCommand(os.Args[2:]))
	default:
		printUsage()
		os.Exit(1)
	}
}

func printUsage() {
	fmt.Printf("gospider %s - A powerful web crawler\n\n", version)
	fmt.Println("Usage:")
	fmt.Println("  gospider <command> [options]")
	fmt.Println()
	fmt.Println("Commands:")
	fmt.Println("  config     Write a shared contract config")
	fmt.Println("  crawl      Crawl a website")
	fmt.Println("  browser    Fetch or instrument a dynamic page")
	fmt.Println("  export     Export JSON items to a contract format")
	fmt.Println("  curl      Convert curl commands into Go code")
	fmt.Println("  run        Execute an inline pyspider-style URL job")
	fmt.Println("  job        Execute a normalized JobSpec from JSON")
	fmt.Println("  async-job  Execute a normalized JobSpec through the async parity surface")
	fmt.Println("  jobdir     Manage a shared pause/resume job directory")
	fmt.Println("  http-cache Inspect or seed the shared HTTP cache store")
	fmt.Println("  console    Inspect shared control-plane and jobdir artifacts")
	fmt.Println("  audit      Inspect audit, connector, and control-plane traces")
	fmt.Println("  capabilities  Print integrated runtime capabilities")
	fmt.Println("  web        Launch the embedded Web UI or API server")
	fmt.Println("  workflow   Execute the lightweight workflow orchestration surface")
	fmt.Println("  media      Download media (YouTube, Youku, etc.)")
	fmt.Println("  ultimate   Run the advanced ultimate spider")
	fmt.Println("  ai         Run AI-assisted extraction, understanding, or spider generation")
	fmt.Println("  selector-studio  Test selectors and extraction expressions")
	fmt.Println("  scrapy     Run scrapy-style project and shell tooling")
	fmt.Println("  scrapy     Run scrapy-style demo authoring flow")
	fmt.Println("  sitemap-discover  Discover sitemap URLs before crawling")
	fmt.Println("  plugins    Inspect shared plugin/integration manifests")
	fmt.Println("  profile-site  Profile a target before crawling")
	fmt.Println("  research   Run the pyspider-style research runtime surfaces")
	fmt.Println("  node-reverse  Call the NodeReverse service directly")
	fmt.Println("  anti-bot   Run anti-bot utilities and local block detection")
	fmt.Println("  doctor     Run diagnostics")
	fmt.Println("  preflight  Run diagnostics through the cross-runtime preflight alias")
	fmt.Println("  version    Show version")
	fmt.Println()
	fmt.Println("Examples:")
	fmt.Println("  gospider config init --output spider-framework.yaml")
	fmt.Println("  gospider crawl --url https://example.com --depth 3 --concurrency 5")
	fmt.Println("  gospider browser fetch --url https://example.com --screenshot artifacts/browser/page.png")
	fmt.Println("  gospider browser trace --url https://example.com --trace-path artifacts/browser/page.trace.zip --har-path artifacts/browser/page.har")
	fmt.Println("  gospider export --input artifacts/datasets/crawl.json --format json --output artifacts/exports/results.json")
	fmt.Println("  gospider curl convert --command \"curl https://example.com\" --target resty")
	fmt.Println("  gospider run https://example.com --runtime http")
	fmt.Println("  gospider job --file contracts/example-job.json")
	fmt.Println("  gospider async-job --file contracts/example-job.json")
	fmt.Println("  gospider jobdir init --path artifacts/jobs/demo --runtime go --url https://example.com")
	fmt.Println("  gospider http-cache status --path artifacts/cache/incremental.json")
	fmt.Println("  gospider console snapshot --control-plane artifacts/control-plane --jobdir artifacts/jobs/demo")
	fmt.Println("  gospider audit tail --control-plane artifacts/control-plane --job-name demo --stream audit")
	fmt.Println("  gospider capabilities")
	fmt.Println("  gospider web --mode ui --port 8080")
	fmt.Println("  gospider media -url https://www.youtube.com/watch?v=xxx -download")
	fmt.Println("  gospider media drm --content \"#EXTM3U ...\"")
	fmt.Println("  gospider ultimate --url https://example.com")
	fmt.Println("  gospider ai --url https://example.com --instructions \"提取标题和摘要\" --schema-json '{\"type\":\"object\",\"properties\":{\"title\":{\"type\":\"string\"},\"summary\":{\"type\":\"string\"}}}'")
	fmt.Println("  gospider selector-studio --html-file page.html --type css --expr title")
	fmt.Println("  gospider scrapy shell --html-file page.html --type css --expr title")
	fmt.Println("  gospider scrapy demo --html-file page.html --output artifacts/exports/scrapy-demo.json")
	fmt.Println("  gospider scrapy contracts validate --project examples/project")
	fmt.Println("  gospider sitemap-discover --url https://example.com")
	fmt.Println("  gospider plugins list")
	fmt.Println("  gospider profile-site --url https://example.com")
	fmt.Println("  gospider research run --url https://example.com --schema-json '{\"properties\":{\"title\":{\"type\":\"string\"}}}'")
	fmt.Println("  gospider node-reverse health --base-url http://localhost:3000")
	fmt.Println("  gospider anti-bot headers --profile cloudflare")
	fmt.Println("  gospider doctor")
	fmt.Println("  gospider preflight --json")
	fmt.Println("  gospider version")
}

func extractTitle(body []byte) string {
	document, err := goquery.NewDocumentFromReader(bytes.NewReader(body))
	if err != nil {
		return ""
	}
	return strings.TrimSpace(document.Find("title").First().Text())
}

func defaultContractConfig() contractConfig {
	var cfg contractConfig
	cfg.Version = 1
	cfg.Project.Name = "go-project"
	cfg.Runtime = "go"
	cfg.Crawl.URLs = []string{"https://example.com"}
	cfg.Crawl.Concurrency = 5
	cfg.Crawl.MaxRequests = 100
	cfg.Crawl.MaxDepth = 3
	cfg.Crawl.TimeoutSeconds = 30
	cfg.Sitemap.Enabled = false
	cfg.Sitemap.URL = "https://example.com/sitemap.xml"
	cfg.Sitemap.MaxURLs = 50
	cfg.Browser.Enabled = true
	cfg.Browser.Headless = true
	cfg.Browser.TimeoutSeconds = 30
	cfg.Browser.ScreenshotPath = "artifacts/browser/page.png"
	cfg.Browser.HTMLPath = "artifacts/browser/page.html"
	cfg.AntiBot.Enabled = true
	cfg.AntiBot.Profile = "chrome-stealth"
	cfg.AntiBot.ProxyPool = "local"
	cfg.AntiBot.SessionMode = "sticky"
	cfg.AntiBot.Stealth = true
	cfg.AntiBot.ChallengePolicy = "browser"
	cfg.AntiBot.CaptchaProvider = "2captcha"
	cfg.AntiBot.CaptchaAPIKey = ""
	cfg.NodeReverse.Enabled = true
	cfg.NodeReverse.BaseURL = "http://localhost:3000"
	cfg.Middleware.UserAgentRotation = true
	cfg.Middleware.RespectRobotsTxt = true
	cfg.Middleware.MinRequestInterval = 200
	cfg.Pipeline.Console = true
	cfg.Pipeline.Dataset = true
	cfg.Pipeline.JSONLPath = "artifacts/exports/results.jsonl"
	cfg.AutoThrottle.Enabled = true
	cfg.AutoThrottle.StartDelayMS = 200
	cfg.AutoThrottle.MaxDelayMS = 5000
	cfg.AutoThrottle.TargetResponseTimeMS = 2000
	cfg.Frontier.Enabled = true
	cfg.Frontier.Autoscale = true
	cfg.Frontier.MinConcurrency = 1
	cfg.Frontier.MaxConcurrency = 16
	cfg.Frontier.LeaseTTLSeconds = 30
	cfg.Frontier.MaxInflightPerDomain = 2
	cfg.Frontier.CheckpointID = "runtime-frontier"
	cfg.Frontier.CheckpointDir = "artifacts/checkpoints/frontier"
	cfg.Observability.StructuredLogs = true
	cfg.Observability.Metrics = true
	cfg.Observability.Trace = true
	cfg.Observability.FailureClassification = true
	cfg.Observability.ArtifactDir = "artifacts/observability"
	cfg.Cache.Enabled = true
	cfg.Cache.StorePath = "artifacts/cache/incremental.json"
	cfg.Cache.DeltaFetch = true
	cfg.Cache.RevalidateSeconds = 3600
	cfg.Plugins.Enabled = true
	cfg.Plugins.Manifest = "contracts/integration-catalog.json"
	cfg.Scrapy.Runner = "http"
	cfg.Scrapy.Spiders = map[string]scrapySpiderContractConfig{
		"demo": {
			Runner:                "http",
			URL:                   "https://example.com",
			Pipelines:             []string{},
			SpiderMiddlewares:     []string{},
			DownloaderMiddlewares: []string{},
			ComponentConfig:       map[string]map[string]any{},
		},
	}
	cfg.Scrapy.ComponentConfig = map[string]map[string]any{
		"field_injector":  {"fields": map[string]any{}},
		"request_headers": {"headers": map[string]any{}},
	}
	cfg.Storage.CheckpointDir = "artifacts/checkpoints"
	cfg.Storage.DatasetDir = "artifacts/datasets"
	cfg.Storage.ExportDir = "artifacts/exports"
	cfg.Export.Format = "json"
	cfg.Export.OutputPath = "artifacts/exports/results.json"
	cfg.Doctor.NetworkTargets = []string{"https://example.com"}
	return cfg
}

func loadContractConfig(path string) (contractConfig, error) {
	cfg := defaultContractConfig()
	if path != "" {
		if _, err := os.Stat(path); err != nil {
			return cfg, fmt.Errorf("config file not found: %s", path)
		}
	} else {
		for _, candidate := range []string{"spider-framework.yaml", "spider-framework.yml", "spider-framework.json", "config.yaml"} {
			if _, err := os.Stat(candidate); err == nil {
				path = candidate
				break
			}
		}
	}
	if path == "" {
		return cfg, validateContractConfig(cfg, "go")
	}
	data, err := os.ReadFile(path)
	if err != nil {
		return cfg, fmt.Errorf("failed to read config: %w", err)
	}
	if strings.HasSuffix(path, ".json") {
		if err := json.Unmarshal(data, &cfg); err != nil {
			return cfg, fmt.Errorf("invalid json config: %w", err)
		}
		return cfg, validateContractConfig(cfg, "go")
	}
	if err := yaml.Unmarshal(data, &cfg); err != nil {
		return cfg, fmt.Errorf("invalid yaml config: %w", err)
	}
	return cfg, validateContractConfig(cfg, "go")
}

func validateContractConfig(cfg contractConfig, expectedRuntime string) error {
	var errors []string
	if cfg.Version < 1 {
		errors = append(errors, "version must be an integer >= 1")
	}
	if strings.TrimSpace(cfg.Project.Name) == "" {
		errors = append(errors, "project.name must be a non-empty string")
	}
	if cfg.Runtime != expectedRuntime {
		errors = append(errors, fmt.Sprintf("runtime mismatch: expected %q, got %q", expectedRuntime, cfg.Runtime))
	}
	if len(cfg.Crawl.URLs) == 0 {
		errors = append(errors, "crawl.urls must be a non-empty string array")
	}
	if cfg.Crawl.Concurrency < 1 {
		errors = append(errors, "crawl.concurrency must be an integer >= 1")
	}
	if cfg.Crawl.MaxRequests < 1 {
		errors = append(errors, "crawl.max_requests must be an integer >= 1")
	}
	if cfg.Crawl.MaxDepth < 0 {
		errors = append(errors, "crawl.max_depth must be an integer >= 0")
	}
	if cfg.Crawl.TimeoutSeconds < 1 {
		errors = append(errors, "crawl.timeout_seconds must be an integer >= 1")
	}
	if cfg.Browser.TimeoutSeconds < 1 {
		errors = append(errors, "browser.timeout_seconds must be an integer >= 1")
	}
	if strings.TrimSpace(cfg.Browser.ScreenshotPath) == "" {
		errors = append(errors, "browser.screenshot_path must be a non-empty string")
	}
	if strings.TrimSpace(cfg.Browser.HTMLPath) == "" {
		errors = append(errors, "browser.html_path must be a non-empty string")
	}
	if strings.TrimSpace(cfg.AntiBot.Profile) == "" {
		errors = append(errors, "anti_bot.profile must be a non-empty string")
	}
	if strings.TrimSpace(cfg.NodeReverse.BaseURL) == "" {
		errors = append(errors, "node_reverse.base_url must be a non-empty string")
	}
	if strings.TrimSpace(cfg.Storage.CheckpointDir) == "" {
		errors = append(errors, "storage.checkpoint_dir must be a non-empty string")
	}
	if strings.TrimSpace(cfg.Storage.DatasetDir) == "" {
		errors = append(errors, "storage.dataset_dir must be a non-empty string")
	}
	if strings.TrimSpace(cfg.Storage.ExportDir) == "" {
		errors = append(errors, "storage.export_dir must be a non-empty string")
	}
	if !map[string]bool{"json": true, "jsonl": true, "csv": true, "md": true}[cfg.Export.Format] {
		errors = append(errors, "export.format must be one of [json jsonl csv md]")
	}
	if strings.TrimSpace(cfg.Export.OutputPath) == "" {
		errors = append(errors, "export.output_path must be a non-empty string")
	}
	if cfg.Frontier.MinConcurrency < 1 {
		errors = append(errors, "frontier.min_concurrency must be an integer >= 1")
	}
	if cfg.Frontier.MaxConcurrency < cfg.Frontier.MinConcurrency {
		errors = append(errors, "frontier.max_concurrency must be an integer >= frontier.min_concurrency")
	}
	if cfg.Frontier.LeaseTTLSeconds < 1 {
		errors = append(errors, "frontier.lease_ttl_seconds must be an integer >= 1")
	}
	if cfg.Frontier.MaxInflightPerDomain < 1 {
		errors = append(errors, "frontier.max_inflight_per_domain must be an integer >= 1")
	}
	if strings.TrimSpace(cfg.Frontier.CheckpointID) == "" {
		errors = append(errors, "frontier.checkpoint_id must be a non-empty string")
	}
	if strings.TrimSpace(cfg.Frontier.CheckpointDir) == "" {
		errors = append(errors, "frontier.checkpoint_dir must be a non-empty string")
	}
	if strings.TrimSpace(cfg.Observability.ArtifactDir) == "" {
		errors = append(errors, "observability.artifact_dir must be a non-empty string")
	}
	if strings.TrimSpace(cfg.Cache.StorePath) == "" {
		errors = append(errors, "cache.store_path must be a non-empty string")
	}
	if cfg.Cache.RevalidateSeconds < 1 {
		errors = append(errors, "cache.revalidate_seconds must be an integer >= 1")
	}
	for _, target := range cfg.Doctor.NetworkTargets {
		if strings.TrimSpace(target) == "" {
			errors = append(errors, "doctor.network_targets must only contain non-empty strings")
			break
		}
	}
	validateStringSlice(&errors, cfg.Scrapy.Pipelines, "scrapy.pipelines")
	validateStringSlice(&errors, cfg.Scrapy.SpiderMiddlewares, "scrapy.spider_middlewares")
	validateStringSlice(&errors, cfg.Scrapy.DownloaderMiddlewares, "scrapy.downloader_middlewares")
	validateAllowedStringSlice(&errors, cfg.Scrapy.Pipelines, "scrapy.pipelines", map[string]bool{
		"field-injector": true,
	})
	validateAllowedStringSlice(&errors, cfg.Scrapy.SpiderMiddlewares, "scrapy.spider_middlewares", map[string]bool{
		"response-context": true,
	})
	validateAllowedStringSlice(&errors, cfg.Scrapy.DownloaderMiddlewares, "scrapy.downloader_middlewares", map[string]bool{
		"request-headers": true,
	})
	for spiderName, spiderCfg := range cfg.Scrapy.Spiders {
		prefix := "scrapy.spiders." + spiderName
		validateStringSlice(&errors, spiderCfg.Pipelines, prefix+".pipelines")
		validateStringSlice(&errors, spiderCfg.SpiderMiddlewares, prefix+".spider_middlewares")
		validateStringSlice(&errors, spiderCfg.DownloaderMiddlewares, prefix+".downloader_middlewares")
		validateAllowedStringSlice(&errors, spiderCfg.Pipelines, prefix+".pipelines", map[string]bool{
			"field-injector": true,
		})
		validateAllowedStringSlice(&errors, spiderCfg.SpiderMiddlewares, prefix+".spider_middlewares", map[string]bool{
			"response-context": true,
		})
		validateAllowedStringSlice(&errors, spiderCfg.DownloaderMiddlewares, prefix+".downloader_middlewares", map[string]bool{
			"request-headers": true,
		})
	}
	if len(errors) > 0 {
		return fmt.Errorf(strings.Join(errors, "; "))
	}
	return nil
}

func validateStringSlice(errors *[]string, values []string, name string) {
	for _, value := range values {
		if strings.TrimSpace(value) == "" {
			*errors = append(*errors, name+" must be a string array")
			return
		}
	}
}

func validateAllowedStringSlice(errors *[]string, values []string, name string, allowed map[string]bool) {
	for _, value := range values {
		trimmed := strings.TrimSpace(value)
		if trimmed == "" {
			continue
		}
		if !allowed[trimmed] {
			*errors = append(*errors, name+" contains unsupported component: "+trimmed)
		}
	}
}

func configCommand(args []string) {
	if len(args) == 0 || args[0] != "init" {
		fmt.Println("Usage: gospider config init [--output <path>]")
		return
	}
	initCmd := flag.NewFlagSet("config init", flag.ExitOnError)
	output := initCmd.String("output", "spider-framework.yaml", "output file")
	_ = initCmd.Parse(args[1:])
	cfg := defaultContractConfig()
	data, _ := yaml.Marshal(&cfg)
	if err := os.MkdirAll(filepath.Dir(*output), 0755); err != nil && filepath.Dir(*output) != "." {
		fmt.Printf("Failed to prepare config directory: %v\n", err)
		os.Exit(1)
	}
	if err := os.WriteFile(*output, data, 0644); err != nil {
		fmt.Printf("Failed to write config: %v\n", err)
		os.Exit(1)
	}
	fmt.Printf("Wrote shared config: %s\n", *output)
}

func browserCommand(args []string) {
	if len(args) == 0 {
		fmt.Println("Usage: gospider browser <fetch|trace|mock|codegen> ...")
		return
	}

	switch args[0] {
	case "fetch":
		fetchCmd := flag.NewFlagSet("browser fetch", flag.ExitOnError)
		url := fetchCmd.String("url", "", "target URL")
		configPath := fetchCmd.String("config", "", "shared contract config path")
		screenshot := fetchCmd.String("screenshot", "", "screenshot path")
		htmlPath := fetchCmd.String("html", "", "html output path")
		_ = fetchCmd.Parse(args[1:])

		cfg, err := loadContractConfig(*configPath)
		if err != nil {
			fmt.Fprintf(os.Stderr, "config error: %v\n", err)
			os.Exit(2)
		}
		if *url == "" && len(cfg.Crawl.URLs) > 0 {
			*url = cfg.Crawl.URLs[0]
		}
		if *screenshot == "" {
			*screenshot = cfg.Browser.ScreenshotPath
		}
		if *htmlPath == "" {
			*htmlPath = cfg.Browser.HTMLPath
		}
		if *url == "" {
			fmt.Println("browser fetch requires --url or a config with crawl.urls")
			os.Exit(2)
		}

		result, err := browserFetchRunnerFactory().Fetch(*url, *screenshot, *htmlPath, cfg)
		if err != nil {
			fmt.Printf("browser fetch failed: %v\n", err)
			os.Exit(1)
		}
		fmt.Printf("title: %s\n", result.Title)
		fmt.Printf("url: %s\n", result.URL)
	case "trace", "mock", "codegen":
		os.Exit(browserToolingCommand(args[0], args[1:]))
	default:
		fmt.Println("Usage: gospider browser <fetch|trace|mock|codegen> ...")
		os.Exit(2)
	}
}

func browserToolingCommand(tooling string, args []string) int {
	cmd := flag.NewFlagSet("browser "+tooling, flag.ExitOnError)
	url := cmd.String("url", "", "target URL")
	tracePath := cmd.String("trace-path", "", "trace output path")
	harPath := cmd.String("har-path", "", "har output path")
	routeManifest := cmd.String("route-manifest", "", "route mocking manifest")
	htmlPath := cmd.String("html", "", "html output path")
	screenshot := cmd.String("screenshot", "", "screenshot output path")
	output := cmd.String("output", "", "generated script output path")
	language := cmd.String("language", "python", "generated script language")
	_ = cmd.Parse(args)

	if strings.TrimSpace(*url) == "" {
		fmt.Fprintf(os.Stderr, "browser %s requires --url\n", tooling)
		return 2
	}
	if tooling == "trace" && strings.TrimSpace(*tracePath) == "" {
		fmt.Fprintln(os.Stderr, "browser trace requires --trace-path")
		return 2
	}
	if tooling == "mock" && strings.TrimSpace(*routeManifest) == "" {
		fmt.Fprintln(os.Stderr, "browser mock requires --route-manifest")
		return 2
	}
	if tooling == "codegen" && strings.TrimSpace(*output) == "" {
		fmt.Fprintln(os.Stderr, "browser codegen requires --output")
		return 2
	}

	toolArgs := []string{"--tooling-command", tooling, "--url", *url}
	if strings.TrimSpace(*tracePath) != "" {
		toolArgs = append(toolArgs, "--trace-path", *tracePath)
	}
	if strings.TrimSpace(*harPath) != "" {
		toolArgs = append(toolArgs, "--har-path", *harPath)
	}
	if strings.TrimSpace(*routeManifest) != "" {
		toolArgs = append(toolArgs, "--route-manifest", *routeManifest)
	}
	if strings.TrimSpace(*htmlPath) != "" {
		toolArgs = append(toolArgs, "--html", *htmlPath)
	}
	if strings.TrimSpace(*screenshot) != "" {
		toolArgs = append(toolArgs, "--screenshot", *screenshot)
	}
	if strings.TrimSpace(*output) != "" {
		toolArgs = append(toolArgs, "--codegen-out", *output)
	}
	if strings.TrimSpace(*language) != "" {
		toolArgs = append(toolArgs, "--codegen-language", *language)
	}
	return runSharedPythonTool("playwright_fetch.py", toolArgs)
}

func jobdirCommand(args []string) int {
	if len(args) == 0 {
		fmt.Fprintln(os.Stderr, "usage: gospider jobdir <init|status|pause|resume|clear> --path <jobdir>")
		return 2
	}
	subcommand := args[0]
	if subcommand != "init" && subcommand != "status" && subcommand != "pause" && subcommand != "resume" && subcommand != "clear" {
		fmt.Fprintln(os.Stderr, "usage: gospider jobdir <init|status|pause|resume|clear> --path <jobdir>")
		return 2
	}

	cmd := flag.NewFlagSet("jobdir "+subcommand, flag.ExitOnError)
	path := cmd.String("path", "", "jobdir path")
	runtimeName := cmd.String("runtime", "go", "runtime name")
	var urls repeatedStringFlag
	cmd.Var(&urls, "url", "seed URL for jobdir init")
	_ = cmd.Parse(args[1:])

	if strings.TrimSpace(*path) == "" {
		fmt.Fprintln(os.Stderr, "jobdir requires --path")
		return 2
	}

	toolArgs := []string{subcommand, "--path", *path}
	if subcommand == "init" {
		toolArgs = append(toolArgs, "--runtime", *runtimeName)
		for _, url := range urls {
			toolArgs = append(toolArgs, "--url", url)
		}
	}
	return runSharedPythonTool("jobdir_tool.py", toolArgs)
}

func httpCacheCommand(args []string) int {
	if len(args) == 0 {
		fmt.Fprintln(os.Stderr, "usage: gospider http-cache <status|clear|seed> --path <cache.json>")
		return 2
	}
	subcommand := args[0]
	if subcommand != "status" && subcommand != "clear" && subcommand != "seed" {
		fmt.Fprintln(os.Stderr, "usage: gospider http-cache <status|clear|seed> --path <cache.json>")
		return 2
	}

	cmd := flag.NewFlagSet("http-cache "+subcommand, flag.ExitOnError)
	path := cmd.String("path", "", "cache store path")
	url := cmd.String("url", "", "cache URL for seed")
	statusCode := cmd.Int("status-code", 200, "status code for seed")
	etag := cmd.String("etag", "", "etag for seed")
	lastModified := cmd.String("last-modified", "", "last-modified for seed")
	contentHash := cmd.String("content-hash", "", "content hash for seed")
	_ = cmd.Parse(args[1:])

	if strings.TrimSpace(*path) == "" {
		fmt.Fprintln(os.Stderr, "http-cache requires --path")
		return 2
	}

	toolArgs := []string{subcommand, "--path", *path}
	if subcommand == "seed" {
		if strings.TrimSpace(*url) == "" {
			fmt.Fprintln(os.Stderr, "http-cache seed requires --url")
			return 2
		}
		toolArgs = append(toolArgs, "--url", *url, "--status-code", fmt.Sprintf("%d", *statusCode))
		if strings.TrimSpace(*etag) != "" {
			toolArgs = append(toolArgs, "--etag", *etag)
		}
		if strings.TrimSpace(*lastModified) != "" {
			toolArgs = append(toolArgs, "--last-modified", *lastModified)
		}
		if strings.TrimSpace(*contentHash) != "" {
			toolArgs = append(toolArgs, "--content-hash", *contentHash)
		}
	}
	return runSharedPythonTool("http_cache_tool.py", toolArgs)
}

func runtimeConsoleCommand(args []string) int {
	if len(args) == 0 {
		fmt.Fprintln(os.Stderr, "usage: gospider console <snapshot|tail> --control-plane <dir>")
		return 2
	}
	subcommand := args[0]
	if subcommand != "snapshot" && subcommand != "tail" {
		fmt.Fprintln(os.Stderr, "usage: gospider console <snapshot|tail> --control-plane <dir>")
		return 2
	}

	cmd := flag.NewFlagSet("console "+subcommand, flag.ExitOnError)
	controlPlane := cmd.String("control-plane", "artifacts/control-plane", "control-plane directory")
	jobdir := cmd.String("jobdir", "", "jobdir path")
	stream := cmd.String("stream", "both", "stream to tail: events|results|both")
	lines := cmd.Int("lines", 20, "line count")
	_ = cmd.Parse(args[1:])

	toolArgs := []string{subcommand, "--control-plane", *controlPlane, "--lines", fmt.Sprintf("%d", *lines)}
	if subcommand == "snapshot" && strings.TrimSpace(*jobdir) != "" {
		toolArgs = append(toolArgs, "--jobdir", *jobdir)
	}
	if subcommand == "tail" {
		toolArgs = append(toolArgs, "--stream", *stream)
	}
	return runSharedPythonTool("runtime_console.py", toolArgs)
}

func auditCommand(args []string) int {
	if len(args) == 0 {
		fmt.Fprintln(os.Stderr, "usage: gospider audit <snapshot|tail> --control-plane <dir>")
		return 2
	}
	subcommand := args[0]
	if subcommand != "snapshot" && subcommand != "tail" {
		fmt.Fprintln(os.Stderr, "usage: gospider audit <snapshot|tail> --control-plane <dir>")
		return 2
	}

	cmd := flag.NewFlagSet("audit "+subcommand, flag.ExitOnError)
	controlPlane := cmd.String("control-plane", "artifacts/control-plane", "control-plane directory")
	jobName := cmd.String("job-name", "", "job name filter")
	stream := cmd.String("stream", "all", "stream to tail: events|results|audit|connector|all")
	lines := cmd.Int("lines", 20, "line count")
	_ = cmd.Parse(args[1:])

	toolArgs := []string{
		subcommand,
		"--control-plane",
		*controlPlane,
		"--job-name",
		*jobName,
		"--lines",
		fmt.Sprintf("%d", *lines),
	}
	if subcommand == "tail" {
		toolArgs = append(toolArgs, "--stream", *stream)
	}
	return runSharedPythonTool("audit_console.py", toolArgs)
}

func webCommand(args []string) int {
	webCmd := flag.NewFlagSet("web", flag.ExitOnError)
	mode := webCmd.String("mode", "ui", "server mode: ui|api")
	host := webCmd.String("host", "0.0.0.0", "listen host")
	port := webCmd.Int("port", 8080, "listen port")
	authToken := webCmd.String("auth-token", "", "optional bearer token")
	_ = webCmd.Parse(args)

	switch strings.ToLower(strings.TrimSpace(*mode)) {
	case "ui":
		server := webui.NewServer(fmt.Sprintf("%d", *port))
		if *host != "0.0.0.0" && *host != "127.0.0.1" && *host != "localhost" {
			fmt.Fprintf(os.Stderr, "web ui currently binds by port only; ignoring host=%s\n", *host)
		}
		if err := server.Run(); err != nil {
			fmt.Fprintf(os.Stderr, "web ui failed: %v\n", err)
			return 1
		}
		return 0
	case "api":
		cfg := &api.Config{
			Host:       *host,
			Port:       *port,
			EnableCORS: true,
			EnableAuth: strings.TrimSpace(*authToken) != "",
			AuthToken:  strings.TrimSpace(*authToken),
		}
		server := api.NewServerWithJobService(cfg, core.NewJobService())
		if err := server.Start(); err != nil {
			fmt.Fprintf(os.Stderr, "api server failed: %v\n", err)
			return 1
		}
		return 0
	default:
		fmt.Fprintln(os.Stderr, "usage: gospider web [--mode <ui|api>] [--host <host>] [--port <port>]")
		return 2
	}
}

func researchCommand(args []string) int {
	if len(args) == 0 {
		fmt.Fprintln(os.Stderr, "usage: gospider research <run|async|soak> ...")
		return 2
	}
	switch args[0] {
	case "run":
		cmd := flag.NewFlagSet("research run", flag.ExitOnError)
		url := cmd.String("url", "", "seed url")
		content := cmd.String("content", "", "inline content")
		schemaJSON := cmd.String("schema-json", "{}", "schema json")
		output := cmd.String("output", "", "output path")
		_ = cmd.Parse(args[1:])
		if *url == "" {
			fmt.Fprintln(os.Stderr, "research run requires --url")
			return 2
		}
		job, err := buildResearchJob([]string{*url}, *schemaJSON, *output)
		if err != nil {
			fmt.Fprintf(os.Stderr, "invalid research schema: %v\n", err)
			return 2
		}
		result, err := research.NewResearchRuntime().Run(job, *content)
		if err != nil {
			fmt.Fprintf(os.Stderr, "research run failed: %v\n", err)
			return 1
		}
		return printJSON(result)
	case "async", "soak":
		cmd := flag.NewFlagSet("research "+args[0], flag.ExitOnError)
		var urls repeatedStringFlag
		cmd.Var(&urls, "url", "seed url (repeatable)")
		content := cmd.String("content", "", "inline content reused for all jobs")
		schemaJSON := cmd.String("schema-json", "{}", "schema json")
		output := cmd.String("output", "", "output path for single-run reuse")
		rounds := cmd.Int("rounds", 1, "soak rounds")
		concurrency := cmd.Int("concurrency", 5, "max concurrent jobs")
		_ = cmd.Parse(args[1:])
		if len(urls) == 0 {
			fmt.Fprintln(os.Stderr, "research async/soak requires at least one --url")
			return 2
		}
		jobs := make([]research.ResearchJob, 0, len(urls))
		contents := make([]string, 0, len(urls))
		for index, url := range urls {
			jobOutput := ""
			if *output != "" && len(urls) == 1 {
				jobOutput = *output
			}
			job, err := buildResearchJob([]string{url}, *schemaJSON, jobOutput)
			if err != nil {
				fmt.Fprintf(os.Stderr, "invalid research schema: %v\n", err)
				return 2
			}
			jobs = append(jobs, job)
			if *content != "" {
				contents = append(contents, *content)
			} else {
				contents = append(contents, fmt.Sprintf("<title>Research %d</title>", index+1))
			}
		}
		runtime := research.NewAsyncResearchRuntime(&research.AsyncResearchConfig{
			MaxConcurrent: *concurrency,
		})
		if args[0] == "soak" {
			return printJSON(runtime.RunSoak(jobs, contents, *rounds))
		}
		results := runtime.RunMultiple(jobs, contents)
		rows := make([]map[string]interface{}, 0, len(results))
		for _, result := range results {
			rows = append(rows, map[string]interface{}{
				"seed":        result.Seed,
				"profile":     result.Profile,
				"extract":     result.Extract,
				"duration_ms": result.DurationMS,
				"dataset":     result.Dataset,
				"error":       result.Error,
			})
		}
		return printJSON(map[string]interface{}{
			"command": "research async",
			"runtime": "go",
			"results": rows,
			"metrics": runtime.SnapshotMetrics(),
		})
	default:
		fmt.Fprintln(os.Stderr, "usage: gospider research <run|async|soak> ...")
		return 2
	}
}

func buildResearchJob(seedURLs []string, schemaJSON string, outputPath string) (research.ResearchJob, error) {
	job := research.ResearchJob{SeedURLs: append([]string{}, seedURLs...)}
	if strings.TrimSpace(schemaJSON) != "" {
		schema := map[string]interface{}{}
		if err := json.Unmarshal([]byte(schemaJSON), &schema); err != nil {
			return job, err
		}
		job.ExtractSchema = schema
	}
	if strings.TrimSpace(outputPath) != "" {
		job.Output = map[string]interface{}{
			"path": outputPath,
		}
	}
	return job, nil
}

func printJSON(payload interface{}) int {
	encoded, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		fmt.Fprintf(os.Stderr, "json marshal failed: %v\n", err)
		return 1
	}
	fmt.Println(string(encoded))
	return 0
}

func doctorCommand(args []string) {
	doctorCommandNamed(args, "doctor")
}

func doctorCommandNamed(args []string, commandName string) {
	doctorCmd := flag.NewFlagSet("doctor", flag.ExitOnError)
	configPath := doctorCmd.String("config", "", "shared contract config path")
	jsonOutput := doctorCmd.Bool("json", false, "render json")
	_ = doctorCmd.Parse(args)

	cfg, err := loadContractConfig(*configPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "config error: %v\n", err)
		os.Exit(2)
	}
	opts := doctorOptions{
		ConfigPath:      *configPath,
		NetworkTargets:  append([]string{}, cfg.Doctor.NetworkTargets...),
		OverrideRedis:   cfg.Doctor.RedisURL,
		CheckRedis:      true,
		CheckBrowser:    true,
		CheckFFmpeg:     true,
		AllowAutoCreate: true,
		WritablePaths: []string{
			cfg.Storage.CheckpointDir,
			cfg.Storage.DatasetDir,
			cfg.Storage.ExportDir,
		},
	}
	report := runDoctor(opts)
	if *jsonOutput {
		payload, err := renderDoctorReportJSONForCommand(report, commandName)
		if err != nil {
			fmt.Printf("Failed to render doctor JSON: %v\n", err)
			os.Exit(1)
		}
		fmt.Println(payload)
		return
	}
	fmt.Println(renderDoctorReportForCommand(report, commandName))
}

func exportCommand(args []string) {
	exportCmd := flag.NewFlagSet("export", flag.ExitOnError)
	input := exportCmd.String("input", "", "input JSON file")
	format := exportCmd.String("format", "json", "output format")
	output := exportCmd.String("output", "", "output path")
	_ = exportCmd.Parse(args)
	if *input == "" || *output == "" {
		fmt.Println("Usage: gospider export --input <path> --format <json|jsonl|csv|md> --output <path>")
		os.Exit(2)
	}
	dataBytes, err := os.ReadFile(*input)
	if err != nil {
		fmt.Printf("Failed to read input: %v\n", err)
		os.Exit(1)
	}
	var items []map[string]interface{}
	var envelope map[string]interface{}
	if err := json.Unmarshal(dataBytes, &envelope); err == nil && envelope != nil {
		if raw, ok := envelope["items"].([]interface{}); ok {
			for _, item := range raw {
				if record, ok := item.(map[string]interface{}); ok {
					items = append(items, record)
				}
			}
		}
	}
	if len(items) == 0 {
		_ = json.Unmarshal(dataBytes, &items)
	}
	if err := os.MkdirAll(filepath.Dir(*output), 0755); err != nil {
		fmt.Printf("Failed to create output directory: %v\n", err)
		os.Exit(1)
	}
	switch *format {
	case "json":
		payload, _ := json.MarshalIndent(map[string]interface{}{
			"schema_version": 1,
			"runtime":        "go",
			"exported_at":    time.Now().Format(time.RFC3339),
			"item_count":     len(items),
			"items":          items,
		}, "", "  ")
		_ = os.WriteFile(*output, payload, 0644)
	case "jsonl":
		var builder strings.Builder
		for _, item := range items {
			row, err := json.Marshal(item)
			if err != nil {
				fmt.Printf("Failed to encode jsonl row: %v\n", err)
				os.Exit(1)
			}
			builder.Write(row)
			builder.WriteByte('\n')
		}
		_ = os.WriteFile(*output, []byte(builder.String()), 0644)
	case "csv":
		file, err := os.Create(*output)
		if err != nil {
			fmt.Printf("Failed to create csv output: %v\n", err)
			os.Exit(1)
		}
		writer := csv.NewWriter(file)
		_ = writer.Write([]string{"title", "url", "snippet", "source", "time"})
		for _, item := range items {
			_ = writer.Write([]string{
				fmt.Sprint(item["title"]),
				fmt.Sprint(item["url"]),
				fmt.Sprint(item["snippet"]),
				fmt.Sprint(item["source"]),
				fmt.Sprint(item["time"]),
			})
		}
		writer.Flush()
		_ = file.Close()
	case "md":
		var builder strings.Builder
		builder.WriteString("# Export\n\n")
		for index, item := range items {
			builder.WriteString(fmt.Sprintf("## %d. %s\n\n", index+1, fmt.Sprint(item["title"])))
			builder.WriteString(fmt.Sprintf("- URL: %s\n", fmt.Sprint(item["url"])))
			builder.WriteString(fmt.Sprintf("- Source: %s\n", fmt.Sprint(item["source"])))
			builder.WriteString(fmt.Sprintf("- Snippet: %s\n\n", fmt.Sprint(item["snippet"])))
		}
		_ = os.WriteFile(*output, []byte(builder.String()), 0644)
	default:
		fmt.Printf("Unsupported format: %s\n", *format)
		os.Exit(2)
	}
	fmt.Printf("exported: %s\n", *output)
}

func loadJobSpecFromFile(path string) (*core.JobSpec, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}

	var job core.JobSpec
	if err := json.Unmarshal(data, &job); err != nil {
		return nil, err
	}

	job.Normalize()

	if job.Output.Path == "" && job.Output.Directory == "" {
		base := strings.TrimSuffix(filepath.Base(path), filepath.Ext(path))
		job.Output.Path = filepath.Join("artifacts", base+".json")
	}

	if err := job.Validate(); err != nil {
		return nil, err
	}

	return &job, nil
}

func jobCommand(args []string) int {
	jobCmd := flag.NewFlagSet("job", flag.ExitOnError)
	file := jobCmd.String("file", "", "JobSpec JSON file")
	_ = jobCmd.Parse(args)

	if *file == "" {
		fmt.Println("Error: --file is required")
		return 2
	}

	job, err := loadJobSpecFromFile(*file)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Failed to load job: %v\n", err)
		return 1
	}
	return executeRuntimeJob(job)
}

func asyncJobCommand(args []string) int {
	jobCmd := flag.NewFlagSet("async-job", flag.ExitOnError)
	file := jobCmd.String("file", "", "JobSpec JSON file")
	content := jobCmd.String("content", "", "inline content override")
	_ = jobCmd.Parse(args)

	if *file == "" {
		fmt.Println("Error: --file is required")
		return 2
	}

	job, err := loadJobSpecFromFile(*file)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Failed to load job: %v\n", err)
		return 1
	}
	if job.Metadata == nil {
		job.Metadata = map[string]interface{}{}
	}
	job.Metadata["execution_mode"] = "async"
	if strings.TrimSpace(*content) != "" {
		job.Metadata["content"] = *content
	}
	return executeRuntimeJob(job)
}

func runCommand(args []string) int {
	runCmd := flag.NewFlagSet("run", flag.ExitOnError)
	urlValue := runCmd.String("url", "", "target URL")
	runtimeValue := runCmd.String("runtime", "http", "runtime: http|browser|media|ai")
	name := runCmd.String("name", "", "job name")
	output := runCmd.String("output", "", "output JSON path")
	content := runCmd.String("content", "", "inline content override")
	_ = runCmd.Parse(args)

	if *urlValue == "" && len(runCmd.Args()) > 0 {
		*urlValue = runCmd.Args()[0]
	}
	if strings.TrimSpace(*urlValue) == "" {
		fmt.Println("Error: run requires a URL")
		return 2
	}

	jobName := strings.TrimSpace(*name)
	if jobName == "" {
		jobName = fmt.Sprintf("go-inline-%d", time.Now().UnixMilli())
	}
	outputPath := strings.TrimSpace(*output)
	if outputPath == "" {
		outputPath = filepath.Join("artifacts", "exports", jobName+".json")
	}
	job := &core.JobSpec{
		Name:    jobName,
		Runtime: core.Runtime(strings.ToLower(strings.TrimSpace(*runtimeValue))),
		Target: core.TargetSpec{
			URL: *urlValue,
		},
		Output: core.OutputSpec{
			Format: "json",
			Path:   outputPath,
		},
	}
	if strings.TrimSpace(*content) != "" {
		job.Metadata = map[string]interface{}{
			"content": *content,
		}
	}
	return executeRuntimeJob(job)
}

func executeRuntimeJob(job *core.JobSpec) int {
	if injectedErr := injectedJobFailure(job); injectedErr != nil {
		result := core.NewJobResult(*job, core.StateFailed)
		result.Error = injectedErr.Error()
		result.FinishedAt = time.Now()
		result.Finalize()
		printAndPersistJobResult(job, result)
		fmt.Fprintf(os.Stderr, "Job failed: %v\n", injectedErr)
		return 1
	}

	config := core.DefaultConfig()
	engine := core.NewSpiderEngine("cli-job", config)
	engine.WithExecutor(runtimedispatch.NewExecutor(runtimedispatch.Options{Config: config}))

	result, err := engine.Run(context.Background(), job)
	printAndPersistJobResult(job, result)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Job failed: %v\n", err)
		return 1
	}
	return 0
}

func printAndPersistJobResult(job *core.JobSpec, result *core.JobResult) {
	if result == nil {
		return
	}
	payload := cliJobResultPayload(result)
	encoded, marshalErr := json.MarshalIndent(payload, "", "  ")
	if marshalErr != nil {
		return
	}
	fmt.Println(string(encoded))
	if job == nil || job.Output.Path == "" {
		return
	}
	if err := os.MkdirAll(filepath.Dir(job.Output.Path), 0755); err != nil {
		return
	}
	_ = os.WriteFile(job.Output.Path, encoded, 0644)

	resultStore := storage.NewFileResultStore(filepath.Join("artifacts", "control-plane", "results.jsonl"))
	eventStore := storage.NewFileEventStore(filepath.Join("artifacts", "control-plane", "events.jsonl"))
	record := storage.ResultRecord{
		ID:         result.JobName,
		Runtime:    string(result.Runtime),
		State:      string(result.State),
		URL:        result.URL,
		StatusCode: result.StatusCode,
		Extract:    result.Extract,
		Warnings:   append([]string(nil), result.Warnings...),
		UpdatedAt:  result.FinishedAt,
	}
	if len(result.ArtifactRefs) > 0 {
		record.Artifacts = make(map[string]storage.ArtifactRecord, len(result.ArtifactRefs))
		for name, artifact := range result.ArtifactRefs {
			record.Artifacts[name] = storage.ArtifactRecord{
				Name:     name,
				Kind:     artifact.Kind,
				URI:      artifact.URI,
				Path:     artifact.Path,
				Size:     artifact.Size,
				Metadata: artifact.Metadata,
			}
		}
	}
	_ = resultStore.Put(record)
	if dbStore := configuredSQLResultStore(); dbStore != nil {
		_ = dbStore.Put(record)
	} else if dbStore := configuredProcessResultStore(); dbStore != nil {
		_ = dbStore.Put(record)
	}
	_ = eventStore.Put(events.New(events.TopicTaskResult, events.TaskResultPayload{
		TaskID:       result.JobName,
		State:        string(result.State),
		Runtime:      string(result.Runtime),
		URL:          result.URL,
		StatusCode:   result.StatusCode,
		Artifacts:    append([]string(nil), result.Artifacts...),
		ArtifactRefs: resultArtifactRefs(result),
		UpdatedAt:    result.FinishedAt,
	}))
	controlPlaneDir := filepath.Join("artifacts", "control-plane")
	_ = appendJSONLRecord(
		filepath.Join(controlPlaneDir, fmt.Sprintf("%s-audit.jsonl", result.JobName)),
		map[string]interface{}{
			"type": "job.result",
			"payload": map[string]interface{}{
				"job_name": result.JobName,
				"runtime":  string(result.Runtime),
				"state":    string(result.State),
				"url":      result.URL,
				"error":    result.Error,
			},
		},
	)
	_ = appendJSONLRecord(
		filepath.Join(controlPlaneDir, fmt.Sprintf("%s-connector.jsonl", result.JobName)),
		map[string]interface{}{
			"job_name":      result.JobName,
			"runtime":       string(result.Runtime),
			"state":         string(result.State),
			"url":           result.URL,
			"output_path":   job.Output.Path,
			"artifact_refs": payload["artifact_refs"],
			"extract":       result.Extract,
		},
	)
}

func configuredProcessResultStore() *storage.ProcessResultStore {
	backend := strings.ToLower(strings.TrimSpace(os.Getenv("GOSPIDER_STORAGE_BACKEND")))
	endpoint := strings.TrimSpace(os.Getenv("GOSPIDER_STORAGE_ENDPOINT"))
	if backend == "" || endpoint == "" {
		return nil
	}
	config := storage.StorageBackendConfig{
		Endpoint:   endpoint,
		Table:      strings.TrimSpace(os.Getenv("GOSPIDER_STORAGE_TABLE")),
		Collection: strings.TrimSpace(os.Getenv("GOSPIDER_STORAGE_COLLECTION")),
	}
	switch backend {
	case "postgres", "postgresql":
		config.Kind = storage.StorageBackendPostgres
	case "mysql":
		config.Kind = storage.StorageBackendMySQL
	case "mongo", "mongodb":
		config.Kind = storage.StorageBackendMongoDB
	default:
		return nil
	}
	return storage.NewProcessResultStore(config)
}

func configuredSQLResultStore() *storage.SQLResultStore {
	mode := strings.ToLower(strings.TrimSpace(os.Getenv("GOSPIDER_STORAGE_MODE")))
	backend := strings.ToLower(strings.TrimSpace(os.Getenv("GOSPIDER_STORAGE_BACKEND")))
	if mode != "driver" || backend == "" {
		return nil
	}
	endpoint := strings.TrimSpace(os.Getenv("GOSPIDER_STORAGE_ENDPOINT"))
	if endpoint == "" {
		return nil
	}
	table := strings.TrimSpace(os.Getenv("GOSPIDER_STORAGE_TABLE"))
	switch backend {
	case "postgres", "postgresql":
		return storage.NewSQLResultStore(storage.SQLBackendPostgres, endpoint, table)
	case "mysql":
		return storage.NewSQLResultStore(storage.SQLBackendMySQL, endpoint, table)
	default:
		return nil
	}
}

func appendJSONLRecord(path string, payload interface{}) error {
	if err := os.MkdirAll(filepath.Dir(path), 0755); err != nil {
		return err
	}
	encoded, err := json.Marshal(payload)
	if err != nil {
		return err
	}
	handle, err := os.OpenFile(path, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0644)
	if err != nil {
		return err
	}
	defer handle.Close()
	if _, err := handle.Write(append(encoded, '\n')); err != nil {
		return err
	}
	return handle.Sync()
}

func cliJobResultPayload(result *core.JobResult) map[string]interface{} {
	artifacts := cliArtifactEnvelope(result)
	return map[string]interface{}{
		"job_name":      result.JobName,
		"runtime":       result.Runtime,
		"state":         result.State,
		"url":           result.URL,
		"status_code":   result.StatusCode,
		"headers":       result.Headers,
		"text":          result.Text,
		"started_at":    result.StartedAt,
		"finished_at":   result.FinishedAt,
		"error":         result.Error,
		"extract":       result.Extract,
		"metadata":      result.Metadata,
		"metrics":       result.Metrics,
		"anti_bot":      result.AntiBot,
		"recovery":      result.Recovery,
		"warnings":      result.Warnings,
		"artifacts":     artifacts,
		"artifact_refs": artifacts,
	}
}

func cliArtifactEnvelope(result *core.JobResult) map[string]map[string]interface{} {
	envelope := map[string]map[string]interface{}{}
	if result == nil {
		return envelope
	}
	if len(result.ArtifactRefs) > 0 {
		for name, artifact := range result.ArtifactRefs {
			envelope[name] = map[string]interface{}{
				"kind":    artifact.Kind,
				"path":    artifact.Path,
				"uri":     artifact.URI,
				"root_id": stringMapValue(artifact.Metadata, "root_id"),
				"stats":   mapMapValue(artifact.Metadata, "stats"),
			}
		}
		return envelope
	}
	for index, path := range result.Artifacts {
		key := fmt.Sprintf("artifact_%d", index+1)
		if strings.Contains(path, "-graph.json") {
			key = "graph"
		}
		envelope[key] = map[string]interface{}{
			"kind": detectArtifactKind(path),
			"path": path,
		}
	}
	return envelope
}

func detectArtifactKind(path string) string {
	lower := strings.ToLower(path)
	switch {
	case strings.HasSuffix(lower, ".png"):
		return "screenshot"
	case strings.HasSuffix(lower, ".html"):
		return "html"
	case strings.HasSuffix(lower, ".json") && strings.Contains(lower, "graph"):
		return "graph"
	default:
		return "artifact"
	}
}

func stringMapValue(metadata map[string]interface{}, key string) string {
	if metadata == nil {
		return ""
	}
	if value, ok := metadata[key].(string); ok {
		return value
	}
	return ""
}

func mapMapValue(metadata map[string]interface{}, key string) map[string]interface{} {
	if metadata == nil {
		return map[string]interface{}{}
	}
	if value, ok := metadata[key].(map[string]interface{}); ok {
		return value
	}
	return map[string]interface{}{}
}

func resultArtifactRefs(result *core.JobResult) map[string]events.ArtifactRef {
	if result == nil || len(result.ArtifactRefs) == 0 {
		return nil
	}
	refs := make(map[string]events.ArtifactRef, len(result.ArtifactRefs))
	for name, artifact := range result.ArtifactRefs {
		refs[name] = events.ArtifactRef{
			Kind:     artifact.Kind,
			URI:      artifact.URI,
			Path:     artifact.Path,
			Size:     artifact.Size,
			Metadata: artifact.Metadata,
		}
	}
	return refs
}

func injectedJobFailure(job *core.JobSpec) error {
	if job == nil || job.Metadata == nil {
		return nil
	}
	if raw, ok := job.Metadata["fail_job"]; ok {
		message := strings.TrimSpace(fmt.Sprint(raw))
		if message == "" || message == "<nil>" {
			message = "injected failure"
		}
		return fmt.Errorf(message)
	}
	return nil
}

func capabilitiesCommand() {
	payload := map[string]any{
		"command":   "capabilities",
		"framework": "gospider",
		"runtime":   "go",
		"version":   version,
		"entrypoints": []string{
			"config",
			"crawl",
			"browser",
			"ai",
			"export",
			"curl",
			"run",
			"job",
			"async-job",
			"jobdir",
			"http-cache",
			"console",
			"audit",
			"capabilities",
			"web",
			"media",
			"ultimate",
			"research",
			"workflow",
			"selector-studio",
			"scrapy",
			"sitemap-discover",
			"plugins",
			"profile-site",
			"node-reverse",
			"anti-bot",
			"doctor",
			"preflight",
			"version",
		},
		"runtimes": []string{
			string(core.RuntimeHTTP),
			string(core.RuntimeBrowser),
			string(core.RuntimeMedia),
			string(core.RuntimeAI),
		},
		"modules": []string{
			"core.JobSpec",
			"core.JobRunner",
			"async.Runtime",
			"core.AutoscaledFrontier",
			"core.FileArtifactStore",
			"core.CurlToGoConverter",
			"browser.SeleniumClient",
			"downloader.SSRFGuard",
			"distributed.NodeDiscovery",
			"distributed.QueueBridgeClient",
			"bridge.CrawleeBridgeClient",
			"connector.FileConnector",
			"events.FileBus",
			"audit.MemoryAuditTrail",
			"audit.FileAuditTrail",
			"storage.ProcessResultStore",
			"storage.ProcessDatasetStore",
			"features.FeatureGateCatalog",
			"research.Job",
			"research.Runtime",
			"research.AsyncRuntime",
			"research.ExperimentTracker",
			"workflow.WorkflowSpider",
			"ai.SentimentAnalyzer",
			"ai.ContentSummarizer",
			"ai.EntityExtractor",
			"runtime.dispatch",
			"audit.control_plane",
			"web.Server",
			"api.Server",
			"runtime.http",
			"runtime.browser",
			"media",
			"ai",
			"antibot",
			"node_reverse",
			"site_profiler",
			"selector_studio",
			"sitemap_discovery",
			"plugin_manifest",
			"api",
			"distributed",
		},
		"shared_contracts": []string{
			"shared-cli",
			"shared-config",
			"runtime-core",
			"autoscaled-frontier",
			"incremental-cache",
			"observability-envelope",
			"scrapy-project",
			"scrapy-plugins-manifest",
			"web-control-plane",
		},
		"feature_gates": features.Catalog(),
		"ai_capabilities": map[string]any{
			"providers":                     []string{"openai", "anthropic", "claude"},
			"few_shot":                      true,
			"sentiment_analysis":            true,
			"summarization":                 true,
			"entity_extraction_specialized": true,
		},
		"operator_products": map[string]any{
			"jobdir": map[string]any{
				"pause_resume": true,
				"state_file":   "job-state.json",
			},
			"http_cache": map[string]any{
				"status_seed_clear": true,
				"backends":          []string{"file-json", "memory"},
				"strategies":        []string{"revalidate", "delta-fetch"},
			},
			"message_queue": map[string]any{
				"default":  "redis",
				"backends": distributed.QueueBackendSupport(),
			},
			"queue_backends": distributed.QueueBackendSupport(),
			"browser_tooling": map[string]any{
				"trace":         true,
				"har":           true,
				"route_mocking": true,
				"codegen":       true,
			},
			"antibot": map[string]any{
				"behavior_randomization": true,
				"night_mode": map[string]any{
					"enabled":           true,
					"start_hour":        23,
					"end_hour":          6,
					"delay_multiplier":  1.5,
					"rate_limit_factor": 0.5,
				},
			},
			"node_discovery": map[string]any{
				"providers": []string{"env", "file", "dns-srv", "consul-http", "etcd-http"},
			},
			"security": map[string]any{
				"ssrf_guard": true,
			},
			"storage_backends": storage.StorageBackendSupport(),
			"autoscaling_pools": map[string]any{
				"frontier":      true,
				"request_queue": "autoscaled-frontier",
				"session_pool":  true,
				"browser_pool":  true,
			},
			"debug_console": map[string]any{
				"snapshot":            true,
				"tail":                true,
				"control_plane_jsonl": true,
			},
			"audit_console": map[string]any{
				"snapshot":   true,
				"tail":       true,
				"job_filter": true,
			},
			"event_system": map[string]any{
				"topics":  []string{"workflow.job.started", "workflow.step.started", "workflow.step.succeeded", "workflow.job.completed"},
				"storage": "jsonl+memory",
			},
			"connectors": map[string]any{
				"native": []string{"memory", "jsonl"},
			},
			"workflow": map[string]any{
				"step_types": []string{"goto", "wait", "click", "type", "select", "hover", "scroll", "eval", "listen_network", "extract", "download", "screenshot"},
				"connectors": true,
				"events":     true,
			},
			"crawlee_bridge": map[string]any{
				"client":   true,
				"endpoint": "/api/crawl",
			},
		},
		"browser_compatibility": browser.BrowserCompatibilitySupport(),
		"control_plane": map[string]any{
			"task_api":        true,
			"result_envelope": true,
			"artifact_refs":   true,
			"graph_artifact":  true,
			"graph_extract":   true,
		},
		"kernel_contracts": map[string][]string{
			"request":        {"core.Request"},
			"fingerprint":    {"core.RequestFingerprint"},
			"frontier":       {"core.AutoscaledFrontier"},
			"scheduler":      {"core.AutoscaledFrontier"},
			"middleware":     {"core.MiddlewareChain"},
			"artifact_store": {"core.FileArtifactStore"},
			"session_pool":   {"core.RuntimeSessionPool"},
			"proxy_policy":   {"core.ProxyPolicy"},
			"observability":  {"core.ObservabilityCollector"},
			"cache":          {"core.IncrementalCrawler"},
		},
		"observability": []string{
			"doctor",
			"preflight",
			"audit",
			"profile-site",
			"selector-studio",
			"scrapy doctor",
			"scrapy profile",
			"scrapy bench",
			"prometheus",
			"opentelemetry-json",
		},
	}

	encoded, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		fmt.Printf("capabilities marshal failed: %v\n", err)
		return
	}
	fmt.Println(string(encoded))
}

func scrapyCommand(args []string) int {
	if len(args) == 0 || (args[0] != "demo" && args[0] != "run" && args[0] != "export" && args[0] != "plan-ai" && args[0] != "sync-ai" && args[0] != "auth-validate" && args[0] != "auth-capture" && args[0] != "scaffold-ai" && args[0] != "profile" && args[0] != "doctor" && args[0] != "bench" && args[0] != "shell" && args[0] != "init" && args[0] != "list" && args[0] != "validate" && args[0] != "genspider" && args[0] != "contracts") {
		fmt.Fprintln(os.Stderr, "usage: gospider scrapy <demo|run|plan-ai|sync-ai|auth-validate|auth-capture|scaffold-ai|contracts> ...")
		return 2
	}
	subcommand := args[0]

	if subcommand == "contracts" {
		if len(args) < 2 || (args[1] != "init" && args[1] != "validate") {
			fmt.Fprintln(os.Stderr, "usage: gospider scrapy contracts <init|validate> --project <dir>")
			return 2
		}
		cmd := flag.NewFlagSet("scrapy contracts "+args[1], flag.ExitOnError)
		project := cmd.String("project", "", "project directory")
		_ = cmd.Parse(args[2:])
		if strings.TrimSpace(*project) == "" {
			fmt.Fprintln(os.Stderr, "scrapy contracts requires --project")
			return 2
		}
		return runSharedPythonTool("spider_contracts.py", []string{args[1], "--project", *project})
	}

	cmd := flag.NewFlagSet("scrapy "+subcommand, flag.ExitOnError)
	targetURL := cmd.String("url", "https://example.com", "target URL")
	project := cmd.String("project", "", "project directory")
	selectedSpider := cmd.String("spider", "", "spider name")
	initPath := cmd.String("path", "", "project directory")
	htmlFile := cmd.String("html-file", "", "local HTML file")
	output := cmd.String("output", "artifacts/exports/gospider-scrapy-demo.json", "output path")
	exportFormat := cmd.String("format", "json", "export format")
	spiderName := cmd.String("name", "", "spider name")
	spiderDomain := cmd.String("domain", "", "target domain")
	sessionName := cmd.String("session", "auth", "session name")
	aiTemplate := cmd.Bool("ai", false, "generate AI extraction template")
	mode := cmd.String("type", "css", "extract mode: css|css_attr|xpath|regex")
	expr := cmd.String("expr", "", "selector or expression")
	attr := cmd.String("attr", "", "attribute name")
	_ = cmd.Parse(args[1:])

	readManifest := func(projectRoot string) (map[string]string, error) {
		data, err := os.ReadFile(filepath.Join(projectRoot, "scrapy-project.json"))
		if err != nil {
			return nil, err
		}
		var manifest map[string]string
		if err := json.Unmarshal(data, &manifest); err != nil {
			return nil, err
		}
		if manifest["runtime"] != "go" {
			return nil, fmt.Errorf("runtime mismatch in %s: expected go", filepath.Join(projectRoot, "scrapy-project.json"))
		}
		return manifest, nil
	}
	parseSpiderMetadata := func(path string) map[string]string {
		metadata := map[string]string{}
		data, err := os.ReadFile(path)
		if err != nil {
			return metadata
		}
		lines := strings.Split(string(data), "\n")
		limit := 5
		if len(lines) < limit {
			limit = len(lines)
		}
		for _, line := range lines[:limit] {
			trimmed := strings.TrimSpace(line)
			if !strings.HasPrefix(trimmed, "// scrapy:") {
				continue
			}
			payload := strings.TrimSpace(strings.TrimPrefix(trimmed, "// scrapy:"))
			for _, part := range strings.Fields(payload) {
				if !strings.Contains(part, "=") {
					continue
				}
				parts := strings.SplitN(part, "=", 2)
				metadata[strings.TrimSpace(parts[0])] = strings.TrimSpace(parts[1])
			}
		}
		return metadata
	}
	relPath := func(projectRoot, path string) string {
		if relative, err := filepath.Rel(projectRoot, path); err == nil {
			return filepath.ToSlash(relative)
		}
		return path
	}
	parseRegisteredSpiders := func(projectRoot, path string) []map[string]string {
		metadata := parseSpiderMetadata(path)
		fset := token.NewFileSet()
		file, err := goparser.ParseFile(fset, path, nil, goparser.ParseComments)
		if err != nil {
			return nil
		}
		registered := []map[string]string{}
		ast.Inspect(file, func(node ast.Node) bool {
			call, ok := node.(*ast.CallExpr)
			if !ok {
				return true
			}
			selector, ok := call.Fun.(*ast.SelectorExpr)
			if !ok || selector.Sel == nil || selector.Sel.Name != "RegisterSpider" || len(call.Args) < 2 {
				return true
			}
			nameLit, ok := call.Args[0].(*ast.BasicLit)
			if !ok || nameLit.Kind != token.STRING {
				return true
			}
			spiderName := strings.Trim(nameLit.Value, `"`)
			constructor := ""
			switch fn := call.Args[1].(type) {
			case *ast.Ident:
				constructor = fn.Name
			case *ast.SelectorExpr:
				constructor = fn.Sel.Name
			}
			item := map[string]string{
				"name":        spiderName,
				"path":        relPath(projectRoot, path),
				"constructor": constructor,
				"runner":      "artifact-project",
			}
			for key, value := range metadata {
				item[key] = value
			}
			registered = append(registered, item)
			return true
		})
		return registered
	}
	parseRegisteredPlugins := func(projectRoot, path string) []map[string]string {
		fset := token.NewFileSet()
		file, err := goparser.ParseFile(fset, path, nil, goparser.ParseComments)
		if err != nil {
			return nil
		}
		metadata := parseSpiderMetadata(path)
		registered := []map[string]string{}
		ast.Inspect(file, func(node ast.Node) bool {
			call, ok := node.(*ast.CallExpr)
			if !ok {
				return true
			}
			selector, ok := call.Fun.(*ast.SelectorExpr)
			if !ok || selector.Sel == nil || selector.Sel.Name != "RegisterPlugin" || len(call.Args) < 2 {
				return true
			}
			nameLit, ok := call.Args[0].(*ast.BasicLit)
			if !ok || nameLit.Kind != token.STRING {
				return true
			}
			pluginName := strings.Trim(nameLit.Value, `"`)
			constructor := ""
			switch fn := call.Args[1].(type) {
			case *ast.Ident:
				constructor = fn.Name
			case *ast.SelectorExpr:
				constructor = fn.Sel.Name
			}
			item := map[string]string{
				"name":        pluginName,
				"path":        relPath(projectRoot, path),
				"constructor": constructor,
			}
			for key, value := range metadata {
				item[key] = value
			}
			registered = append(registered, item)
			return true
		})
		return registered
	}
	discoverPlugins := func(projectRoot string) []map[string]string {
		plugins := []map[string]string{}
		pluginsDir := filepath.Join(projectRoot, "plugins")
		if entries, err := os.ReadDir(pluginsDir); err == nil {
			for _, entry := range entries {
				if entry.IsDir() || filepath.Ext(entry.Name()) != ".go" {
					continue
				}
				path := filepath.Join(pluginsDir, entry.Name())
				registered := parseRegisteredPlugins(projectRoot, path)
				if len(registered) > 0 {
					plugins = append(plugins, registered...)
				}
			}
		}
		sort.SliceStable(plugins, func(i, j int) bool {
			return plugins[i]["name"] < plugins[j]["name"]
		})
		return plugins
	}
	discoverSpiders := func(projectRoot string, manifest map[string]string) []map[string]string {
		spiders := []map[string]string{}
		if entry := strings.TrimSpace(manifest["entry"]); entry != "" {
			item := map[string]string{"name": strings.TrimSuffix(filepath.Base(entry), filepath.Ext(entry)), "path": entry}
			for key, value := range parseSpiderMetadata(filepath.Join(projectRoot, entry)) {
				item[key] = value
			}
			spiders = append(spiders, item)
		}
		spidersDir := filepath.Join(projectRoot, "spiders")
		if entries, err := os.ReadDir(spidersDir); err == nil {
			for _, entry := range entries {
				if entry.IsDir() || filepath.Ext(entry.Name()) != ".go" {
					continue
				}
				path := filepath.Join(spidersDir, entry.Name())
				registered := parseRegisteredSpiders(projectRoot, path)
				if len(registered) > 0 {
					spiders = append(spiders, registered...)
					continue
				}
				item := map[string]string{"name": strings.TrimSuffix(entry.Name(), ".go"), "path": filepath.Join("spiders", entry.Name())}
				for key, value := range parseSpiderMetadata(path) {
					item[key] = value
				}
				spiders = append(spiders, item)
			}
		}
		sort.SliceStable(spiders, func(i, j int) bool {
			return spiders[i]["name"] < spiders[j]["name"]
		})
		return spiders
	}
	resolveProjectOutput := func(projectRoot string, manifest map[string]string, spider string) string {
		defaultOutput := manifest["output"]
		if strings.TrimSpace(defaultOutput) == "" {
			defaultOutput = "artifacts/exports/items.json"
		}
		if strings.TrimSpace(spider) != "" && strings.HasSuffix(defaultOutput, "items.json") {
			return filepath.Join(projectRoot, "artifacts", "exports", spider+".json")
		}
		return filepath.Join(projectRoot, defaultOutput)
	}
	resolveScrapyRunnerDetail := func(projectCfg contractConfig, spiderName string, metadata map[string]string) (string, string) {
		normalize := func(value string) string {
			switch strings.TrimSpace(strings.ToLower(value)) {
			case "browser", "http", "hybrid":
				return strings.TrimSpace(strings.ToLower(value))
			default:
				return ""
			}
		}
		if runner := normalize(metadata["runner"]); runner != "" {
			return runner, "metadata"
		}
		if spiderName != "" {
			if spiderCfg, ok := projectCfg.Scrapy.Spiders[spiderName]; ok {
				if runner := normalize(spiderCfg.Runner); runner != "" {
					return runner, "scrapy.spiders"
				}
			}
		}
		if runner := normalize(projectCfg.Scrapy.Runner); runner != "" {
			return runner, "scrapy.runner"
		}
		return "http", "default"
	}
	resolveScrapyURLDetail := func(projectCfg contractConfig, spiderName string, metadata map[string]string, manifestURL string) (string, string) {
		if spiderName != "" {
			if spiderCfg, ok := projectCfg.Scrapy.Spiders[spiderName]; ok && strings.TrimSpace(spiderCfg.URL) != "" {
				return strings.TrimSpace(spiderCfg.URL), "scrapy.spiders"
			}
		}
		if urlValue := strings.TrimSpace(metadata["url"]); urlValue != "" {
			return urlValue, "metadata"
		}
		if urlValue := strings.TrimSpace(manifestURL); urlValue != "" {
			return urlValue, "manifest"
		}
		return "https://example.com", "default"
	}
	resolveSpiderDisplayMetadata := func(projectRoot string, manifest map[string]string) []map[string]string {
		spiders := discoverSpiders(projectRoot, manifest)
		projectCfg := defaultContractConfig()
		projectCfgPath := filepath.Join(projectRoot, "spider-framework.yaml")
		if loadedCfg, err := loadContractConfig(projectCfgPath); err == nil {
			projectCfg = loadedCfg
		}
		for _, spider := range spiders {
			name := spider["name"]
			spider["runner"], spider["runner_source"] = resolveScrapyRunnerDetail(projectCfg, name, spider)
			spider["url"], spider["url_source"] = resolveScrapyURLDetail(projectCfg, name, spider, manifest["url"])
			spider["pipelines"] = strings.Join(configuredScrapyPipelinesForSpider(projectCfg, name), ",")
			spider["spider_middlewares"] = strings.Join(configuredScrapySpiderMiddlewaresForSpider(projectCfg, name), ",")
			spider["downloader_middlewares"] = strings.Join(configuredScrapyDownloaderMiddlewaresForSpider(projectCfg, name), ",")
		}
		return spiders
	}
	buildDeclarativePipelines := func(projectCfg contractConfig, spiderName string) []scrapyapi.ItemPipeline {
		pipelines := []scrapyapi.ItemPipeline{}
		componentConfig := mergedScrapyComponentConfigForSpider(projectCfg, spiderName)
		for _, name := range configuredScrapyPipelinesForSpider(projectCfg, spiderName) {
			switch strings.TrimSpace(name) {
			case "field-injector":
				pipelines = append(pipelines, declarativeFieldInjectorPipeline{
					fields: readStringAnyMap(componentConfig["field_injector"], "fields"),
				})
			}
		}
		return pipelines
	}
	buildDeclarativeSpiderMiddlewares := func(projectCfg contractConfig, spiderName string) []scrapyapi.SpiderMiddleware {
		middlewares := []scrapyapi.SpiderMiddleware{}
		for _, name := range configuredScrapySpiderMiddlewaresForSpider(projectCfg, spiderName) {
			switch strings.TrimSpace(name) {
			case "response-context":
				middlewares = append(middlewares, declarativeResponseContextSpiderMiddleware{})
			}
		}
		return middlewares
	}
	buildDeclarativeDownloaderMiddlewares := func(projectCfg contractConfig, spiderName string) []scrapyapi.DownloaderMiddleware {
		middlewares := []scrapyapi.DownloaderMiddleware{}
		componentConfig := mergedScrapyComponentConfigForSpider(projectCfg, spiderName)
		for _, name := range configuredScrapyDownloaderMiddlewaresForSpider(projectCfg, spiderName) {
			switch strings.TrimSpace(name) {
			case "request-headers":
				middlewares = append(middlewares, declarativeRequestHeadersMiddleware{
					headers: readStringMap(componentConfig["request_headers"], "headers"),
				})
			}
		}
		return middlewares
	}
	browserFetchForScrapy := func(request *scrapyapi.Request, cfg contractConfig) (*scrapyapi.Response, error) {
		currentCfg := cfg
		if request != nil {
			if timeout, ok := request.Meta["browser_timeout_seconds"].(int); ok && timeout > 0 {
				currentCfg.Browser.TimeoutSeconds = timeout
			}
			if screenshot, ok := request.Meta["browser_screenshot_path"].(string); ok && strings.TrimSpace(screenshot) != "" {
				currentCfg.Browser.ScreenshotPath = screenshot
			}
			if htmlPath, ok := request.Meta["browser_html_path"].(string); ok && strings.TrimSpace(htmlPath) != "" {
				currentCfg.Browser.HTMLPath = htmlPath
			}
			if browserMeta, ok := request.Meta["browser"].(map[string]any); ok {
				if timeout, ok := browserMeta["timeout_seconds"].(int); ok && timeout > 0 {
					currentCfg.Browser.TimeoutSeconds = timeout
				}
				if screenshot, ok := browserMeta["screenshot_path"].(string); ok && strings.TrimSpace(screenshot) != "" {
					currentCfg.Browser.ScreenshotPath = screenshot
				}
				if htmlPath, ok := browserMeta["html_path"].(string); ok && strings.TrimSpace(htmlPath) != "" {
					currentCfg.Browser.HTMLPath = htmlPath
				}
				if storageState, ok := browserMeta["storage_state_file"].(string); ok && strings.TrimSpace(storageState) != "" {
					currentCfg.Browser.StorageStateFile = storageState
				}
				if cookiesFile, ok := browserMeta["cookies_file"].(string); ok && strings.TrimSpace(cookiesFile) != "" {
					currentCfg.Browser.CookiesFile = cookiesFile
				}
			}
		}
		htmlPath := currentCfg.Browser.HTMLPath
		if strings.TrimSpace(htmlPath) == "" {
			tempFile, err := os.CreateTemp("", "gospider-scrapy-browser-*.html")
			if err != nil {
				return nil, err
			}
			htmlPath = tempFile.Name()
			_ = tempFile.Close()
			defer os.Remove(htmlPath)
		}
		result, err := browserFetchRunnerFactory().Fetch(request.URL, currentCfg.Browser.ScreenshotPath, htmlPath, currentCfg)
		if err != nil {
			return nil, err
		}
		body, err := os.ReadFile(htmlPath)
		if err != nil {
			return nil, err
		}
		resolvedURL := request.URL
		if strings.TrimSpace(result.URL) != "" {
			resolvedURL = result.URL
		}
		return &scrapyapi.Response{
			URL:        resolvedURL,
			StatusCode: http.StatusOK,
			Headers:    http.Header{},
			Body:       body,
			Text:       string(body),
			Request:    request,
		}, nil
	}
	runProjectArtifact := func(projectRoot string, manifest map[string]string, spider map[string]string, outputPath string) (bool, int) {
		runner := strings.TrimSpace(manifest["runner"])
		if runner == "" {
			return false, 0
		}
		env := append(os.Environ(),
			"GOSPIDER_SCRAPY_RUNNER=1",
			"GOSPIDER_SCRAPY_PROJECT="+projectRoot,
			"GOSPIDER_SCRAPY_SPIDER="+spider["name"],
			"GOSPIDER_SCRAPY_URL="+*targetURL,
			"GOSPIDER_SCRAPY_OUTPUT="+outputPath,
		)
		if strings.TrimSpace(*htmlFile) != "" {
			env = append(env, "GOSPIDER_SCRAPY_HTML_FILE="+*htmlFile)
		}
		if reverseURL := strings.TrimSpace(os.Getenv("GOSPIDER_SCRAPY_REVERSE_URL")); reverseURL != "" {
			env = append(env, "GOSPIDER_SCRAPY_REVERSE_URL="+reverseURL)
		}
		runnerPath := filepath.Join(projectRoot, filepath.FromSlash(runner))
		if _, err := os.Stat(runnerPath); err != nil {
			return false, 0
		}
		command := exec.Command(runnerPath)
		command.Dir = projectRoot
		command.Env = env
		command.Stdout = os.Stdout
		command.Stderr = os.Stderr
		if err := command.Run(); err != nil {
			fmt.Fprintf(os.Stderr, "failed to execute scrapy project artifact: %v\n", err)
			return true, 1
		}
		return true, 0
	}

	if subcommand == "list" {
		if strings.TrimSpace(*project) == "" {
			fmt.Fprintln(os.Stderr, "scrapy list requires --project")
			return 2
		}
		manifest, err := readManifest(*project)
		if err != nil {
			fmt.Fprintf(os.Stderr, "failed to read scrapy project manifest: %v\n", err)
			return 2
		}
		projectCfg := defaultContractConfig()
		projectCfgPath := filepath.Join(*project, "spider-framework.yaml")
		if loadedCfg, err := loadContractConfig(projectCfgPath); err == nil {
			projectCfg = loadedCfg
		}
		spiders := resolveSpiderDisplayMetadata(*project, manifest)
		spiderPayloads := make([]map[string]any, 0, len(spiders))
		for _, spider := range spiders {
			entry := map[string]any{}
			for key, value := range spider {
				entry[key] = value
			}
			entry["pipelines"] = configuredScrapyPipelinesForSpider(projectCfg, spider["name"])
			entry["spider_middlewares"] = configuredScrapySpiderMiddlewaresForSpider(projectCfg, spider["name"])
			entry["downloader_middlewares"] = configuredScrapyDownloaderMiddlewaresForSpider(projectCfg, spider["name"])
			spiderPayloads = append(spiderPayloads, entry)
		}
		payload := map[string]any{
			"command":                "scrapy list",
			"runtime":                "go",
			"project":                *project,
			"spiders":                spiderPayloads,
			"pipelines":              configuredScrapyPipelinesForSpider(projectCfg, ""),
			"spider_middlewares":     configuredScrapySpiderMiddlewaresForSpider(projectCfg, ""),
			"downloader_middlewares": configuredScrapyDownloaderMiddlewaresForSpider(projectCfg, ""),
		}
		if plugins := discoverPlugins(*project); len(plugins) > 0 {
			payload["plugins"] = plugins
		}
		encoded, _ := json.MarshalIndent(payload, "", "  ")
		fmt.Println(string(encoded))
		return 0
	}

	if subcommand == "shell" {
		html := ""
		source := ""
		switch {
		case strings.TrimSpace(*htmlFile) != "":
			data, err := os.ReadFile(*htmlFile)
			if err != nil {
				fmt.Fprintf(os.Stderr, "failed to read html file: %v\n", err)
				return 1
			}
			html = string(data)
			source = *htmlFile
		case strings.TrimSpace(*targetURL) != "":
			resp, err := http.Get(*targetURL)
			if err != nil {
				fmt.Fprintf(os.Stderr, "failed to fetch url: %v\n", err)
				return 1
			}
			defer resp.Body.Close()
			body, err := io.ReadAll(io.LimitReader(resp.Body, 1<<20))
			if err != nil {
				fmt.Fprintf(os.Stderr, "failed to read response body: %v\n", err)
				return 1
			}
			html = string(body)
			source = *targetURL
		default:
			fmt.Fprintln(os.Stderr, "scrapy shell requires --url or --html-file")
			return 2
		}
		p := parser.NewHTMLParser(html)
		if p == nil {
			fmt.Fprintln(os.Stderr, "failed to initialize html parser")
			return 1
		}
		values := []string{}
		switch strings.ToLower(strings.TrimSpace(*mode)) {
		case "css":
			values = p.CSS(*expr)
		case "css_attr":
			values = p.CSSAttr(*expr, *attr)
		case "xpath":
			if result, err := p.XPathFirstStrict(*expr); err == nil && strings.TrimSpace(result) != "" {
				values = []string{result}
			}
		case "regex":
			if compiled := parser.MustCompileRegex(*expr); compiled != nil {
				matches := compiled.FindAllStringSubmatch(html, -1)
				for _, match := range matches {
					if len(match) > 1 {
						values = append(values, match[1])
					} else if len(match) > 0 {
						values = append(values, match[0])
					}
				}
			}
		}
		payload := map[string]any{
			"command": "scrapy shell",
			"runtime": "go",
			"source":  source,
			"type":    *mode,
			"expr":    *expr,
			"attr":    *attr,
			"count":   len(values),
			"values":  values,
		}
		encoded, _ := json.MarshalIndent(payload, "", "  ")
		fmt.Println(string(encoded))
		return 0
	}

	if subcommand == "profile" {
		source := ""
		html := ""
		profileRunner := "http"
		profileRunnerSource := "default"
		profileURLSource := "default"
		if strings.TrimSpace(*project) != "" {
			manifest, err := readManifest(*project)
			if err != nil {
				fmt.Fprintf(os.Stderr, "failed to read scrapy project manifest: %v\n", err)
				return 2
			}
			projectCfgPath := filepath.Join(*project, "spider-framework.yaml")
			projectCfg := defaultContractConfig()
			if loadedCfg, err := loadContractConfig(projectCfgPath); err == nil {
				projectCfg = loadedCfg
			}
			spiders := resolveSpiderDisplayMetadata(*project, manifest)
			if strings.TrimSpace(*selectedSpider) != "" {
				matches := []map[string]string{}
				for _, spider := range spiders {
					if spider["name"] == *selectedSpider {
						matches = append(matches, spider)
					}
				}
				if len(matches) == 0 {
					fmt.Fprintf(os.Stderr, "unknown spider in %s: %s\n", *project, *selectedSpider)
					return 2
				}
				*targetURL = matches[0]["url"]
				profileRunner = matches[0]["runner"]
				profileRunnerSource = matches[0]["runner_source"]
				profileURLSource = matches[0]["url_source"]
			} else {
				*targetURL, profileURLSource = resolveScrapyURLDetail(projectCfg, "", map[string]string{}, manifest["url"])
				profileRunner, profileRunnerSource = resolveScrapyRunnerDetail(projectCfg, "", map[string]string{})
			}
		}
		switch {
		case strings.TrimSpace(*htmlFile) != "":
			data, err := os.ReadFile(*htmlFile)
			if err != nil {
				fmt.Fprintf(os.Stderr, "failed to read html file: %v\n", err)
				return 1
			}
			html = string(data)
			source = *htmlFile
		case strings.TrimSpace(*targetURL) != "":
			resp, err := http.Get(*targetURL)
			if err != nil {
				fmt.Fprintf(os.Stderr, "failed to fetch url: %v\n", err)
				return 1
			}
			defer resp.Body.Close()
			body, err := io.ReadAll(io.LimitReader(resp.Body, 1<<20))
			if err != nil {
				fmt.Fprintf(os.Stderr, "failed to read response body: %v\n", err)
				return 1
			}
			html = string(body)
			source = *targetURL
		default:
			fmt.Fprintln(os.Stderr, "scrapy profile requires --project, --url, or --html-file")
			return 2
		}
		p := parser.NewHTMLParser(html)
		if p == nil {
			fmt.Fprintln(os.Stderr, "failed to initialize html parser")
			return 1
		}
		payload := map[string]any{
			"command":         "scrapy profile",
			"runtime":         "go",
			"project":         *project,
			"spider":          *selectedSpider,
			"source":          source,
			"resolved_runner": profileRunner,
			"runner_source":   map[bool]string{true: "html-fixture", false: profileRunnerSource}[strings.TrimSpace(*htmlFile) != ""],
			"resolved_url":    *targetURL,
			"url_source":      map[bool]string{true: "html-fixture", false: profileURLSource}[strings.TrimSpace(*htmlFile) != ""],
			"title":           p.Title(),
			"link_count":      len(p.Links()),
			"image_count":     len(p.Images()),
			"text_length":     len(p.Text()),
			"html_length":     len(html),
		}
		encoded, _ := json.MarshalIndent(payload, "", "  ")
		fmt.Println(string(encoded))
		return 0
	}

	if subcommand == "plan-ai" || subcommand == "sync-ai" {
		if subcommand == "sync-ai" && strings.TrimSpace(*project) == "" {
			fmt.Fprintln(os.Stderr, "scrapy sync-ai requires --project")
			return 2
		}
		source := ""
		html := ""
		resolvedURL := ""
		if strings.TrimSpace(*project) != "" {
			manifest, err := readManifest(*project)
			if err != nil {
				fmt.Fprintf(os.Stderr, "failed to read scrapy project manifest: %v\n", err)
				return 2
			}
			projectCfgPath := filepath.Join(*project, "spider-framework.yaml")
			projectCfg := defaultContractConfig()
			if loadedCfg, err := loadContractConfig(projectCfgPath); err == nil {
				projectCfg = loadedCfg
			}
			spiders := resolveSpiderDisplayMetadata(*project, manifest)
			if strings.TrimSpace(*selectedSpider) != "" {
				matches := []map[string]string{}
				for _, spider := range spiders {
					if spider["name"] == *selectedSpider {
						matches = append(matches, spider)
					}
				}
				if len(matches) == 0 {
					fmt.Fprintf(os.Stderr, "unknown spider in %s: %s\n", *project, *selectedSpider)
					return 2
				}
				*targetURL = matches[0]["url"]
			} else {
				*targetURL, _ = resolveScrapyURLDetail(projectCfg, "", map[string]string{}, manifest["url"])
			}
		}
		switch {
		case strings.TrimSpace(*htmlFile) != "":
			data, err := os.ReadFile(*htmlFile)
			if err != nil {
				fmt.Fprintf(os.Stderr, "failed to read html file: %v\n", err)
				return 1
			}
			html = string(data)
			source = *htmlFile
			if strings.TrimSpace(*targetURL) != "" {
				resolvedURL = *targetURL
			} else {
				resolvedURL = "file://" + filepath.ToSlash(*htmlFile)
			}
		case strings.TrimSpace(*targetURL) != "":
			resp, err := http.Get(*targetURL)
			if err != nil {
				fmt.Fprintf(os.Stderr, "failed to fetch url: %v\n", err)
				return 1
			}
			defer resp.Body.Close()
			body, err := io.ReadAll(io.LimitReader(resp.Body, 1<<20))
			if err != nil {
				fmt.Fprintf(os.Stderr, "failed to read response body: %v\n", err)
				return 1
			}
			html = string(body)
			source = *targetURL
			resolvedURL = *targetURL
		default:
			fmt.Fprintf(os.Stderr, "scrapy %s requires --project, --url, or --html-file\n", subcommand)
			return 2
		}

		profile := buildSiteProfile(resolvedURL, html)
		candidateFields := []string{}
		if rawFields, ok := profile["candidate_fields"].([]string); ok {
			candidateFields = rawFields
		} else if rawFields, ok := profile["candidate_fields"].([]any); ok {
			for _, item := range rawFields {
				candidateFields = append(candidateFields, fmt.Sprint(item))
			}
		}
		spiderPlanName := strings.TrimSpace(*spiderName)
		if spiderPlanName == "" {
			spiderPlanName = "ai_spider"
		}
		schema := aiSchemaFromCandidateFields(candidateFields)
		blueprint := buildAIBlueprint(resolvedURL, spiderPlanName, profile, schema, html)
		writtenFiles := []string{}
		payload := map[string]any{
			"command":             "scrapy " + subcommand,
			"runtime":             "go",
			"project":             *project,
			"spider":              *selectedSpider,
			"spider_name":         spiderPlanName,
			"source":              source,
			"resolved_url":        resolvedURL,
			"recommended_runtime": profile["recommended_runtime"],
			"page_profile":        profile,
			"schema":              schema,
			"blueprint":           blueprint,
			"suggested_commands": []string{
				fmt.Sprintf("gospider scrapy genspider --name %s --domain %s --project %s --ai", spiderPlanName, deriveDomainFromURL(resolvedURL), map[bool]string{true: ".", false: *project}[strings.TrimSpace(*project) == ""]),
				fmt.Sprintf("gospider ai --url %s --instructions %q --schema-file ai-schema.json", resolvedURL, "提取核心字段"),
			},
			"written_files": writtenFiles,
		}
		if strings.TrimSpace(*project) != "" {
			schemaPath := filepath.Join(*project, "ai-schema.json")
			blueprintPath := filepath.Join(*project, "ai-blueprint.json")
			promptPath := filepath.Join(*project, "ai-extract-prompt.txt")
			authPath := filepath.Join(*project, "ai-auth.json")
			planPath := filepath.Join(*project, "ai-plan.json")
			if trimmed := strings.TrimSpace(*output); trimmed != "" && trimmed != "artifacts/exports/gospider-scrapy-demo.json" {
				planPath = *output
			}
			schemaBytes, _ := json.MarshalIndent(schema, "", "  ")
			blueprintBytes, _ := json.MarshalIndent(blueprint, "", "  ")
			if err := os.WriteFile(schemaPath, append(schemaBytes, '\n'), 0644); err == nil {
				writtenFiles = append(writtenFiles, schemaPath)
			}
			if err := os.WriteFile(blueprintPath, append(blueprintBytes, '\n'), 0644); err == nil {
				writtenFiles = append(writtenFiles, blueprintPath)
			}
			if err := os.WriteFile(promptPath, []byte(fmt.Sprint(blueprint["extraction_prompt"])+"\n"), 0644); err == nil {
				writtenFiles = append(writtenFiles, promptPath)
			}
			authBytes, _ := json.MarshalIndent(map[string]any{
				"headers":            map[string]string{},
				"cookies":            map[string]string{},
				"storage_state_file": "",
				"cookies_file":       "",
				"session":            "auth",
				"actions":            []map[string]any{},
				"action_examples":    defaultAuthActionExamples(),
				"notes":              "Fill session headers/cookies here when authentication is required.",
			}, "", "  ")
			if err := os.WriteFile(authPath, append(authBytes, '\n'), 0644); err == nil {
				writtenFiles = append(writtenFiles, authPath)
			}
			writtenFiles = append(writtenFiles, planPath)
			payload["written_files"] = writtenFiles
			planBytes, _ := json.MarshalIndent(payload, "", "  ")
			if err := os.WriteFile(planPath, append(planBytes, '\n'), 0644); err == nil {
				// already included for deterministic payload
			}
		} else if strings.TrimSpace(*output) != "" {
			writtenFiles = append(writtenFiles, *output)
			payload["written_files"] = writtenFiles
			planBytes, _ := json.MarshalIndent(payload, "", "  ")
			if err := os.MkdirAll(filepath.Dir(*output), 0755); err == nil {
				if err := os.WriteFile(*output, append(planBytes, '\n'), 0644); err == nil {
					// already included for deterministic payload
				}
			}
		}
		if subcommand == "sync-ai" && strings.TrimSpace(*project) != "" {
			jobPath := filepath.Join(*project, "ai-job.json")
			jobPayload := map[string]any{
				"name":    spiderPlanName + "-ai-job",
				"runtime": "ai",
				"target":  map[string]any{"url": resolvedURL},
				"extract": []map[string]any{},
				"output": map[string]any{
					"format": "json",
					"path":   "artifacts/exports/ai-job-output.json",
				},
				"metadata": map[string]any{
					"schema_file": "ai-schema.json",
				},
			}
			if props, ok := schema["properties"].(map[string]any); ok {
				extract := []map[string]any{}
				for field := range props {
					extract = append(extract, map[string]any{"field": field, "type": "ai"})
				}
				jobPayload["extract"] = extract
			}
			jobBytes, _ := json.MarshalIndent(jobPayload, "", "  ")
			if err := os.WriteFile(jobPath, append(jobBytes, '\n'), 0644); err == nil {
				payload["written_files"] = append(payload["written_files"].([]string), jobPath)
			}
		}
		encoded, _ := json.MarshalIndent(payload, "", "  ")
		fmt.Println(string(encoded))
		return 0
	}

	if subcommand == "auth-validate" {
		if strings.TrimSpace(*project) == "" {
			fmt.Fprintln(os.Stderr, "scrapy auth-validate requires --project")
			return 2
		}
		manifest, err := readManifest(*project)
		if err != nil {
			fmt.Fprintf(os.Stderr, "failed to read scrapy project manifest: %v\n", err)
			return 2
		}
		projectCfgPath := filepath.Join(*project, "spider-framework.yaml")
		projectCfg := defaultContractConfig()
		if loadedCfg, err := loadContractConfig(projectCfgPath); err == nil {
			projectCfg = loadedCfg
		}
		if strings.TrimSpace(*selectedSpider) != "" {
			spiders := resolveSpiderDisplayMetadata(*project, manifest)
			found := false
			for _, spider := range spiders {
				if spider["name"] == *selectedSpider {
					*targetURL = spider["url"]
					found = true
					break
				}
			}
			if !found {
				fmt.Fprintf(os.Stderr, "unknown spider in %s: %s\n", *project, *selectedSpider)
				return 2
			}
		} else if strings.TrimSpace(*targetURL) == "" {
			*targetURL, _ = resolveScrapyURLDetail(projectCfg, "", map[string]string{}, manifest["url"])
		}

		assets := projectruntime.LoadAIProjectAssets(*project)
		source := ""
		html := ""
		resolvedURL := ""
		runnerUsed := "fixture"
		switch {
		case strings.TrimSpace(*htmlFile) != "":
			data, err := os.ReadFile(*htmlFile)
			if err != nil {
				fmt.Fprintf(os.Stderr, "failed to read html file: %v\n", err)
				return 1
			}
			html = string(data)
			source = *htmlFile
			if strings.TrimSpace(*targetURL) != "" {
				resolvedURL = *targetURL
			} else {
				resolvedURL = "file://" + filepath.ToSlash(*htmlFile)
			}
		case strings.TrimSpace(*targetURL) != "":
			resolvedURL = *targetURL
			source = *targetURL
			runnerUsed = map[bool]string{true: "browser", false: "http"}[assets.RecommendedRunner == "browser"]
			if assets.RecommendedRunner == "browser" {
				cfgCopy := projectCfg
				cfgCopy.Browser.StorageStateFile = assets.StorageStateFile
				cfgCopy.Browser.CookiesFile = assets.CookiesFile
				result, err := browserFetchRunnerFactory().Fetch(*targetURL, cfgCopy.Browser.ScreenshotPath, cfgCopy.Browser.HTMLPath, cfgCopy)
				if err != nil {
					fmt.Fprintf(os.Stderr, "browser auth validate failed: %v\n", err)
					return 1
				}
				body, err := os.ReadFile(result.HTMLPath)
				if err != nil {
					fmt.Fprintf(os.Stderr, "failed to read browser html output: %v\n", err)
					return 1
				}
				html = string(body)
				if strings.TrimSpace(result.URL) != "" {
					resolvedURL = result.URL
				}
			} else {
				resp, err := http.Get(*targetURL)
				if err != nil {
					fmt.Fprintf(os.Stderr, "failed to fetch url: %v\n", err)
					return 1
				}
				defer resp.Body.Close()
				body, err := io.ReadAll(io.LimitReader(resp.Body, 1<<20))
				if err != nil {
					fmt.Fprintf(os.Stderr, "failed to read response body: %v\n", err)
					return 1
				}
				html = string(body)
			}
		default:
			fmt.Fprintln(os.Stderr, "scrapy auth-validate requires --project plus --url, manifest url, or --html-file")
			return 2
		}

		authenticated, indicators := authValidationStatus(html)
		payload := map[string]any{
			"command":                 "scrapy auth-validate",
			"runtime":                 "go",
			"project":                 *project,
			"spider":                  *selectedSpider,
			"source":                  source,
			"resolved_url":            resolvedURL,
			"authentication_required": assets.AuthRequired,
			"recommended_runner":      assets.RecommendedRunner,
			"runner_used":             runnerUsed,
			"authenticated":           authenticated,
			"indicators":              indicators,
			"auth_assets": map[string]any{
				"has_headers":        len(assets.RequestHeaders) > 0,
				"storage_state_file": assets.StorageStateFile,
				"cookies_file":       assets.CookiesFile,
			},
		}
		encoded, _ := json.MarshalIndent(payload, "", "  ")
		fmt.Println(string(encoded))
		return 0
	}

	if subcommand == "auth-capture" {
		if strings.TrimSpace(*project) == "" {
			fmt.Fprintln(os.Stderr, "scrapy auth-capture requires --project")
			return 2
		}
		manifest, err := readManifest(*project)
		if err != nil {
			fmt.Fprintf(os.Stderr, "failed to read scrapy project manifest: %v\n", err)
			return 2
		}
		projectCfgPath := filepath.Join(*project, "spider-framework.yaml")
		projectCfg := defaultContractConfig()
		if loadedCfg, err := loadContractConfig(projectCfgPath); err == nil {
			projectCfg = loadedCfg
		}
		if strings.TrimSpace(*selectedSpider) != "" {
			spiders := resolveSpiderDisplayMetadata(*project, manifest)
			found := false
			for _, spider := range spiders {
				if spider["name"] == *selectedSpider {
					*targetURL = spider["url"]
					found = true
					break
				}
			}
			if !found {
				fmt.Fprintf(os.Stderr, "unknown spider in %s: %s\n", *project, *selectedSpider)
				return 2
			}
		} else if strings.TrimSpace(*targetURL) == "" {
			*targetURL, _ = resolveScrapyURLDetail(projectCfg, "", map[string]string{}, manifest["url"])
		}
		if strings.TrimSpace(*htmlFile) != "" && strings.TrimSpace(*targetURL) == "" {
			*targetURL = "file://" + filepath.ToSlash(*htmlFile)
		}
		if strings.TrimSpace(*targetURL) == "" {
			fmt.Fprintln(os.Stderr, "scrapy auth-capture requires --project plus --url, manifest url, or --html-file")
			return 2
		}

		authDir := filepath.Join(*project, "artifacts", "auth")
		if err := os.MkdirAll(authDir, 0755); err != nil {
			fmt.Fprintf(os.Stderr, "failed to create auth dir: %v\n", err)
			return 1
		}
		statePath := filepath.Join(authDir, *sessionName+"-state.json")
		cookiesPath := filepath.Join(authDir, *sessionName+"-cookies.json")
		authPath := filepath.Join(*project, "ai-auth.json")
		projectCfg.Browser.StorageStateFile = statePath
		projectCfg.Browser.CookiesFile = cookiesPath
		projectCfg.Browser.AuthFile = authPath

		result, err := browserFetchRunnerFactory().Fetch(*targetURL, projectCfg.Browser.ScreenshotPath, projectCfg.Browser.HTMLPath, projectCfg)
		if err != nil {
			fmt.Fprintf(os.Stderr, "auth capture failed: %v\n", err)
			return 1
		}

		authPayload := map[string]any{}
		if data, err := os.ReadFile(authPath); err == nil {
			_ = json.Unmarshal(data, &authPayload)
		}
		authPayload["headers"] = map[string]string{}
		authPayload["cookies"] = map[string]string{}
		authPayload["storage_state_file"] = filepath.ToSlash(filepath.Join("artifacts", "auth", *sessionName+"-state.json"))
		authPayload["cookies_file"] = filepath.ToSlash(filepath.Join("artifacts", "auth", *sessionName+"-cookies.json"))
		authPayload["session"] = *sessionName
		if _, ok := authPayload["actions"]; !ok {
			authPayload["actions"] = []map[string]any{}
		}
		if _, ok := authPayload["action_examples"]; !ok {
			authPayload["action_examples"] = defaultAuthActionExamples()
		}
		if _, ok := authPayload["node_reverse_base_url"]; !ok {
			authPayload["node_reverse_base_url"] = "http://localhost:3000"
		}
		if _, ok := authPayload["capture_reverse_profile"]; !ok {
			authPayload["capture_reverse_profile"] = false
		}
		if authPayload["capture_reverse_profile"] == true {
			if baseURL, ok := authPayload["node_reverse_base_url"].(string); ok && strings.TrimSpace(baseURL) != "" {
				htmlSourcePath := result.HTMLPath
				if strings.TrimSpace(htmlSourcePath) == "" {
					htmlSourcePath = projectCfg.Browser.HTMLPath
				}
				if summary := projectruntime.CollectReverseSummary(baseURL, *targetURL, htmlSourcePath); summary != nil {
					authPayload["reverse_runtime"] = summary
				}
			}
		}
		authPayload["notes"] = "Fill session headers/cookies here when authentication is required."
		authBytes, _ := json.MarshalIndent(authPayload, "", "  ")
		if err := os.WriteFile(authPath, append(authBytes, '\n'), 0644); err != nil {
			fmt.Fprintf(os.Stderr, "failed to write ai-auth.json: %v\n", err)
			return 1
		}

		payload := map[string]any{
			"command":      "scrapy auth-capture",
			"runtime":      "go",
			"project":      *project,
			"spider":       *selectedSpider,
			"session":      *sessionName,
			"resolved_url": map[bool]string{true: *targetURL, false: result.URL}[strings.TrimSpace(result.URL) == ""],
			"written_files": []string{
				authPath,
				statePath,
				cookiesPath,
			},
		}
		encoded, _ := json.MarshalIndent(payload, "", "  ")
		fmt.Println(string(encoded))
		return 0
	}

	if subcommand == "scaffold-ai" {
		if strings.TrimSpace(*project) == "" {
			fmt.Fprintln(os.Stderr, "scrapy scaffold-ai requires --project")
			return 2
		}
		manifest, err := readManifest(*project)
		if err != nil {
			fmt.Fprintf(os.Stderr, "failed to read scrapy project manifest: %v\n", err)
			return 2
		}
		projectCfgPath := filepath.Join(*project, "spider-framework.yaml")
		projectCfg := defaultContractConfig()
		if loadedCfg, err := loadContractConfig(projectCfgPath); err == nil {
			projectCfg = loadedCfg
		}
		if strings.TrimSpace(*selectedSpider) != "" {
			spiders := resolveSpiderDisplayMetadata(*project, manifest)
			found := false
			for _, spider := range spiders {
				if spider["name"] == *selectedSpider {
					*targetURL = spider["url"]
					found = true
					break
				}
			}
			if !found {
				fmt.Fprintf(os.Stderr, "unknown spider in %s: %s\n", *project, *selectedSpider)
				return 2
			}
		} else if strings.TrimSpace(*targetURL) == "" {
			*targetURL, _ = resolveScrapyURLDetail(projectCfg, "", map[string]string{}, manifest["url"])
		}

		source := ""
		html := ""
		resolvedURL := ""
		switch {
		case strings.TrimSpace(*htmlFile) != "":
			data, err := os.ReadFile(*htmlFile)
			if err != nil {
				fmt.Fprintf(os.Stderr, "failed to read html file: %v\n", err)
				return 1
			}
			html = string(data)
			source = *htmlFile
			if strings.TrimSpace(*targetURL) != "" {
				resolvedURL = *targetURL
			} else {
				resolvedURL = "file://" + filepath.ToSlash(*htmlFile)
			}
		case strings.TrimSpace(*targetURL) != "":
			resp, err := http.Get(*targetURL)
			if err != nil {
				fmt.Fprintf(os.Stderr, "failed to fetch url: %v\n", err)
				return 1
			}
			defer resp.Body.Close()
			body, err := io.ReadAll(io.LimitReader(resp.Body, 1<<20))
			if err != nil {
				fmt.Fprintf(os.Stderr, "failed to read response body: %v\n", err)
				return 1
			}
			html = string(body)
			source = *targetURL
			resolvedURL = *targetURL
		default:
			fmt.Fprintln(os.Stderr, "scrapy scaffold-ai requires --project plus --url, manifest url, or --html-file")
			return 2
		}

		profile := buildSiteProfile(resolvedURL, html)
		candidateFields := []string{}
		if rawFields, ok := profile["candidate_fields"].([]string); ok {
			candidateFields = rawFields
		} else if rawFields, ok := profile["candidate_fields"].([]any); ok {
			for _, item := range rawFields {
				candidateFields = append(candidateFields, fmt.Sprint(item))
			}
		}
		schema := aiSchemaFromCandidateFields(candidateFields)
		spiderPlanName := strings.TrimSpace(*spiderName)
		if spiderPlanName == "" {
			spiderPlanName = "ai_spider"
		}
		blueprint := buildAIBlueprint(resolvedURL, spiderPlanName, profile, schema, html)
		domain := deriveDomainFromURL(resolvedURL)
		spidersDir := filepath.Join(*project, "spiders")
		if err := os.MkdirAll(spidersDir, 0755); err != nil {
			fmt.Fprintf(os.Stderr, "failed to create spiders dir: %v\n", err)
			return 1
		}
		spiderPath := filepath.Join(spidersDir, spiderPlanName+".go")
		if err := os.WriteFile(spiderPath, []byte(renderGoAISpiderTemplate(spiderPlanName, domain)), 0644); err != nil {
			fmt.Fprintf(os.Stderr, "failed to write ai spider template: %v\n", err)
			return 1
		}
		schemaPath := filepath.Join(*project, "ai-schema.json")
		blueprintPath := filepath.Join(*project, "ai-blueprint.json")
		promptPath := filepath.Join(*project, "ai-extract-prompt.txt")
		authPath := filepath.Join(*project, "ai-auth.json")
		schemaBytes, _ := json.MarshalIndent(schema, "", "  ")
		if err := os.WriteFile(schemaPath, append(schemaBytes, '\n'), 0644); err != nil {
			fmt.Fprintf(os.Stderr, "failed to write ai schema: %v\n", err)
			return 1
		}
		blueprintBytes, _ := json.MarshalIndent(blueprint, "", "  ")
		if err := os.WriteFile(blueprintPath, append(blueprintBytes, '\n'), 0644); err != nil {
			fmt.Fprintf(os.Stderr, "failed to write ai blueprint: %v\n", err)
			return 1
		}
		if err := os.WriteFile(promptPath, []byte(fmt.Sprint(blueprint["extraction_prompt"])+"\n"), 0644); err != nil {
			fmt.Fprintf(os.Stderr, "failed to write ai prompt: %v\n", err)
			return 1
		}
		authBytes, _ := json.MarshalIndent(map[string]any{
			"headers":                 map[string]string{},
			"cookies":                 map[string]string{},
			"storage_state_file":      "",
			"cookies_file":            "",
			"session":                 "auth",
			"actions":                 []map[string]any{},
			"action_examples":         defaultAuthActionExamples(),
			"node_reverse_base_url":   "http://localhost:3000",
			"capture_reverse_profile": false,
			"notes":                   "Fill session headers/cookies here when authentication is required.",
		}, "", "  ")
		if err := os.WriteFile(authPath, append(authBytes, '\n'), 0644); err != nil {
			fmt.Fprintf(os.Stderr, "failed to write ai auth skeleton: %v\n", err)
			return 1
		}
		planPath := filepath.Join(*project, "ai-plan.json")
		if trimmed := strings.TrimSpace(*output); trimmed != "" && trimmed != "artifacts/exports/gospider-scrapy-demo.json" {
			planPath = *output
		}
		payload := map[string]any{
			"command":             "scrapy scaffold-ai",
			"runtime":             "go",
			"project":             *project,
			"spider":              *selectedSpider,
			"spider_name":         spiderPlanName,
			"source":              source,
			"resolved_url":        resolvedURL,
			"recommended_runtime": profile["recommended_runtime"],
			"page_profile":        profile,
			"schema":              schema,
			"blueprint":           blueprint,
			"written_files":       []string{schemaPath, blueprintPath, promptPath, authPath, planPath, spiderPath},
			"suggested_commands": []string{
				fmt.Sprintf("gospider scrapy run --project %s --spider %s", *project, spiderPlanName),
				fmt.Sprintf("gospider ai --url %s --instructions %q --schema-file ai-schema.json", resolvedURL, "提取核心字段"),
			},
		}
		planBytes, _ := json.MarshalIndent(payload, "", "  ")
		if err := os.MkdirAll(filepath.Dir(planPath), 0755); err == nil {
			_ = os.WriteFile(planPath, append(planBytes, '\n'), 0644)
		}
		encoded, _ := json.MarshalIndent(payload, "", "  ")
		fmt.Println(string(encoded))
		return 0
	}

	if subcommand == "doctor" {
		if strings.TrimSpace(*project) == "" {
			fmt.Fprintln(os.Stderr, "scrapy doctor requires --project")
			return 2
		}
		checks := []map[string]string{}
		projectCfg := defaultContractConfig()
		configPath := filepath.Join(*project, "spider-framework.yaml")
		configStatus := "warning"
		if _, err := os.Stat(configPath); err == nil {
			configStatus = "passed"
			if loadedCfg, cfgErr := loadContractConfig(configPath); cfgErr == nil {
				projectCfg = loadedCfg
			}
		}
		manifestPath := filepath.Join(*project, "scrapy-project.json")
		if _, err := os.Stat(manifestPath); err != nil {
			checks = append(checks, map[string]string{"name": "manifest", "status": "failed", "details": manifestPath})
		} else {
			checks = append(checks, map[string]string{"name": "manifest", "status": "passed", "details": manifestPath})
			manifest, err := readManifest(*project)
			if err != nil {
				checks = append(checks, map[string]string{"name": "runtime", "status": "failed", "details": err.Error()})
			} else {
				checks = append(checks, map[string]string{"name": "runtime", "status": "passed", "details": "go"})
				runnerPath := "project runner artifact not configured; built-in metadata runner will be used"
				runnerStatus := "warning"
				if runner := strings.TrimSpace(manifest["runner"]); runner != "" {
					runnerPath = filepath.Join(*project, filepath.FromSlash(runner))
					if _, err := os.Stat(runnerPath); err == nil {
						runnerStatus = "passed"
					}
				}
				checks = append(checks, map[string]string{"name": "runner_artifact", "status": runnerStatus, "details": runnerPath})
				spiders := resolveSpiderDisplayMetadata(*project, manifest)
				if len(spiders) == 0 {
					checks = append(checks, map[string]string{"name": "spider_loader", "status": "warning", "details": "no spider files discovered"})
				} else {
					checks = append(checks, map[string]string{"name": "spider_loader", "status": "passed", "details": fmt.Sprintf("%d spiders discovered", len(spiders))})
					for _, spider := range spiders {
						checks = append(checks, map[string]string{"name": "spider:" + spider["name"], "status": "passed", "details": spider["path"] + " runner=" + spider["runner"] + " runner_source=" + spider["runner_source"] + " url=" + spider["url"] + " url_source=" + spider["url_source"] + " " + spiderComponentSummary(projectCfg, spider["name"])})
					}
				}
			}
		}
		checks = append(checks, map[string]string{"name": "config", "status": configStatus, "details": configPath})
		appendGoDeclarativeComponentChecks(&checks, projectCfg)
		pluginManifestPath := filepath.Join(*project, "scrapy-plugins.json")
		pluginManifestStatus := "warning"
		pluginManifestDetails := pluginManifestPath
		if _, err := os.Stat(pluginManifestPath); err == nil {
			if err := validateScrapyPluginManifest(pluginManifestPath); err != nil {
				pluginManifestStatus = "failed"
				pluginManifestDetails = err.Error()
			} else {
				pluginManifestStatus = "passed"
			}
		}
		checks = append(checks, map[string]string{"name": "plugin_manifest", "status": pluginManifestStatus, "details": pluginManifestDetails})
		exportsDir := filepath.Join(*project, "artifacts", "exports")
		exportStatus := "warning"
		if info, err := os.Stat(exportsDir); err == nil && info.IsDir() {
			exportStatus = "passed"
		}
		checks = append(checks, map[string]string{"name": "exports_dir", "status": exportStatus, "details": exportsDir})
		summary := "passed"
		for _, check := range checks {
			if check["status"] == "failed" {
				summary = "failed"
				break
			}
			if check["status"] == "warning" {
				summary = "warning"
			}
		}
		payload := map[string]any{"command": "scrapy doctor", "runtime": "go", "project": *project, "summary": summary, "checks": checks}
		encoded, _ := json.MarshalIndent(payload, "", "  ")
		fmt.Println(string(encoded))
		if summary == "failed" {
			return 1
		}
		return 0
	}

	if subcommand == "bench" {
		source := ""
		html := ""
		var fetchMS float64
		benchRunner := "http"
		benchRunnerSource := "default"
		benchURLSource := "default"
		if strings.TrimSpace(*project) != "" {
			manifest, err := readManifest(*project)
			if err != nil {
				fmt.Fprintf(os.Stderr, "failed to read scrapy project manifest: %v\n", err)
				return 2
			}
			projectCfgPath := filepath.Join(*project, "spider-framework.yaml")
			projectCfg := defaultContractConfig()
			if loadedCfg, err := loadContractConfig(projectCfgPath); err == nil {
				projectCfg = loadedCfg
			}
			spiders := resolveSpiderDisplayMetadata(*project, manifest)
			if strings.TrimSpace(*selectedSpider) != "" {
				matches := []map[string]string{}
				for _, spider := range spiders {
					if spider["name"] == *selectedSpider {
						matches = append(matches, spider)
					}
				}
				if len(matches) == 0 {
					fmt.Fprintf(os.Stderr, "unknown spider in %s: %s\n", *project, *selectedSpider)
					return 2
				}
				*targetURL = matches[0]["url"]
				benchRunner = matches[0]["runner"]
				benchRunnerSource = matches[0]["runner_source"]
				benchURLSource = matches[0]["url_source"]
			} else {
				*targetURL, benchURLSource = resolveScrapyURLDetail(projectCfg, "", map[string]string{}, manifest["url"])
				benchRunner, benchRunnerSource = resolveScrapyRunnerDetail(projectCfg, "", map[string]string{})
			}
		}
		switch {
		case strings.TrimSpace(*htmlFile) != "":
			data, err := os.ReadFile(*htmlFile)
			if err != nil {
				fmt.Fprintf(os.Stderr, "failed to read html file: %v\n", err)
				return 1
			}
			html = string(data)
			source = *htmlFile
		case strings.TrimSpace(*targetURL) != "":
			startFetch := time.Now()
			resp, err := http.Get(*targetURL)
			if err != nil {
				fmt.Fprintf(os.Stderr, "failed to fetch url: %v\n", err)
				return 1
			}
			defer resp.Body.Close()
			body, err := io.ReadAll(io.LimitReader(resp.Body, 1<<20))
			if err != nil {
				fmt.Fprintf(os.Stderr, "failed to read response body: %v\n", err)
				return 1
			}
			fetchMS = float64(time.Since(startFetch).Microseconds()) / 1000.0
			html = string(body)
			source = *targetURL
		default:
			fmt.Fprintln(os.Stderr, "scrapy bench requires --project, --url, or --html-file")
			return 2
		}
		started := time.Now()
		p := parser.NewHTMLParser(html)
		if p == nil {
			fmt.Fprintln(os.Stderr, "failed to initialize html parser")
			return 1
		}
		payload := map[string]any{
			"command":         "scrapy bench",
			"runtime":         "go",
			"project":         *project,
			"spider":          *selectedSpider,
			"source":          source,
			"resolved_runner": benchRunner,
			"runner_source":   map[bool]string{true: "html-fixture", false: benchRunnerSource}[strings.TrimSpace(*htmlFile) != ""],
			"resolved_url":    *targetURL,
			"url_source":      map[bool]string{true: "html-fixture", false: benchURLSource}[strings.TrimSpace(*htmlFile) != ""],
			"elapsed_ms":      float64(time.Since(started).Microseconds()) / 1000.0,
			"fetch_ms":        fetchMS,
			"title":           p.Title(),
			"link_count":      len(p.Links()),
			"image_count":     len(p.Images()),
			"text_length":     len(p.Text()),
			"html_length":     len(html),
		}
		encoded, _ := json.MarshalIndent(payload, "", "  ")
		fmt.Println(string(encoded))
		return 0
	}

	if subcommand == "export" {
		if strings.TrimSpace(*project) == "" {
			fmt.Fprintln(os.Stderr, "scrapy export requires --project")
			return 2
		}
		manifest, err := readManifest(*project)
		if err != nil {
			fmt.Fprintf(os.Stderr, "failed to read scrapy project manifest: %v\n", err)
			return 2
		}
		if strings.TrimSpace(*selectedSpider) != "" {
			found := false
			for _, spider := range discoverSpiders(*project, manifest) {
				if spider["name"] == *selectedSpider {
					found = true
					break
				}
			}
			if !found {
				fmt.Fprintf(os.Stderr, "unknown spider in %s: %s\n", *project, *selectedSpider)
				return 2
			}
		}
		inputPath := resolveProjectOutput(*project, manifest, *selectedSpider)
		data, err := os.ReadFile(inputPath)
		if err != nil {
			fmt.Fprintf(os.Stderr, "missing scrapy project output: %v\n", err)
			return 2
		}
		var rows []map[string]string
		if err := json.Unmarshal(data, &rows); err != nil {
			fmt.Fprintf(os.Stderr, "invalid scrapy project output: %v\n", err)
			return 1
		}
		targetOutput := *output
		if targetOutput == "artifacts/exports/gospider-scrapy-demo.json" {
			targetOutput = strings.TrimSuffix(inputPath, filepath.Ext(inputPath)) + "." + *exportFormat
		}
		if err := os.MkdirAll(filepath.Dir(targetOutput), 0755); err != nil {
			fmt.Fprintf(os.Stderr, "failed to prepare export dir: %v\n", err)
			return 1
		}
		switch *exportFormat {
		case "json":
			encodedRows, marshalErr := json.MarshalIndent(rows, "", "  ")
			if marshalErr != nil {
				fmt.Fprintf(os.Stderr, "scrapy export failed: %v\n", marshalErr)
				return 1
			}
			err = os.WriteFile(targetOutput, encodedRows, 0644)
		case "csv":
			err = writeScrapyCSV(targetOutput, rows)
		case "md":
			err = writeScrapyMarkdown(targetOutput, rows)
		default:
			fmt.Fprintf(os.Stderr, "unsupported scrapy export format: %s\n", *exportFormat)
			return 2
		}
		if err != nil {
			fmt.Fprintf(os.Stderr, "scrapy export failed: %v\n", err)
			return 1
		}
		payload := map[string]any{"command": "scrapy export", "runtime": "go", "project": *project, "spider": *selectedSpider, "input": inputPath, "output": targetOutput, "format": *exportFormat}
		encoded, _ := json.MarshalIndent(payload, "", "  ")
		fmt.Println(string(encoded))
		return 0
	}

	if subcommand == "validate" {
		if strings.TrimSpace(*project) == "" {
			fmt.Fprintln(os.Stderr, "scrapy validate requires --project")
			return 2
		}
		checks := []map[string]string{}
		projectCfg := defaultContractConfig()
		configPath := filepath.Join(*project, "spider-framework.yaml")
		configStatus := "warning"
		if _, err := os.Stat(configPath); err == nil {
			configStatus = "passed"
			if loadedCfg, cfgErr := loadContractConfig(configPath); cfgErr == nil {
				projectCfg = loadedCfg
			}
		}
		manifestPath := filepath.Join(*project, "scrapy-project.json")
		if _, err := os.Stat(manifestPath); err != nil {
			checks = append(checks, map[string]string{"name": "manifest", "status": "failed", "details": manifestPath})
		} else {
			checks = append(checks, map[string]string{"name": "manifest", "status": "passed", "details": manifestPath})
			manifest, err := readManifest(*project)
			if err != nil {
				checks = append(checks, map[string]string{"name": "runtime", "status": "failed", "details": err.Error()})
			} else {
				checks = append(checks, map[string]string{"name": "runtime", "status": "passed", "details": "go"})
				entryPath := filepath.Join(*project, manifest["entry"])
				status := "failed"
				if _, err := os.Stat(entryPath); err == nil {
					status = "passed"
				}
				checks = append(checks, map[string]string{"name": "entry", "status": status, "details": entryPath})
				runnerPath := "project runner artifact not configured; built-in metadata runner will be used"
				runnerStatus := "warning"
				if runner := strings.TrimSpace(manifest["runner"]); runner != "" {
					runnerPath = filepath.Join(*project, filepath.FromSlash(runner))
					if _, err := os.Stat(runnerPath); err == nil {
						runnerStatus = "passed"
					}
				}
				checks = append(checks, map[string]string{"name": "runner_artifact", "status": runnerStatus, "details": runnerPath})
				for _, spider := range resolveSpiderDisplayMetadata(*project, manifest) {
					checks = append(checks, map[string]string{"name": "spider:" + spider["name"], "status": "passed", "details": spider["path"] + " runner=" + spider["runner"] + " runner_source=" + spider["runner_source"] + " url=" + spider["url"] + " url_source=" + spider["url_source"] + " " + spiderComponentSummary(projectCfg, spider["name"])})
				}
				plugins := discoverPlugins(*project)
				if len(plugins) == 0 {
					checks = append(checks, map[string]string{"name": "plugins", "status": "warning", "details": "no registered project plugins"})
				} else {
					checks = append(checks, map[string]string{"name": "plugins", "status": "passed", "details": fmt.Sprintf("%d plugins discovered", len(plugins))})
					for _, plugin := range plugins {
						checks = append(checks, map[string]string{"name": "plugin:" + plugin["name"], "status": "passed", "details": plugin["path"]})
					}
				}
			}
		}
		checks = append(checks, map[string]string{"name": "config", "status": configStatus, "details": configPath})
		appendGoDeclarativeComponentChecks(&checks, projectCfg)
		pluginManifestPath := filepath.Join(*project, "scrapy-plugins.json")
		pluginManifestStatus := "warning"
		pluginManifestDetails := pluginManifestPath
		if _, err := os.Stat(pluginManifestPath); err == nil {
			if err := validateScrapyPluginManifest(pluginManifestPath); err != nil {
				pluginManifestStatus = "failed"
				pluginManifestDetails = err.Error()
			} else {
				pluginManifestStatus = "passed"
			}
		}
		checks = append(checks, map[string]string{"name": "plugin_manifest", "status": pluginManifestStatus, "details": pluginManifestDetails})
		summary := "passed"
		for _, check := range checks {
			if check["status"] == "failed" {
				summary = "failed"
				break
			}
		}
		payload := map[string]any{"command": "scrapy validate", "runtime": "go", "project": *project, "summary": summary, "checks": checks}
		encoded, _ := json.MarshalIndent(payload, "", "  ")
		fmt.Println(string(encoded))
		if summary == "passed" {
			return 0
		}
		return 1
	}

	if subcommand == "genspider" {
		if strings.TrimSpace(*project) == "" {
			fmt.Fprintln(os.Stderr, "scrapy genspider requires --project")
			return 2
		}
		if strings.TrimSpace(*spiderName) == "" || strings.TrimSpace(*spiderDomain) == "" {
			fmt.Fprintln(os.Stderr, "scrapy genspider requires --name and --domain")
			return 2
		}
		if _, err := readManifest(*project); err != nil {
			fmt.Fprintf(os.Stderr, "failed to read scrapy project manifest: %v\n", err)
			return 2
		}
		spidersDir := filepath.Join(*project, "spiders")
		if err := os.MkdirAll(spidersDir, 0755); err != nil {
			fmt.Fprintf(os.Stderr, "failed to create spiders dir: %v\n", err)
			return 1
		}
		target := filepath.Join(spidersDir, *spiderName+".go")
		var content string
		if *aiTemplate {
			content = renderGoAISpiderTemplate(*spiderName, *spiderDomain)
		} else {
			content = renderGoStandardSpiderTemplate(*spiderName, *spiderDomain)
		}
		if err := os.WriteFile(target, []byte(content), 0644); err != nil {
			fmt.Fprintf(os.Stderr, "failed to write spider template: %v\n", err)
			return 1
		}
		payload := map[string]any{"command": "scrapy genspider", "runtime": "go", "project": *project, "spider": *spiderName, "path": target, "template": map[bool]string{true: "ai", false: "standard"}[*aiTemplate]}
		encoded, _ := json.MarshalIndent(payload, "", "  ")
		fmt.Println(string(encoded))
		return 0
	}

	if subcommand == "init" {
		if strings.TrimSpace(*initPath) == "" {
			fmt.Fprintln(os.Stderr, "scrapy init requires --path")
			return 2
		}
		projectRoot := *initPath
		_, currentFile, _, _ := runtime.Caller(0)
		repoRoot := filepath.Dir(filepath.Dir(filepath.Dir(currentFile)))
		repoGoSum, _ := os.ReadFile(filepath.Join(repoRoot, "go.sum"))
		if err := os.MkdirAll(projectRoot, 0755); err != nil {
			fmt.Fprintf(os.Stderr, "failed to create project directory: %v\n", err)
			return 1
		}
		cfg := defaultContractConfig()
		cfg.Project.Name = filepath.Base(projectRoot)
		cfg.Scrapy.Plugins = []string{"field-injector"}
		configBytes, _ := yaml.Marshal(&cfg)
		files := map[string]string{
			"scrapy-project.json":   fmt.Sprintf("{\n  \"name\": %q,\n  \"runtime\": \"go\",\n  \"entry\": \"main.go\",\n  \"runner\": \"dist/gospider-project\",\n  \"url\": \"https://example.com\",\n  \"output\": \"artifacts/exports/items.json\"\n}\n", filepath.Base(projectRoot)),
			"go.mod":                "module gospiderproject\n\ngo 1.22\n",
			"go.sum":                string(repoGoSum),
			"go.work":               "go 1.22\n\nuse .\nuse " + filepath.ToSlash(repoRoot) + "\n",
			"main.go":               "package main\n\nimport (\n\t\"fmt\"\n\t\"os\"\n\n\tscrapyapi \"gospider/scrapy\"\n\tprojectruntime \"gospider/scrapy/project\"\n\t_ \"gospiderproject/plugins\"\n\t_ \"gospiderproject/spiders\"\n)\n\nfunc main() {\n\tif handled, err := projectruntime.RunFromEnv(); handled {\n\t\tif err != nil {\n\t\t\tpanic(err)\n\t\t}\n\t\treturn\n\t}\n\tspider, err := projectruntime.ResolveSpider(\"\")\n\tif err != nil {\n\t\tpanic(err)\n\t}\n\tplugins, err := projectruntime.ResolvePlugins(nil)\n\tif err != nil {\n\t\tpanic(err)\n\t}\n\tprocess := scrapyapi.NewCrawlerProcess(spider)\n\tfor _, plugin := range plugins {\n\t\tprocess.AddPlugin(plugin)\n\t}\n\titems, err := process.Run()\n\tif err != nil {\n\t\tpanic(err)\n\t}\n\texporter := scrapyapi.NewFeedExporter(\"json\", \"artifacts/exports/items.json\")\n\tfor _, item := range items {\n\t\texporter.ExportItem(item)\n\t}\n\tif err := exporter.Close(); err != nil {\n\t\tpanic(err)\n\t}\n\tfmt.Fprintln(os.Stdout, \"exported\", len(items), \"items\")\n}\n",
			"plugins/default.go":    "package plugins\n\nimport (\n\tscrapyapi \"gospider/scrapy\"\n\tprojectruntime \"gospider/scrapy/project\"\n)\n\ntype ProjectPlugin struct{}\n\nfunc NewProjectPlugin() scrapyapi.Plugin { return &ProjectPlugin{} }\n\nfunc (p *ProjectPlugin) PrepareSpider(spider *scrapyapi.Spider) error { return nil }\nfunc (p *ProjectPlugin) ProvidePipelines() []scrapyapi.ItemPipeline { return nil }\nfunc (p *ProjectPlugin) OnSpiderOpened(spider *scrapyapi.Spider) error { return nil }\nfunc (p *ProjectPlugin) OnSpiderClosed(spider *scrapyapi.Spider) error { return nil }\nfunc (p *ProjectPlugin) ProcessItem(item scrapyapi.Item, spider *scrapyapi.Spider) (scrapyapi.Item, error) { item[\"plugin\"] = \"project-plugin\"; return item, nil }\n\nfunc init() {\n\tprojectruntime.RegisterPlugin(\"project-plugin\", NewProjectPlugin)\n}\n",
			"scrapy-plugins.json":   "{\n  \"plugins\": [\n    {\n      \"name\": \"field-injector\",\n      \"priority\": 10,\n      \"config\": {\n        \"fields\": {\n          \"plugin\": \"project-plugin\"\n        }\n      }\n    }\n  ]\n}\n",
			"spiders/demo.go":       "package spiders\n\n// scrapy: url=https://example.com\n\nimport (\n\tscrapyapi \"gospider/scrapy\"\n\tprojectruntime \"gospider/scrapy/project\"\n)\n\nfunc NewDemoSpider() *scrapyapi.Spider {\n\treturn scrapyapi.NewSpider(\"demo\", func(response *scrapyapi.Response) ([]any, error) {\n\t\treturn []any{scrapyapi.NewItem().Set(\"title\", response.CSS(\"title\").Get()).Set(\"url\", response.URL).Set(\"framework\", \"gospider\")}, nil\n\t}).AddStartURL(\"https://example.com\")\n}\n\nfunc init() {\n\tprojectruntime.RegisterSpider(\"demo\", NewDemoSpider)\n}\n",
			"run-scrapy.sh":         "#!/usr/bin/env bash\nset -euo pipefail\n\ngospider scrapy run --project .\n",
			"run-scrapy.ps1":        "gospider scrapy run --project .\n",
			"README.md":             "# " + filepath.Base(projectRoot) + "\n\n## Quick Start\n\n```bash\ngospider scrapy run --project .\ngospider scrapy run --project . --spider demo\ngo build -o dist/gospider-project .\n```\n\n`scrapy run --project` 会优先执行 `scrapy-project.json` 里配置的 project runner artifact；如果 artifact 尚未构建，会回退到 built-in metadata runner。\n\n## AI Starter\n\n```bash\ngospider ai --url https://example.com --instructions \"提取标题和摘要\" --schema-file ai-schema.json\ngospider job --file ai-job.json\n```\n\n## Plugin SDK\n\n`plugins/` 下的注册型插件用于 project runner artifact，`scrapy-plugins.json` 用于 built-in metadata runner 和内置插件。\n",
			"ai-schema.json":        "{\n  \"type\": \"object\",\n  \"properties\": {\n    \"title\": { \"type\": \"string\" },\n    \"summary\": { \"type\": \"string\" },\n    \"url\": { \"type\": \"string\" }\n  }\n}\n",
			"ai-job.json":           "{\n  \"name\": \"gospider-ai-job\",\n  \"runtime\": \"ai\",\n  \"target\": { \"url\": \"https://example.com\" },\n  \"extract\": [\n    { \"field\": \"title\", \"type\": \"ai\" },\n    { \"field\": \"summary\", \"type\": \"ai\" },\n    { \"field\": \"url\", \"type\": \"ai\" }\n  ],\n  \"output\": { \"format\": \"json\", \"path\": \"artifacts/exports/ai-job-output.json\" },\n  \"metadata\": { \"content\": \"<title>Demo</title>\", \"schema_file\": \"ai-schema.json\" }\n}\n",
			"job.json":              "{\n  \"name\": \"gospider-job\",\n  \"runtime\": \"http\",\n  \"target\": { \"url\": \"https://example.com\" },\n  \"output\": { \"format\": \"json\", \"path\": \"artifacts/exports/job-output.json\" }\n}\n",
			"spider-framework.yaml": string(configBytes),
		}
		for relativePath, content := range files {
			filePath := filepath.Join(projectRoot, relativePath)
			if err := os.MkdirAll(filepath.Dir(filePath), 0755); err != nil {
				fmt.Fprintf(os.Stderr, "failed to prepare %s: %v\n", filePath, err)
				return 1
			}
			if err := os.WriteFile(filePath, []byte(content), 0644); err != nil {
				fmt.Fprintf(os.Stderr, "failed to write %s: %v\n", filePath, err)
				return 1
			}
		}
		payload := map[string]any{"command": "scrapy init", "runtime": "go", "project": projectRoot}
		encoded, _ := json.MarshalIndent(payload, "", "  ")
		fmt.Println(string(encoded))
		return 0
	}

	projectCfg := defaultContractConfig()
	selectedRunner := "http"
	runnerSource := "default"
	urlSource := "default"

	if subcommand == "run" {
		if strings.TrimSpace(*project) == "" {
			fmt.Fprintln(os.Stderr, "scrapy run requires --project")
			return 2
		}
		manifestPath := filepath.Join(*project, "scrapy-project.json")
		data, err := os.ReadFile(manifestPath)
		if err != nil {
			fmt.Fprintf(os.Stderr, "failed to read scrapy project manifest: %v\n", err)
			return 2
		}
		var manifest struct {
			Runtime string `json:"runtime"`
			Runner  string `json:"runner"`
			URL     string `json:"url"`
			Output  string `json:"output"`
		}
		if err := json.Unmarshal(data, &manifest); err != nil {
			fmt.Fprintf(os.Stderr, "invalid scrapy project manifest: %v\n", err)
			return 2
		}
		if manifest.Runtime != "go" {
			fmt.Fprintf(os.Stderr, "runtime mismatch in %s: expected go\n", manifestPath)
			return 2
		}
		manifestMap := map[string]string{
			"runtime": manifest.Runtime,
			"runner":  manifest.Runner,
			"url":     manifest.URL,
			"output":  manifest.Output,
		}
		selectedMetadata := map[string]string{}
		if strings.TrimSpace(*selectedSpider) != "" {
			matches := []map[string]string{}
			for _, spider := range discoverSpiders(*project, manifestMap) {
				if spider["name"] == *selectedSpider {
					matches = append(matches, spider)
				}
			}
			if len(matches) == 0 {
				fmt.Fprintf(os.Stderr, "unknown spider in %s: %s\n", *project, *selectedSpider)
				return 2
			}
			selectedMetadata = matches[0]
		}
		projectCfg = defaultContractConfig()
		projectCfgPath := filepath.Join(*project, "spider-framework.yaml")
		if loadedCfg, err := loadContractConfig(projectCfgPath); err == nil {
			projectCfg = loadedCfg
		}
		*targetURL, urlSource = resolveScrapyURLDetail(projectCfg, *selectedSpider, selectedMetadata, manifest.URL)
		if *output == "artifacts/exports/gospider-scrapy-demo.json" {
			*output = resolveProjectOutput(*project, manifestMap, *selectedSpider)
		}
		selectedRunner, runnerSource = resolveScrapyRunnerDetail(projectCfg, *selectedSpider, selectedMetadata)
		if projectCfg, err := loadContractConfig(projectCfgPath); err == nil {
			manifestPath := filepath.Join(*project, "scrapy-plugins.json")
			if len(projectCfg.Scrapy.Plugins) > 0 {
				if _, statErr := os.Stat(manifestPath); statErr != nil {
					os.Setenv("GOSPIDER_SCRAPY_PLUGINS", strings.Join(projectCfg.Scrapy.Plugins, ","))
					defer os.Unsetenv("GOSPIDER_SCRAPY_PLUGINS")
				}
			}
			if strings.TrimSpace(projectCfg.NodeReverse.BaseURL) != "" {
				os.Setenv("GOSPIDER_SCRAPY_REVERSE_URL", projectCfg.NodeReverse.BaseURL)
				defer os.Unsetenv("GOSPIDER_SCRAPY_REVERSE_URL")
			}
		}
		if selectedRunner == "http" {
			if executed, code := runProjectArtifact(*project, manifestMap, selectedMetadata, *output); executed {
				return code
			}
		}
	}

	spider := scrapyapi.NewSpider("gospider-scrapy-demo", func(response *scrapyapi.Response) ([]any, error) {
		return []any{
			scrapyapi.NewItem().
				Set("title", response.CSS("title").Get()).
				Set("url", response.URL).
				Set("framework", "gospider"),
		}, nil
	})

	pluginSpecs := []projectruntime.PluginSpec{}
	if strings.TrimSpace(*project) != "" {
		pluginSpecs = projectruntime.LoadPluginSpecsFromManifest(*project)
		if len(pluginSpecs) == 0 {
			projectCfgPath := filepath.Join(*project, "spider-framework.yaml")
			if _, err := os.Stat(projectCfgPath); err == nil {
				if projectCfg, err := loadContractConfig(projectCfgPath); err == nil {
					for _, name := range projectCfg.Scrapy.Plugins {
						pluginSpecs = append(pluginSpecs, projectruntime.PluginSpec{Name: name, Enabled: true})
					}
				}
			}
		}
	}
	plugins, err := projectruntime.ResolvePluginSpecs(pluginSpecs)
	if err != nil {
		fmt.Fprintf(os.Stderr, "failed to resolve scrapy project plugins: %v\n", err)
		return 1
	}
	resolvedPluginNames := []string{}
	for _, spec := range pluginSpecs {
		if spec.Enabled && strings.TrimSpace(spec.Name) != "" {
			resolvedPluginNames = append(resolvedPluginNames, spec.Name)
		}
	}
	if len(resolvedPluginNames) == 0 {
		resolvedPluginNames = projectruntime.PluginNames()
	}
	declarativePipelines := buildDeclarativePipelines(projectCfg, *selectedSpider)
	declarativeSpiderMiddlewares := buildDeclarativeSpiderMiddlewares(projectCfg, *selectedSpider)
	declarativeDownloaderMiddlewares := buildDeclarativeDownloaderMiddlewares(projectCfg, *selectedSpider)
	pipelineNames := collectGoPipelineNames(plugins, declarativePipelines)
	spiderMiddlewareNames := collectGoSpiderMiddlewareNames(plugins, declarativeSpiderMiddlewares)
	downloaderMiddlewareNames := collectGoDownloaderMiddlewareNames(plugins, declarativeDownloaderMiddlewares)
	settingsSource := ""
	if strings.TrimSpace(*project) != "" {
		candidate := filepath.Join(*project, "spider-framework.yaml")
		if _, err := os.Stat(candidate); err == nil {
			settingsSource = candidate
		}
	}
	spider.AddStartURL(*targetURL)
	configMap := map[string]any{"runner": selectedRunner}
	if strings.TrimSpace(*htmlFile) != "" {
		configMap["runner"] = "browser"
	}
	process := scrapyapi.NewCrawlerProcess(spider).WithConfig(configMap)
	if strings.TrimSpace(*htmlFile) != "" {
		fixturePath := *htmlFile
		process.WithBrowserFetch(func(request *scrapyapi.Request, spider *scrapyapi.Spider) (*scrapyapi.Response, error) {
			body, err := os.ReadFile(fixturePath)
			if err != nil {
				return nil, err
			}
			return &scrapyapi.Response{
				URL:        request.URL,
				StatusCode: http.StatusOK,
				Headers:    http.Header{},
				Body:       body,
				Text:       string(body),
				Request:    request,
			}, nil
		})
	}
	if selectedRunner == "browser" || selectedRunner == "hybrid" {
		process.WithBrowserFetch(func(request *scrapyapi.Request, spider *scrapyapi.Spider) (*scrapyapi.Response, error) {
			return browserFetchForScrapy(request, projectCfg)
		})
	}
	for _, plugin := range plugins {
		process.AddPlugin(plugin)
	}
	for _, pipeline := range declarativePipelines {
		process.AddPipeline(pipeline)
	}
	for _, middleware := range declarativeSpiderMiddlewares {
		process.AddSpiderMiddleware(middleware)
	}
	for _, middleware := range declarativeDownloaderMiddlewares {
		process.AddDownloaderMiddleware(middleware)
	}
	items, err := process.Run()
	if err != nil {
		fmt.Fprintf(os.Stderr, "scrapy demo failed: %v\n", err)
		return 1
	}

	exporter := scrapyapi.NewFeedExporter("json", *output)
	for _, item := range items {
		exporter.ExportItem(item)
	}
	if err := exporter.Close(); err != nil {
		fmt.Fprintf(os.Stderr, "failed to export scrapy demo items: %v\n", err)
		return 1
	}

	payload := map[string]any{
		"command":                "scrapy " + subcommand,
		"runtime":                "go",
		"spider":                 *selectedSpider,
		"project_runner":         "built-in-metadata-runner",
		"runner":                 selectedRunner,
		"resolved_runner":        selectedRunner,
		"runner_source":          map[bool]string{true: "html-fixture", false: runnerSource}[strings.TrimSpace(*htmlFile) != ""],
		"resolved_url":           *targetURL,
		"url_source":             map[bool]string{true: "html-fixture", false: urlSource}[strings.TrimSpace(*htmlFile) != ""],
		"item_count":             len(items),
		"output":                 *output,
		"settings_source":        settingsSource,
		"plugins":                resolvedPluginNames,
		"pipelines":              pipelineNames,
		"spider_middlewares":     spiderMiddlewareNames,
		"downloader_middlewares": downloaderMiddlewareNames,
		"runtime_features": map[string]any{
			"browser":      selectedRunner == "browser" || selectedRunner == "hybrid" || strings.TrimSpace(*htmlFile) != "",
			"anti_bot":     projectCfg.AntiBot.Enabled,
			"node_reverse": projectCfg.NodeReverse.Enabled && strings.TrimSpace(projectCfg.NodeReverse.BaseURL) != "",
			"distributed":  true,
		},
	}
	if projectCfg.NodeReverse.Enabled && strings.TrimSpace(projectCfg.NodeReverse.BaseURL) != "" {
		if summary := projectruntime.CollectReverseSummary(projectCfg.NodeReverse.BaseURL, *targetURL, *htmlFile); summary != nil {
			payload["reverse"] = summary
		}
	}
	encoded, _ := json.MarshalIndent(payload, "", "  ")
	fmt.Println(string(encoded))
	return 0
}

func ultimateCommand(args []string) {
	ultimateCmd := flag.NewFlagSet("ultimate", flag.ExitOnError)
	url := ultimateCmd.String("url", "", "target URL")
	configPath := ultimateCmd.String("config", "", "shared contract config path")
	reverseServiceURL := ultimateCmd.String("reverse-service-url", "", "NodeReverse service URL")
	jsonOutput := ultimateCmd.Bool("json", false, "only emit the final JSON envelope")
	quietOutput := ultimateCmd.Bool("quiet", false, "suppress progress logs")
	_ = ultimateCmd.Parse(args)

	cfg, err := loadContractConfig(*configPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "config error: %v\n", err)
		os.Exit(2)
	}

	urls := append([]string{}, cfg.Crawl.URLs...)
	if *url != "" {
		urls = []string{*url}
	}
	if len(urls) == 0 {
		fmt.Println("ultimate requires --url or a config with crawl.urls")
		os.Exit(2)
	}

	reverseURL := *reverseServiceURL
	if reverseURL == "" {
		reverseURL = cfg.NodeReverse.BaseURL
	}
	if reverseURL == "" {
		reverseURL = os.Getenv("SPIDER_REVERSE_SERVICE_URL")
	}
	checkpointDir := cfg.Storage.CheckpointDir
	if strings.TrimSpace(checkpointDir) == "" || checkpointDir == "artifacts/checkpoints" {
		checkpointDir = filepath.Join("artifacts", "ultimate", "checkpoints")
	}

	proxyServers := []string{}
	if value := strings.TrimSpace(cfg.AntiBot.ProxyPool); value != "" && value != "local" {
		for _, item := range strings.Split(value, ",") {
			trimmed := strings.TrimSpace(item)
			if trimmed != "" {
				proxyServers = append(proxyServers, trimmed)
			}
		}
	}

	spider := ultimate.NewUltimateSpider(&ultimate.UltimateConfig{
		ReverseServiceURL: reverseURL,
		MaxConcurrency:    cfg.Crawl.Concurrency,
		MaxRetries:        3,
		Timeout:           time.Duration(cfg.Crawl.TimeoutSeconds) * time.Second,
		UserAgent:         cfg.Browser.UserAgent,
		ProxyServers:      proxyServers,
		OutputFormat:      cfg.Export.Format,
		CheckpointDir:     checkpointDir,
		EnableBrowser:     cfg.Browser.Enabled,
	})
	runUltimate := func() ([]*ultimate.CrawlResult, error) {
		if !*jsonOutput && !*quietOutput {
			return spider.Start(urls)
		}

		originalStdout := os.Stdout
		reader, writer, pipeErr := os.Pipe()
		if pipeErr != nil {
			return spider.Start(urls)
		}
		os.Stdout = writer
		done := make(chan struct{})
		go func() {
			_, _ = io.Copy(io.Discard, reader)
			close(done)
		}()
		results, err := spider.Start(urls)
		_ = writer.Close()
		os.Stdout = originalStdout
		<-done
		return results, err
	}

	results, err := runUltimate()
	failedCount := 0
	normalizedResults := make([]map[string]any, 0, len(results))
	for _, result := range results {
		if result == nil {
			failedCount++
			normalizedResults = append(normalizedResults, map[string]any{
				"task_id":          "",
				"url":              "",
				"success":          false,
				"error":            "nil result",
				"duration":         "",
				"anti_bot_level":   "",
				"anti_bot_signals": []string{},
				"proxy_used":       "",
			})
			continue
		}
		if !result.Success {
			failedCount++
		}
		errorText := ""
		if result.Error != nil {
			errorText = result.Error.Error()
		}
		normalizedResults = append(normalizedResults, map[string]any{
			"task_id":          result.TaskID,
			"url":              result.URL,
			"success":          result.Success,
			"error":            errorText,
			"duration":         result.Duration.String(),
			"anti_bot_level":   result.AntiBotLevel,
			"anti_bot_signals": result.AntiBotSignals,
			"proxy_used":       result.ProxyUsed,
			"reverse":          result.ReverseRuntime,
		})
	}
	payload := map[string]any{
		"command":      "ultimate",
		"runtime":      "go",
		"summary":      "passed",
		"summary_text": fmt.Sprintf("%d results, %d failed", len(results), failedCount),
		"exit_code":    0,
		"url_count":    len(urls),
		"result_count": len(results),
		"results":      normalizedResults,
	}
	if err != nil {
		payload["summary"] = "failed"
		payload["exit_code"] = 1
	} else if failedCount > 0 {
		payload["summary"] = "failed"
		payload["exit_code"] = 1
	}
	encoded, marshalErr := json.MarshalIndent(payload, "", "  ")
	if marshalErr == nil {
		fmt.Println(string(encoded))
	}
	if err != nil {
		fmt.Fprintf(os.Stderr, "ultimate failed: %v\n", err)
		os.Exit(1)
	}
}

func nodeReverseCommand(args []string) int {
	if len(args) == 0 {
		fmt.Println("Usage: gospider node-reverse <health|profile|detect|fingerprint-spoof|tls-fingerprint|canvas-fingerprint|analyze-crypto|signature-reverse|ast|webpack|function-call|browser-simulate> [options]")
		return 2
	}
	switch args[0] {
	case "health":
		return nodeReverseHealthCommand(args[1:])
	case "profile":
		return nodeReverseProfileCommand(args[1:])
	case "detect":
		return nodeReverseDetectCommand(args[1:])
	case "fingerprint-spoof":
		return nodeReverseFingerprintSpoofCommand(args[1:])
	case "tls-fingerprint":
		return nodeReverseTLSFingerprintCommand(args[1:])
	case "canvas-fingerprint":
		return nodeReverseCanvasFingerprintCommand(args[1:])
	case "analyze-crypto":
		return nodeReverseAnalyzeCryptoCommand(args[1:])
	case "signature-reverse":
		return nodeReverseSignatureReverseCommand(args[1:])
	case "ast":
		return nodeReverseASTCommand(args[1:])
	case "webpack":
		return nodeReverseWebpackCommand(args[1:])
	case "function-call":
		return nodeReverseFunctionCallCommand(args[1:])
	case "browser-simulate":
		return nodeReverseBrowserSimulateCommand(args[1:])
	default:
		fmt.Printf("unknown node-reverse subcommand: %s\n", args[0])
		return 2
	}
}

func nodeReverseHealthCommand(args []string) int {
	cmd := flag.NewFlagSet("node-reverse health", flag.ExitOnError)
	baseURL := cmd.String("base-url", "", "NodeReverse service URL")
	_ = cmd.Parse(args)

	client := nodereverse.NewNodeReverseClient(*baseURL)
	healthy, err := client.HealthCheck()
	payload := map[string]any{
		"command":  "node-reverse health",
		"runtime":  "go",
		"base_url": client.BaseURL,
		"healthy":  healthy && err == nil,
	}
	encoded, _ := json.MarshalIndent(payload, "", "  ")
	fmt.Println(string(encoded))
	if err != nil || !healthy {
		return 1
	}
	return 0
}

func nodeReverseProfileCommand(args []string) int {
	cmd := flag.NewFlagSet("node-reverse profile", flag.ExitOnError)
	baseURL := cmd.String("base-url", "", "NodeReverse service URL")
	targetURL := cmd.String("url", "", "target URL")
	htmlFile := cmd.String("html-file", "", "local HTML file")
	statusCode := cmd.Int("status-code", 0, "HTTP status code")
	_ = cmd.Parse(args)

	html, resolvedURL := loadHTMLForProfile(*targetURL, *htmlFile)
	if html == "" {
		fmt.Fprintln(os.Stderr, "node-reverse profile requires --url or --html-file")
		return 2
	}
	client := nodereverse.NewNodeReverseClient(*baseURL)
	resp, err := client.ProfileAntiBot(nodereverse.AntiBotProfileRequest{
		HTML:       html,
		URL:        resolvedURL,
		StatusCode: *statusCode,
	})
	if err != nil {
		fmt.Fprintf(os.Stderr, "node-reverse profile failed: %v\n", err)
		return 1
	}
	encoded, _ := json.MarshalIndent(resp, "", "  ")
	fmt.Println(string(encoded))
	if !resp.Success {
		return 1
	}
	return 0
}

func nodeReverseDetectCommand(args []string) int {
	cmd := flag.NewFlagSet("node-reverse detect", flag.ExitOnError)
	baseURL := cmd.String("base-url", "", "NodeReverse service URL")
	targetURL := cmd.String("url", "", "target URL")
	htmlFile := cmd.String("html-file", "", "local HTML file")
	statusCode := cmd.Int("status-code", 0, "HTTP status code")
	_ = cmd.Parse(args)

	html, resolvedURL := loadHTMLForProfile(*targetURL, *htmlFile)
	if html == "" {
		fmt.Fprintln(os.Stderr, "node-reverse detect requires --url or --html-file")
		return 2
	}
	client := nodereverse.NewNodeReverseClient(*baseURL)
	resp, err := client.DetectAntiBot(nodereverse.AntiBotProfileRequest{
		HTML:       html,
		URL:        resolvedURL,
		StatusCode: *statusCode,
	})
	if err != nil {
		fmt.Fprintf(os.Stderr, "node-reverse detect failed: %v\n", err)
		return 1
	}
	encoded, _ := json.MarshalIndent(resp, "", "  ")
	fmt.Println(string(encoded))
	if !resp.Success {
		return 1
	}
	return 0
}

func nodeReverseFingerprintSpoofCommand(args []string) int {
	cmd := flag.NewFlagSet("node-reverse fingerprint-spoof", flag.ExitOnError)
	baseURL := cmd.String("base-url", "", "NodeReverse service URL")
	browser := cmd.String("browser", "chrome", "browser type")
	platform := cmd.String("platform", "windows", "platform type")
	_ = cmd.Parse(args)

	client := nodereverse.NewNodeReverseClient(*baseURL)
	resp, err := client.SpoofFingerprint(nodereverse.FingerprintSpoofRequest{
		Browser:  *browser,
		Platform: *platform,
	})
	if err != nil {
		fmt.Fprintf(os.Stderr, "node-reverse fingerprint-spoof failed: %v\n", err)
		return 1
	}
	encoded, _ := json.MarshalIndent(resp, "", "  ")
	fmt.Println(string(encoded))
	if !resp.Success {
		return 1
	}
	return 0
}

func nodeReverseTLSFingerprintCommand(args []string) int {
	cmd := flag.NewFlagSet("node-reverse tls-fingerprint", flag.ExitOnError)
	baseURL := cmd.String("base-url", "", "NodeReverse service URL")
	browser := cmd.String("browser", "chrome", "browser type")
	version := cmd.String("version", "120", "browser version")
	_ = cmd.Parse(args)

	client := nodereverse.NewNodeReverseClient(*baseURL)
	resp, err := client.GenerateTLSFingerprint(nodereverse.TLSFingerprintRequest{
		Browser: *browser,
		Version: *version,
	})
	if err != nil {
		fmt.Fprintf(os.Stderr, "node-reverse tls-fingerprint failed: %v\n", err)
		return 1
	}
	encoded, _ := json.MarshalIndent(resp, "", "  ")
	fmt.Println(string(encoded))
	if !resp.Success {
		return 1
	}
	return 0
}

func nodeReverseCanvasFingerprintCommand(args []string) int {
	cmd := flag.NewFlagSet("node-reverse canvas-fingerprint", flag.ExitOnError)
	baseURL := cmd.String("base-url", "", "NodeReverse service URL")
	_ = cmd.Parse(args)

	client := nodereverse.NewNodeReverseClient(*baseURL)
	resp, err := client.CanvasFingerprint()
	if err != nil {
		fmt.Fprintf(os.Stderr, "node-reverse canvas-fingerprint failed: %v\n", err)
		return 1
	}
	encoded, _ := json.MarshalIndent(resp, "", "  ")
	fmt.Println(string(encoded))
	if !resp.Success {
		return 1
	}
	return 0
}

func nodeReverseAnalyzeCryptoCommand(args []string) int {
	cmd := flag.NewFlagSet("node-reverse analyze-crypto", flag.ExitOnError)
	baseURL := cmd.String("base-url", "", "NodeReverse service URL")
	codeFile := cmd.String("code-file", "", "local code file")
	_ = cmd.Parse(args)

	if strings.TrimSpace(*codeFile) == "" {
		fmt.Fprintln(os.Stderr, "node-reverse analyze-crypto requires --code-file")
		return 2
	}
	code, err := os.ReadFile(*codeFile)
	if err != nil {
		fmt.Fprintf(os.Stderr, "failed to read code file: %v\n", err)
		return 1
	}
	client := nodereverse.NewNodeReverseClient(*baseURL)
	resp, err := client.AnalyzeCrypto(string(code))
	if err != nil {
		fmt.Fprintf(os.Stderr, "node-reverse analyze-crypto failed: %v\n", err)
		return 1
	}
	encoded, _ := json.MarshalIndent(resp, "", "  ")
	fmt.Println(string(encoded))
	if !resp.Success {
		return 1
	}
	return 0
}

func nodeReverseSignatureReverseCommand(args []string) int {
	cmd := flag.NewFlagSet("node-reverse signature-reverse", flag.ExitOnError)
	baseURL := cmd.String("base-url", "", "NodeReverse service URL")
	codeFile := cmd.String("code-file", "", "local code file")
	inputData := cmd.String("input-data", "", "sample input data")
	expectedOutput := cmd.String("expected-output", "", "expected output data")
	_ = cmd.Parse(args)

	if strings.TrimSpace(*codeFile) == "" || strings.TrimSpace(*inputData) == "" || strings.TrimSpace(*expectedOutput) == "" {
		fmt.Fprintln(os.Stderr, "node-reverse signature-reverse requires --code-file, --input-data, and --expected-output")
		return 2
	}
	code, err := os.ReadFile(*codeFile)
	if err != nil {
		fmt.Fprintf(os.Stderr, "failed to read code file: %v\n", err)
		return 1
	}
	client := nodereverse.NewNodeReverseClient(*baseURL)
	resp, err := client.ReverseSignature(string(code), *inputData, *expectedOutput)
	if err != nil {
		fmt.Fprintf(os.Stderr, "node-reverse signature-reverse failed: %v\n", err)
		return 1
	}
	encoded, _ := json.MarshalIndent(resp, "", "  ")
	fmt.Println(string(encoded))
	if !resp.Success {
		return 1
	}
	return 0
}

func nodeReverseASTCommand(args []string) int {
	cmd := flag.NewFlagSet("node-reverse ast", flag.ExitOnError)
	baseURL := cmd.String("base-url", "", "NodeReverse service URL")
	codeFile := cmd.String("code-file", "", "local code file")
	analysis := cmd.String("analysis", "crypto,obfuscation,anti-debug", "comma-separated analysis types")
	_ = cmd.Parse(args)

	if strings.TrimSpace(*codeFile) == "" {
		fmt.Fprintln(os.Stderr, "node-reverse ast requires --code-file")
		return 2
	}
	code, err := os.ReadFile(*codeFile)
	if err != nil {
		fmt.Fprintf(os.Stderr, "failed to read code file: %v\n", err)
		return 1
	}
	analysisTypes := make([]string, 0, 4)
	for _, item := range strings.Split(*analysis, ",") {
		item = strings.TrimSpace(item)
		if item != "" {
			analysisTypes = append(analysisTypes, item)
		}
	}
	client := nodereverse.NewNodeReverseClient(*baseURL)
	resp, err := client.AnalyzeAST(string(code), analysisTypes)
	if err != nil {
		fmt.Fprintf(os.Stderr, "node-reverse ast failed: %v\n", err)
		return 1
	}
	encoded, _ := json.MarshalIndent(resp, "", "  ")
	fmt.Println(string(encoded))
	if !resp.Success {
		return 1
	}
	return 0
}

func nodeReverseWebpackCommand(args []string) int {
	cmd := flag.NewFlagSet("node-reverse webpack", flag.ExitOnError)
	baseURL := cmd.String("base-url", "", "NodeReverse service URL")
	codeFile := cmd.String("code-file", "", "local code file")
	_ = cmd.Parse(args)

	if strings.TrimSpace(*codeFile) == "" {
		fmt.Fprintln(os.Stderr, "node-reverse webpack requires --code-file")
		return 2
	}
	code, err := os.ReadFile(*codeFile)
	if err != nil {
		fmt.Fprintf(os.Stderr, "failed to read code file: %v\n", err)
		return 1
	}
	client := nodereverse.NewNodeReverseClient(*baseURL)
	resp, err := client.AnalyzeWebpack(string(code))
	if err != nil {
		fmt.Fprintf(os.Stderr, "node-reverse webpack failed: %v\n", err)
		return 1
	}
	encoded, _ := json.MarshalIndent(resp, "", "  ")
	fmt.Println(string(encoded))
	if success, ok := resp["success"].(bool); ok && success {
		return 0
	}
	return 1
}

func nodeReverseFunctionCallCommand(args []string) int {
	cmd := flag.NewFlagSet("node-reverse function-call", flag.ExitOnError)
	baseURL := cmd.String("base-url", "", "NodeReverse service URL")
	codeFile := cmd.String("code-file", "", "local code file")
	functionName := cmd.String("function-name", "", "function name")
	var fnArgs repeatedStringFlag
	cmd.Var(&fnArgs, "arg", "function argument (repeatable)")
	_ = cmd.Parse(args)

	if strings.TrimSpace(*codeFile) == "" || strings.TrimSpace(*functionName) == "" {
		fmt.Fprintln(os.Stderr, "node-reverse function-call requires --code-file and --function-name")
		return 2
	}
	code, err := os.ReadFile(*codeFile)
	if err != nil {
		fmt.Fprintf(os.Stderr, "failed to read code file: %v\n", err)
		return 1
	}
	callArgs := make([]interface{}, 0, len(fnArgs))
	for _, value := range fnArgs {
		callArgs = append(callArgs, value)
	}
	client := nodereverse.NewNodeReverseClient(*baseURL)
	resp, err := client.CallFunction(*functionName, callArgs, string(code))
	if err != nil {
		fmt.Fprintf(os.Stderr, "node-reverse function-call failed: %v\n", err)
		return 1
	}
	encoded, _ := json.MarshalIndent(resp, "", "  ")
	fmt.Println(string(encoded))
	if !resp.Success {
		return 1
	}
	return 0
}

func nodeReverseBrowserSimulateCommand(args []string) int {
	cmd := flag.NewFlagSet("node-reverse browser-simulate", flag.ExitOnError)
	baseURL := cmd.String("base-url", "", "NodeReverse service URL")
	codeFile := cmd.String("code-file", "", "local code file")
	userAgent := cmd.String("user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "browser user agent")
	language := cmd.String("language", "zh-CN", "browser language")
	platform := cmd.String("platform", "Win32", "browser platform")
	_ = cmd.Parse(args)

	if strings.TrimSpace(*codeFile) == "" {
		fmt.Fprintln(os.Stderr, "node-reverse browser-simulate requires --code-file")
		return 2
	}
	code, err := os.ReadFile(*codeFile)
	if err != nil {
		fmt.Fprintf(os.Stderr, "failed to read code file: %v\n", err)
		return 1
	}
	client := nodereverse.NewNodeReverseClient(*baseURL)
	resp, err := client.SimulateBrowser(string(code), map[string]string{
		"userAgent": *userAgent,
		"language":  *language,
		"platform":  *platform,
	})
	if err != nil {
		fmt.Fprintf(os.Stderr, "node-reverse browser-simulate failed: %v\n", err)
		return 1
	}
	encoded, _ := json.MarshalIndent(resp, "", "  ")
	fmt.Println(string(encoded))
	if !resp.Success {
		return 1
	}
	return 0
}

func antiBotCommand(args []string) int {
	if len(args) == 0 {
		fmt.Println("Usage: gospider anti-bot <headers|profile> [options]")
		return 2
	}
	switch args[0] {
	case "headers":
		return antiBotHeadersCommand(args[1:])
	case "profile":
		return antiBotProfileCommand(args[1:])
	default:
		fmt.Printf("unknown anti-bot subcommand: %s\n", args[0])
		return 2
	}
}

func antiBotHeadersCommand(args []string) int {
	cmd := flag.NewFlagSet("anti-bot headers", flag.ExitOnError)
	profile := cmd.String("profile", "default", "header profile: default|cloudflare|akamai")
	_ = cmd.Parse(args)

	rotator := antibot.NewUserAgentRotator()
	headers := map[string]string{
		"User-Agent": rotator.GetRandomUserAgent(),
		"Accept":     "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
	}
	switch strings.ToLower(*profile) {
	case "cloudflare":
		headers["sec-ch-ua"] = "\"Not_A Brand\";v=\"8\", \"Chromium\";v=\"120\""
		headers["sec-fetch-site"] = "none"
	case "akamai":
		headers["X-Requested-With"] = "XMLHttpRequest"
	}

	payload := map[string]any{
		"command":     "anti-bot headers",
		"runtime":     "go",
		"profile":     *profile,
		"headers":     headers,
		"fingerprint": fmt.Sprintf("go-%d", time.Now().UnixNano()),
	}
	encoded, _ := json.MarshalIndent(payload, "", "  ")
	fmt.Println(string(encoded))
	return 0
}

func antiBotProfileCommand(args []string) int {
	cmd := flag.NewFlagSet("anti-bot profile", flag.ExitOnError)
	targetURL := cmd.String("url", "", "target URL")
	htmlFile := cmd.String("html-file", "", "local HTML file")
	statusCode := cmd.Int("status-code", 200, "HTTP status code")
	_ = cmd.Parse(args)

	html, resolvedURL := loadHTMLForProfile(*targetURL, *htmlFile)
	if html == "" {
		fmt.Fprintln(os.Stderr, "anti-bot profile requires --url or --html-file")
		return 2
	}

	blocked := detectBlockedHTML(html, *statusCode)
	signals := antiBotSignals(html, *statusCode)
	payload := map[string]any{
		"command":        "anti-bot profile",
		"runtime":        "go",
		"url":            resolvedURL,
		"blocked":        blocked,
		"status_code":    *statusCode,
		"signals":        signals,
		"level":          antiBotLevel(signals, blocked),
		"fingerprint":    fmt.Sprintf("go-%d", time.Now().UnixNano()),
		"recommendation": antiBotRecommendation(blocked, signals),
	}
	encoded, _ := json.MarshalIndent(payload, "", "  ")
	fmt.Println(string(encoded))
	if blocked {
		return 1
	}
	return 0
}

func loadHTMLForProfile(targetURL string, htmlFile string) (string, string) {
	if strings.TrimSpace(htmlFile) != "" {
		data, err := os.ReadFile(htmlFile)
		if err == nil {
			return string(data), targetURL
		}
		return "", targetURL
	}
	if strings.TrimSpace(targetURL) == "" {
		return "", ""
	}
	resp, err := http.Get(targetURL)
	if err != nil {
		return "", targetURL
	}
	defer resp.Body.Close()
	body, err := io.ReadAll(io.LimitReader(resp.Body, 1<<20))
	if err != nil {
		return "", targetURL
	}
	return string(body), targetURL
}

func detectBlockedHTML(html string, statusCode int) bool {
	lower := strings.ToLower(html)
	keywords := []string{
		"access denied",
		"blocked",
		"captcha",
		"forbidden",
		"just a moment",
		"datadome",
		"cf-chl",
	}
	for _, keyword := range keywords {
		if strings.Contains(lower, keyword) {
			return true
		}
	}
	return statusCode == http.StatusForbidden || statusCode == http.StatusTooManyRequests
}

func antiBotSignals(html string, statusCode int) []string {
	lower := strings.ToLower(html)
	signals := make([]string, 0)
	matches := map[string]string{
		"captcha":           "captcha",
		"cf-ray":            "vendor:cloudflare",
		"cf-chl":            "challenge:cloudflare",
		"datadome":          "vendor:datadome",
		"akamai":            "vendor:akamai",
		"just a moment":     "challenge:browser",
		"forbidden":         "status:forbidden",
		"too many requests": "status:throttled",
	}
	for token, signal := range matches {
		if strings.Contains(lower, token) {
			signals = append(signals, signal)
		}
	}
	if statusCode == http.StatusForbidden {
		signals = append(signals, "status:403")
	}
	if statusCode == http.StatusTooManyRequests {
		signals = append(signals, "status:429")
	}
	if len(signals) == 0 {
		signals = append(signals, "clear")
	}
	return signals
}

func antiBotLevel(signals []string, blocked bool) string {
	if !blocked {
		return "low"
	}
	if len(signals) >= 3 {
		return "high"
	}
	return "medium"
}

func antiBotRecommendation(blocked bool, signals []string) string {
	if !blocked {
		return "continue with current session"
	}
	if containsSignal(signals, "captcha") {
		return "enable captcha solving and session reuse"
	}
	if containsSignal(signals, "vendor:cloudflare") {
		return "switch to browser runtime with stealth headers"
	}
	return "rotate identity and proxy before retry"
}

func profileSiteCommand(args []string) int {
	cmd := flag.NewFlagSet("profile-site", flag.ExitOnError)
	targetURL := cmd.String("url", "", "target URL")
	htmlFile := cmd.String("html-file", "", "local HTML file")
	baseURL := cmd.String("base-url", "http://localhost:3000", "NodeReverse service URL")
	_ = cmd.Parse(args)

	html, resolvedURL := loadHTMLForProfile(*targetURL, *htmlFile)
	if html == "" {
		fmt.Fprintln(os.Stderr, "profile-site requires --url or --html-file")
		return 2
	}
	profile := buildSiteProfile(resolvedURL, html)
	if *baseURL != "" {
		client := nodereverse.NewNodeReverseClient(*baseURL)
		detectResp, _ := client.DetectAntiBot(nodereverse.AntiBotProfileRequest{
			HTML: html,
			URL:  resolvedURL,
		})
		profileResp, _ := client.ProfileAntiBot(nodereverse.AntiBotProfileRequest{
			HTML: html,
			URL:  resolvedURL,
		})
		spoofResp, _ := client.SpoofFingerprint(nodereverse.FingerprintSpoofRequest{
			Browser:  "chrome",
			Platform: "windows",
		})
		tlsResp, _ := client.GenerateTLSFingerprint(nodereverse.TLSFingerprintRequest{
			Browser: "chrome",
			Version: "120",
		})
		canvasResp, _ := client.CanvasFingerprint()
		cryptoResp, _ := client.AnalyzeCrypto(html)
		profile["reverse"] = map[string]any{
			"detect":             detectResp,
			"profile":            profileResp,
			"fingerprint_spoof":  spoofResp,
			"tls_fingerprint":    tlsResp,
			"canvas_fingerprint": canvasResp,
			"crypto_analysis":    cryptoResp,
		}
		if focus := reverseFocusPayload(profile["reverse"]); len(focus) > 0 {
			profile["reverse_focus"] = focus
		}
		if profileResp != nil && profileResp.Success {
			profile["anti_bot_level"] = profileResp.Level
			profile["anti_bot_signals"] = profileResp.Signals
			profile["node_reverse_recommended"] = len(profileResp.Signals) > 0
		}
	}
	encoded, _ := json.MarshalIndent(profile, "", "  ")
	fmt.Println(string(encoded))
	return 0
}

func reverseFocusPayload(reversePayload any) map[string]any {
	reverse, ok := reversePayload.(map[string]any)
	if !ok {
		return nil
	}
	var chains []map[string]any
	switch crypto := reverse["crypto_analysis"].(type) {
	case map[string]any:
		analysis, ok := crypto["analysis"].(map[string]any)
		if !ok {
			return nil
		}
		rawChains, ok := analysis["keyFlowChains"].([]any)
		if !ok || len(rawChains) == 0 {
			return nil
		}
		chains = make([]map[string]any, 0, len(rawChains))
		for _, item := range rawChains {
			if chain, ok := item.(map[string]any); ok {
				chains = append(chains, chain)
			}
		}
	case *nodereverse.CryptoAnalyzeResponse:
		for _, item := range crypto.Analysis.KeyFlowChains {
			chains = append(chains, item)
		}
	default:
		return nil
	}
	if len(chains) == 0 {
		return nil
	}
	bestIndex := -1
	bestScore := -1.0
	bestSinkCount := -1
	bestDerivationCount := -1
	for index, chain := range chains {
		score, _ := chain["confidence"].(float64)
		sinkCount := 0
		if sinks, ok := chain["sinks"].([]any); ok {
			sinkCount = len(sinks)
		} else if sinks, ok := chain["sinks"].([]string); ok {
			sinkCount = len(sinks)
		}
		derivationCount := 0
		if derivations, ok := chain["derivations"].([]any); ok {
			derivationCount = len(derivations)
		} else if derivations, ok := chain["derivations"].([]map[string]any); ok {
			derivationCount = len(derivations)
		}
		if bestIndex == -1 || score > bestScore || (score == bestScore && sinkCount > bestSinkCount) || (score == bestScore && sinkCount == bestSinkCount && derivationCount > bestDerivationCount) {
			bestIndex = index
			bestScore = score
			bestSinkCount = sinkCount
			bestDerivationCount = derivationCount
		}
	}
	if bestIndex < 0 {
		return nil
	}
	top := chains[bestIndex]
	sourceKind := "unknown"
	if source, ok := top["source"].(map[string]any); ok {
		if kind, ok := source["kind"].(string); ok && strings.TrimSpace(kind) != "" {
			sourceKind = kind
		}
	}
	primarySink := "unknown-sink"
	if sinks, ok := top["sinks"].([]any); ok && len(sinks) > 0 {
		if sink, ok := sinks[0].(string); ok && strings.TrimSpace(sink) != "" {
			primarySink = sink
		}
	}
	nextSteps := make([]string, 0, 3)
	if strings.HasPrefix(sourceKind, "storage.") {
		nextSteps = append(nextSteps, "instrument browser storage reads first")
	}
	if strings.HasPrefix(sourceKind, "network.") {
		nextSteps = append(nextSteps, "capture response body before key derivation")
	}
	if strings.Contains(primarySink, "crypto.subtle.") {
		nextSteps = append(nextSteps, "hook WebCrypto at the sink boundary")
	}
	if strings.HasPrefix(primarySink, "jwt.") || strings.Contains(fmt.Sprint(reverse["crypto_analysis"]), "HMAC") {
		nextSteps = append(nextSteps, "rebuild canonical signing input before reproducing the sink")
	}
	if len(nextSteps) == 0 {
		nextSteps = append(nextSteps, "trace the chain from source through derivations into the first sink")
	}
	return map[string]any{
		"priority_chain": top,
		"summary":        fmt.Sprintf("trace `%v` from `%s` into `%s`", top["variable"], sourceKind, primarySink),
		"next_steps":     nextSteps,
	}
}

func buildSiteProfile(url string, html string) map[string]any {
	lower := strings.ToLower(html)
	pageType := "generic"
	if strings.Contains(lower, "<li") || strings.Contains(lower, "<ul") {
		pageType = "list"
	}
	if strings.Contains(lower, "<article") || strings.Contains(lower, "<h1") {
		pageType = "detail"
	}
	candidateFields := make([]string, 0)
	for _, pair := range []struct {
		token string
		field string
	}{
		{"<title", "title"},
		{"price", "price"},
		{"author", "author"},
		{"date", "date"},
	} {
		if strings.Contains(lower, pair.token) {
			candidateFields = append(candidateFields, pair.field)
		}
	}
	signals := antiBotSignals(html, 200)
	riskLevel := "low"
	if strings.Contains(lower, "<form") || containsSignal(signals, "captcha") {
		riskLevel = "medium"
	}
	if containsSignal(signals, "captcha") || containsSignal(signals, "vendor:cloudflare") {
		riskLevel = "high"
	}
	recommendedRuntime := "go"
	if pageType == "detail" {
		recommendedRuntime = "python"
	}
	if containsSignal(signals, "vendor:cloudflare") {
		recommendedRuntime = "java"
	}
	return map[string]any{
		"command":                  "profile-site",
		"runtime":                  "go",
		"framework":                "gospider",
		"version":                  version,
		"url":                      url,
		"page_type":                pageType,
		"candidate_fields":         candidateFields,
		"risk_level":               riskLevel,
		"signals":                  signals,
		"recommended_runtime":      recommendedRuntime,
		"anti_bot_recommended":     riskLevel != "low",
		"node_reverse_recommended": false,
	}
}

func aiCommand(args []string) int {
	cmd := flag.NewFlagSet("ai", flag.ExitOnError)
	targetURL := cmd.String("url", "", "target URL")
	htmlFile := cmd.String("html-file", "", "local HTML file")
	configPath := cmd.String("config", "", "shared contract config path")
	instructions := cmd.String("instructions", "", "structured extraction instructions")
	schemaFile := cmd.String("schema-file", "", "JSON schema file path")
	schemaJSON := cmd.String("schema-json", "", "inline JSON schema")
	question := cmd.String("question", "", "page understanding question")
	description := cmd.String("description", "", "natural language spider description")
	outputPath := cmd.String("output", "", "optional output JSON path")
	_ = cmd.Parse(args)

	cfg, err := loadContractConfig(*configPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "config error: %v\n", err)
		return 2
	}

	mode := detectAIMode(*instructions, *question, *description, *schemaFile, *schemaJSON)
	warnings := []string{}
	engine := "heuristic-fallback"
	source := "description"
	resolvedURL := ""
	var result map[string]any

	if mode == "generate-config" {
		result = heuristicAIGenerateConfig(*description)
		if extractor, warningText := newGoAIExtractor(); extractor != nil {
			generated, llmErr := extractor.GenerateSpiderConfig(*description)
			if llmErr == nil && len(generated) > 0 {
				result = generated
				engine = "llm"
			} else if llmErr != nil {
				warnings = append(warnings, llmErr.Error())
			}
		} else if warningText != "" {
			warnings = append(warnings, warningText)
		}
	} else {
		if strings.TrimSpace(*targetURL) == "" && len(cfg.Crawl.URLs) > 0 {
			*targetURL = cfg.Crawl.URLs[0]
			source = "config"
		}
		if strings.TrimSpace(*htmlFile) != "" {
			source = "html-file"
		} else if strings.TrimSpace(*targetURL) != "" && source != "config" {
			source = "url"
		}

		html, candidateURL := loadHTMLForProfile(*targetURL, *htmlFile)
		if html == "" {
			fmt.Fprintln(os.Stderr, "ai requires --url, --html-file, or a config with crawl.urls")
			return 2
		}
		resolvedURL = candidateURL
		if resolvedURL == "" && strings.TrimSpace(*htmlFile) != "" {
			resolvedURL = "file://" + filepath.ToSlash(*htmlFile)
		}

		switch mode {
		case "extract":
			schema, schemaErr := loadAISchema(*schemaFile, *schemaJSON)
			if schemaErr != nil {
				fmt.Fprintf(os.Stderr, "invalid ai schema: %v\n", schemaErr)
				return 2
			}
			result = heuristicAIExtract(resolvedURL, html, schema)
			instructionText := strings.TrimSpace(*instructions)
			if instructionText == "" {
				instructionText = "提取页面中的核心结构化字段"
			}
			if extractor, warningText := newGoAIExtractor(); extractor != nil {
				extracted, llmErr := extractor.ExtractStructured(truncateAIContent(html, 12000), instructionText, schema)
				if llmErr == nil && len(extracted) > 0 {
					result = extracted
					engine = "llm"
				} else if llmErr != nil {
					warnings = append(warnings, llmErr.Error())
				}
			} else if warningText != "" {
				warnings = append(warnings, warningText)
			}
		case "understand":
			result = heuristicAIUnderstand(resolvedURL, html, *question)
			questionText := strings.TrimSpace(*question)
			if questionText == "" {
				questionText = "请总结页面类型、核心内容和推荐提取字段。"
			}
			if extractor, warningText := newGoAIExtractor(); extractor != nil {
				answer, llmErr := extractor.UnderstandPage(truncateAIContent(html, 12000), questionText)
				if llmErr == nil && strings.TrimSpace(answer) != "" {
					result = map[string]any{
						"answer":       answer,
						"page_profile": buildSiteProfile(resolvedURL, html),
					}
					engine = "llm"
				} else if llmErr != nil {
					warnings = append(warnings, llmErr.Error())
				}
			} else if warningText != "" {
				warnings = append(warnings, warningText)
			}
		default:
			fmt.Fprintf(os.Stderr, "unsupported ai mode: %s\n", mode)
			return 2
		}
	}

	payload := map[string]any{
		"command":      "ai",
		"runtime":      "go",
		"mode":         mode,
		"summary":      "passed",
		"summary_text": fmt.Sprintf("%s mode completed with engine %s", mode, engine),
		"exit_code":    0,
		"engine":       engine,
		"source":       source,
		"warnings":     warnings,
		"result":       result,
	}
	if resolvedURL != "" {
		payload["url"] = resolvedURL
	}

	encoded, marshalErr := json.MarshalIndent(payload, "", "  ")
	if marshalErr != nil {
		fmt.Fprintf(os.Stderr, "failed to encode ai payload: %v\n", marshalErr)
		return 1
	}
	if strings.TrimSpace(*outputPath) != "" {
		if err := os.MkdirAll(filepath.Dir(*outputPath), 0o755); err != nil {
			fmt.Fprintf(os.Stderr, "failed to prepare ai output dir: %v\n", err)
			return 1
		}
		if err := os.WriteFile(*outputPath, encoded, 0o644); err != nil {
			fmt.Fprintf(os.Stderr, "failed to write ai output: %v\n", err)
			return 1
		}
	}
	fmt.Println(string(encoded))
	return 0
}

func detectAIMode(instructions string, question string, description string, schemaFile string, schemaJSON string) string {
	if strings.TrimSpace(description) != "" {
		return "generate-config"
	}
	if strings.TrimSpace(question) != "" {
		return "understand"
	}
	if strings.TrimSpace(instructions) != "" || strings.TrimSpace(schemaFile) != "" || strings.TrimSpace(schemaJSON) != "" {
		return "extract"
	}
	return "understand"
}

func newGoAIExtractor() (*spiderai.AIExtractor, string) {
	config := spiderai.DefaultAIConfig()
	if strings.TrimSpace(config.APIKey) == "" {
		return nil, "AI_API_KEY / OPENAI_API_KEY not set; used heuristic fallback"
	}
	return spiderai.NewAIExtractor(config), ""
}

func loadAISchema(schemaFile string, schemaJSON string) (map[string]any, error) {
	if strings.TrimSpace(schemaFile) != "" {
		raw, err := os.ReadFile(schemaFile)
		if err != nil {
			return nil, err
		}
		return parseAISchemaJSON(string(raw))
	}
	if strings.TrimSpace(schemaJSON) != "" {
		return parseAISchemaJSON(schemaJSON)
	}
	return aiDefaultSchema(), nil
}

func parseAISchemaJSON(raw string) (map[string]any, error) {
	var payload map[string]any
	if err := json.Unmarshal([]byte(raw), &payload); err != nil {
		return nil, err
	}
	return payload, nil
}

func aiDefaultSchema() map[string]any {
	return map[string]any{
		"type": "object",
		"properties": map[string]any{
			"title":   map[string]any{"type": "string"},
			"url":     map[string]any{"type": "string"},
			"summary": map[string]any{"type": "string"},
		},
	}
}

func heuristicAIUnderstand(url string, html string, question string) map[string]any {
	profile := buildSiteProfile(url, html)
	questionText := strings.TrimSpace(question)
	if questionText == "" {
		questionText = "请总结页面类型、核心内容和推荐提取字段。"
	}
	answer := fmt.Sprintf(
		"页面类型=%v，候选字段=%v，风险等级=%v。问题：%s",
		profile["page_type"],
		profile["candidate_fields"],
		profile["risk_level"],
		questionText,
	)
	return map[string]any{
		"answer":       answer,
		"page_profile": profile,
	}
}

func heuristicAIGenerateConfig(description string) map[string]any {
	fields := []string{"title", "url", "summary"}
	lower := strings.ToLower(description)
	if strings.Contains(lower, "price") || strings.Contains(lower, "价格") {
		fields = append(fields, "price")
	}
	if strings.Contains(lower, "author") || strings.Contains(lower, "作者") {
		fields = append(fields, "author")
	}
	if strings.Contains(lower, "date") || strings.Contains(lower, "时间") || strings.Contains(lower, "日期") {
		fields = append(fields, "published_at")
	}
	if strings.Contains(lower, "content") || strings.Contains(lower, "正文") {
		fields = append(fields, "content")
	}

	startURLs := []string{"https://example.com"}
	for _, token := range strings.Fields(description) {
		candidate := strings.Trim(token, " \t\r\n,.;'\"()[]{}")
		if strings.HasPrefix(candidate, "http://") || strings.HasPrefix(candidate, "https://") {
			startURLs = []string{candidate}
			break
		}
	}

	return map[string]any{
		"start_urls": startURLs,
		"rules": []map[string]any{
			{
				"name":         "auto-generated",
				"pattern":      ".*",
				"extract":      fields,
				"follow_links": true,
			},
		},
		"settings": map[string]any{
			"concurrency": 3,
			"max_depth":   2,
			"delay":       500,
		},
		"source_description": description,
	}
}

func heuristicAIExtract(url string, html string, schema map[string]any) map[string]any {
	properties, _ := schema["properties"].(map[string]any)
	if len(properties) == 0 {
		properties = aiDefaultSchema()["properties"].(map[string]any)
	}
	doc, _ := goquery.NewDocumentFromReader(strings.NewReader(html))
	text := aiCompactText(aiDocumentText(doc, html))
	result := map[string]any{}
	for fieldName, rawSpec := range properties {
		spec, _ := rawSpec.(map[string]any)
		expectedType, _ := spec["type"].(string)
		result[fieldName] = heuristicAIFieldValue(fieldName, expectedType, url, text, doc)
	}
	return result
}

func aiSchemaFromCandidateFields(fields []string) map[string]any {
	properties := map[string]any{}
	ordered := []string{"title", "summary", "url"}
	for _, field := range fields {
		found := false
		for _, existing := range ordered {
			if existing == field {
				found = true
				break
			}
		}
		if !found {
			ordered = append(ordered, field)
		}
	}
	for _, field := range ordered {
		lower := strings.ToLower(field)
		switch {
		case strings.Contains(lower, "price") || strings.Contains(lower, "amount") || strings.Contains(lower, "score") || strings.Contains(lower, "rating"):
			properties[field] = map[string]any{"type": "number"}
		case strings.Contains(lower, "count") || strings.Contains(lower, "total"):
			properties[field] = map[string]any{"type": "integer"}
		case strings.Contains(lower, "images") || strings.Contains(lower, "links") || strings.Contains(lower, "tags") || strings.Contains(lower, "items"):
			properties[field] = map[string]any{"type": "array", "items": map[string]any{"type": "string"}}
		default:
			properties[field] = map[string]any{"type": "string"}
		}
	}
	return map[string]any{"type": "object", "properties": properties}
}

func buildAIBlueprint(resolvedURL string, spiderName string, profile map[string]any, schema map[string]any, html string) map[string]any {
	candidateFields := []string{}
	if rawFields, ok := profile["candidate_fields"].([]string); ok {
		candidateFields = append(candidateFields, rawFields...)
	} else if rawFields, ok := profile["candidate_fields"].([]any); ok {
		for _, item := range rawFields {
			candidateFields = append(candidateFields, fmt.Sprint(item))
		}
	}
	schemaProperties, _ := schema["properties"].(map[string]any)
	fieldNames := make([]string, 0, len(schemaProperties))
	for key := range schemaProperties {
		fieldNames = append(fieldNames, key)
	}
	sort.Strings(fieldNames)
	pageType := fmt.Sprint(profile["page_type"])
	riskLevel := fmt.Sprint(profile["risk_level"])
	lowered := strings.ToLower(html)
	signals := []string{}
	if rawSignals, ok := profile["signals"].([]string); ok {
		signals = append(signals, rawSignals...)
	} else if rawSignals, ok := profile["signals"].([]any); ok {
		for _, item := range rawSignals {
			signals = append(signals, fmt.Sprint(item))
		}
	}
	return map[string]any{
		"version":          1,
		"spider_name":      spiderName,
		"resolved_url":     resolvedURL,
		"page_type":        pageType,
		"candidate_fields": candidateFields,
		"schema":           schema,
		"extraction_prompt": fmt.Sprintf(
			"请从页面中提取以下字段，并只返回 JSON：%s。缺失字段返回空字符串或空数组。",
			strings.Join(fieldNames, ", "),
		),
		"follow_rules": []map[string]any{
			{
				"name":        "same-domain-content",
				"enabled":     true,
				"description": "优先跟进同域详情页和内容页链接",
			},
		},
		"pagination": map[string]any{
			"enabled":   pageType == "list" || pageType == "generic" || strings.Contains(lowered, `rel="next"`) || strings.Contains(lowered, "pagination") || strings.Contains(lowered, "page=") || strings.Contains(lowered, "next page") || strings.Contains(lowered, "下一页"),
			"strategy":  "follow next page or numbered pagination links",
			"selectors": []string{"a[rel='next']", ".next", ".pagination a"},
		},
		"authentication": map[string]any{
			"required": strings.Contains(lowered, `type="password"`) || strings.Contains(lowered, `type='password'`) || strings.Contains(lowered, "login") || strings.Contains(lowered, "sign in") || strings.Contains(lowered, "signin") || strings.Contains(lowered, "登录"),
			"strategy": map[bool]string{true: "capture session/login flow before crawl", false: "not required"}[strings.Contains(lowered, `type="password"`) || strings.Contains(lowered, `type='password'`) || strings.Contains(lowered, "login") || strings.Contains(lowered, "sign in") || strings.Contains(lowered, "signin") || strings.Contains(lowered, "登录")],
		},
		"javascript_runtime": map[string]any{
			"required":           strings.Contains(lowered, "__next_data__") || strings.Contains(lowered, "window.__") || strings.Contains(lowered, "webpack") || strings.Contains(lowered, "fetch(") || strings.Contains(lowered, "graphql") || strings.Contains(lowered, "xhr"),
			"recommended_runner": map[bool]string{true: "browser", false: "http"}[strings.Contains(lowered, "__next_data__") || strings.Contains(lowered, "window.__") || strings.Contains(lowered, "webpack") || strings.Contains(lowered, "fetch(") || strings.Contains(lowered, "graphql") || strings.Contains(lowered, "xhr")],
		},
		"reverse_engineering": map[string]any{
			"required": strings.Contains(lowered, "crypto") || strings.Contains(lowered, "signature") || strings.Contains(lowered, "token") || strings.Contains(lowered, "webpack") || strings.Contains(lowered, "obfusc") || strings.Contains(lowered, "encrypt") || strings.Contains(lowered, "decrypt"),
			"notes":    map[bool]string{true: "inspect network/API signing or obfuscated scripts", false: "not required"}[strings.Contains(lowered, "crypto") || strings.Contains(lowered, "signature") || strings.Contains(lowered, "token") || strings.Contains(lowered, "webpack") || strings.Contains(lowered, "obfusc") || strings.Contains(lowered, "encrypt") || strings.Contains(lowered, "decrypt")],
		},
		"anti_bot_strategy": map[string]any{
			"risk_level":         riskLevel,
			"signals":            signals,
			"recommended_runner": map[bool]string{true: "browser", false: "http"}[riskLevel != "low"],
			"notes":              "高风险页面建议先走浏览器模式并降低抓取速率",
		},
	}
}

func renderGoAISpiderTemplate(spiderName string, spiderDomain string) string {
	constructorName := "New" + strings.Title(strings.ReplaceAll(spiderName, "_", " "))
	constructorName = strings.ReplaceAll(constructorName, " ", "") + "Spider"
	return fmt.Sprintf(`package spiders

// scrapy: url=https://%s

import (
	"strings"

	spiderai "gospider/ai"
	scrapyapi "gospider/scrapy"
	projectruntime "gospider/scrapy/project"
)

func %s() *scrapyapi.Spider {
	assets := projectruntime.LoadAIProjectAssets(".")
	var parse scrapyapi.Callback
	parse = func(response *scrapyapi.Response) ([]any, error) {
		cfg := spiderai.DefaultAIConfig()
		data := map[string]any{
			"title":   response.CSS("title").Get(),
			"summary": response.XPath("//meta[@name='description']/@content").Get(),
			"url":     response.URL,
		}
		if strings.TrimSpace(cfg.APIKey) != "" {
			extractor := spiderai.NewAIExtractor(cfg)
			if extracted, err := extractor.ExtractStructured(response.Text, assets.ExtractionPrompt, assets.Schema); err == nil && len(extracted) > 0 {
				data = extracted
			}
		}
		item := scrapyapi.NewItem().Set("framework", "gospider-ai")
		for key, value := range data {
			item = item.Set(key, value)
		}
		outputs := []any{item}
		for _, req := range projectruntime.CollectAIPaginationRequests(response, parse, assets) {
			outputs = append(outputs, req)
		}
		return outputs, nil
	}
	spider := scrapyapi.NewSpider("%s", parse).AddStartURL("https://%s")
	return projectruntime.ApplyAIStartMeta(spider, assets)
}

func init() {
	projectruntime.RegisterSpider("%s", %s)
}
`, spiderDomain, constructorName, spiderName, spiderDomain, spiderName, constructorName)
}

func renderGoStandardSpiderTemplate(spiderName string, spiderDomain string) string {
	constructorName := "New" + strings.Title(strings.ReplaceAll(spiderName, "_", " "))
	constructorName = strings.ReplaceAll(constructorName, " ", "") + "Spider"
	return fmt.Sprintf(`package spiders

// scrapy: url=https://%s

import (
	scrapyapi "gospider/scrapy"
	projectruntime "gospider/scrapy/project"
)

func %s() *scrapyapi.Spider {
	return scrapyapi.NewSpider("%s", func(response *scrapyapi.Response) ([]any, error) {
		return []any{
			scrapyapi.NewItem().
				Set("title", response.CSS("title").Get()).
				Set("url", response.URL).
				Set("framework", "gospider"),
		}, nil
	}).AddStartURL("https://%s")
}

func init() {
	projectruntime.RegisterSpider("%s", %s)
}
`, spiderDomain, constructorName, spiderName, spiderDomain, spiderName, constructorName)
}

func deriveDomainFromURL(raw string) string {
	if strings.TrimSpace(raw) == "" {
		return "example.com"
	}
	if parsed, err := url.Parse(raw); err == nil && strings.TrimSpace(parsed.Host) != "" {
		return parsed.Host
	}
	return "example.com"
}

func authValidationStatus(html string) (bool, []string) {
	lower := strings.ToLower(html)
	indicators := []string{}
	if strings.Contains(lower, `type="password"`) || strings.Contains(lower, `type='password'`) {
		indicators = append(indicators, "password-input")
	}
	if strings.Contains(lower, "login") || strings.Contains(lower, "sign in") || strings.Contains(lower, "signin") || strings.Contains(lower, "登录") {
		indicators = append(indicators, "login-marker")
	}
	return len(indicators) == 0, indicators
}

func heuristicAIFieldValue(fieldName string, expectedType string, url string, text string, doc *goquery.Document) any {
	lower := strings.ToLower(fieldName)
	switch {
	case strings.Contains(lower, "title") || strings.Contains(lower, "headline"):
		return firstNonEmptyString(
			aiMetaValue(doc, "property", "og:title"),
			aiMetaValue(doc, "name", "twitter:title"),
			aiSelectionText(doc, "title"),
			aiSelectionText(doc, "h1"),
		)
	case lower == "url" || strings.Contains(lower, "link"):
		if expectedType == "array" {
			return []string{url}
		}
		return url
	case strings.Contains(lower, "summary") || strings.Contains(lower, "description") || lower == "desc":
		return firstNonEmptyString(
			aiMetaValue(doc, "name", "description"),
			aiMetaValue(doc, "property", "og:description"),
			aiTruncate(text, 220),
		)
	case strings.Contains(lower, "content") || strings.Contains(lower, "body") || lower == "text":
		return aiTruncate(text, 1200)
	case strings.Contains(lower, "author"):
		return firstNonEmptyString(
			aiMetaValue(doc, "name", "author"),
			aiMetaValue(doc, "property", "article:author"),
			aiSelectionText(doc, "[rel='author']"),
		)
	case strings.Contains(lower, "date") || strings.Contains(lower, "time") || strings.Contains(lower, "published"):
		return firstNonEmptyString(
			aiMetaValue(doc, "property", "article:published_time"),
			aiMetaValue(doc, "name", "pubdate"),
			aiSelectionAttr(doc, "time", "datetime"),
			aiSelectionText(doc, "time"),
		)
	case strings.Contains(lower, "image") || strings.Contains(lower, "thumbnail") || strings.Contains(lower, "cover"):
		return firstNonEmptyString(
			aiMetaValue(doc, "property", "og:image"),
			aiSelectionAttr(doc, "img", "src"),
		)
	case strings.Contains(lower, "price"):
		return aiFindToken(text, []string{"¥", "￥", "$", "usd", "rmb"})
	default:
		if expectedType == "array" {
			return []string{}
		}
		return ""
	}
}

func aiDocumentText(doc *goquery.Document, html string) string {
	if doc != nil {
		if body := strings.TrimSpace(doc.Find("body").Text()); body != "" {
			return body
		}
		if all := strings.TrimSpace(doc.Text()); all != "" {
			return all
		}
	}
	return html
}

func aiCompactText(value string) string {
	return strings.Join(strings.Fields(strings.TrimSpace(value)), " ")
}

func aiTruncate(value string, max int) string {
	compact := aiCompactText(value)
	if len(compact) <= max {
		return compact
	}
	return strings.TrimSpace(compact[:max]) + "..."
}

func aiSelectionText(doc *goquery.Document, selector string) string {
	if doc == nil {
		return ""
	}
	return aiCompactText(doc.Find(selector).First().Text())
}

func aiSelectionAttr(doc *goquery.Document, selector string, attr string) string {
	if doc == nil {
		return ""
	}
	value, _ := doc.Find(selector).First().Attr(attr)
	return strings.TrimSpace(value)
}

func aiMetaValue(doc *goquery.Document, attr string, name string) string {
	if doc == nil {
		return ""
	}
	value, _ := doc.Find(fmt.Sprintf("meta[%s='%s']", attr, name)).First().Attr("content")
	return strings.TrimSpace(value)
}

func aiFindToken(text string, tokens []string) string {
	for _, item := range strings.Fields(strings.ToLower(text)) {
		for _, token := range tokens {
			if strings.Contains(item, strings.ToLower(token)) {
				return strings.Trim(item, ".,;:!?()[]{}\"'")
			}
		}
	}
	return ""
}

func firstNonEmptyString(values ...string) string {
	for _, value := range values {
		if strings.TrimSpace(value) != "" {
			return strings.TrimSpace(value)
		}
	}
	return ""
}

func truncateAIContent(content string, max int) string {
	if len(content) <= max {
		return content
	}
	return content[:max]
}

func selectorStudioCommand(args []string) int {
	cmd := flag.NewFlagSet("selector-studio", flag.ExitOnError)
	targetURL := cmd.String("url", "", "target URL")
	htmlFile := cmd.String("html-file", "", "local HTML file")
	mode := cmd.String("type", "css", "extract mode: css|css_attr|xpath|regex")
	expr := cmd.String("expr", "", "selector or expression")
	attr := cmd.String("attr", "", "attribute name for css_attr")
	_ = cmd.Parse(args)

	html, resolvedURL := loadHTMLForProfile(*targetURL, *htmlFile)
	if html == "" {
		fmt.Fprintln(os.Stderr, "selector-studio requires --url or --html-file")
		return 2
	}
	p := parser.NewHTMLParser(html)
	if p == nil {
		fmt.Fprintln(os.Stderr, "failed to initialize html parser")
		return 1
	}
	values := []string{}
	switch strings.ToLower(strings.TrimSpace(*mode)) {
	case "css":
		values = p.CSS(*expr)
	case "css_attr":
		values = p.CSSAttr(*expr, *attr)
	case "xpath":
		if result, err := p.XPathFirstStrict(*expr); err == nil && strings.TrimSpace(result) != "" {
			values = []string{result}
		}
	case "regex":
		if compiled := parser.MustCompileRegex(*expr); compiled != nil {
			matches := compiled.FindAllStringSubmatch(html, -1)
			for _, match := range matches {
				if len(match) > 1 {
					values = append(values, match[1])
				} else if len(match) > 0 {
					values = append(values, match[0])
				}
			}
		}
	}
	payload := map[string]any{
		"command":   "selector-studio",
		"runtime":   "go",
		"framework": "gospider",
		"version":   version,
		"url":       resolvedURL,
		"type":      *mode,
		"expr":      *expr,
		"attr":      *attr,
		"count":     len(values),
		"values":    values,
	}
	encoded, _ := json.MarshalIndent(payload, "", "  ")
	fmt.Println(string(encoded))
	return 0
}

type sitemapURLSet struct {
	URLs []string
}

func sitemapDiscoverCommand(args []string) int {
	cmd := flag.NewFlagSet("sitemap-discover", flag.ExitOnError)
	targetURL := cmd.String("url", "", "target site URL")
	sitemapFile := cmd.String("sitemap-file", "", "local sitemap XML file")
	_ = cmd.Parse(args)

	content := ""
	resolved := ""
	switch {
	case strings.TrimSpace(*sitemapFile) != "":
		data, err := os.ReadFile(*sitemapFile)
		if err != nil {
			fmt.Fprintf(os.Stderr, "failed to read sitemap file: %v\n", err)
			return 1
		}
		content = string(data)
		resolved = *sitemapFile
	case strings.TrimSpace(*targetURL) != "":
		candidate := strings.TrimRight(*targetURL, "/") + "/sitemap.xml"
		resp, err := http.Get(candidate)
		if err != nil {
			fmt.Fprintf(os.Stderr, "failed to fetch sitemap: %v\n", err)
			return 1
		}
		defer resp.Body.Close()
		body, err := io.ReadAll(io.LimitReader(resp.Body, 2<<20))
		if err != nil {
			fmt.Fprintf(os.Stderr, "failed to read sitemap response: %v\n", err)
			return 1
		}
		content = string(body)
		resolved = candidate
	default:
		fmt.Fprintln(os.Stderr, "sitemap-discover requires --url or --sitemap-file")
		return 2
	}

	urls := parseSitemapURLs(content)
	payload := map[string]any{
		"command":   "sitemap-discover",
		"runtime":   "go",
		"source":    resolved,
		"url_count": len(urls),
		"urls":      urls,
	}
	encoded, _ := json.MarshalIndent(payload, "", "  ")
	fmt.Println(string(encoded))
	return 0
}

func parseSitemapURLs(content string) []string {
	type urlEntry struct {
		Loc string `xml:"loc"`
	}
	type urlSet struct {
		Entries []urlEntry `xml:"url"`
	}
	type sitemapIndex struct {
		Entries []urlEntry `xml:"sitemap"`
	}
	urls := make([]string, 0)
	var set urlSet
	if err := xml.Unmarshal([]byte(content), &set); err == nil {
		for _, entry := range set.Entries {
			if strings.TrimSpace(entry.Loc) != "" {
				urls = append(urls, strings.TrimSpace(entry.Loc))
			}
		}
	}
	if len(urls) > 0 {
		return urls
	}
	var index sitemapIndex
	if err := xml.Unmarshal([]byte(content), &index); err == nil {
		for _, entry := range index.Entries {
			if strings.TrimSpace(entry.Loc) != "" {
				urls = append(urls, strings.TrimSpace(entry.Loc))
			}
		}
	}
	return urls
}

func pluginsCommand(args []string) int {
	if len(args) == 0 || (args[0] != "list" && args[0] != "run") {
		fmt.Fprintln(os.Stderr, "usage: plugins <list|run> ...")
		return 2
	}
	if args[0] == "run" {
		return pluginsRunCommand(args[1:])
	}
	cmd := flag.NewFlagSet("plugins list", flag.ExitOnError)
	manifest := cmd.String("manifest", filepath.Join("contracts", "integration-catalog.json"), "plugin/integration manifest path")
	_ = cmd.Parse(args[1:])
	data, err := os.ReadFile(*manifest)
	if err != nil {
		fmt.Fprintf(os.Stderr, "failed to read manifest: %v\n", err)
		return 1
	}
	var payload map[string]any
	if err := json.Unmarshal(data, &payload); err != nil {
		fmt.Fprintf(os.Stderr, "invalid manifest json: %v\n", err)
		return 1
	}
	result := map[string]any{
		"command":  "plugins list",
		"runtime":  "go",
		"manifest": *manifest,
		"plugins":  firstNonNil(payload["plugins"], payload["entrypoints"]),
	}
	encoded, _ := json.MarshalIndent(result, "", "  ")
	fmt.Println(string(encoded))
	return 0
}

func pluginsRunCommand(args []string) int {
	pluginID := ""
	manifest := filepath.Join("contracts", "integration-catalog.json")
	pluginArgs := []string{}
	for index := 0; index < len(args); index++ {
		switch args[index] {
		case "--plugin":
			if index+1 >= len(args) {
				fmt.Fprintln(os.Stderr, "plugins run requires a value for --plugin")
				return 2
			}
			pluginID = args[index+1]
			index++
		case "--manifest":
			if index+1 >= len(args) {
				fmt.Fprintln(os.Stderr, "plugins run requires a value for --manifest")
				return 2
			}
			manifest = args[index+1]
			index++
		case "--":
			pluginArgs = append(pluginArgs, args[index+1:]...)
			index = len(args)
		default:
			pluginArgs = append(pluginArgs, args[index])
		}
	}
	if strings.TrimSpace(pluginID) == "" {
		fmt.Fprintln(os.Stderr, "plugins run requires --plugin")
		return 2
	}
	_ = manifest
	switch pluginID {
	case "profile-site":
		return profileSiteCommand(pluginArgs)
	case "sitemap-discover":
		return sitemapDiscoverCommand(pluginArgs)
	case "selector-studio":
		return selectorStudioCommand(pluginArgs)
	case "anti-bot":
		return antiBotCommand(pluginArgs)
	case "node-reverse":
		return nodeReverseCommand(pluginArgs)
	default:
		fmt.Fprintf(os.Stderr, "unknown plugin id: %s\n", pluginID)
		return 2
	}
}

func firstNonNil(values ...any) any {
	for _, value := range values {
		if value != nil {
			return value
		}
	}
	return nil
}

func antiBotHeaders(cfg contractConfig) map[string]string {
	if !cfg.AntiBot.Enabled {
		return map[string]string{}
	}
	rotator := antibot.NewUserAgentRotator()
	profile := strings.ToLower(strings.TrimSpace(cfg.AntiBot.Profile))
	headers := map[string]string{
		"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
	}
	switch profile {
	case "cloudflare":
		headers["User-Agent"] = rotator.GetBrowserUserAgent("chrome")
		headers["sec-ch-ua"] = "\"Not_A Brand\";v=\"8\", \"Chromium\";v=\"120\""
		headers["sec-fetch-site"] = "none"
	case "akamai":
		headers["User-Agent"] = rotator.GetBrowserUserAgent("chrome")
		headers["X-Requested-With"] = "XMLHttpRequest"
	default:
		headers["User-Agent"] = rotator.GetRandomUserAgent()
	}
	return headers
}

func antiBotUserAgent(cfg contractConfig) string {
	return antiBotHeaders(cfg)["User-Agent"]
}

func antiBotProxy(cfg contractConfig) string {
	value := strings.TrimSpace(cfg.AntiBot.ProxyPool)
	if value == "" || value == "local" {
		return ""
	}
	for _, item := range strings.Split(value, ",") {
		trimmed := strings.TrimSpace(item)
		if trimmed != "" {
			return trimmed
		}
	}
	return ""
}

func discoverSitemapTargets(seedURL string, cfg contractConfig) []string {
	source := strings.TrimSpace(cfg.Sitemap.URL)
	if source == "" && seedURL != "" {
		source = strings.TrimRight(seedURL, "/") + "/sitemap.xml"
	}
	if source == "" {
		return nil
	}
	resp, err := http.Get(source)
	if err != nil {
		return nil
	}
	defer resp.Body.Close()
	body, err := io.ReadAll(io.LimitReader(resp.Body, 2<<20))
	if err != nil {
		return nil
	}
	urls := parseSitemapURLs(string(body))
	if cfg.Sitemap.MaxURLs > 0 && len(urls) > cfg.Sitemap.MaxURLs {
		return urls[:cfg.Sitemap.MaxURLs]
	}
	return urls
}

func mergeTargets(base []string, extra []string) []string {
	seen := map[string]bool{}
	merged := make([]string, 0, len(base)+len(extra))
	for _, target := range append(base, extra...) {
		if strings.TrimSpace(target) == "" || seen[target] {
			continue
		}
		seen[target] = true
		merged = append(merged, target)
	}
	return merged
}

func writeDatasetJSONL(path string, rows []map[string]interface{}) error {
	if err := os.MkdirAll(filepath.Dir(path), 0755); err != nil {
		return err
	}
	var builder strings.Builder
	for _, row := range rows {
		encoded, err := json.Marshal(row)
		if err != nil {
			return err
		}
		builder.Write(encoded)
		builder.WriteByte('\n')
		_ = storage.MirrorDatasetRow(row)
	}
	return os.WriteFile(path, []byte(builder.String()), 0644)
}

func writeScrapyCSV(path string, rows []map[string]string) error {
	file, err := os.Create(path)
	if err != nil {
		return err
	}
	defer file.Close()

	writer := csv.NewWriter(file)
	defer writer.Flush()
	headers := []string{"title", "url", "snippet", "source", "time"}
	if err := writer.Write(headers); err != nil {
		return err
	}
	for _, row := range rows {
		record := []string{row["title"], row["url"], row["snippet"], row["source"], row["time"]}
		if err := writer.Write(record); err != nil {
			return err
		}
	}
	return nil
}

func writeScrapyMarkdown(path string, rows []map[string]string) error {
	var builder strings.Builder
	builder.WriteString("# Scrapy Export\n\n")
	for index, row := range rows {
		builder.WriteString(fmt.Sprintf("## %d. %s\n\n", index+1, row["title"]))
		builder.WriteString(fmt.Sprintf("- URL: %s\n", row["url"]))
		if row["snippet"] != "" {
			builder.WriteString(fmt.Sprintf("- Snippet: %s\n", row["snippet"]))
		}
		if row["source"] != "" {
			builder.WriteString(fmt.Sprintf("- Source: %s\n", row["source"]))
		}
		builder.WriteString("\n")
	}
	return os.WriteFile(path, []byte(builder.String()), 0644)
}

func validateScrapyPluginManifest(path string) error {
	data, err := os.ReadFile(path)
	if err != nil {
		return err
	}
	var payload any
	if err := json.Unmarshal(data, &payload); err != nil {
		return fmt.Errorf("invalid plugin manifest json: %w", err)
	}
	object, ok := payload.(map[string]any)
	if !ok {
		return fmt.Errorf("plugin manifest must be an object")
	}
	if version, exists := object["version"]; exists {
		number, ok := version.(float64)
		if !ok || number < 1 || float64(int(number)) != number {
			return fmt.Errorf("plugin manifest version must be an integer >= 1")
		}
	}
	items, ok := object["plugins"].([]any)
	if !ok {
		return fmt.Errorf("plugin manifest must contain a plugins array")
	}
	for _, item := range items {
		switch value := item.(type) {
		case string:
			if strings.TrimSpace(value) == "" {
				return fmt.Errorf("plugin name must be a non-empty string")
			}
		case map[string]any:
			name, ok := value["name"].(string)
			if !ok || strings.TrimSpace(name) == "" {
				return fmt.Errorf("plugin object must include a non-empty name")
			}
			if enabled, exists := value["enabled"]; exists {
				if _, ok := enabled.(bool); !ok {
					return fmt.Errorf("plugin enabled must be a boolean")
				}
			}
			if priority, exists := value["priority"]; exists {
				number, ok := priority.(float64)
				if !ok || float64(int(number)) != number {
					return fmt.Errorf("plugin priority must be an integer")
				}
			}
			if config, exists := value["config"]; exists {
				if _, ok := config.(map[string]any); !ok {
					return fmt.Errorf("plugin config must be an object")
				}
			}
		default:
			return fmt.Errorf("plugin entries must be strings or objects")
		}
	}
	return nil
}

func maxInt(values ...int) int {
	maxValue := 0
	for _, value := range values {
		if value > maxValue {
			maxValue = value
		}
	}
	return maxValue
}

func containsSignal(signals []string, target string) bool {
	for _, signal := range signals {
		if signal == target {
			return true
		}
	}
	return false
}

func pythonCommand() string {
	if value := os.Getenv("SPIDER_PYTHON"); value != "" {
		return value
	}
	candidates := []string{
		filepath.Join("..", ".venv", "Scripts", "python.exe"),
		filepath.Join("..", "..", ".venv", "Scripts", "python.exe"),
		"python",
	}
	for _, candidate := range candidates {
		if candidate == "python" {
			return candidate
		}
		if _, err := os.Stat(candidate); err == nil {
			return candidate
		}
	}
	return "python"
}

func sharedToolPath(name string) string {
	if name == "playwright_fetch.py" {
		for _, envName := range []string{"GOSPIDER_PLAYWRIGHT_HELPER", "SPIDER_PLAYWRIGHT_HELPER"} {
			if value := strings.TrimSpace(os.Getenv(envName)); value != "" {
				return value
			}
		}
	}
	candidates := []string{
		filepath.Join("..", "tools", name),
		filepath.Join("..", "..", "tools", name),
	}
	for _, candidate := range candidates {
		if _, err := os.Stat(candidate); err == nil {
			return candidate
		}
	}
	return filepath.Join("..", "tools", name)
}

func helperScriptPath() string {
	return sharedToolPath("playwright_fetch.py")
}

func defaultAuthActionExamples() []map[string]any {
	return []map[string]any{
		{"type": "goto", "url": "https://example.com/login"},
		{"type": "type", "selector": "#username", "value": "demo"},
		{"type": "type", "selector": "#password", "value": "secret"},
		{
			"type": "if",
			"when": map[string]any{"selector_exists": "#otp"},
			"then": []map[string]any{{"type": "mfa_totp", "selector": "#otp", "totp_env": "SPIDER_AUTH_TOTP_SECRET"}},
		},
		{
			"type": "if",
			"when": map[string]any{"selector_exists": ".cf-turnstile,[data-sitekey]"},
			"then": []map[string]any{{
				"type": "captcha_solve", "challenge": "turnstile", "selector": ".cf-turnstile,[data-sitekey]", "provider": "anticaptcha", "save_as": "captcha_token",
			}},
		},
		{"type": "submit", "selector": "#password"},
		{"type": "wait_network_idle"},
		{"type": "reverse_profile", "save_as": "reverse_runtime"},
		{"type": "assert", "url_contains": "/dashboard"},
		{"type": "save_as", "value": "url", "save_as": "final_url"},
	}
}

func runSharedPythonTool(scriptName string, toolArgs []string) int {
	args := append([]string{sharedToolPath(scriptName)}, toolArgs...)
	cmd := exec.Command(pythonCommand(), args...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		if exitErr, ok := err.(*exec.ExitError); ok {
			return exitErr.ExitCode()
		}
		fmt.Fprintf(os.Stderr, "failed to launch shared tool %s: %v\n", scriptName, err)
		return 1
	}
	return 0
}

type declarativeFieldInjectorPipeline struct {
	fields map[string]any
}

func (p declarativeFieldInjectorPipeline) ProcessItem(item scrapyapi.Item) (scrapyapi.Item, error) {
	for key, value := range p.fields {
		item[key] = value
	}
	return item, nil
}

type declarativeResponseContextSpiderMiddleware struct{}

func (declarativeResponseContextSpiderMiddleware) ProcessSpiderOutput(response *scrapyapi.Response, result []any, spider *scrapyapi.Spider) ([]any, error) {
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

type declarativeRequestHeadersMiddleware struct {
	headers map[string]string
}

func (m declarativeRequestHeadersMiddleware) ProcessRequest(request *scrapyapi.Request, spider *scrapyapi.Spider) (*scrapyapi.Request, error) {
	for key, value := range m.headers {
		request.Headers[key] = value
	}
	return request, nil
}

func (m declarativeRequestHeadersMiddleware) ProcessResponse(response *scrapyapi.Response, spider *scrapyapi.Spider) (*scrapyapi.Response, error) {
	return response, nil
}

func readStringAnyMap(config map[string]any, key string) map[string]any {
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

func readStringMap(config map[string]any, key string) map[string]string {
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

func cloneAnyValue(value any) any {
	switch typed := value.(type) {
	case map[string]any:
		return cloneStringAnyMap(typed)
	case []any:
		cloned := make([]any, 0, len(typed))
		for _, item := range typed {
			cloned = append(cloned, cloneAnyValue(item))
		}
		return cloned
	default:
		return value
	}
}

func cloneStringAnyMap(source map[string]any) map[string]any {
	if len(source) == 0 {
		return map[string]any{}
	}
	cloned := make(map[string]any, len(source))
	for key, value := range source {
		cloned[key] = cloneAnyValue(value)
	}
	return cloned
}

func mergeStringAnyMaps(base map[string]any, overlay map[string]any) map[string]any {
	merged := cloneStringAnyMap(base)
	for key, value := range overlay {
		if existing, ok := merged[key]; ok {
			existingMap, existingIsMap := existing.(map[string]any)
			overlayMap, overlayIsMap := value.(map[string]any)
			if existingIsMap && overlayIsMap {
				merged[key] = mergeStringAnyMaps(existingMap, overlayMap)
				continue
			}
		}
		merged[key] = cloneAnyValue(value)
	}
	return merged
}

func mergeComponentConfig(base map[string]map[string]any, overlay map[string]map[string]any) map[string]map[string]any {
	merged := map[string]map[string]any{}
	for key, value := range base {
		merged[key] = cloneStringAnyMap(value)
	}
	for key, value := range overlay {
		if existing, ok := merged[key]; ok {
			merged[key] = mergeStringAnyMaps(existing, value)
			continue
		}
		merged[key] = cloneStringAnyMap(value)
	}
	return merged
}

func mergeUniqueStrings(base []string, overlay []string) []string {
	seen := map[string]bool{}
	merged := []string{}
	for _, group := range [][]string{base, overlay} {
		for _, value := range group {
			trimmed := strings.TrimSpace(value)
			if trimmed == "" || seen[trimmed] {
				continue
			}
			seen[trimmed] = true
			merged = append(merged, trimmed)
		}
	}
	return merged
}

func configuredScrapyPipelinesForSpider(projectCfg contractConfig, spiderName string) []string {
	values := append([]string{}, projectCfg.Scrapy.Pipelines...)
	if spiderCfg, ok := projectCfg.Scrapy.Spiders[spiderName]; ok {
		values = mergeUniqueStrings(values, spiderCfg.Pipelines)
	}
	return values
}

func configuredScrapySpiderMiddlewaresForSpider(projectCfg contractConfig, spiderName string) []string {
	values := append([]string{}, projectCfg.Scrapy.SpiderMiddlewares...)
	if spiderCfg, ok := projectCfg.Scrapy.Spiders[spiderName]; ok {
		values = mergeUniqueStrings(values, spiderCfg.SpiderMiddlewares)
	}
	return values
}

func configuredScrapyDownloaderMiddlewaresForSpider(projectCfg contractConfig, spiderName string) []string {
	values := append([]string{}, projectCfg.Scrapy.DownloaderMiddlewares...)
	if spiderCfg, ok := projectCfg.Scrapy.Spiders[spiderName]; ok {
		values = mergeUniqueStrings(values, spiderCfg.DownloaderMiddlewares)
	}
	return values
}

func mergedScrapyComponentConfigForSpider(projectCfg contractConfig, spiderName string) map[string]map[string]any {
	merged := mergeComponentConfig(projectCfg.Scrapy.ComponentConfig, map[string]map[string]any{})
	if spiderCfg, ok := projectCfg.Scrapy.Spiders[spiderName]; ok {
		merged = mergeComponentConfig(merged, spiderCfg.ComponentConfig)
	}
	return merged
}

func spiderComponentSummary(projectCfg contractConfig, spiderName string) string {
	return fmt.Sprintf(
		"pipelines=%s spider_middlewares=%s downloader_middlewares=%s",
		strings.Join(configuredScrapyPipelinesForSpider(projectCfg, spiderName), ","),
		strings.Join(configuredScrapySpiderMiddlewaresForSpider(projectCfg, spiderName), ","),
		strings.Join(configuredScrapyDownloaderMiddlewaresForSpider(projectCfg, spiderName), ","),
	)
}

func collectGoPipelineNames(plugins []scrapyapi.Plugin, declarative []scrapyapi.ItemPipeline) []string {
	names := []string{}
	for _, pipeline := range declarative {
		names = append(names, goComponentName(pipeline))
	}
	for _, plugin := range plugins {
		for _, pipeline := range plugin.ProvidePipelines() {
			names = append(names, goComponentName(pipeline))
		}
	}
	return names
}

func collectGoSpiderMiddlewareNames(plugins []scrapyapi.Plugin, declarative []scrapyapi.SpiderMiddleware) []string {
	names := []string{}
	for _, middleware := range declarative {
		names = append(names, goComponentName(middleware))
	}
	for _, plugin := range plugins {
		if provider, ok := plugin.(scrapyapi.SpiderMiddlewareProvider); ok {
			for _, middleware := range provider.ProvideSpiderMiddlewares() {
				names = append(names, goComponentName(middleware))
			}
		}
	}
	return names
}

func collectGoDownloaderMiddlewareNames(plugins []scrapyapi.Plugin, declarative []scrapyapi.DownloaderMiddleware) []string {
	names := []string{}
	for _, middleware := range declarative {
		names = append(names, goComponentName(middleware))
	}
	for _, plugin := range plugins {
		if provider, ok := plugin.(scrapyapi.DownloaderMiddlewareProvider); ok {
			for _, middleware := range provider.ProvideDownloaderMiddlewares() {
				names = append(names, goComponentName(middleware))
			}
		}
	}
	return names
}

func appendGoDeclarativeComponentChecks(checks *[]map[string]string, projectCfg contractConfig) {
	pipelines := append([]string{}, projectCfg.Scrapy.Pipelines...)
	spiderMiddlewares := append([]string{}, projectCfg.Scrapy.SpiderMiddlewares...)
	downloaderMiddlewares := append([]string{}, projectCfg.Scrapy.DownloaderMiddlewares...)
	*checks = append(*checks, map[string]string{
		"name":   "components",
		"status": "passed",
		"details": fmt.Sprintf(
			"pipelines=%d spider_middlewares=%d downloader_middlewares=%d",
			len(pipelines),
			len(spiderMiddlewares),
			len(downloaderMiddlewares),
		),
	})
	for _, name := range pipelines {
		*checks = append(*checks, map[string]string{"name": "pipeline:" + name, "status": "passed", "details": "declarative pipeline"})
	}
	for _, name := range spiderMiddlewares {
		*checks = append(*checks, map[string]string{"name": "spider_middleware:" + name, "status": "passed", "details": "declarative spider middleware"})
	}
	for _, name := range downloaderMiddlewares {
		*checks = append(*checks, map[string]string{"name": "downloader_middleware:" + name, "status": "passed", "details": "declarative downloader middleware"})
	}
}

func goComponentName(value any) string {
	componentType := reflect.TypeOf(value)
	if componentType == nil {
		return "unknown"
	}
	if componentType.Kind() == reflect.Ptr {
		componentType = componentType.Elem()
	}
	if name := componentType.Name(); name != "" {
		return name
	}
	return componentType.String()
}

func (playwrightBrowserFetchRunner) Fetch(url string, screenshot string, htmlPath string, cfg contractConfig) (browserFetchResult, error) {
	if screenshot != "" {
		if err := os.MkdirAll(filepath.Dir(screenshot), 0755); err != nil && filepath.Dir(screenshot) != "." {
			return browserFetchResult{}, err
		}
	}
	if htmlPath != "" {
		if err := os.MkdirAll(filepath.Dir(htmlPath), 0755); err != nil && filepath.Dir(htmlPath) != "." {
			return browserFetchResult{}, err
		}
	}

	args := []string{
		helperScriptPath(),
		"--url", url,
		"--timeout-seconds", fmt.Sprintf("%d", cfg.Browser.TimeoutSeconds),
	}
	if screenshot != "" {
		args = append(args, "--screenshot", screenshot)
	}
	if htmlPath != "" {
		args = append(args, "--html", htmlPath)
	}
	if cfg.Browser.UserAgent != "" {
		args = append(args, "--user-agent", cfg.Browser.UserAgent)
	}
	if cfg.Browser.StorageStateFile != "" {
		if _, err := os.Stat(cfg.Browser.StorageStateFile); err == nil {
			args = append(args, "--storage-state", cfg.Browser.StorageStateFile)
		}
		args = append(args, "--save-storage-state", cfg.Browser.StorageStateFile)
	}
	if cfg.Browser.CookiesFile != "" {
		if _, err := os.Stat(cfg.Browser.CookiesFile); err == nil {
			args = append(args, "--cookies-file", cfg.Browser.CookiesFile)
		}
		args = append(args, "--save-cookies-file", cfg.Browser.CookiesFile)
	}
	if cfg.Browser.AuthFile != "" {
		args = append(args, "--auth-file", cfg.Browser.AuthFile)
	}
	if cfg.Browser.Headless {
		args = append(args, "--headless")
	}

	cmd := exec.Command(pythonCommand(), args...)
	output, err := cmd.CombinedOutput()
	if err != nil {
		return browserFetchResult{}, fmt.Errorf("%w: %s", err, strings.TrimSpace(string(output)))
	}
	var result browserFetchResult
	if err := json.Unmarshal(output, &result); err != nil {
		return browserFetchResult{}, err
	}
	return result, nil
}
