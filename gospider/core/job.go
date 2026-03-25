package core

// Runtime identifies the primary execution mode for a job.
type Runtime string

const (
	RuntimeHTTP    Runtime = "http"
	RuntimeBrowser Runtime = "browser"
)
