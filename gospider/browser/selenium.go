package browser

import (
	"bytes"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"

	"gospider/antibot"
)

type SeleniumConfig struct {
	WebDriverURL string
	BrowserName  string
	Headless     bool
	UserAgent    string
	Proxy        string
	Timeout      time.Duration
	UserDataDir  string
	WindowSize   string
	ExtraArgs    []string
}

type SeleniumClient struct {
	baseURL    string
	sessionID  string
	httpClient *http.Client
}

func DefaultSeleniumConfig() *SeleniumConfig {
	return &SeleniumConfig{
		WebDriverURL: "http://localhost:4444",
		BrowserName:  "chrome",
		Headless:     true,
		Timeout:      30 * time.Second,
	}
}

func NewSeleniumClient(config *SeleniumConfig) (*SeleniumClient, error) {
	if config == nil {
		config = DefaultSeleniumConfig()
	}
	timeout := config.Timeout
	if timeout <= 0 {
		timeout = 30 * time.Second
	}
	client := &http.Client{Timeout: timeout}

	payload := map[string]any{
		"capabilities": map[string]any{
			"alwaysMatch": map[string]any{
				"browserName": config.BrowserName,
			},
		},
	}
	alwaysMatch := payload["capabilities"].(map[string]any)["alwaysMatch"].(map[string]any)
	if config.UserAgent != "" || config.Proxy != "" || config.Headless || config.UserDataDir != "" || len(config.ExtraArgs) > 0 || config.WindowSize != "" {
		args := []string{}
		if config.Headless {
			args = append(args, "--headless=new")
		}
		if config.WindowSize != "" {
			args = append(args, "--window-size="+config.WindowSize)
		}
		if config.UserAgent != "" {
			args = append(args, "--user-agent="+config.UserAgent)
		}
		if config.Proxy != "" {
			args = append(args, "--proxy-server="+config.Proxy)
		}
		if config.UserDataDir != "" {
			args = append(args, "--user-data-dir="+config.UserDataDir)
		}
		args = append(args, config.ExtraArgs...)
		alwaysMatch["goog:chromeOptions"] = map[string]any{
			"args": args,
		}
	}

	encoded, err := json.Marshal(payload)
	if err != nil {
		return nil, err
	}
	baseURL := strings.TrimRight(config.WebDriverURL, "/")
	resp, err := client.Post(baseURL+"/session", "application/json", bytes.NewReader(encoded))
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 300 {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("selenium session create failed: %s", strings.TrimSpace(string(body)))
	}

	var result map[string]any
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, err
	}

	sessionID := extractSeleniumSessionID(result)
	if sessionID == "" {
		return nil, fmt.Errorf("selenium did not return a session id")
	}

	return &SeleniumClient{
		baseURL:    baseURL,
		sessionID:  sessionID,
		httpClient: client,
	}, nil
}

func (c *SeleniumClient) Navigate(url string) error {
	return c.postJSON("/url", map[string]any{"url": url}, nil)
}

func (c *SeleniumClient) ExecuteScript(script string, args ...any) (any, error) {
	var out map[string]any
	err := c.postJSON("/execute/sync", map[string]any{
		"script": script,
		"args":   args,
	}, &out)
	if err != nil {
		return nil, err
	}
	return out["value"], nil
}

func (c *SeleniumClient) ExecuteCDPCommand(command string, params map[string]any) (any, error) {
	var out map[string]any
	err := c.postJSON("/goog/cdp/execute", map[string]any{
		"cmd":    command,
		"params": params,
	}, &out)
	if err != nil {
		return nil, err
	}
	return out["value"], nil
}

func (c *SeleniumClient) ApplyEcommerceRuntimeProfile(userAgent string) {
	_, _ = c.ExecuteCDPCommand("Page.addScriptToEvaluateOnNewDocument", map[string]any{
		"source": ecommerceRuntimeScript(),
	})
	if userAgent != "" {
		_, _ = c.ExecuteCDPCommand("Network.setUserAgentOverride", map[string]any{
			"userAgent": userAgent,
			"platform":  "Windows",
		})
	}
	_, _ = c.ExecuteCDPCommand("Emulation.setTimezoneOverride", map[string]any{"timezoneId": "Asia/Shanghai"})
	_, _ = c.ExecuteCDPCommand("Emulation.setLocaleOverride", map[string]any{"locale": "zh-CN"})
}

func (c *SeleniumClient) Warmup(url string) {
	if strings.TrimSpace(url) == "" {
		return
	}
	_ = c.Navigate(url)
	_ = c.WaitReady(15 * time.Second)
	time.Sleep(700 * time.Millisecond)
	_, _ = c.ExecuteScript("window.scrollBy(0, Math.floor((window.innerHeight || 800) * 0.5)); return true;")
	time.Sleep(500 * time.Millisecond)
}

func (c *SeleniumClient) WaitReady(timeout time.Duration) error {
	if timeout <= 0 {
		timeout = 30 * time.Second
	}
	deadline := time.Now().Add(timeout)
	for time.Now().Before(deadline) {
		value, err := c.ExecuteScript("return document.readyState")
		if err == nil && fmt.Sprint(value) == "complete" {
			return nil
		}
		time.Sleep(250 * time.Millisecond)
	}
	return fmt.Errorf("selenium document ready timeout after %s", timeout)
}

func ecommerceRuntimeScript() string {
	return `
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en-US', 'en'] });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
window.chrome = window.chrome || { runtime: {} };
`
}

func (c *SeleniumClient) ScrollToBottom(rounds int, pause time.Duration) error {
	if rounds <= 0 {
		rounds = 6
	}
	if pause <= 0 {
		pause = 800 * time.Millisecond
	}
	var lastHeight string
	stable := 0
	for i := 0; i < rounds; i++ {
		height, _ := c.ExecuteScript("return String(document.body ? document.body.scrollHeight : 0)")
		currentHeight := fmt.Sprint(height)
		if _, err := c.ExecuteScript("window.scrollBy(0, Math.max(600, window.innerHeight || 800)); return true;"); err != nil {
			return err
		}
		time.Sleep(pause)
		if currentHeight == lastHeight {
			stable++
			if stable >= 2 {
				break
			}
		} else {
			stable = 0
			lastHeight = currentHeight
		}
	}
	return nil
}

func (c *SeleniumClient) DetectAccessChallenge() (map[string]any, error) {
	html, err := c.HTML()
	if err != nil {
		return nil, err
	}
	title, _ := c.Title()
	currentURL, _ := c.CurrentURL()
	report := antibot.AnalyzeAccessFriction(http.StatusOK, nil, html, currentURL+"\n"+title)
	return map[string]any{
		"blocked":          report.Blocked,
		"signals":          report.Signals,
		"url":              currentURL,
		"title":            title,
		"friction_profile": report,
	}, nil
}

func (c *SeleniumClient) WaitForManualAccess(timeout time.Duration) error {
	if timeout <= 0 {
		return nil
	}
	deadline := time.Now().Add(timeout)
	for time.Now().Before(deadline) {
		challenge, err := c.DetectAccessChallenge()
		if err == nil && challenge["blocked"] == false {
			return nil
		}
		time.Sleep(3 * time.Second)
	}
	return nil
}

func (c *SeleniumClient) HTML() (string, error) {
	value, err := c.getValue("/source")
	if err != nil {
		return "", err
	}
	html, _ := value.(string)
	return html, nil
}

func (c *SeleniumClient) Title() (string, error) {
	value, err := c.getValue("/title")
	if err != nil {
		return "", err
	}
	title, _ := value.(string)
	return title, nil
}

func (c *SeleniumClient) Screenshot() ([]byte, error) {
	value, err := c.getValue("/screenshot")
	if err != nil {
		return nil, err
	}
	encoded, _ := value.(string)
	return base64.StdEncoding.DecodeString(encoded)
}

func (c *SeleniumClient) CurrentURL() (string, error) {
	value, err := c.getValue("/url")
	if err != nil {
		return "", err
	}
	current, _ := value.(string)
	return current, nil
}

func (c *SeleniumClient) Close() error {
	req, err := http.NewRequest(http.MethodDelete, c.sessionURL(""), nil)
	if err != nil {
		return err
	}
	resp, err := c.httpClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 300 {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("selenium session close failed: %s", strings.TrimSpace(string(body)))
	}
	return nil
}

func (c *SeleniumClient) postJSON(path string, payload any, out *map[string]any) error {
	encoded, err := json.Marshal(payload)
	if err != nil {
		return err
	}
	resp, err := c.httpClient.Post(c.sessionURL(path), "application/json", bytes.NewReader(encoded))
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 300 {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("selenium command failed: %s", strings.TrimSpace(string(body)))
	}
	if out != nil {
		return json.NewDecoder(resp.Body).Decode(out)
	}
	return nil
}

func (c *SeleniumClient) getValue(path string) (any, error) {
	resp, err := c.httpClient.Get(c.sessionURL(path))
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 300 {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("selenium command failed: %s", strings.TrimSpace(string(body)))
	}
	var payload map[string]any
	if err := json.NewDecoder(resp.Body).Decode(&payload); err != nil {
		return nil, err
	}
	return payload["value"], nil
}

func (c *SeleniumClient) sessionURL(path string) string {
	if path == "" {
		return fmt.Sprintf("%s/session/%s", c.baseURL, c.sessionID)
	}
	return fmt.Sprintf("%s/session/%s%s", c.baseURL, c.sessionID, path)
}

func extractSeleniumSessionID(payload map[string]any) string {
	if sessionID, ok := payload["sessionId"].(string); ok && sessionID != "" {
		return sessionID
	}
	value, ok := payload["value"].(map[string]any)
	if !ok {
		return ""
	}
	if sessionID, ok := value["sessionId"].(string); ok && sessionID != "" {
		return sessionID
	}
	return ""
}
