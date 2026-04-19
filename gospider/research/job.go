package research

// ResearchJob mirrors the project-oriented research job shape exposed by pyspider.
type ResearchJob struct {
	SeedURLs      []string               `json:"seed_urls"`
	SiteProfile   map[string]interface{} `json:"site_profile,omitempty"`
	ExtractSchema map[string]interface{} `json:"extract_schema,omitempty"`
	ExtractSpecs  []map[string]interface{} `json:"extract_specs,omitempty"`
	Policy        map[string]interface{} `json:"policy,omitempty"`
	Output        map[string]interface{} `json:"output,omitempty"`
}

