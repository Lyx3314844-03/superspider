package core

import (
	"container/heap"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"
)

// RequestFingerprint is the stable identity for a normalized request envelope.
type RequestFingerprint string

// FingerprintForRequest computes a stable fingerprint for a request.
func FingerprintForRequest(request *Request) RequestFingerprint {
	if request == nil {
		return ""
	}
	payload := map[string]interface{}{
		"url":      request.URL,
		"method":   strings.ToUpper(request.Method),
		"headers":  request.Headers,
		"body":     request.Body,
		"meta":     request.Meta,
		"priority": request.Priority,
	}
	data, _ := json.Marshal(payload)
	sum := sha256.Sum256(data)
	return RequestFingerprint(hex.EncodeToString(sum[:]))
}

// ArtifactRecord describes an emitted artifact stored on disk.
type ArtifactRecord struct {
	Name     string                 `json:"name"`
	Kind     string                 `json:"kind"`
	Path     string                 `json:"path"`
	Size     int64                  `json:"size"`
	Metadata map[string]interface{} `json:"metadata,omitempty"`
}

// ArtifactStore persists runtime artifacts.
type ArtifactStore interface {
	PutBytes(name string, kind string, data []byte, metadata map[string]interface{}) (ArtifactRecord, error)
	List() []ArtifactRecord
}

// FileArtifactStore writes artifacts into a local directory.
type FileArtifactStore struct {
	root    string
	mu      sync.RWMutex
	records []ArtifactRecord
}

// NewFileArtifactStore creates a filesystem-backed artifact store.
func NewFileArtifactStore(root string) *FileArtifactStore {
	_ = os.MkdirAll(root, 0o755)
	return &FileArtifactStore{root: root, records: make([]ArtifactRecord, 0)}
}

// PutBytes stores an artifact payload.
func (s *FileArtifactStore) PutBytes(name string, kind string, data []byte, metadata map[string]interface{}) (ArtifactRecord, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	if err := os.MkdirAll(s.root, 0o755); err != nil {
		return ArtifactRecord{}, err
	}
	safeName := strings.NewReplacer("/", "_", "\\", "_").Replace(name)
	path := filepath.Join(s.root, safeName)
	if ext := artifactExtension(kind); ext != "" && !strings.HasSuffix(path, ext) {
		path += ext
	}
	if err := os.WriteFile(path, data, 0o644); err != nil {
		return ArtifactRecord{}, err
	}
	record := ArtifactRecord{
		Name:     safeName,
		Kind:     kind,
		Path:     path,
		Size:     int64(len(data)),
		Metadata: metadata,
	}
	s.records = append(s.records, record)
	return record, nil
}

// List returns all recorded artifacts.
func (s *FileArtifactStore) List() []ArtifactRecord {
	s.mu.RLock()
	defer s.mu.RUnlock()
	records := make([]ArtifactRecord, len(s.records))
	copy(records, s.records)
	return records
}

func artifactExtension(kind string) string {
	switch kind {
	case "html":
		return ".html"
	case "json", "trace":
		return ".json"
	case "text":
		return ".txt"
	case "screenshot":
		return ".png"
	default:
		return ""
	}
}

// RuntimeSession models a leased session identity.
type RuntimeSession struct {
	SessionID          string            `json:"session_id"`
	CreatedAtUnix      int64             `json:"created_at_unix"`
	LastUsedAtUnix     int64             `json:"last_used_at_unix"`
	Headers            map[string]string `json:"headers,omitempty"`
	Cookies            map[string]string `json:"cookies,omitempty"`
	FingerprintProfile string            `json:"fingerprint_profile"`
	ProxyID            string            `json:"proxy_id,omitempty"`
	LeaseCount         int               `json:"lease_count"`
	FailureCount       int               `json:"failure_count"`
	InUse              bool              `json:"in_use"`
}

// RuntimeSessionPool is the shared session-pool contract surface.
type RuntimeSessionPool struct {
	maxSessions int
	mu          sync.Mutex
	sessions    map[string]*RuntimeSession
}

// NewRuntimeSessionPool creates a contract-compatible session pool.
func NewRuntimeSessionPool(maxSessions int) *RuntimeSessionPool {
	if maxSessions < 1 {
		maxSessions = 1
	}
	return &RuntimeSessionPool{
		maxSessions: maxSessions,
		sessions:    make(map[string]*RuntimeSession),
	}
}

// Acquire returns a reusable session or allocates a new one.
func (p *RuntimeSessionPool) Acquire(proxyID string, fingerprintProfile string) *RuntimeSession {
	p.mu.Lock()
	defer p.mu.Unlock()

	for _, session := range p.sessions {
		if !session.InUse && session.ProxyID == proxyID && session.FingerprintProfile == fingerprintProfile {
			session.InUse = true
			session.LeaseCount++
			session.LastUsedAtUnix = time.Now().Unix()
			return session
		}
	}

	if len(p.sessions) >= p.maxSessions {
		var oldest *RuntimeSession
		for _, session := range p.sessions {
			if oldest == nil || session.LastUsedAtUnix < oldest.LastUsedAtUnix {
				oldest = session
			}
		}
		if oldest != nil {
			oldest.InUse = true
			oldest.LeaseCount++
			oldest.LastUsedAtUnix = time.Now().Unix()
			return oldest
		}
	}

	now := time.Now().Unix()
	seed := sha256.Sum256([]byte(time.Now().Format(time.RFC3339Nano)))
	session := &RuntimeSession{
		SessionID:          "session-" + hex.EncodeToString(seed[:])[:12],
		CreatedAtUnix:      now,
		LastUsedAtUnix:     now,
		Headers:            map[string]string{},
		Cookies:            map[string]string{},
		FingerprintProfile: fingerprintProfile,
		ProxyID:            proxyID,
		LeaseCount:         1,
		InUse:              true,
	}
	p.sessions[session.SessionID] = session
	return session
}

// Release returns a session to the pool.
func (p *RuntimeSessionPool) Release(sessionID string, success bool) {
	p.mu.Lock()
	defer p.mu.Unlock()
	session := p.sessions[sessionID]
	if session == nil {
		return
	}
	session.InUse = false
	session.LastUsedAtUnix = time.Now().Unix()
	if !success {
		session.FailureCount++
	}
}

// Snapshot returns a serializable pool state.
func (p *RuntimeSessionPool) Snapshot() map[string]interface{} {
	p.mu.Lock()
	defer p.mu.Unlock()
	items := make([]RuntimeSession, 0, len(p.sessions))
	for _, session := range p.sessions {
		items = append(items, *session)
	}
	return map[string]interface{}{
		"max_sessions": p.maxSessions,
		"sessions":     items,
	}
}

// ProxyEndpoint describes a scored proxy.
type ProxyEndpoint struct {
	ProxyID      string  `json:"proxy_id"`
	URL          string  `json:"url"`
	SuccessCount int     `json:"success_count"`
	FailureCount int     `json:"failure_count"`
	Available    bool    `json:"available"`
	LastError    string  `json:"last_error,omitempty"`
	Score        float64 `json:"score"`
}

// ProxyPolicy chooses and scores proxies across requests.
type ProxyPolicy struct {
	mu      sync.Mutex
	proxies map[string]*ProxyEndpoint
}

// NewProxyPolicy creates an empty policy.
func NewProxyPolicy() *ProxyPolicy {
	return &ProxyPolicy{proxies: make(map[string]*ProxyEndpoint)}
}

// AddProxy registers a proxy endpoint.
func (p *ProxyPolicy) AddProxy(proxyID string, url string) *ProxyEndpoint {
	p.mu.Lock()
	defer p.mu.Unlock()
	if proxyID == "" {
		proxyID = "proxy-" + strings.ReplaceAll(time.Now().Format("150405.000"), ".", "")
	}
	endpoint := &ProxyEndpoint{ProxyID: proxyID, URL: url, Available: true, Score: 1}
	p.proxies[proxyID] = endpoint
	return endpoint
}

// Choose returns the highest-score available proxy.
func (p *ProxyPolicy) Choose() *ProxyEndpoint {
	p.mu.Lock()
	defer p.mu.Unlock()
	var selected *ProxyEndpoint
	for _, proxy := range p.proxies {
		if !proxy.Available {
			continue
		}
		if selected == nil || proxy.Score > selected.Score {
			selected = proxy
		}
	}
	return selected
}

// Record updates proxy health.
func (p *ProxyPolicy) Record(proxyID string, success bool, errMsg string) {
	p.mu.Lock()
	defer p.mu.Unlock()
	proxy := p.proxies[proxyID]
	if proxy == nil {
		return
	}
	if success {
		proxy.SuccessCount++
		proxy.Available = true
		proxy.LastError = ""
	} else {
		proxy.FailureCount++
		proxy.LastError = errMsg
		if proxy.FailureCount >= 3 && proxy.FailureCount > proxy.SuccessCount {
			proxy.Available = false
		}
	}
	total := proxy.SuccessCount + proxy.FailureCount
	if total == 0 {
		proxy.Score = 1
	} else {
		proxy.Score = float64(proxy.SuccessCount) / float64(total)
	}
}

// Snapshot returns the proxy inventory.
func (p *ProxyPolicy) Snapshot() map[string]interface{} {
	p.mu.Lock()
	defer p.mu.Unlock()
	items := make([]ProxyEndpoint, 0, len(p.proxies))
	for _, proxy := range p.proxies {
		items = append(items, *proxy)
	}
	return map[string]interface{}{"proxies": items}
}

// Middleware is the shared request/response contract for runtime hooks.
type Middleware interface {
	ProcessRequest(request *Request) (*Request, error)
	ProcessResponse(response interface{}, request *Request) (interface{}, error)
}

// MiddlewareChain applies middleware in the shared order.
type MiddlewareChain struct {
	middlewares []Middleware
}

// Add appends middleware to the chain.
func (c *MiddlewareChain) Add(middleware Middleware) {
	c.middlewares = append(c.middlewares, middleware)
}

// ProcessRequest runs request hooks in registration order.
func (c *MiddlewareChain) ProcessRequest(request *Request) (*Request, error) {
	current := request
	var err error
	for _, middleware := range c.middlewares {
		if current == nil {
			return nil, nil
		}
		current, err = middleware.ProcessRequest(current)
		if err != nil {
			return nil, err
		}
	}
	return current, nil
}

// ProcessResponse runs response hooks in reverse order.
func (c *MiddlewareChain) ProcessResponse(response interface{}, request *Request) (interface{}, error) {
	current := response
	var err error
	for index := len(c.middlewares) - 1; index >= 0; index-- {
		current, err = c.middlewares[index].ProcessResponse(current, request)
		if err != nil {
			return nil, err
		}
	}
	return current, nil
}

// StructuredEvent is the normalized observability event envelope.
type StructuredEvent struct {
	Timestamp time.Time              `json:"timestamp"`
	Level     string                 `json:"level"`
	Event     string                 `json:"event"`
	TraceID   string                 `json:"trace_id,omitempty"`
	Fields    map[string]interface{} `json:"fields,omitempty"`
}

// ObservabilityCollector gathers logs, metrics, traces, and failure categories.
type ObservabilityCollector struct {
	mu      sync.Mutex
	Events  []StructuredEvent       `json:"events"`
	Metrics map[string]float64      `json:"metrics"`
	Traces  map[string][]StructuredEvent `json:"traces"`
}

// NewObservabilityCollector creates an empty collector.
func NewObservabilityCollector() *ObservabilityCollector {
	return &ObservabilityCollector{
		Events:  make([]StructuredEvent, 0),
		Metrics: make(map[string]float64),
		Traces:  make(map[string][]StructuredEvent),
	}
}

// StartTrace starts a new structured trace.
func (c *ObservabilityCollector) StartTrace(name string) string {
	traceID := "trace-" + strings.ReplaceAll(time.Now().Format("150405.000"), ".", "")
	c.Log("info", name, traceID, map[string]interface{}{"phase": "start"})
	return traceID
}

// EndTrace records the trace completion event.
func (c *ObservabilityCollector) EndTrace(traceID string, fields map[string]interface{}) {
	c.Log("info", "trace.complete", traceID, fields)
}

// Log records a structured event.
func (c *ObservabilityCollector) Log(level string, event string, traceID string, fields map[string]interface{}) {
	c.mu.Lock()
	defer c.mu.Unlock()
	entry := StructuredEvent{
		Timestamp: time.Now().UTC(),
		Level:     level,
		Event:     event,
		TraceID:   traceID,
		Fields:    fields,
	}
	c.Events = append(c.Events, entry)
	c.Metrics["events."+event]++
	if traceID != "" {
		c.Traces[traceID] = append(c.Traces[traceID], entry)
	}
}

// RecordRequest records a normalized request event.
func (c *ObservabilityCollector) RecordRequest(request *Request, traceID string) {
	c.mu.Lock()
	c.Metrics["requests.total"]++
	c.mu.Unlock()
	if request != nil {
		c.Log("info", "request.enqueued", traceID, map[string]interface{}{
			"url":      request.URL,
			"priority": request.Priority,
		})
	}
}

// RecordResult records latency and failure classification.
func (c *ObservabilityCollector) RecordResult(request *Request, latencyMS float64, statusCode int, err error, traceID string) string {
	classification := ClassifyFailure(statusCode, err, "")
	c.mu.Lock()
	c.Metrics["requests.latency_ms.total"] += latencyMS
	c.Metrics["results."+classification]++
	c.mu.Unlock()
	fields := map[string]interface{}{
		"url":            "",
		"latency_ms":     latencyMS,
		"status_code":    statusCode,
		"classification": classification,
	}
	if request != nil {
		fields["url"] = request.URL
	}
	if err != nil {
		fields["error"] = err.Error()
	}
	level := "info"
	if classification != "ok" && classification != "not_modified" {
		level = "error"
	}
	c.Log(level, "request.completed", traceID, fields)
	return classification
}

// Summary returns a condensed metrics summary.
func (c *ObservabilityCollector) Summary() map[string]interface{} {
	c.mu.Lock()
	defer c.mu.Unlock()
	requests := c.Metrics["requests.total"]
	latency := c.Metrics["requests.latency_ms.total"]
	average := 0.0
	if requests > 0 {
		average = latency / requests
	}
	return map[string]interface{}{
		"events":             len(c.Events),
		"traces":             len(c.Traces),
		"metrics":            c.Metrics,
		"average_latency_ms": average,
	}
}

// PrometheusText renders a lightweight Prometheus exposition payload.
func (c *ObservabilityCollector) PrometheusText(prefix string) string {
	if strings.TrimSpace(prefix) == "" {
		prefix = "spider_runtime"
	}
	summary := c.Summary()
	lines := []string{
		fmt.Sprintf("# HELP %s_events_total Total structured events emitted by the runtime", prefix),
		fmt.Sprintf("# TYPE %s_events_total counter", prefix),
		fmt.Sprintf("%s_events_total %v", prefix, summary["events"]),
		fmt.Sprintf("# HELP %s_traces_total Total traces recorded by the runtime", prefix),
		fmt.Sprintf("# TYPE %s_traces_total gauge", prefix),
		fmt.Sprintf("%s_traces_total %v", prefix, summary["traces"]),
	}
	if metrics, ok := summary["metrics"].(map[string]float64); ok {
		for key, value := range metrics {
			lines = append(lines, fmt.Sprintf("%s_%s %v", prefix, strings.ReplaceAll(key, ".", "_"), value))
		}
	}
	lines = append(lines, fmt.Sprintf("%s_average_latency_ms %v", prefix, summary["average_latency_ms"]))
	return strings.Join(lines, "\n") + "\n"
}

// OTELPayload returns a JSON-friendly OpenTelemetry-style metrics envelope.
func (c *ObservabilityCollector) OTELPayload(serviceName string) map[string]interface{} {
	if strings.TrimSpace(serviceName) == "" {
		serviceName = "spider-runtime"
	}
	summary := c.Summary()
	points := make([]map[string]interface{}, 0)
	if metrics, ok := summary["metrics"].(map[string]float64); ok {
		for key, value := range metrics {
			points = append(points, map[string]interface{}{
				"name":  key,
				"value": value,
				"unit":  "1",
			})
		}
	}
	points = append(points, map[string]interface{}{
		"name":  "average_latency_ms",
		"value": summary["average_latency_ms"],
		"unit":  "ms",
	})
	return map[string]interface{}{
		"resource": map[string]interface{}{"service.name": serviceName},
		"scope":    "gospider/core/runtime_contracts",
		"metrics":  points,
		"events":   summary["events"],
		"traces":   summary["traces"],
	}
}

// ClassifyFailure returns the shared failure class for a result.
func ClassifyFailure(statusCode int, err error, body string) string {
	message := strings.ToLower(body)
	if err != nil {
		message += " " + strings.ToLower(err.Error())
	}
	switch {
	case statusCode == 304:
		return "not_modified"
	case statusCode == 401 || statusCode == 403:
		return "blocked"
	case statusCode == 404:
		return "not_found"
	case statusCode == 408 || strings.Contains(message, "timeout"):
		return "timeout"
	case statusCode == 429 || strings.Contains(message, "rate limit") || strings.Contains(message, "too many requests"):
		return "throttled"
	case strings.Contains(message, "captcha") || strings.Contains(message, "challenge"):
		return "anti_bot"
	case strings.Contains(message, "proxy"):
		return "proxy"
	case statusCode >= 500:
		return "server"
	case err != nil:
		return "runtime"
	default:
		return "ok"
	}
}

// FrontierConfig configures the shared autoscaled frontier.
type FrontierConfig struct {
	CheckpointDir         string `json:"checkpoint_dir"`
	CheckpointID          string `json:"checkpoint_id"`
	Autoscale             bool   `json:"autoscale"`
	MinConcurrency        int    `json:"min_concurrency"`
	MaxConcurrency        int    `json:"max_concurrency"`
	TargetLatencyMS       int    `json:"target_latency_ms"`
	LeaseTTLSeconds       int    `json:"lease_ttl_seconds"`
	MaxInflightPerDomain  int    `json:"max_inflight_per_domain"`
}

// DefaultFrontierConfig returns the shared defaults.
func DefaultFrontierConfig() FrontierConfig {
	return FrontierConfig{
		CheckpointDir:        filepath.Join("artifacts", "checkpoints", "frontier"),
		CheckpointID:         "runtime-frontier",
		Autoscale:            true,
		MinConcurrency:       1,
		MaxConcurrency:       16,
		TargetLatencyMS:      1200,
		LeaseTTLSeconds:      30,
		MaxInflightPerDomain: 2,
	}
}

type frontierRequest struct {
	URL         string                 `json:"url"`
	Method      string                 `json:"method"`
	Headers     map[string]string      `json:"headers,omitempty"`
	Body        string                 `json:"body,omitempty"`
	Meta        map[string]interface{} `json:"meta,omitempty"`
	Priority    int                    `json:"priority"`
	Fingerprint string                 `json:"fingerprint"`
}

type frontierItem struct {
	priority int
	sequence int
	request  frontierRequest
}

type frontierHeap []frontierItem

func (h frontierHeap) Len() int { return len(h) }
func (h frontierHeap) Less(i, j int) bool {
	if h[i].priority == h[j].priority {
		return h[i].sequence < h[j].sequence
	}
	return h[i].priority > h[j].priority
}
func (h frontierHeap) Swap(i, j int) { h[i], h[j] = h[j], h[i] }
func (h *frontierHeap) Push(x interface{}) {
	*h = append(*h, x.(frontierItem))
}
func (h *frontierHeap) Pop() interface{} {
	old := *h
	item := old[len(old)-1]
	*h = old[:len(old)-1]
	return item
}

// FrontierLease stores a leased request and its expiry.
type FrontierLease struct {
	Request     *Request  `json:"-"`
	Fingerprint string    `json:"fingerprint"`
	LeasedAt    time.Time `json:"leased_at"`
	ExpiresAt   time.Time `json:"expires_at"`
}

// AutoscaledFrontier provides deduped scheduling, backpressure, and checkpoint resume.
type AutoscaledFrontier struct {
	config                  FrontierConfig
	checkpoint              *CheckpointManager
	observability           *ObservabilityCollector
	mu                      sync.Mutex
	queue                   frontierHeap
	sequence                int
	known                   map[string]struct{}
	leases                  map[string]*FrontierLease
	domainInflight          map[string]int
	latencies               []float64
	outcomes                []bool
	recommendedConcurrency  int
	deadLetters             []frontierRequest
}

// NewAutoscaledFrontier creates a frontier with shared defaults.
func NewAutoscaledFrontier(config FrontierConfig) (*AutoscaledFrontier, error) {
	if config.CheckpointDir == "" {
		config = DefaultFrontierConfig()
	}
	if config.MinConcurrency < 1 {
		config.MinConcurrency = 1
	}
	if config.MaxConcurrency < config.MinConcurrency {
		config.MaxConcurrency = config.MinConcurrency
	}
	if config.LeaseTTLSeconds < 1 {
		config.LeaseTTLSeconds = 30
	}
	if config.MaxInflightPerDomain < 1 {
		config.MaxInflightPerDomain = 1
	}
	checkpoint, err := NewCheckpointManager(config.CheckpointDir, 0, 10)
	if err != nil {
		return nil, err
	}
	frontier := &AutoscaledFrontier{
		config:                 config,
		checkpoint:             checkpoint,
		observability:          NewObservabilityCollector(),
		queue:                  make(frontierHeap, 0),
		known:                  make(map[string]struct{}),
		leases:                 make(map[string]*FrontierLease),
		domainInflight:         make(map[string]int),
		recommendedConcurrency: config.MinConcurrency,
		deadLetters:            make([]frontierRequest, 0),
	}
	heap.Init(&frontier.queue)
	return frontier, nil
}

// RecommendedConcurrency returns the current autoscaled concurrency target.
func (f *AutoscaledFrontier) RecommendedConcurrency() int {
	f.mu.Lock()
	defer f.mu.Unlock()
	return f.recommendedConcurrency
}

// DeadLetterCount returns the number of exhausted requests.
func (f *AutoscaledFrontier) DeadLetterCount() int {
	f.mu.Lock()
	defer f.mu.Unlock()
	return len(f.deadLetters)
}

// Push enqueues a request if it has not already been seen.
func (f *AutoscaledFrontier) Push(request *Request) bool {
	if request == nil {
		return false
	}
	fingerprint := string(FingerprintForRequest(request))
	f.mu.Lock()
	defer f.mu.Unlock()
	if _, exists := f.known[fingerprint]; exists {
		return false
	}
	if _, leased := f.leases[fingerprint]; leased {
		return false
	}
	f.known[fingerprint] = struct{}{}
	f.sequence++
	heap.Push(&f.queue, frontierItem{
		priority: request.Priority,
		sequence: f.sequence,
		request:  serializeFrontierRequest(request, fingerprint),
	})
	f.observability.RecordRequest(request, "")
	return true
}

// Lease pops the next request that is not currently backpressured for its domain.
func (f *AutoscaledFrontier) Lease() *Request {
	f.mu.Lock()
	defer f.mu.Unlock()
	_ = f.reapExpiredLeasesLocked(time.Now(), 3)
	blocked := make([]frontierItem, 0)
	for f.queue.Len() > 0 {
		item := heap.Pop(&f.queue).(frontierItem)
		domain := normalizeFrontierDomain(item.request.URL)
		if domain != "" && f.domainInflight[domain] >= f.config.MaxInflightPerDomain {
			blocked = append(blocked, item)
			continue
		}
		request := deserializeFrontierRequest(item.request)
		lease := &FrontierLease{
			Request:     request,
			Fingerprint: item.request.Fingerprint,
			LeasedAt:    time.Now().UTC(),
			ExpiresAt:   time.Now().UTC().Add(time.Duration(f.config.LeaseTTLSeconds) * time.Second),
		}
		f.leases[item.request.Fingerprint] = lease
		if domain != "" {
			f.domainInflight[domain]++
		}
		for _, blockedItem := range blocked {
			heap.Push(&f.queue, blockedItem)
		}
		return request
	}
	for _, blockedItem := range blocked {
		heap.Push(&f.queue, blockedItem)
	}
	return nil
}

// Heartbeat extends an active lease.
func (f *AutoscaledFrontier) Heartbeat(request *Request, ttlSeconds int) bool {
	f.mu.Lock()
	defer f.mu.Unlock()
	fingerprint := string(FingerprintForRequest(request))
	lease := f.leases[fingerprint]
	if lease == nil {
		return false
	}
	if ttlSeconds < 1 {
		ttlSeconds = f.config.LeaseTTLSeconds
	}
	lease.ExpiresAt = time.Now().UTC().Add(time.Duration(ttlSeconds) * time.Second)
	return true
}

// Ack finalizes a leased request and feeds autoscaling metrics.
func (f *AutoscaledFrontier) Ack(request *Request, success bool, latencyMS float64, err error, statusCode int, maxRetries int) {
	f.mu.Lock()
	defer f.mu.Unlock()

	if request == nil {
		return
	}
	if maxRetries < 0 {
		maxRetries = 0
	}
	fingerprint := string(FingerprintForRequest(request))
	delete(f.leases, fingerprint)
	domain := normalizeFrontierDomain(request.URL)
	if domain != "" && f.domainInflight[domain] > 0 {
		f.domainInflight[domain]--
	}
	if !success {
		retryCount := 0
		if raw, ok := request.Meta["retry_count"]; ok {
			switch value := raw.(type) {
			case int:
				retryCount = value
			case float64:
				retryCount = int(value)
			}
		}
		if retryCount >= maxRetries {
			f.deadLetters = append(f.deadLetters, serializeFrontierRequest(request, fingerprint))
		} else {
			if request.Meta == nil {
				request.Meta = map[string]interface{}{}
			}
			request.Meta["retry_count"] = retryCount + 1
			f.sequence++
			heap.Push(&f.queue, frontierItem{
				priority: request.Priority,
				sequence: f.sequence,
				request:  serializeFrontierRequest(request, fingerprint),
			})
		}
	}
	f.latencies = appendWindow(f.latencies, latencyMS, 64)
	f.outcomes = appendOutcomeWindow(f.outcomes, success, 64)
	f.adjustConcurrencyLocked()
	f.observability.RecordResult(request, latencyMS, statusCode, err, "")
}

// Persist checkpoints the frontier state.
func (f *AutoscaledFrontier) Persist() error {
	f.mu.Lock()
	defer f.mu.Unlock()
	pending := make([]string, 0, len(f.queue))
	for _, item := range f.queue {
		pending = append(pending, item.request.URL)
	}
	return f.checkpoint.Save(
		f.config.CheckpointID,
		keysFromSet(f.known),
		pending,
		map[string]interface{}{"frontier": f.snapshotLocked()},
		map[string]interface{}{
			"autoscale":               f.config.Autoscale,
			"min_concurrency":         f.config.MinConcurrency,
			"max_concurrency":         f.config.MaxConcurrency,
			"lease_ttl_seconds":       f.config.LeaseTTLSeconds,
			"max_inflight_per_domain": f.config.MaxInflightPerDomain,
		},
		true,
	)
}

// Load restores the frontier from a checkpoint if present.
func (f *AutoscaledFrontier) Load() bool {
	state, err := f.checkpoint.Load(f.config.CheckpointID)
	var snapshot interface{}
	if err == nil && state != nil {
		snapshot = state.Stats["frontier"]
	} else {
		raw, readErr := os.ReadFile(filepath.Join(f.config.CheckpointDir, f.config.CheckpointID+".checkpoint.json"))
		if readErr != nil {
			return false
		}
		var payload struct {
			Stats map[string]interface{} `json:"stats"`
		}
		if unmarshalErr := json.Unmarshal(raw, &payload); unmarshalErr != nil {
			return false
		}
		snapshot = payload.Stats["frontier"]
	}
	if snapshot == nil {
		return false
	}
	raw, marshalErr := json.Marshal(snapshot)
	if marshalErr != nil {
		return false
	}
	var decoded frontierSnapshot
	if err := json.Unmarshal(raw, &decoded); err != nil {
		return false
	}
	f.mu.Lock()
	defer f.mu.Unlock()
	f.restoreLocked(decoded)
	return true
}

// Snapshot returns a serializable frontier snapshot.
func (f *AutoscaledFrontier) Snapshot() map[string]interface{} {
	f.mu.Lock()
	defer f.mu.Unlock()
	return f.snapshotLocked()
}

// ReapExpiredLeases requeues expired leases and returns the number reaped.
func (f *AutoscaledFrontier) ReapExpiredLeases(now time.Time, maxRetries int) int {
	f.mu.Lock()
	defer f.mu.Unlock()
	return f.reapExpiredLeasesLocked(now, maxRetries)
}

type frontierSnapshot struct {
	Pending                []frontierRequest `json:"pending"`
	Known                  []string          `json:"known"`
	DomainInflight         map[string]int    `json:"domain_inflight"`
	RecommendedConcurrency int               `json:"recommended_concurrency"`
	Latencies              []float64         `json:"latencies"`
	Outcomes               []bool            `json:"outcomes"`
	DeadLetters            []frontierRequest `json:"dead_letters"`
}

func (f *AutoscaledFrontier) snapshotLocked() map[string]interface{} {
	pending := make([]frontierRequest, 0, len(f.queue))
	for _, item := range f.queue {
		pending = append(pending, item.request)
	}
	return map[string]interface{}{
		"pending":                 pending,
		"known":                   keysFromSet(f.known),
		"domain_inflight":         f.domainInflight,
		"recommended_concurrency": f.recommendedConcurrency,
		"latencies":               f.latencies,
		"outcomes":                f.outcomes,
		"dead_letters":            f.deadLetters,
	}
}

func (f *AutoscaledFrontier) restoreLocked(snapshot frontierSnapshot) {
	f.queue = make(frontierHeap, 0, len(snapshot.Pending))
	heap.Init(&f.queue)
	f.known = make(map[string]struct{}, len(snapshot.Known))
	for _, fingerprint := range snapshot.Known {
		f.known[fingerprint] = struct{}{}
	}
	f.leases = make(map[string]*FrontierLease)
	f.domainInflight = snapshot.DomainInflight
	if f.domainInflight == nil {
		f.domainInflight = make(map[string]int)
	}
	f.latencies = snapshot.Latencies
	f.outcomes = snapshot.Outcomes
	f.deadLetters = snapshot.DeadLetters
	f.recommendedConcurrency = snapshot.RecommendedConcurrency
	if f.recommendedConcurrency < f.config.MinConcurrency {
		f.recommendedConcurrency = f.config.MinConcurrency
	}
	f.sequence = 0
	for _, request := range snapshot.Pending {
		f.sequence++
		heap.Push(&f.queue, frontierItem{
			priority: request.Priority,
			sequence: f.sequence,
			request:  request,
		})
	}
}

func (f *AutoscaledFrontier) reapExpiredLeasesLocked(now time.Time, maxRetries int) int {
	reaped := 0
	for fingerprint, lease := range f.leases {
		if lease.ExpiresAt.After(now) {
			continue
		}
		reaped++
		delete(f.leases, fingerprint)
		domain := normalizeFrontierDomain(lease.Request.URL)
		if domain != "" && f.domainInflight[domain] > 0 {
			f.domainInflight[domain]--
		}
		retryCount := 0
		if raw, ok := lease.Request.Meta["retry_count"]; ok {
			switch value := raw.(type) {
			case int:
				retryCount = value
			case float64:
				retryCount = int(value)
			}
		}
		if retryCount >= maxRetries {
			f.deadLetters = append(f.deadLetters, serializeFrontierRequest(lease.Request, fingerprint))
			continue
		}
		if lease.Request.Meta == nil {
			lease.Request.Meta = map[string]interface{}{}
		}
		lease.Request.Meta["retry_count"] = retryCount + 1
		f.sequence++
		heap.Push(&f.queue, frontierItem{
			priority: lease.Request.Priority,
			sequence: f.sequence,
			request:  serializeFrontierRequest(lease.Request, fingerprint),
		})
	}
	return reaped
}

func (f *AutoscaledFrontier) adjustConcurrencyLocked() {
	if !f.config.Autoscale {
		return
	}
	avgLatency := 0.0
	for _, item := range f.latencies {
		avgLatency += item
	}
	if len(f.latencies) > 0 {
		avgLatency = avgLatency / float64(len(f.latencies))
	}
	failures := 0
	for _, success := range f.outcomes {
		if !success {
			failures++
		}
	}
	failureRate := 0.0
	if len(f.outcomes) > 0 {
		failureRate = float64(failures) / float64(len(f.outcomes))
	}
	if failureRate > 0.2 || avgLatency > float64(f.config.TargetLatencyMS)*1.4 {
		if f.recommendedConcurrency > f.config.MinConcurrency {
			f.recommendedConcurrency--
		}
		return
	}
	if f.queue.Len() > f.recommendedConcurrency && avgLatency < float64(f.config.TargetLatencyMS) && f.recommendedConcurrency < f.config.MaxConcurrency {
		f.recommendedConcurrency++
	}
}

func serializeFrontierRequest(request *Request, fingerprint string) frontierRequest {
	meta := map[string]interface{}{}
	for key, value := range request.Meta {
		meta[key] = value
	}
	headers := map[string]string{}
	for key, value := range request.Headers {
		headers[key] = value
	}
	return frontierRequest{
		URL:         request.URL,
		Method:      request.Method,
		Headers:     headers,
		Body:        request.Body,
		Meta:        meta,
		Priority:    request.Priority,
		Fingerprint: fingerprint,
	}
}

func deserializeFrontierRequest(payload frontierRequest) *Request {
	return &Request{
		URL:      payload.URL,
		Method:   payload.Method,
		Headers:  payload.Headers,
		Body:     payload.Body,
		Meta:     payload.Meta,
		Priority: payload.Priority,
	}
}

func normalizeFrontierDomain(rawURL string) string {
	if !strings.Contains(rawURL, "://") {
		return ""
	}
	parts := strings.SplitN(strings.SplitN(rawURL, "://", 2)[1], "/", 2)
	host := strings.ToLower(parts[0])
	if host == "" {
		return ""
	}
	return strings.Split(host, ":")[0]
}

func appendWindow(values []float64, next float64, max int) []float64 {
	values = append(values, next)
	if len(values) > max {
		values = values[len(values)-max:]
	}
	return values
}

func appendOutcomeWindow(values []bool, next bool, max int) []bool {
	values = append(values, next)
	if len(values) > max {
		values = values[len(values)-max:]
	}
	return values
}

func keysFromSet(values map[string]struct{}) []string {
	result := make([]string, 0, len(values))
	for key := range values {
		result = append(result, key)
	}
	return result
}

// EnsureFrontierPersisted is a small helper for tests and integration code.
func EnsureFrontierPersisted(frontier *AutoscaledFrontier) error {
	if frontier == nil {
		return errors.New("frontier is nil")
	}
	return frontier.Persist()
}
