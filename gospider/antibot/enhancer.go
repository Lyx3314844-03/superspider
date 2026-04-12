package antibot

import (
	"crypto/rand"
	"crypto/tls"
	"fmt"
	"math/big"
	"net/http"
	"strings"
	"time"
)

// EnhancedAntiBot provides advanced anti-detection features
type EnhancedAntiBot struct {
	// TLS fingerprinting
	tlsProfiles []*tls.Config
	
	// User-Agent pool
	userAgents []string
	
	// Delay ranges
	minDelay time.Duration
	maxDelay time.Duration
	
	// Browser fingerprints
	fingerprints []BrowserFingerprint
}

// BrowserFingerprint stores browser fingerprint data
type BrowserFingerprint struct {
	UserAgent      string
	Platform       string
	Vendor         string
	Renderer       string
	ViewportWidth  int
	ViewportHeight int
	ScreenWidth    int
	ScreenHeight   int
	ColorDepth     int
	HardwareConcurrency int
	DeviceMemory   int
}

// NewEnhancedAntiBot creates a new enhanced anti-bot instance
func NewEnhancedAntiBot() *EnhancedAntiBot {
	return &EnhancedAntiBot{
		userAgents: []string{
			"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
			"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
			"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
			"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
			"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
			"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
		},
		minDelay: 1 * time.Second,
		maxDelay: 3 * time.Second,
		fingerprints: generateFingerprints(),
	}
}

func generateFingerprints() []BrowserFingerprint {
	return []BrowserFingerprint{
		{UserAgent: "Chrome/120.0.0.0", Platform: "Win32", Vendor: "Google Inc.", Renderer: "ANGLE (Intel, Intel(R) UHD Graphics Direct3D11 vs_5_0 ps_5_0)", ViewportWidth: 1920, ViewportHeight: 1080, ScreenWidth: 1920, ScreenHeight: 1080, ColorDepth: 24, HardwareConcurrency: 8, DeviceMemory: 8},
		{UserAgent: "Chrome/120.0.0.0", Platform: "MacIntel", Vendor: "Apple Inc.", Renderer: "Apple M1", ViewportWidth: 1440, ViewportHeight: 900, ScreenWidth: 2560, ScreenHeight: 1440, ColorDepth: 24, HardwareConcurrency: 8, DeviceMemory: 16},
		{UserAgent: "Firefox/121.0", Platform: "Win64", Vendor: "", Renderer: "NVIDIA GeForce RTX 3080 Direct3D11", ViewportWidth: 1920, ViewportHeight: 1080, ScreenWidth: 3840, ScreenHeight: 2160, ColorDepth: 24, HardwareConcurrency: 16, DeviceMemory: 32},
	}
}

// RandomUserAgent returns a random User-Agent string
func (e *EnhancedAntiBot) RandomUserAgent() string {
	n, _ := rand.Int(rand.Reader, big.NewInt(int64(len(e.userAgents))))
	return e.userAgents[n.Int64()]
}

// RandomDelay returns a random delay between min and max
func (e *EnhancedAntiBot) RandomDelay() time.Duration {
	n, _ := rand.Int(rand.Reader, big.NewInt(int64(e.maxDelay-e.minDelay)))
	return e.minDelay + time.Duration(n.Int64())
}

// GetFingerprint returns a random browser fingerprint
func (e *EnhancedAntiBot) GetFingerprint() BrowserFingerprint {
	n, _ := rand.Int(rand.Reader, big.NewInt(int64(len(e.fingerprints))))
	return e.fingerprints[n.Int64()]
}

// WrapTransport wraps an http.RoundTripper with anti-detection
func (e *EnhancedAntiBot) WrapTransport(rt http.RoundTripper) http.RoundTripper {
	return &AntiBotTransport{
		base: rt,
		ab: e,
	}
}

// AntiBotTransport implements http.RoundTripper with anti-detection
type AntiBotTransport struct {
	base http.RoundTripper
	ab  *EnhancedAntiBot
}

func (t *AntiBotTransport) RoundTrip(req *http.Request) (*http.Response, error) {
	// Set random User-Agent
	req.Header.Set("User-Agent", t.ab.RandomUserAgent())
	
	// Add common headers
	req.Header.Set("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8")
	req.Header.Set("Accept-Language", "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7")
	req.Header.Set("Accept-Encoding", "gzip, deflate, br")
	req.Header.Set("Connection", "keep-alive")
	req.Header.Set("Upgrade-Insecure-Requests", "1")
	req.Header.Set("Sec-Fetch-Dest", "document")
	req.Header.Set("Sec-Fetch-Mode", "navigate")
	req.Header.Set("Sec-Fetch-Site", "none")
	req.Header.Set("Sec-Fetch-User", "?1")
	
	// Random delay
	time.Sleep(t.ab.RandomDelay())
	
	// For HTTPS, add TLS fingerprint specific headers
	if strings.HasPrefix(req.URL.Scheme, "https") {
		req.Header.Set("Sec-WebSocket-Version", "13")
	}
	
	return t.base.RoundTrip(req)
}

// InitTLSProfiles initializes custom TLS profiles
func (e *EnhancedAntiBot) InitTLSProfiles() {
	// Chrome-like TLS fingerprint
	chromeTLS := tls.Config{
		ServerName: "",
		// Set custom curve preferences
		CurvePreferences: []tls.CurveID{
			tls.CurveP256,
			tls.X25519,
		},
		// Set custom cipher suites
		CipherSuites: []uint16{
			tls.TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256,
			tls.TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384,
			tls.TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256,
			tls.TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384,
		},
		MinVersion: tls.VersionTLS12,
		MaxVersion: tls.VersionTLS13,
	}
	
e.tlsProfiles = append(e.tlsProfiles, &chromeTLS)
}

// CreateTLSConfig creates a custom TLS configuration
func (e *EnhancedAntiBot) CreateTLSConfig() *tls.Config {
	if len(e.tlsProfiles) == 0 {
		e.InitTLSProfiles()
	}
	return e.tlsProfiles[0]
}

// VerifyConnection verifies the connection is not blocked
func (e *EnhancedAntiBot) VerifyConnection() error {
	client := &http.Client{
		Transport: e.WrapTransport(http.DefaultTransport),
		Timeout:   10 * time.Second,
	}
	
	resp, err := client.Get("https://www.google.com")
	if err != nil {
		return fmt.Errorf("connection verification failed: %w", err)
	}
	defer resp.Body.Close()
	
	if resp.StatusCode != 200 {
		return fmt.Errorf("unexpected status code: %d", resp.StatusCode)
	}
	
	return nil
}

// RandomMouseMovement generates random mouse movement data
func (e *EnhancedAntiBot) RandomMouseMovement() []struct{X, Y int} {
	var movements []struct{X, Y int}
	points := 5 + int(time.Now().UnixNano()%10)
	
	x, y := 0, 0
	for i := 0; i < points; i++ {
		dx := int(time.Now().UnixNano()%50) - 25
		dy := int(time.Now().UnixNano()%50) - 25
		x += dx
		y += dy
		movements = append(movements, struct{X, Y int}{x, y})
	}
	
	return movements
}

// RandomScrollBehavior generates random scroll behavior
func (e *EnhancedAntiBot) RandomScrollBehavior() (distance int, delay time.Duration) {
	distance = 100 + int(time.Now().UnixNano()%500)
	delay = 50 + time.Duration(time.Now().UnixNano()%150)*time.Millisecond
	return
}

func init() {
	// Register the enhanced anti-bot module
	fmt.Println("Enhanced Anti-Bot module loaded")
}
