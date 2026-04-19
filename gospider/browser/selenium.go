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
)

type SeleniumConfig struct {
	WebDriverURL string
	BrowserName  string
	Headless     bool
	UserAgent    string
	Proxy        string
	Timeout      time.Duration
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
	if config.UserAgent != "" || config.Proxy != "" || config.Headless {
		args := []string{}
		if config.Headless {
			args = append(args, "--headless=new")
		}
		if config.UserAgent != "" {
			args = append(args, "--user-agent="+config.UserAgent)
		}
		if config.Proxy != "" {
			args = append(args, "--proxy-server="+config.Proxy)
		}
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
