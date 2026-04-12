package core

import (
	"encoding/json"
	"net/http"
	"strconv"
	"time"
)

// JobResult is the normalized result envelope emitted by runtimes.
// Legacy fields remain for compatibility while V2 fields carry richer result semantics.
type JobResult struct {
	JobName    string        `json:"job_name"`
	Runtime    Runtime       `json:"runtime"`
	State      TaskState     `json:"state"`
	URL        string        `json:"url"`
	StatusCode int           `json:"status_code,omitempty"`
	Headers    http.Header   `json:"headers,omitempty"`
	Body       []byte        `json:"-"`
	Text       string        `json:"text,omitempty"`
	Duration   time.Duration `json:"-"`
	StartedAt  time.Time     `json:"started_at,omitempty"`
	FinishedAt time.Time     `json:"finished_at,omitempty"`
	Error      string        `json:"error,omitempty"`

	// Legacy compatibility fields.
	Artifacts   []string               `json:"artifacts,omitempty"`
	MediaRecord []MediaArtifact        `json:"media_record,omitempty"`
	Metadata    map[string]interface{} `json:"metadata,omitempty"`

	// V2 result envelope fields.
	ArtifactRefs map[string]ArtifactRef `json:"artifact_refs,omitempty"`
	Extract      map[string]interface{} `json:"extract,omitempty"`
	Metrics      *ResultMetrics         `json:"metrics,omitempty"`
	AntiBot      *AntiBotTrace          `json:"anti_bot,omitempty"`
	Recovery     map[string]interface{} `json:"recovery,omitempty"`
	Warnings     []string               `json:"warnings,omitempty"`
}

// ArtifactRef describes a named artifact emitted by a runtime.
type ArtifactRef struct {
	Kind     string                 `json:"kind,omitempty"`
	URI      string                 `json:"uri,omitempty"`
	Path     string                 `json:"path,omitempty"`
	Size     int64                  `json:"size,omitempty"`
	Metadata map[string]interface{} `json:"metadata,omitempty"`
}

// ResultMetrics captures lightweight transport/runtime metrics.
type ResultMetrics struct {
	LatencyMS int64 `json:"latency_ms,omitempty"`
	BytesIn   int64 `json:"bytes_in,omitempty"`
	BytesOut  int64 `json:"bytes_out,omitempty"`
}

// AntiBotTrace captures anti-bot decisions and outcomes.
type AntiBotTrace struct {
	Challenge          string `json:"challenge,omitempty"`
	ProxyID            string `json:"proxy_id,omitempty"`
	FingerprintProfile string `json:"fingerprint_profile,omitempty"`
	SessionMode        string `json:"session_mode,omitempty"`
	Stealth            bool   `json:"stealth,omitempty"`
}

// MediaArtifact captures a downloaded or discovered media output.
type MediaArtifact struct {
	Type string `json:"type"`
	URL  string `json:"url"`
	Path string `json:"path,omitempty"`
}

// NewJobResult creates a normalized result envelope rooted in a job spec.
func NewJobResult(job JobSpec, state TaskState) *JobResult {
	result := &JobResult{
		JobName:   job.Name,
		Runtime:   job.Runtime,
		State:     state,
		URL:       job.Target.URL,
		StartedAt: time.Now(),
	}
	result.EnsureEnvelope()
	return result
}

// EnsureEnvelope initializes v2-friendly optional fields.
func (r *JobResult) EnsureEnvelope() {
	if r == nil {
		return
	}
	if r.Metadata == nil {
		r.Metadata = make(map[string]interface{})
	}
	if r.ArtifactRefs == nil {
		r.ArtifactRefs = make(map[string]ArtifactRef)
	}
	if r.Extract == nil {
		r.Extract = make(map[string]interface{})
	}
}

// Finalize stamps finished time and derives latency/bytes metrics.
func (r *JobResult) Finalize() {
	if r == nil {
		return
	}
	if r.StartedAt.IsZero() {
		r.StartedAt = time.Now()
	}
	if r.FinishedAt.IsZero() {
		r.FinishedAt = time.Now()
	}
	if r.Duration <= 0 {
		r.Duration = r.FinishedAt.Sub(r.StartedAt)
	}
	if r.Metrics == nil {
		r.Metrics = &ResultMetrics{}
	}
	if r.Metrics.LatencyMS == 0 {
		r.Metrics.LatencyMS = r.Duration.Milliseconds()
	}
	if r.Metrics.BytesIn == 0 && len(r.Body) > 0 {
		r.Metrics.BytesIn = int64(len(r.Body))
	}
}

// SetArtifact records a named artifact and mirrors its location into the legacy artifacts slice.
func (r *JobResult) SetArtifact(name string, artifact ArtifactRef) {
	if r == nil || name == "" {
		return
	}
	r.EnsureEnvelope()
	r.ArtifactRefs[name] = artifact

	location := artifact.URI
	if location == "" {
		location = artifact.Path
	}
	if location == "" {
		return
	}
	for _, existing := range r.Artifacts {
		if existing == location {
			return
		}
	}
	r.Artifacts = append(r.Artifacts, location)
}

// SetExtractField records a structured extraction output.
func (r *JobResult) SetExtractField(field string, value interface{}) {
	if r == nil || field == "" {
		return
	}
	r.EnsureEnvelope()
	r.Extract[field] = value
}

// AddWarning appends a non-fatal warning to the result envelope.
func (r *JobResult) AddWarning(message string) {
	if r == nil || message == "" {
		return
	}
	r.Warnings = append(r.Warnings, message)
}

// SetAntiBotTrace attaches anti-bot trace details.
func (r *JobResult) SetAntiBotTrace(trace AntiBotTrace) {
	if r == nil {
		return
	}
	r.AntiBot = &trace
}

// SetRecoveryTrace attaches a structured recovery envelope.
func (r *JobResult) SetRecoveryTrace(recovery map[string]interface{}) {
	if r == nil || len(recovery) == 0 {
		return
	}
	r.Recovery = cloneStringMap(recovery)
}

// AddMediaArtifact records a media artifact in both legacy and v2 envelope fields.
func (r *JobResult) AddMediaArtifact(artifact MediaArtifact) {
	if r == nil {
		return
	}
	r.MediaRecord = append(r.MediaRecord, artifact)
	name := artifact.Type
	if name == "" {
		name = "media"
	}
	if _, exists := r.ArtifactRefs[name]; exists {
		name = nextArtifactKey(name, r.ArtifactRefs)
	}
	r.SetArtifact(name, ArtifactRef{
		Kind: name,
		URI:  artifact.URL,
		Path: artifact.Path,
	})
}

func nextArtifactKey(base string, existing map[string]ArtifactRef) string {
	for i := 2; ; i++ {
		candidate := base + "_" + strconv.Itoa(i)
		if _, ok := existing[candidate]; !ok {
			return candidate
		}
	}
}

func cloneStringMap(source map[string]interface{}) map[string]interface{} {
	encoded, err := json.Marshal(source)
	if err != nil {
		return source
	}
	var cloned map[string]interface{}
	if err := json.Unmarshal(encoded, &cloned); err != nil {
		return source
	}
	return cloned
}
