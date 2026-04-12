package dispatch

import (
	"context"
	"fmt"
	"net/url"
	"path"
	"strings"
	"time"

	gai "gospider/ai"
	"gospider/core"
	"gospider/media"
	browserruntime "gospider/runtime/browser"
	httpruntime "gospider/runtime/http"
)

// Options configures the default multi-runtime executor.
type Options struct {
	Config          *core.Config
	BrowserExecutor browserruntime.Executor
	MediaExecutor   core.Executor
	AIExecutor      core.Executor
	AIAPIKey        string
	AIBaseURL       string
	AIModel         string
}

// NewExecutor creates a capability-based dispatcher for normalized jobs.
func NewExecutor(opts Options) core.Executor {
	router := core.NewRoutingExecutor()
	router.Register(core.RuntimeHTTP, httpruntime.NewRuntime())
	router.Register(core.RuntimeBrowser, browserruntime.NewRuntime(opts.BrowserExecutor))
	if opts.MediaExecutor != nil {
		router.Register(core.RuntimeMedia, opts.MediaExecutor)
	} else {
		router.Register(core.RuntimeMedia, &mediaExecutor{config: opts.Config})
	}
	if opts.AIExecutor != nil {
		router.Register(core.RuntimeAI, opts.AIExecutor)
	} else {
		router.Register(core.RuntimeAI, &aiExecutor{
			apiKey:  opts.AIAPIKey,
			baseURL: opts.AIBaseURL,
			model:   opts.AIModel,
		})
	}
	router.SetFallback(&unsupportedExecutor{})
	return &policyExecutor{inner: router}
}

type unsupportedExecutor struct{}

func (e *unsupportedExecutor) Execute(_ context.Context, job core.JobSpec) (*core.JobResult, error) {
	result := core.NewJobResult(job, core.StateFailed)
	result.Error = fmt.Sprintf("runtime %q is not supported", job.Runtime)
	result.Metadata["capability"] = "unsupported"
	result.FinishedAt = time.Now()
	result.Finalize()
	return result, fmt.Errorf(result.Error)
}

type mediaExecutor struct {
	config *core.Config
}

func (e *mediaExecutor) Execute(_ context.Context, job core.JobSpec) (*core.JobResult, error) {
	if err := job.Validate(); err != nil {
		return nil, err
	}
	if job.Runtime != core.RuntimeMedia {
		return nil, fmt.Errorf("media executor cannot execute %q jobs", job.Runtime)
	}

	result := core.NewJobResult(job, core.StateFailed)
	result.Metadata["capability"] = "media"

	artifactType := resolveMediaType(job)
	outputDir := resolveMediaOutputDir(e.config, job)

	if !job.Media.Download {
		result.State = core.StateSucceeded
		result.Text = job.Target.URL
		result.AddMediaArtifact(core.MediaArtifact{
			Type: artifactType,
			URL:  job.Target.URL,
			Path: outputDir,
		})
		result.FinishedAt = time.Now()
		result.Finalize()
		return result, nil
	}

	if artifactType == "hls" || artifactType == "dash" {
		result.Error = fmt.Sprintf("%s downloading is not configured in the default dispatcher", artifactType)
		result.AddWarning("Use a dedicated media runtime for segmented stream downloads.")
		result.FinishedAt = time.Now()
		result.Finalize()
		return result, fmt.Errorf(result.Error)
	}

	downloader := media.NewMediaDownloader(outputDir)
	filename := inferFilename(job.Target.URL, artifactType)

	var download *media.DownloadResult
	switch artifactType {
	case "image":
		download = downloader.DownloadImage(job.Target.URL, filename)
	case "audio":
		download = downloader.DownloadAudio(job.Target.URL, filename)
	default:
		download = downloader.DownloadVideo(job.Target.URL, filename)
	}

	if download == nil {
		result.Error = "media download returned no result"
		result.FinishedAt = time.Now()
		result.Finalize()
		return result, fmt.Errorf(result.Error)
	}
	if !download.Success {
		result.Error = download.Error
		result.FinishedAt = time.Now()
		result.Finalize()
		return result, fmt.Errorf(download.Error)
	}

	result.State = core.StateSucceeded
	result.Metrics = &core.ResultMetrics{
		BytesIn: download.Size,
	}
	result.AddMediaArtifact(core.MediaArtifact{
		Type: artifactType,
		URL:  download.URL,
		Path: download.Path,
	})
	result.FinishedAt = time.Now()
	result.Finalize()
	return result, nil
}

type aiExecutor struct {
	apiKey  string
	baseURL string
	model   string
}

func (e *aiExecutor) Execute(_ context.Context, job core.JobSpec) (*core.JobResult, error) {
	if err := job.Validate(); err != nil {
		return nil, err
	}
	if job.Runtime != core.RuntimeAI {
		return nil, fmt.Errorf("ai executor cannot execute %q jobs", job.Runtime)
	}

	result := core.NewJobResult(job, core.StateFailed)
	result.Metadata["capability"] = "ai"

	if mock, ok := job.Metadata["mock_extract"].(map[string]interface{}); ok {
		result.State = core.StateSucceeded
		for field, value := range mock {
			result.SetExtractField(field, value)
		}
		applyMockEnvelope(result, job.Metadata)
		result.FinishedAt = time.Now()
		result.Finalize()
		return result, nil
	}

	content := ""
	if job.Target.Body != "" {
		content = job.Target.Body
	}
	if metadataContent, ok := job.Metadata["content"].(string); ok && metadataContent != "" {
		content = metadataContent
	}
	if content == "" {
		result.Error = "ai runtime requires target.body or metadata.content"
		applyMockEnvelope(result, job.Metadata)
		result.FinishedAt = time.Now()
		result.Finalize()
		return result, fmt.Errorf(result.Error)
	}

	config := gai.DefaultAIConfig()
	if e.apiKey != "" {
		config.APIKey = e.apiKey
	}
	if e.baseURL != "" {
		config.BaseURL = e.baseURL
	}
	if e.model != "" {
		config.Model = e.model
	}
	if apiKey, ok := job.Metadata["api_key"].(string); ok && apiKey != "" {
		config.APIKey = apiKey
	}
	if baseURL, ok := job.Metadata["api_base_url"].(string); ok && baseURL != "" {
		config.BaseURL = baseURL
	}
	if model, ok := job.Metadata["model"].(string); ok && model != "" {
		config.Model = model
	}

	if config.APIKey == "" {
		result.Error = "ai runtime is not configured"
		result.AddWarning("Provide metadata.mock_extract for offline tests or configure an API key.")
		applyMockEnvelope(result, job.Metadata)
		result.FinishedAt = time.Now()
		result.Finalize()
		return result, fmt.Errorf(result.Error)
	}

	instructions := "Extract the requested fields from the supplied content."
	if rawInstructions, ok := job.Metadata["instructions"].(string); ok && rawInstructions != "" {
		instructions = rawInstructions
	}

	aiExtractor := gai.NewAIExtractor(config)
	extracted, err := aiExtractor.ExtractStructured(content, instructions, buildAISchema(job))
	if err != nil {
		result.Error = err.Error()
		applyMockEnvelope(result, job.Metadata)
		result.FinishedAt = time.Now()
		result.Finalize()
		return result, err
	}

	result.State = core.StateSucceeded
	for field, value := range extracted {
		result.SetExtractField(field, value)
	}
	applyMockEnvelope(result, job.Metadata)
	result.FinishedAt = time.Now()
	result.Finalize()
	return result, nil
}

func applyMockEnvelope(result *core.JobResult, metadata map[string]interface{}) {
	if result == nil || metadata == nil {
		return
	}

	if mockAntiBot, ok := metadata["mock_antibot"].(map[string]interface{}); ok && len(mockAntiBot) > 0 {
		trace := core.AntiBotTrace{}
		if challenge, ok := mockAntiBot["challenge"].(string); ok {
			trace.Challenge = challenge
		}
		if proxyID, ok := mockAntiBot["proxy_id"].(string); ok {
			trace.ProxyID = proxyID
		}
		if fingerprintProfile, ok := mockAntiBot["fingerprint_profile"].(string); ok {
			trace.FingerprintProfile = fingerprintProfile
		}
		if sessionMode, ok := mockAntiBot["session_mode"].(string); ok {
			trace.SessionMode = sessionMode
		}
		if stealth, ok := mockAntiBot["stealth"].(bool); ok {
			trace.Stealth = stealth
		}
		result.SetAntiBotTrace(trace)
	}

	if mockRecovery, ok := metadata["mock_recovery"].(map[string]interface{}); ok && len(mockRecovery) > 0 {
		result.SetRecoveryTrace(mockRecovery)
	}

	for _, warning := range mockWarnings(metadata["mock_warnings"]) {
		result.AddWarning(warning)
	}
}

func mockWarnings(value interface{}) []string {
	switch typed := value.(type) {
	case []string:
		return append([]string(nil), typed...)
	case []interface{}:
		warnings := make([]string, 0, len(typed))
		for _, item := range typed {
			text, ok := item.(string)
			if ok && text != "" {
				warnings = append(warnings, text)
			}
		}
		return warnings
	default:
		return nil
	}
}

func resolveMediaType(job core.JobSpec) string {
	if len(job.Media.Types) > 0 && job.Media.Types[0] != "" {
		return strings.ToLower(job.Media.Types[0])
	}

	lower := strings.ToLower(job.Target.URL)
	switch {
	case strings.Contains(lower, ".m3u8"):
		return "hls"
	case strings.Contains(lower, ".mpd"):
		return "dash"
	case strings.Contains(lower, ".jpg"), strings.Contains(lower, ".jpeg"), strings.Contains(lower, ".png"), strings.Contains(lower, ".gif"), strings.Contains(lower, ".webp"):
		return "image"
	case strings.Contains(lower, ".mp3"), strings.Contains(lower, ".wav"), strings.Contains(lower, ".aac"):
		return "audio"
	default:
		return "video"
	}
}

func resolveMediaOutputDir(config *core.Config, job core.JobSpec) string {
	switch {
	case job.Media.OutputDir != "":
		return job.Media.OutputDir
	case job.Resources.DownloadDir != "":
		return job.Resources.DownloadDir
	case config != nil && config.Media.OutputDir != "":
		return config.Media.OutputDir
	case config != nil && config.Output.DownloadDir != "":
		return config.Output.DownloadDir
	default:
		return "./downloads"
	}
}

func inferFilename(rawURL, artifactType string) string {
	parsed, err := url.Parse(rawURL)
	if err == nil {
		base := path.Base(parsed.Path)
		if base != "" && base != "." && base != "/" {
			return base
		}
	}

	switch artifactType {
	case "image":
		return "media.jpg"
	case "audio":
		return "media.mp3"
	case "hls":
		return "media.m3u8"
	case "dash":
		return "media.mpd"
	default:
		return "media.mp4"
	}
}

func buildAISchema(job core.JobSpec) map[string]interface{} {
	properties := make(map[string]interface{})
	required := make([]string, 0)

	for _, extract := range job.Extract {
		if len(extract.Schema) > 0 {
			return extract.Schema
		}
		if extract.Field == "" {
			continue
		}
		properties[extract.Field] = map[string]interface{}{
			"type": "string",
		}
		if extract.Required {
			required = append(required, extract.Field)
		}
	}

	if len(properties) == 0 {
		if schema, ok := job.Metadata["schema"].(map[string]interface{}); ok {
			return schema
		}
	}

	schema := map[string]interface{}{
		"type":       "object",
		"properties": properties,
	}
	if len(required) > 0 {
		schema["required"] = required
	}
	return schema
}
