package features

import (
	"os"
	"strconv"
	"strings"
)

var defaultFeatureState = map[string]bool{
	"ai":          true,
	"browser":     true,
	"distributed": true,
	"media":       true,
	"workflow":    true,
	"crawlee":     true,
}

var profileCatalog = map[string][]string{
	"lite":        {"browser", "workflow"},
	"ai":          {"ai", "browser", "workflow"},
	"distributed": {"browser", "distributed", "workflow", "crawlee"},
	"full":        {"ai", "browser", "distributed", "media", "workflow", "crawlee"},
}

// Enabled resolves a feature gate from environment overrides with safe defaults.
func Enabled(name string) bool {
	normalized := strings.ToLower(strings.TrimSpace(name))
	override := strings.TrimSpace(os.Getenv(envName(normalized)))
	if override == "" {
		return defaultFeatureState[normalized]
	}
	value, err := strconv.ParseBool(override)
	if err != nil {
		return defaultFeatureState[normalized]
	}
	return value
}

// Catalog returns capability metadata for feature-gated builds.
func Catalog() map[string]any {
	features := make(map[string]bool, len(defaultFeatureState))
	for name := range defaultFeatureState {
		features[name] = Enabled(name)
	}
	return map[string]any{
		"default_profile": "full",
		"profiles":        profileCatalog,
		"env_prefix":      "GOSPIDER_FEATURE_",
		"features":        features,
	}
}

func envName(name string) string {
	replaced := strings.NewReplacer("-", "_", ".", "_").Replace(strings.ToUpper(name))
	return "GOSPIDER_FEATURE_" + replaced
}
