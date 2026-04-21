package browserruntime

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"time"

	browserpkg "gospider/browser"
	"gospider/core"
)

// Executor abstracts the browser work so tests can inject a stub.
type Executor func(ctx context.Context, job core.JobSpec) (string, error)

// Runtime executes normalized browser jobs and returns normalized job results.
type Runtime struct {
	executor Executor
}

// NewRuntime creates a browser runtime with an optional executor override.
func NewRuntime(executor Executor) *Runtime {
	if executor == nil {
		executor = defaultExecutor
	}
	return &Runtime{executor: executor}
}

func defaultExecutor(ctx context.Context, job core.JobSpec) (string, error) {
	if content, ok, err := executeMockBrowser(job); ok {
		return content, err
	}

	cfg := browserpkg.DefaultConfig()
	if job.Browser.Profile != "" {
		cfg.Stealth = true
	}
	if job.Browser.UserAgent != "" {
		cfg.UserAgent = job.Browser.UserAgent
	}
	if job.Browser.Viewport.Width > 0 {
		cfg.ViewportWidth = job.Browser.Viewport.Width
	}
	if job.Browser.Viewport.Height > 0 {
		cfg.ViewportHeight = job.Browser.Viewport.Height
	}
	cfg.Headless = !(!job.Browser.Headless && job.Browser.Profile == "")

	browser := browserpkg.NewBrowser(cfg)
	if err := browser.Start(); err != nil {
		return "", err
	}
	defer browser.Close()

	if err := browser.Navigate(job.Target.URL); err != nil {
		return "", err
	}

	screenshotPath := screenshotArtifactPath(job)
	for _, action := range job.Browser.Actions {
		switch action.Type {
		case "goto":
			if action.URL != "" {
				if err := browser.Navigate(action.URL); err != nil && !action.Optional {
					return "", err
				}
			}
		case "wait":
			waitFor := 500 * time.Millisecond
			if action.Timeout > 0 {
				waitFor = action.Timeout
			}
			time.Sleep(waitFor)
		case "click":
			if action.Selector != "" {
				if frameSelector := extraString(action.Extra, "frame_selector"); frameSelector != "" {
					if err := browser.ClickInFrame(frameSelector, action.Selector); err != nil && !action.Optional {
						return "", err
					}
				} else if err := browser.Click(action.Selector); err != nil && !action.Optional {
					return "", err
				}
			}
		case "type":
			if action.Selector != "" {
				if frameSelector := extraString(action.Extra, "frame_selector"); frameSelector != "" {
					if err := browser.FillInFrame(frameSelector, action.Selector, action.Value); err != nil && !action.Optional {
						return "", err
					}
				} else if err := browser.Fill(action.Selector, action.Value); err != nil && !action.Optional {
					return "", err
				}
			}
		case "upload":
			if action.Selector != "" && action.Value != "" {
				if err := browser.UploadFile(action.Selector, action.Value); err != nil && !action.Optional {
					return "", err
				}
			}
		case "shadow_text", "shadow_html", "shadow_extract":
			selectorPath, err := actionShadowPath(action)
			if err != nil {
				if !action.Optional {
					return "", err
				}
				break
			}
			expression := action.Value
			if expression == "" {
				if action.Type == "shadow_html" {
					expression = "target.outerHTML || target.textContent || ''"
				} else {
					expression = "target.textContent || ''"
				}
			}
			value, err := browser.ExecuteShadowDOM(expression, selectorPath...)
			if err != nil && !action.Optional {
				return "", err
			}
			if err == nil && action.SaveAs != "" {
				if writeErr := writeArtifact(action.SaveAs, []byte(fmt.Sprint(value))); writeErr != nil && !action.Optional {
					return "", writeErr
				}
			}
		case "listen_realtime", "capture_realtime":
			waitFor := 500 * time.Millisecond
			if action.Timeout > 0 {
				waitFor = action.Timeout
			}
			time.Sleep(waitFor)
			target := action.SaveAs
			if target == "" {
				target = realtimeArtifactPath(job)
			}
			if err := browser.SaveRealtimeToFile(target); err != nil && !action.Optional {
				return "", err
			}
		case "scroll":
			if _, err := browser.ExecuteJS("window.scrollTo(0, document.body.scrollHeight)"); err != nil && !action.Optional {
				return "", err
			}
		case "hover":
			if action.Selector != "" {
				if err := browser.Hover(action.Selector); err != nil && !action.Optional {
					return "", err
				}
			}
		case "eval":
			if action.Value != "" {
				if frameSelector := extraString(action.Extra, "frame_selector"); frameSelector != "" {
					if _, err := browser.ExecuteInFrame(frameSelector, action.Value); err != nil && !action.Optional {
						return "", err
					}
				} else if _, err := browser.ExecuteJS(action.Value); err != nil && !action.Optional {
					return "", err
				}
			}
		case "screenshot":
			target := action.SaveAs
			if target == "" {
				target = screenshotPath
			}
			if err := browser.Screenshot(target); err != nil && !action.Optional {
				return "", err
			}
			screenshotPath = target
		}
	}

	if wantsCapture(job, "screenshot") {
		if err := browser.Screenshot(screenshotPath); err != nil {
			return "", err
		}
	}

	content, err := browser.GetContent()
	if err != nil {
		return "", err
	}
	if wantsCapture(job, "console") {
		_ = browser.SaveConsoleToFile(consoleArtifactPath(job))
	}
	if wantsCapture(job, "network") {
		_ = browser.SaveNetworkToFile(networkArtifactPath(job))
	}
	if wantsCapture(job, "har") {
		_ = browser.SaveHARToFile(harArtifactPath(job))
	}
	if wantsRealtimeCapture(job) {
		_ = browser.SaveRealtimeToFile(realtimeArtifactPath(job))
	}
	return content, nil
}

func extraString(extra map[string]interface{}, key string) string {
	if extra == nil {
		return ""
	}
	value, ok := extra[key]
	if !ok {
		return ""
	}
	text, ok := value.(string)
	if !ok {
		return ""
	}
	return text
}

func actionShadowPath(action core.ActionSpec) ([]string, error) {
	if value, ok := action.Extra["shadow_path"]; ok {
		switch typed := value.(type) {
		case []string:
			return typed, nil
		case []interface{}:
			path := make([]string, 0, len(typed))
			for _, item := range typed {
				text, ok := item.(string)
				if !ok {
					return nil, fmt.Errorf("extra.shadow_path must contain only strings")
				}
				path = append(path, text)
			}
			return path, nil
		case string:
			return browserpkg.SplitShadowPathForRuntime(typed), nil
		default:
			return nil, fmt.Errorf("extra.shadow_path must be a string or string array")
		}
	}
	if action.Selector == "" {
		return nil, fmt.Errorf("shadow action requires selector or extra.shadow_path")
	}
	return browserpkg.SplitShadowPathForRuntime(action.Selector), nil
}

// Execute runs a browser job through the configured executor.
func (r *Runtime) Execute(ctx context.Context, job core.JobSpec) (*core.JobResult, error) {
	if err := job.Validate(); err != nil {
		return nil, err
	}
	if job.Runtime != core.RuntimeBrowser {
		return nil, fmt.Errorf("browser runtime cannot execute %q jobs", job.Runtime)
	}

	startedAt := time.Now()
	html, err := r.executor(ctx, job)
	finishedAt := time.Now()
	state := core.StateSucceeded
	errText := ""
	if err != nil {
		state = core.StateFailed
		errText = err.Error()
	}

	result := &core.JobResult{
		JobName:    job.Name,
		Runtime:    core.RuntimeBrowser,
		State:      state,
		URL:        job.Target.URL,
		Body:       []byte(html),
		Text:       html,
		StartedAt:  startedAt,
		FinishedAt: finishedAt,
		Duration:   finishedAt.Sub(startedAt),
		Error:      errText,
	}
	result.EnsureEnvelope()
	if len(job.Browser.Capture) > 0 {
		result.Metadata["capture"] = append([]string(nil), job.Browser.Capture...)
	}
	if job.Browser.Profile != "" {
		result.SetAntiBotTrace(core.AntiBotTrace{
			FingerprintProfile: job.Browser.Profile,
			SessionMode:        job.AntiBot.SessionMode,
			Stealth:            job.AntiBot.Stealth,
		})
	}
	applyMockBrowserEnvelope(result, job.Metadata)
	if wantsCapture(job, "html") {
		htmlPath := htmlArtifactPath(job)
		if err := writeArtifact(htmlPath, []byte(html)); err == nil {
			result.SetArtifact("html", core.ArtifactRef{Kind: "html", Path: htmlPath})
		} else {
			result.AddWarning("failed to persist html artifact: " + err.Error())
		}
	}
	if wantsCapture(job, "dom") {
		domPath := domArtifactPath(job)
		if err := writeArtifact(domPath, []byte(html)); err == nil {
			result.SetArtifact("dom", core.ArtifactRef{Kind: "dom", Path: domPath})
		} else {
			result.AddWarning("failed to persist dom artifact: " + err.Error())
		}
	}
	if wantsCapture(job, "screenshot") {
		path := screenshotArtifactPath(job)
		if _, statErr := os.Stat(path); statErr == nil {
			result.SetArtifact("screenshot", core.ArtifactRef{Kind: "screenshot", Path: path})
		} else {
			result.AddWarning("expected screenshot artifact was not created")
		}
	}
	if wantsCapture(job, "console") {
		path := consoleArtifactPath(job)
		if _, statErr := os.Stat(path); statErr == nil {
			result.SetArtifact("console", core.ArtifactRef{Kind: "console", Path: path})
		} else {
			result.AddWarning("expected console artifact was not created")
		}
	}
	if wantsCapture(job, "network") {
		path := networkArtifactPath(job)
		if _, statErr := os.Stat(path); statErr == nil {
			result.SetArtifact("network", core.ArtifactRef{Kind: "network", Path: path})
		} else {
			result.AddWarning("expected network artifact was not created")
		}
	}
	if wantsCapture(job, "har") {
		path := harArtifactPath(job)
		if _, statErr := os.Stat(path); statErr == nil {
			result.SetArtifact("har", core.ArtifactRef{Kind: "har", Path: path})
		} else {
			result.AddWarning("expected har artifact was not created")
		}
	}
	if wantsRealtimeCapture(job) {
		path := realtimeArtifactPath(job)
		if _, statErr := os.Stat(path); statErr == nil {
			result.SetArtifact("realtime", core.ArtifactRef{Kind: "realtime", Path: path})
		} else {
			result.AddWarning("expected realtime artifact was not created")
		}
	}
	result.Finalize()
	if err != nil {
		return result, err
	}
	return result, nil
}

func wantsCapture(job core.JobSpec, capture string) bool {
	for _, item := range job.Browser.Capture {
		if item == capture {
			return true
		}
	}
	return false
}

func wantsRealtimeCapture(job core.JobSpec) bool {
	return wantsCapture(job, "realtime") || wantsCapture(job, "websocket") || wantsCapture(job, "sse")
}

func artifactBaseName(job core.JobSpec) string {
	if job.Output.ArtifactPrefix != "" {
		return job.Output.ArtifactPrefix
	}
	if job.Name != "" {
		return job.Name
	}
	return "browser-job"
}

func artifactDirectory(job core.JobSpec) string {
	if job.Output.Directory != "" {
		return job.Output.Directory
	}
	return filepath.Join("artifacts", "browser")
}

func htmlArtifactPath(job core.JobSpec) string {
	return filepath.Join(artifactDirectory(job), artifactBaseName(job)+"-page.html")
}

func domArtifactPath(job core.JobSpec) string {
	return filepath.Join(artifactDirectory(job), artifactBaseName(job)+"-dom.html")
}

func screenshotArtifactPath(job core.JobSpec) string {
	return filepath.Join(artifactDirectory(job), artifactBaseName(job)+"-screenshot.png")
}

func consoleArtifactPath(job core.JobSpec) string {
	return filepath.Join(artifactDirectory(job), artifactBaseName(job)+"-console.json")
}

func networkArtifactPath(job core.JobSpec) string {
	return filepath.Join(artifactDirectory(job), artifactBaseName(job)+"-network.json")
}

func harArtifactPath(job core.JobSpec) string {
	return filepath.Join(artifactDirectory(job), artifactBaseName(job)+"-network.har")
}

func realtimeArtifactPath(job core.JobSpec) string {
	return filepath.Join(artifactDirectory(job), artifactBaseName(job)+"-realtime.json")
}

func writeArtifact(path string, data []byte) error {
	if err := os.MkdirAll(filepath.Dir(path), 0755); err != nil {
		return err
	}
	return os.WriteFile(path, data, 0644)
}

func executeMockBrowser(job core.JobSpec) (string, bool, error) {
	if job.Metadata == nil {
		return "", false, nil
	}
	mock, ok := job.Metadata["mock_browser"].(map[string]interface{})
	if !ok || len(mock) == 0 {
		return "", false, nil
	}

	html, err := mockBrowserHTML(mock)
	if err != nil {
		return "", true, err
	}
	actionLog := make([]string, 0, len(job.Browser.Actions))
	for _, action := range job.Browser.Actions {
		switch action.Type {
		case "goto":
			target := action.URL
			if target == "" {
				target = job.Target.URL
			}
			actionLog = append(actionLog, "goto:"+target)
		case "type":
			actionLog = append(actionLog, "type:"+action.Selector+"="+action.Value)
		case "click":
			actionLog = append(actionLog, "click:"+action.Selector)
		case "wait":
			actionLog = append(actionLog, "wait")
		case "hover":
			actionLog = append(actionLog, "hover:"+action.Selector)
		case "eval":
			actionLog = append(actionLog, "eval")
		case "upload":
			actionLog = append(actionLog, "upload:"+action.Selector+"="+action.Value)
		case "shadow_text", "shadow_html", "shadow_extract":
			actionLog = append(actionLog, action.Type+":"+action.Selector)
		case "listen_realtime", "capture_realtime":
			target := action.SaveAs
			if target == "" {
				target = realtimeArtifactPath(job)
			}
			if err := writeArtifact(target, []byte(mockString(mock["realtime_text"], "[]"))); err != nil {
				return "", true, err
			}
			actionLog = append(actionLog, "realtime:"+target)
		case "screenshot":
			target := action.SaveAs
			if target == "" {
				target = screenshotArtifactPath(job)
			}
			if err := writeArtifact(target, []byte(mockString(mock["screenshot_text"], "mock-browser-screenshot"))); err != nil {
				return "", true, err
			}
			actionLog = append(actionLog, "shot:"+target)
		}
	}
	if len(actionLog) > 0 {
		mock["action_log"] = actionLog
	}
	if wantsCapture(job, "screenshot") {
		if err := writeArtifact(screenshotArtifactPath(job), []byte(mockString(mock["screenshot_text"], "mock-browser-screenshot"))); err != nil {
			return "", true, err
		}
	}
	if wantsCapture(job, "console") {
		entries, err := decodeJSONLike[[]browserpkg.ConsoleEntry](mock["console_entries"])
		if err != nil {
			return "", true, err
		}
		data, err := json.MarshalIndent(entries, "", "  ")
		if err != nil {
			return "", true, err
		}
		if err := writeArtifact(consoleArtifactPath(job), data); err != nil {
			return "", true, err
		}
	}
	if wantsCapture(job, "network") {
		entries, err := decodeJSONLike[[]browserpkg.NetworkEntry](mock["network_entries"])
		if err != nil {
			return "", true, err
		}
		data, err := json.MarshalIndent(entries, "", "  ")
		if err != nil {
			return "", true, err
		}
		if err := writeArtifact(networkArtifactPath(job), data); err != nil {
			return "", true, err
		}
	}
	if wantsCapture(job, "har") {
		if raw, exists := mock["har"]; exists {
			data, err := json.MarshalIndent(raw, "", "  ")
			if err != nil {
				return "", true, err
			}
			if err := writeArtifact(harArtifactPath(job), data); err != nil {
				return "", true, err
			}
		} else if raw, exists := mock["har_entries"]; exists {
			payload := map[string]interface{}{
				"log": map[string]interface{}{
					"version": "1.2",
					"creator": map[string]interface{}{
						"name":    "gospider-mock",
						"version": "1.0.0",
					},
					"entries": raw,
				},
			}
			data, err := json.MarshalIndent(payload, "", "  ")
			if err != nil {
				return "", true, err
			}
			if err := writeArtifact(harArtifactPath(job), data); err != nil {
				return "", true, err
			}
		}
	}
	if wantsRealtimeCapture(job) {
		payload := mock["realtime_entries"]
		if payload == nil {
			payload = []map[string]interface{}{}
		}
		data, err := json.MarshalIndent(payload, "", "  ")
		if err != nil {
			return "", true, err
		}
		if err := writeArtifact(realtimeArtifactPath(job), data); err != nil {
			return "", true, err
		}
	}
	return html, true, nil
}

func mockBrowserHTML(mock map[string]interface{}) (string, error) {
	if html := mockString(mock["html_content"], ""); html != "" {
		return html, nil
	}
	path := mockString(mock["html_fixture_path"], "")
	if path == "" {
		return "<html><title>mock-browser</title></html>", nil
	}
	data, err := os.ReadFile(path)
	if err != nil {
		return "", err
	}
	return string(data), nil
}

func applyMockBrowserEnvelope(result *core.JobResult, metadata map[string]interface{}) {
	if result == nil || metadata == nil {
		return
	}
	mock, ok := metadata["mock_browser"].(map[string]interface{})
	if !ok || len(mock) == 0 {
		return
	}
	if antiBot, ok := mock["anti_bot"].(map[string]interface{}); ok {
		trace := core.AntiBotTrace{}
		if value := mockString(antiBot["challenge"], ""); value != "" {
			trace.Challenge = value
		}
		if value := mockString(antiBot["proxy_id"], ""); value != "" {
			trace.ProxyID = value
		}
		if value := mockString(antiBot["fingerprint_profile"], ""); value != "" {
			trace.FingerprintProfile = value
		}
		if value := mockString(antiBot["session_mode"], ""); value != "" {
			trace.SessionMode = value
		}
		if stealth, ok := antiBot["stealth"].(bool); ok {
			trace.Stealth = stealth
		}
		result.SetAntiBotTrace(trace)
	}
	if recovery, ok := mock["recovery"].(map[string]interface{}); ok && len(recovery) > 0 {
		result.SetRecoveryTrace(recovery)
	}
	if actionLog := mockStringSlice(mock["action_log"]); len(actionLog) > 0 {
		result.Metadata["browser_actions"] = append([]string(nil), actionLog...)
	}
	for _, warning := range mockWarnings(mock["warnings"]) {
		result.AddWarning(warning)
	}
}

func mockStringSlice(value interface{}) []string {
	switch typed := value.(type) {
	case []string:
		return append([]string(nil), typed...)
	case []interface{}:
		out := make([]string, 0, len(typed))
		for _, item := range typed {
			text := mockString(item, "")
			if text != "" {
				out = append(out, text)
			}
		}
		return out
	default:
		return nil
	}
}

func mockWarnings(value interface{}) []string {
	switch typed := value.(type) {
	case []string:
		return append([]string(nil), typed...)
	case []interface{}:
		out := make([]string, 0, len(typed))
		for _, item := range typed {
			text := mockString(item, "")
			if text != "" {
				out = append(out, text)
			}
		}
		return out
	default:
		return nil
	}
}

func mockString(value interface{}, fallback string) string {
	if value == nil {
		return fallback
	}
	text := fmt.Sprint(value)
	if text == "" || text == "<nil>" {
		return fallback
	}
	return text
}

func decodeJSONLike[T any](value interface{}) (T, error) {
	var zero T
	if value == nil {
		return zero, nil
	}
	data, err := json.Marshal(value)
	if err != nil {
		return zero, err
	}
	var decoded T
	if err := json.Unmarshal(data, &decoded); err != nil {
		return zero, err
	}
	return decoded, nil
}
